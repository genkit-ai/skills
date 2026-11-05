# Agent HTTP Serving & Remote Client (Experimental)

> See [agents.md](agents.md) · [FastAPI](fastapi.md).

Mount an agent on FastAPI with `serve_agent` from `genkit_fastapi.exp`, and connect from another Python service or CLI with `remote_agent` from `genkit.exp.agent`. Stable flows use `serve_flow` from `genkit_fastapi` ([FastAPI](fastapi.md)).

## Serve an agent with FastAPI

`serve_agent(agent)` mounts `POST /{agent.name}` (for one-shot JSON, `?stream=true` / `Accept: text/event-stream` SSE streaming, and detached runs). When `agent.store` is configured, it also mounts `POST /{agent.name}/getSnapshot` (returning `404` when missing) and `POST /{agent.name}/abort`. Callers can also pass `?session_id=` or `?thread_id=` as query parameters.

```python
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from genkit_fastapi.exp import serve_agent
from genkit_google_genai import GoogleAI

from genkit.exp import Genkit
from genkit.exp.agent import InMemorySessionStore

ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini('gemini-flash-latest'))

agent = ai.define_agent(
    name='weatherAgent',
    system='Weather assistant. Keep answers under two sentences.',
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

# Mounts /api/weatherAgent, /api/weatherAgent/getSnapshot, and /api/weatherAgent/abort
app.include_router(serve_agent(agent), prefix='/api')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)
```

Override the route path with `serve_agent(agent, base_path='/chat')`. Run alongside the Developer UI with:

```bash
genkit start -- uv run server.py
```

## Connect with `remote_agent`

`remote_agent` returns an `AgentClient` implementing the same `chat()`, `load_chat()`, `get_snapshot()`, and `abort()` surface as an in-process `Agent`:

```python
from genkit.exp.agent import remote_agent


async def run_client() -> None:
    client = remote_agent(
        url='http://127.0.0.1:8080/api/weatherAgent',
        state_management='server',  # use 'client' when the server agent has no store
        timeout=60.0,
    )

    # 1. One-shot turn
    chat = client.chat()
    res = await chat.send('Weather in Tokyo?')
    print(res.text, res.snapshot_id)

    # 2. Streamed follow-up turn
    turn = chat.send_stream('What about humidity?')
    async for chunk in turn.stream:
        if chunk.text:
            print(chunk.text, end='', flush=True)
    final = await turn.response

    # 3. Rehydrate from the server store onto a new chat handle
    assert final.snapshot_id is not None
    resumed = await client.load_chat(snapshot_id=final.snapshot_id)
    await resumed.send('Which city were we discussing?')
```

Pass `state_schema=MyStateModel` to `remote_agent(...)` when you want `chat.state`, `res.state`, and `chunk.custom` validated into a Pydantic model on the client. Omit any trailing slash on `url`.

## Auth, `context_dependency`, and `PublicError`

Resolve caller identity on the **server** with `context_dependency` (applied to the turn, `getSnapshot`, and `abort` routes). Return a `dict` — non-dict return values (such as Pydantic models) are ignored — so tools and `SessionStore` hooks receive it via `ctx.context` on `ToolContext` (or `Genkit.current_context()`).

Error handling follows two distinct boundaries:

- **FastAPI `context_dependency`**: Resolved by FastAPI's `Depends(...)` graph before Genkit runs; raise `fastapi.HTTPException(status_code=401, ...)` to reject unauthenticated requests.
- **Genkit HTTP / SSE boundary (`serve_agent`, `handle_genkit_request`, `genkit_fastapi_handler`, `to_sse`)**: Once inside Genkit (pre-turn `AgentInitError`, `SessionStore` tenant checks on `getSnapshot`/`abort`, or `context_provider`), unhandled exceptions and plain `GenkitError` instances log server-side and return generic `500` (`{"status": "INTERNAL", "message": "Internal Error"}`). Raise `PublicError(status, message, details)` (`from genkit import PublicError`) when the HTTP caller should see the classified status and message (`UNAUTHENTICATED` -> `401`, `PERMISSION_DENIED` -> `403`, `NOT_FOUND` -> `404`, `INVALID_ARGUMENT` -> `400`). Exceptions raised inside a running tool end the turn normally with `res.finish_reason == AgentFinishReason.FAILED` and `res.error`.

```python
from fastapi import FastAPI, Header, HTTPException
from genkit_fastapi.exp import serve_agent

from genkit import PublicError, ToolContext
from genkit.exp.agent import InMemorySessionStore, SessionSnapshot, remote_agent


async def resolve_user(x_api_key: str | None = Header(default=None)) -> dict[str, object]:
    if not x_api_key:
        raise HTTPException(status_code=401, detail='Missing X-Api-Key header.')
    return {'tenant_id': 'acme', 'role': 'admin'}


class TenantScopedStore(InMemorySessionStore):
    async def get_snapshot(
        self,
        *,
        snapshot_id: str | None = None,
        session_id: str | None = None,
        context: dict[str, object] | None = None,
    ) -> SessionSnapshot | None:
        if not (context or {}).get('tenant_id'):
            # Reaches HTTP callers on /getSnapshot as 403 {"status":"PERMISSION_DENIED",...}
            raise PublicError('PERMISSION_DENIED', 'Tenant context required.')
        return await super().get_snapshot(snapshot_id=snapshot_id, session_id=session_id, context=context)


@ai.tool(name='whoami', description='Inspect caller tenant context.')
async def whoami(ctx: ToolContext) -> dict[str, object]:
    auth = ctx.context or {}
    return {'tenant_id': auth.get('tenant_id'), 'role': auth.get('role')}


app = FastAPI()
app.include_router(
    serve_agent(agent, context_dependency=resolve_user),
    prefix='/api',
)

# Remote client forwards static headers or an async/sync header-provider callable:
authed_client = remote_agent(
    url='http://127.0.0.1:8080/api/weatherAgent',
    state_management='server',
    headers={'X-Api-Key': 'sk-live-...'},
)
```

## Custom HTTP routes (`handle_genkit_request` and `genkit.web`)

When you need custom FastAPI route signatures, path parameters, or non-FastAPI ASGI handlers:

- **`handle_genkit_request(request, action=agent, context=..., init=...)`** (`genkit_fastapi`): executes one Genkit action request using the standard JSON / SSE wire protocol while letting your `@app.post(...)` route build `context` and `init` directly.
- **`to_sse(...)` and `RequestData`** (`genkit.web`): `to_sse(chat.send_stream(...))` frames any stream handle (`chat.send_stream()`, `flow.stream()`) as Genkit SSE lines (`data: {"message": ...}` followed by `data: {"result": ...}`), and `RequestData` exposes `.method`, `.headers`, and `.input` for framework-agnostic auth context providers:

```python
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from genkit_fastapi import handle_genkit_request

from genkit.web import to_sse

custom_app = FastAPI()


# Option A: Full Genkit wire contract (JSON + SSE) inside a custom FastAPI route
@custom_app.post('/tenants/{tenant_id}/chat')
async def tenant_agent_route(tenant_id: str, request: Request) -> Response:
    return await handle_genkit_request(
        request,
        action=agent,
        context={'tenant_id': tenant_id},
    )


# Option B: Stream a chat turn directly as SSE from a custom endpoint
@custom_app.post('/sessions/{session_id}/stream')
async def stream_session_turn(session_id: str, prompt: str) -> StreamingResponse:
    chat = agent.chat(session_id=session_id)
    turn = chat.send_stream(prompt)
    return StreamingResponse(to_sse(turn), media_type='text/event-stream')
```
