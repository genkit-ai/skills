# Working with Agent State (Beta)

> **Beta / preview API.** See [agents.md](agents.md),
> [sessions](agents-sessions.md).

Three layers on the session: **messages**, **custom** (`state_schema`),
**artifacts**. With `state_schema`, `chat.state` / `response.state` /
`chunk.custom` are instances of that model.

## Typed custom state

```python
from pydantic import BaseModel

from genkit import Genkit
from genkit.agent import InMemorySessionStore
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')


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
print(chat.state.name)
```

## Streaming patches (custom agent)

In [`handle_turn`](agents-custom.md), `sess.update_custom(...)` mutates custom
state; clients see live `chunk.custom`:

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
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')


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
        fr = (
            AgentFinishReason.STOP
            if res.finish_reason == FinishReason.STOP
            else AgentFinishReason.UNKNOWN
        )
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
        print(chunk.custom.turns)
final = await turn.response
```

## Client transforms (egress only)

`state_transform` / `chunk_transform` on `define_agent` run on the way **out**.
They do not rewrite what the store persists.

- `state_transform` must return a `SessionState` (never `None` to clear)
- `chunk_transform` may return `None` to drop a chunk
