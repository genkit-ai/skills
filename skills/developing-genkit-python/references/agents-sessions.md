# Agent Sessions & Persistence (Beta)

> **Beta / preview API.** Stores from `genkit.agent`:
> `InMemorySessionStore`, `FileSessionStore`. See [agents.md](agents.md).

With a `store`, the server owns history. Each turn writes an immutable
**snapshot**; that chain is what branching and [detach](agents-background.md)
need. Interrupts work with or without a store
([HITL](agents-human-in-the-loop.md)).

## Pick a store

```python
from genkit.agent import InMemorySessionStore, FileSessionStore

mem_store = InMemorySessionStore()  # lost on restart
file_store = FileSessionStore('./.snapshots')  # one JSON file per snapshot

# Optional: prune long chains; reject ambiguous session_id after forks.
pruning = FileSessionStore(
    './.snapshots',
    max_persisted_chain_length=3,
    reject_ambiguous_session=True,
)
```

```python
from genkit import Genkit
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')

agent = ai.define_agent(
    name='logbookAgent',
    model='googleai/gemini-flash-latest',
    system='You are a personal logbook assistant.',
    store=file_store,
)

chat = agent.chat()
res1 = await chat.send('Log this: I started studying Genkit today.')
res2 = await chat.send('What did I study today?')
print(res1.snapshot_id, res2.snapshot_id)

resumed = await agent.load_chat(snapshot_id=res2.snapshot_id)
await resumed.send('Add another note.')
```

## Typed session state

Pass a Pydantic `state_schema`; seed with `agent.chat(state=...)`. Details and
streaming patches: [state](agents-state.md).

## What a store unlocks

Without: multi-turn on one `chat`, interrupts / `ToolApproval`.

With: durable `snapshot_id` / `session_id`, `load_chat`, branching,
`chat.detach` / background tasks, server-side `chat.abort` / `task.abort`.
