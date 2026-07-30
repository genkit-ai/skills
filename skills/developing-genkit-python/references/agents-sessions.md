# Agent Sessions & Persistence (Beta)

> **Beta / preview API.** Session stores are imported from `genkit.agent`
> (`InMemorySessionStore`, `FileSessionStore`) and `genkit_google_cloud`
> (`FirestoreSessionStore`). See [agents.md](agents.md) for the basics first.

When an agent has a `store`, the **server** owns the session history. Each turn
produces an immutable **snapshot**; the snapshot chain is what carries
conversation state forward. A store also enables [branching](agents-branching.md)
and [background execution](agents-background.md). (Interrupts work with or without
a store — see [human-in-the-loop](agents-human-in-the-loop.md).)

## Pick a store

```python
from genkit.agent import InMemorySessionStore, FileSessionStore

# In-memory: great for tests/dev; lost on process restart.
mem_store = InMemorySessionStore()

# File-backed: one JSON file per snapshot under the directory.
file_store = FileSessionStore('./.snapshots')

# Optional: prune long chains; reject ambiguous session_id lookups after forks.
pruning = FileSessionStore(
    './.snapshots',
    max_persisted_chain_length=3,
    reject_ambiguous_session=True,
)
```

Attach it to the agent:

```python
agent = ai.define_agent(
    name='logbookAgent',
    model='googleai/gemini-flash-latest',
    system='You are a personal logbook assistant.',
    store=file_store,
)
```

A single `chat` persists to the store and threads the snapshot forward
automatically:

```python
chat = agent.chat()
res1 = await chat.send('Log this: I started studying Genkit today.')
res2 = await chat.send('What did I study today?')  # remembers turn 1
print(res1.snapshot_id, res2.snapshot_id)
```

Resume a prior conversation by snapshot id:

```python
resumed = await agent.load_chat(snapshot_id=res2.snapshot_id)
await resumed.send('Add another note.')
```

## Typed session state

Use `state_schema` (a Pydantic model) to attach typed custom state. Loaded
snapshots validate against it; `chat.state` and streamed `chunk.custom` become
instances of that model.

```python
from pydantic import BaseModel

from genkit.agent import InMemorySessionStore


class Profile(BaseModel):
    name: str
    tier: str = 'free'


agent = ai.define_agent(
    name='profileAgent',
    model='googleai/gemini-flash-latest',
    system='Greet the user by name and tailor answers to their tier.',
    store=InMemorySessionStore(),
    state_schema=Profile,
)

# Seed custom state when opening the chat.
chat = agent.chat(state=Profile(name='Ada', tier='pro'))
```

See [Working with state](agents-state.md) for streaming custom patches from a
custom agent.

## Firestore session store (scalable, Beta)

For production, `FirestoreSessionStore` (from `genkit_google_cloud`) persists
each turn as an incremental diff anchored to periodic checkpoints.

```python
from genkit_google_cloud import FirestoreSessionStore

agent = ai.define_agent(
    name='myAgent',
    model='googleai/gemini-flash-latest',
    system='You are a helpful assistant.',
    # Defaults to AsyncClient() using Application Default Credentials.
    store=FirestoreSessionStore(),
)
```

Useful options:

- `client` / `sync_client`: explicit Firestore clients.
- `collection`: snapshot collection (default `"genkit-sessions"`).
- `checkpoint_interval`: turns between full-state checkpoints (default `25`).
- `shard_size`: max bytes per shard/diff document.
- `reject_ambiguous_session`: raise on ambiguous `session_id` after a fork.

Install: `uv add genkit-plugin-google-cloud` (import remains `genkit_google_cloud`).

## What a store unlocks

| Capability | Needs store? |
|---|---|
| Multi-turn on one `chat` object | No |
| Durable `snapshot_id` / `session_id` | **Yes** |
| `load_chat(snapshot_id=...)` | **Yes** |
| Branching / time-travel | **Yes** |
| `chat.detach(...)` / background tasks | **Yes** |
| Server-side `chat.abort()` / `task.abort()` | **Yes** |
| Interrupts / ToolApproval | No (works either way) |
