# Agent HTTP Clients (Beta)

> **Beta / preview API.** See [agents.md](agents.md).

Python exposes a client-side HTTP transport so one process can talk to an agent
served elsewhere. There is **not** yet a dedicated FastAPI helper that mounts an
agent the way `genkit_fastapi_handler` mounts flows — server exposure is typically
via the Genkit reflection / action HTTP surface or a custom route that streams
the agent action. The **client** API below is ready to use.

## `remote_agent`

```python
from genkit.agent import remote_agent

client = remote_agent(
    url='https://host/api/myAgent',
    state_management='server',  # or 'client' — required
    # Optional overrides (default to `{url}/getSnapshot` and `{url}/abort`):
    # get_snapshot_url='...',
    # abort_url='...',
    # headers={'Authorization': 'Bearer ...'},  # or a sync/async callable
)

chat = client.chat()
turn = chat.send_stream('Weather in Tokyo?')
async for chunk in turn.stream:
    if chunk.text:
        print(chunk.text, end='', flush=True)
res = await turn.response
print(res.snapshot_id, chat.snapshot_id)
```

`state_management`:

- `'server'` — server has a store; client tracks `snapshot_id` / `session_id`.
- `'client'` — no server store; client round-trips the state blob each turn.

The returned client has the same `chat` / `load_chat` / `send` / `resume` /
`detach` surface as an in-process `Agent`.

## Wire shape (for custom servers)

Turns are POST requests with JSON body roughly:

```json
{ "data": { /* AgentInput */ }, "init": { /* AgentInit */ } }
```

and `Accept: text/event-stream`. Stream events are `data: {...}` lines (chunks,
then a final `result`). Companion endpoints:

- `POST {url}/getSnapshot` — lookup by `snapshotId` or `sessionId`
- `POST {url}/abort` — abort a running snapshot

## Errors

Transport and failed turns surface as `AgentError` (from `genkit.agent`) with
`message`, `status`, `details`, and optionally `snapshot_id` / `state`.
