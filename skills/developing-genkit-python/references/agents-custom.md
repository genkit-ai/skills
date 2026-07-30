# Advanced Custom Agents — `define_custom_agent` (Beta)

> **Beta / preview API.** See [agents.md](agents.md) and
> [agent state](agents-state.md).

`define_agent` runs a single prompt + tool loop. When you need **full control of
the turn** — multiple model calls, custom logic between them, manual
message/state management, or custom progress streaming — use
`ai.define_custom_agent`.

## When to use it

Reach for `define_custom_agent` when a turn needs to:

- make **multiple model calls** with your own orchestration between them;
- run **multi-step workflows** (decompose → research → synthesize);
- **manually manage** messages and custom state;
- **stream custom status** updates to the client mid-turn.

Otherwise prefer `define_agent` (simpler; custom state still works via
`state_schema`).

## Signature

```python
async def fn(sess: SessionRunner, ctx: ActionRunContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, turn_ctx: TurnContext) -> TurnResult | None:
        ...
        return TurnResult(finish_reason=AgentFinishReason.STOP)

    await sess.run(handle_turn)
    return await sess.result()

agent = ai.define_custom_agent(
    name='customCoder',
    fn=fn,
    store=store,                 # optional
    state_schema=MyState,        # optional
)
```

Key pieces:

- `sess.run(handle_turn)` — runs the turn loop; adds the incoming user message
  before calling your handler so `get_messages()` includes it.
- `sess.get_messages` / `add_messages` / `set_messages`
- `sess.get_custom` / `update_custom`
- `sess.get_artifacts` / `add_artifacts`
- `ctx.send_chunk(AgentStreamChunk(...))` — stream to the client
- `turn_ctx.snapshot_id` — reserved when a store is present (useful as an
  external workspace key for the turn)

## Example: streaming custom agent

```python
from genkit import ActionRunContext, FinishReason, Genkit, Message
from genkit.agent import (
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


async def custom_coder_fn(sess: SessionRunner, ctx: ActionRunContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, _: TurnContext) -> TurnResult | None:
        history = await sess.get_messages()
        messages = [Message(m) for m in history] if history else None

        stream_resp = ai.generate_stream(
            model='googleai/gemini-flash-latest',
            system='Concise coding assistant.',
            messages=messages,
        )
        async for chunk in stream_resp.stream:
            ctx.send_chunk(AgentStreamChunk(model_chunk=chunk))

        res = await stream_resp.response
        if res.message:
            await sess.add_messages(res.message)

        fr = (
            AgentFinishReason.STOP
            if res.finish_reason == FinishReason.STOP
            else AgentFinishReason.UNKNOWN
        )
        return TurnResult(finish_reason=fr)

    await sess.run(handle_turn)
    return await sess.result()


agent = ai.define_custom_agent(name='customCoder', fn=custom_coder_fn, store=store)
```

From the caller's side, `agent.chat().send(...)` works the same as a prompt
agent — sessions, streaming, and the store are unchanged.
