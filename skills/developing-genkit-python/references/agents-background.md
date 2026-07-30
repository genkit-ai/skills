# Background Agents / Detaching (Beta)

> **Beta / preview API.** Detaching requires a
> [session store](agents-sessions.md) so the server can persist the result.
> See [agents.md](agents.md).

Detaching runs a turn in the background: the server saves a `pending` snapshot
and returns a `snapshot_id` **immediately**, keeps processing, then updates the
snapshot to a terminal status (`completed` / `failed` / `aborted` / `expired`).
The client polls for completion and can abort.

## Define the agent (store required)

```python
from genkit.agent import InMemorySessionStore

agent = ai.define_agent(
    name='backgroundAgent',
    model='googleai/gemini-flash-latest',
    system='Senior research analyst. Produce a comprehensive markdown report.',
    store=InMemorySessionStore(),  # REQUIRED for detach
)
```

## Detach + wait / poll

`chat.detach(message)` returns a `DetachedTask`. The detached turn's reply does
**not** stream back into the original `chat` object — reload from the store when
you need the messages.

```python
from genkit.agent import SnapshotStatus

chat = agent.chat()
task = await chat.detach('Write a report on renewable energy trends')
print(task.snapshot_id)  # available immediately

# Block until terminal:
snapshot = await task.wait(interval=2.0)
print(snapshot.status)  # completed | failed | aborted | expired

# Or poll for a live UI:
async for snap in task.poll(interval=2.0):
    if snap.status == SnapshotStatus.COMPLETED:
        break
    if snap.status in (SnapshotStatus.FAILED, SnapshotStatus.ABORTED, SnapshotStatus.EXPIRED):
        break

# Cancel server-side work:
await task.abort()
```

Reload results into a chat when you need the conversation view:

```python
done = await agent.load_chat(snapshot_id=task.snapshot_id)
print(done.messages)
```

## Abort: client vs server (critical)

| Call | Effect |
|---|---|
| `turn.abort()` | **Client detach** — stop listening; the server turn keeps running and may still persist. |
| `asyncio.timeout` around stream/response | Same as `turn.abort()`, then re-raises `TimeoutError`. |
| `chat.abort()` / `task.abort()` | **Server cancel** — needs a store; fires abort signal; snapshot settles `ABORTED` and is **not** a resume point. |

After a server abort, reload the session leaf (last good snapshot), not the
aborted one. After a successful detach, reload via `load_chat` to see the reply.

## Status values

- `pending` — still processing.
- `completed` — finished successfully.
- `failed` — error during processing.
- `aborted` — cancelled via `abort()`.
- `expired` — worker stopped responding (e.g. server restart); terminal.
