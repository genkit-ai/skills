# Agents (Beta)

> **Beta / preview API.** Agents landed recently in Genkit Python. Public types
> live under `genkit.agent`. Import paths and signatures may still change.
>
> **Requires a Genkit Python build that includes agents.** Stable PyPI `genkit`
> 0.8.x does **not** yet export `define_agent`. Install from the agents branch /
> local checkout your team points you at (or a newer release once published).

An **agent** is a persistent, multi-turn conversation primitive built on prompts
+ tools. Compared to a bare `ai.generate` loop, an agent adds:

- **Sessions**: multi-turn history tracked as immutable **snapshots**.
- **State**: typed session state (messages + custom data + artifacts).
- **Interrupts**: human-in-the-loop pause/resume.
- **Branching**: fork a conversation from any snapshot.
- **Detaching**: run a turn in the background and poll for the result.

Progressive disclosure — read the file for the level you need:

- This file: defining an agent, chatting, streaming, and **client-managed state** (no store).
- [Sessions & persistence](agents-sessions.md): `SessionStore`, `InMemorySessionStore`, `FileSessionStore`, `FirestoreSessionStore`.
- [Human-in-the-loop / interrupts](agents-human-in-the-loop.md): pausing for approval/input and resuming.
- [Branching](agents-branching.md): forking a conversation from a snapshot.
- [Background agents](agents-background.md): detaching long-running turns and polling.
- [Working with state](agents-state.md): typed custom session state streamed to the client.
- [Artifacts](agents-artifacts.md): producing/reading named deliverables.
- [Advanced custom agents](agents-custom.md): `define_custom_agent` for full turn control.
- [HTTP clients](agents-http.md): `remote_agent` / `HttpAgentTransport`.

## Setup

```python
from genkit import Genkit
from genkit_google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-flash-latest',
)
```

## Define an agent

`ai.define_agent` combines prompt + tool config + (optional) session store into a
single registered action.

```python
from pydantic import BaseModel

from genkit import Genkit
from genkit_google_genai import GoogleAI
from genkit.agent import InMemorySessionStore

ai = Genkit(plugins=[GoogleAI()])


class WeatherInput(BaseModel):
    location: str


class WeatherOutput(BaseModel):
    weather: str
    temperature: str


@ai.tool(name='getWeather', description='Get weather for a city.')
async def get_weather(input: WeatherInput) -> WeatherOutput:
    return WeatherOutput(weather='Sunny', temperature='21°C')


agent = ai.define_agent(
    name='weatherAgent',
    model='googleai/gemini-flash-latest',
    system='Weather assistant. Use getWeather for weather questions.',
    tools=[get_weather],
    # store is optional. Omit it for client-managed state (see below).
    store=InMemorySessionStore(),
)
```

Common `define_agent` options:

- `name` (required): action name.
- `model`: model id (e.g. `googleai/gemini-flash-latest`).
- `system`: system prompt (`str` or list of parts).
- `tools`: tools available to the agent.
- `use`: middleware instances (e.g. `ToolApproval`, `Artifacts`, `Filesystem`).
- `store`: a `SessionStore` for server-side persistence. See [sessions](agents-sessions.md).
- `state_schema`: a Pydantic model describing custom session state.
- `max_turns`, `config`, `description`, `metadata`, `state_transform`, `chunk_transform`.

For a registered Dotprompt, use `ai.define_prompt_agent(name=...)` with the same
prompt name. For full turn control, use [`define_custom_agent`](agents-custom.md).

## Agents and middleware go hand in hand

Most agent capabilities — artifacts, filesystem access, skill loading, tool
approval, retries — are middleware you pass via `use=[...]`. Register the
middleware plugin once:

