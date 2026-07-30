# Background Agents / Detaching (Beta)

> **Beta / preview API.** Needs a [session store](agents-sessions.md).
> See [agents.md](agents.md).

`chat.detach(message)` returns a `DetachedTask` with a `snapshot_id`
immediately. The server keeps working and updates the snapshot to a terminal
status (`completed` / `failed` / `aborted` / `expired`). The reply does **not**
land on the original `chat` — `load_chat` when you need messages.

```python
from genkit.agent import InMemorySessionStore, SnapshotStatus

agent = ai.define_agent(
    name='backgroundAgent',
    model='googleai/gemini-flash-latest',
    system='Senior research analyst. Produce a comprehensive markdown report.',
    store=InMemorySessionStore(),  # required
)

chat = agent.chat()
task = await chat.detach('Write a report on renewable energy trends')
print(task.snapshot_id)

snapshot = await task.wait(interval=2.0)  # or: async for snap in task.poll(...)
print(snapshot.status)

await task.abort()  # server cancel

done = await agent.load_chat(snapshot_id=task.snapshot_id)
print(done.messages)
```

## Abort: client vs server

- `turn.abort()` — stop listening; server turn may still finish and persist
- `asyncio.timeout` around stream/response — same, then re-raises `TimeoutError`
- `chat.abort()` / `task.abort()` — server cancel (needs store); snapshot is
  `ABORTED`, **not** a resume point

After server abort, reload the last good leaf, not the aborted snapshot.
