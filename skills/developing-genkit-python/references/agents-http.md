# Agent HTTP Clients (Beta)

> **Beta / preview API.** See [agents.md](agents.md).

`serve_agent` mounts a FastAPI router; `remote_agent` talks to it from another
process. Flows: `serve_flow` — see [FastAPI](fastapi.md).

## Serve

```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from genkit import Genkit
from genkit.agent import InMemorySessionStore
from genkit_fastapi import serve_agent
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')

agent = ai.define_agent(
    name='weatherAgent',
    system='Weather assistant. Be concise.',
    store=InMemorySessionStore(),
)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
    expose_headers=['X-Genkit-Stream-Id'],
)

# POST /api/weatherAgent (+ /getSnapshot, /abort when store is set)
app.include_router(serve_agent(agent), prefix='/api')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)
```

Path defaults to `/{agent.name}`; override with `base_path=...`.

```bash
genkit start -- uv run server.py
```

## `remote_agent`

```python
from genkit.agent import remote_agent

client = remote_agent(
    url='http://localhost:8080/api/weatherAgent',
    state_management='server',  # or 'client'
)

chat = client.chat()
res = await chat.send('Weather in Tokyo?')
print(res.text, res.snapshot_id)
```

- `'server'` — server has a store; client tracks ids
- `'client'` — no server store; client round-trips state each turn

Same surface as in-process: `chat` / `load_chat` / `send` / `send_stream` /
`resume` / `resume_stream` / `detach`.

## Wire shape

POST body roughly `{ "data": { /* AgentInput */ }, "init": { /* AgentInit */ } }`.
`Accept: text/event-stream` for streaming (`data: {...}` chunks, then
`result`). Companions: `POST {url}/getSnapshot`, `POST {url}/abort`.

Failed turns → `AgentError` (`message`, `status`, `details`, optional
`snapshot_id` / `state`).