```python
from genkit_middleware import Middleware, ToolApproval, Filesystem, Skills, Retry
from genkit.agent import FileSessionStore

ai = Genkit(plugins=[GoogleAI(), Middleware()])

coding_agent = ai.define_agent(
    name='codingAgent',
    model='googleai/gemini-flash-latest',
    system='Expert coding assistant in a sandboxed workspace.',
    use=[
        # Empty allowed_tools ⇒ every tool needs approval; list names to auto-approve.
        ToolApproval(allowed_tools=['list_files', 'read_file', 'use_skill']),
        Filesystem(root_dir='./workspace', allow_write_access=True),
        Skills(skill_paths=['./skills']),
        Retry(),
    ],
    store=FileSessionStore('./.snapshots'),  # needed for durable approval/resume
    max_turns=30,
)
```

## Chat with an agent

`agent.chat()` opens a conversation. One `chat` carries state forward across
turns. Prefer the **Action-style** split (same idea as `ai.generate` /
`ai.generate_stream` and `Action.run` / `Action.stream`):

| Method | Returns | When to use |
| --- | --- | --- |
| `await chat.send(...)` | `AgentResponse` | Primary path — you only need the final result |
| `chat.send_stream(...)` | `AgentTurn` (`.stream` / `.response`) | You want incremental chunks |
| `await chat.resume(...)` | `AgentResponse` | Continue after an interrupt (non-streaming) |
| `chat.resume_stream(...)` | `AgentTurn` | Continue after an interrupt (streaming) |

```python
chat = agent.chat()

# Non-streaming (primary) — prefer this when you don't need chunks:
res = await chat.send('Weather in Tokyo?')
print(res.text)
print(res.snapshot_id)  # immutable checkpoint id (None if no store)

# Streaming — same turn, with a live chunk view:
turn = chat.send_stream('What about Paris?')
async for chunk in turn.stream:
    if chunk.text:
        print(chunk.accumulated_text, end='\r', flush=True)
final = await turn.response
# or: final = await turn
```

### Streaming semantics (important)

- **You do not have to drain chunks.** `await turn.response` (or `await turn`)
  completes whether or not you read `.stream`. Custom-state patches and
  message stitching still apply — the client pumps the transport internally.
- **Chunks are per-turn.** Each `send_stream` / `resume_stream` has its own
  buffer. Unread chunks from turn N do **not** show up on turn N+1's stream.
  Dropping the turn handle (or draining it later) is how unread chunks go away.
- **Don't overlap sends on one `chat`.** Turns are single-flight; overlapping
  `send` / `send_stream` on the same session can corrupt local history.

Follow-up turns on the same `chat` remember prior context automatically.

## Resume a stored conversation

With a store, hold onto `snapshot_id` and rehydrate later:

```python
checkpoint = res.snapshot_id
resumed = await agent.load_chat(snapshot_id=checkpoint)
await resumed.send('What city did I ask about?')
```

You can also open `agent.chat(snapshot_id=...)` when you already know the id.

## Client-managed state (no server store)

If the agent has **no `store`**, the server is stateless. `session_id` /
`snapshot_id` stay `None`. You own messages + custom state + artifacts and
hand them back on the next chat:

```python
agent = ai.define_agent(
    name='echoNoStore',
    model='googleai/gemini-flash-latest',
    system='Echo assistant. Answer briefly and remember context.',
)

chat = agent.chat()
await chat.send('My name is Ada. Remember it.')

messages, state, artifacts = chat.messages, chat.state, chat.artifacts
resumed = agent.chat(messages=messages, state=state, artifacts=artifacts)
await resumed.send('What is my name? One word.')
```

Use client-managed state when you don't want server-side storage. Use a
[session store](agents-sessions.md) when the server should own history, or when
you need branching or background execution. ([Interrupts](agents-human-in-the-loop.md)
work either way.)

## Entrypoint

For apps started with `genkit start`, use `ai.run_main(main())`:

```python
async def main() -> None:
    chat = agent.chat()
    print((await chat.send('hi')).text)

if __name__ == '__main__':
    ai.run_main(main())
```
