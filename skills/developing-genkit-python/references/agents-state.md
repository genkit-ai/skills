# Working with Agent State (Beta)

> **Beta / preview API.** See [agents.md](agents.md) and
> [sessions](agents-sessions.md).

Session state has three layers:

- **messages** — the conversation transcript.
- **custom** — your typed app state (`state_schema`).
- **artifacts** — named deliverables (see [artifacts](agents-artifacts.md)).

With `state_schema`, `chat.state`, `response.state`, and streamed `chunk.custom`
are instances of that Pydantic model (attribute access, not dict keys).

## Typed custom state on a prompt agent

```python
from pydantic import BaseModel

from genkit.agent import InMemorySessionStore


class Profile(BaseModel):
    name: str
    tier: str = 'free'


agent = ai.define_agent(
    name='profileAgent',
    model='googleai/gemini-flash-latest',
    system='Greet the user by name.',
    store=InMemorySessionStore(),
    state_schema=Profile,
)

chat = agent.chat(state=Profile(name='Ada', tier='pro'))
res = await chat.send('Hello')
print(chat.state.name)  # typed
```

## Streaming custom patches from a custom agent

Inside `define_custom_agent`, call `sess.update_custom(...)` to mutate custom
state. Clients see live `chunk.custom` updates:

```python
from pydantic import BaseModel

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


class Progress(BaseModel):
    turns: int = 0


async def stateful_fn(sess: SessionRunner, ctx: ActionRunContext) -> AgentResult:
    async def handle_turn(inp: AgentInput, _: TurnContext) -> TurnResult | None:
        await sess.update_custom(lambda c: {'turns': (c or {}).get('turns', 0) + 1})

        history = await sess.get_messages()
        messages = [Message(m) for m in history] if history else None
        stream_resp = ai.generate_stream(
            model='googleai/gemini-flash-latest',
            system='Acknowledge progress in one sentence.',
            messages=messages,
        )
        async for chunk in stream_resp.stream:
            ctx.send_chunk(AgentStreamChunk(model_chunk=chunk))

        res = await stream_resp.response
        if res.message:
            await sess.add_messages(res.message)
        fr = AgentFinishReason.STOP if res.finish_reason == FinishReason.STOP else AgentFinishReason.UNKNOWN
        return TurnResult(finish_reason=fr)

    await sess.run(handle_turn)
    return await sess.result()


agent = ai.define_custom_agent(
    name='statefulAgent',
    fn=stateful_fn,
    store=InMemorySessionStore(),
    state_schema=Progress,
)

chat = agent.chat()
turn = chat.send_stream('Go')
async for chunk in turn.stream:
    if chunk.custom is not None:
        print(chunk.custom.turns)  # Progress, not a dict
final = await turn.response
```

## Client transforms (egress only)

`state_transform` / `chunk_transform` on `define_agent` run on the way **out** to
the client. They do not rewrite what the store persists.

- `state_transform` must return a `SessionState` (never `None` to clear).
- `chunk_transform` may return `None` to drop a chunk (e.g. redact secrets).
