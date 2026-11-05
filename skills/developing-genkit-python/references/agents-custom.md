# Custom Agents — `define_custom_agent` (Experimental)

> See [agents.md](agents.md).

`ai.define_agent` runs a built-in model + tool loop. When you need custom multi-step orchestration, subagent delegation, custom streaming, or manual control over messages, custom state, and artifacts, register a custom turn loop with `ai.define_custom_agent`. Callers still talk to the agent through `chat.send(...)`, `chat.send_stream(...)`, `chat.detach(...)`, and `serve_agent(...)`.

## Anatomy

Register one async `fn(sess: SessionRunner, ctx: AgentContext) -> AgentResult`. Inside `fn`, define `handle_turn(inp: AgentInput, turn_ctx: TurnContext) -> TurnResult | None`, pass it to `await sess.run(handle_turn)`, and return `await sess.result()`:

```python
from genkit.exp.agent import (
    AgentContext,
    AgentFinishReason,
    AgentInput,
    AgentResult,
    SessionRunner,
    TurnContext,
    TurnResult,
)


async def custom_fn(sess: SessionRunner, ctx: AgentContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, turn_ctx: TurnContext) -> TurnResult | None:
        # 1. inp.message is already appended to sess.get_messages() before handle_turn runs
        # 2. Emit live chunks with ctx.send_chunk(AgentStreamChunk(...))
        # 3. Persist assistant/tool messages via sess.add_messages([...]) or sess.set_messages([...])
        return TurnResult(finish_reason=AgentFinishReason.STOP)

    await sess.run(handle_turn)
    return await sess.result()
```

Runtime mechanics:

- **Automatic user message append**: Before calling `handle_turn`, `sess.run` appends `inp.message` (`AgentInput` carries `message`, `resume`, and `detach`) to session history. `await sess.get_messages()` already returns `list[Message]` including the current user prompt — do not wrap items in `Message(m)`.
- **`TurnContext` (`turn_ctx`)**: Exposes `snapshot_id` (pre-reserved at turn start when a `store` is configured, `None` otherwise), `parent_snapshot_id`, and `turn_index` (0-based). Pre-reserving `snapshot_id` lets you name external worktrees or scratch directories after the snapshot before the turn commits.
- **`SessionRunner` (`sess`) helpers**: `get_messages()` / `add_messages([...])` / `set_messages([...])`, `get_custom()` / `update_custom(sync_fn)`, and `get_artifacts()` / `add_artifacts([...])`. Both `add_messages` and `add_artifacts` take a `list`.
- **Turn completion and failures**: `TurnResult` accepts `(finish_reason=..., error=...)` — it does **not** take `messages=`. Raising an exception inside `handle_turn` ends the turn gracefully with `finish_reason=AgentFinishReason.FAILED` and populates `res.error` on the caller's `AgentResponse`.

## Streaming custom agent example

```python
from genkit_google_genai import GoogleAI

from genkit import FinishReason
from genkit.exp import Genkit
from genkit.exp.agent import (
    AgentContext,
    AgentFinishReason,
    AgentInput,
    AgentResult,
    AgentStreamChunk,
    InMemorySessionStore,
    SessionRunner,
    TurnContext,
    TurnResult,
)

ai = Genkit(plugins=[GoogleAI()])
store = InMemorySessionStore()


async def custom_coder_fn(sess: SessionRunner, ctx: AgentContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, turn_ctx: TurnContext) -> TurnResult | None:
        # 1. Read history (already includes inp.message as list[Message])
        history = await sess.get_messages()

        # 2. Stream model chunks out through AgentContext
        stream_resp = ai.generate_stream(
            model=GoogleAI.gemini('gemini-flash-latest'),
            system='Concise Python systems assistant.',
            messages=history or None,
        )
        async for chunk in stream_resp.stream:
            ctx.send_chunk(AgentStreamChunk(model_chunk=chunk))

        # 3. Persist the assistant reply so subsequent turns see it
        res = await stream_resp.response
        if res.message:
            await sess.add_messages([res.message])

        fr = (
            AgentFinishReason.STOP
            if res.finish_reason == FinishReason.STOP
            else AgentFinishReason.UNKNOWN
        )
        return TurnResult(finish_reason=fr)

    await sess.run(handle_turn)
    return await sess.result()


agent = ai.define_custom_agent(name='customCoder', fn=custom_coder_fn, store=store)


async def main() -> None:
    chat = agent.chat()
    res = await chat.send('Show a dict comprehension that inverts keys and values.')
    print(res.text)


if __name__ == '__main__':
    ai.run_main(main())
```

## Non-streaming `handle_turn` with tools

When `ai.generate(..., tools=[...])` runs a multi-step tool loop inside `handle_turn`, `res.messages` contains the full conversation transcript (prior history + intermediate tool requests/responses + final model reply, plus a `Role.SYSTEM` message when `system=` was passed). Strip `Role.SYSTEM` and save the updated transcript with `await sess.set_messages(...)`:

```python
from datetime import datetime, timezone

from genkit import Role
from genkit.exp.agent import (
    AgentContext,
    AgentFinishReason,
    AgentInput,
    AgentResult,
    SessionRunner,
    TurnContext,
    TurnResult,
)


@ai.tool(name='utcNow', description='Return the current UTC timestamp.')
async def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def ops_agent_fn(sess: SessionRunner, ctx: AgentContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, turn_ctx: TurnContext) -> TurnResult | None:
        history = await sess.get_messages()
        res = await ai.generate(
            model=GoogleAI.gemini('gemini-flash-latest'),
            system='Ops assistant. Use utcNow when asked for the current time.',
            messages=history,
            tools=[utc_now],
        )
        # Persist tool-request, tool-response, and final model messages without duplicating system
        await sess.set_messages([m for m in res.messages if m.role != Role.SYSTEM])
        return TurnResult(finish_reason=AgentFinishReason.STOP)

    await sess.run(handle_turn)
    return await sess.result()
```

Related guides: [state](agents-state.md) · [artifacts](agents-artifacts.md) · [tools](agents.md#tools-progress-chunks-and-multipart-responses)
