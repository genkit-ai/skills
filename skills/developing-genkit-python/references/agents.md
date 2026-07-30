# Agents (Beta)

> **Beta / preview API.** Types under `genkit.agent`.

An **agent** is a multi-turn conversation with history, optional typed state,
interrupts, branching, and background turns — on top of prompts + tools.

Deeper topics: [sessions](agents-sessions.md),
[HITL](agents-human-in-the-loop.md), [branching](agents-branching.md),
[background](agents-background.md), [state](agents-state.md),
[artifacts](agents-artifacts.md), [custom agents](agents-custom.md),
[HTTP](agents-http.md).

## Define an agent

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
    store=InMemorySessionStore(),  # omit for client-managed state (below)
)
```

Useful options: `use` (middleware), `state_schema`, `max_turns`, `config`,
`state_transform`, `chunk_transform`. Dotprompt → `ai.define_prompt_agent(name=...)`.
Full turn control → [`define_custom_agent`](agents-custom.md).

## Middleware

Register `Middleware()` once, pass instances via `use=[...]`:

```python
from genkit_middleware import Middleware, ToolApproval, Filesystem, Skills, Retry
from genkit.agent import FileSessionStore

ai = Genkit(plugins=[GoogleAI(), Middleware()])

coding_agent = ai.define_agent(
    name='codingAgent',
    model='googleai/gemini-flash-latest',
    system='Expert coding assistant in a sandboxed workspace.',
    use=[
        # Empty allowed_tools ⇒ every tool needs approval.
        ToolApproval(allowed_tools=['list_files', 'read_file', 'use_skill']),
        Filesystem(root_dir='./workspace', allow_write_access=True),
        Skills(skill_paths=['./skills']),
        Retry(),
    ],
    store=FileSessionStore('./.snapshots'),
    max_turns=30,
)
```

## Chat

- `await chat.send(...)` → `AgentResponse`
- `chat.send_stream(...)` → `AgentTurn` (`.stream` / `.response`)
- `await chat.resume(...)` / `chat.resume_stream(...)` — after an interrupt

```python
chat = agent.chat()

res = await chat.send('Weather in Tokyo?')
print(res.text, res.snapshot_id)  # snapshot_id is None without a store

turn = chat.send_stream('What about Paris?')
async for chunk in turn.stream:
    if chunk.text:
        print(chunk.accumulated_text, end='\r', flush=True)
final = await turn.response  # or: await turn
```

You do not need to drain `.stream` for the turn to finish or for state
patches to apply. Each stream has its own buffer. Don't overlap sends on one
`chat`.

With a store, rehydrate later:

```python
resumed = await agent.load_chat(snapshot_id=res.snapshot_id)
await resumed.send('What city did I ask about?')
```

`agent.chat(snapshot_id=...)` only attaches a resume handle — it does **not**
load history. Use `load_chat` when you need messages / state / artifacts.

## Client-managed state (no store)

No `store` ⇒ server is stateless; `session_id` / `snapshot_id` stay `None`.
Round-trip messages / state / artifacts yourself:

```python
agent = ai.define_agent(
    name='echoNoStore',
    model='googleai/gemini-flash-latest',
    system='Echo assistant. Answer briefly and remember context.',
)

chat = agent.chat()
await chat.send('My name is Ada. Remember it.')

resumed = agent.chat(
    messages=chat.messages, state=chat.state, artifacts=chat.artifacts
)
await resumed.send('What is my name? One word.')
```

Use a [store](agents-sessions.md) when the server should own history, or when
you need branching / detach. [Interrupts](agents-human-in-the-loop.md) work
either way.

For `genkit start` apps, entrypoint is `ai.run_main(main())`.
