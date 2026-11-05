# Common Errors — Genkit Python 0.13

Fast fixes for 0.13 errors and subtle runtime pitfalls. Upgrading a 0.12 codebase? Read [Migrating from 0.12 to 0.13](migrating-from-0.12.md).

---

## `ImportError` on `ActionRunContext`, `ToolRunContext`, `MediaPart`, `TextPart`, or `genkit.agent`

0.13 enforces one public namespace per symbol and removes 0.12 wrapper types:

```python
# Contexts
from genkit import FlowContext, ToolContext
from genkit.model import ModelContext

# Parts (MediaPart and TextPart are removed; Part(root=...) raises ValueError)
from genkit import Media, Message, Part, Role
text_part = Part.from_text('Hello')
img_part = Part.from_media('https://example.com/photo.jpg', content_type='image/jpeg')

# Experimental agents & integrations
from genkit.exp import Genkit, current_session
from genkit.exp.agent import Agent, InMemorySessionStore, Session
from genkit_fastapi.exp import serve_agent
from genkit_middleware.exp import Artifacts
```

Note on `Middleware` imports:
- `from genkit_middleware import Middleware, Retry, ToolApproval` imports the **`Middleware()` plugin** and built-in middleware classes.
- `from genkit.middleware import Middleware, MiddlewareContext` imports the **base class** for authoring custom middleware.

---

## `GenkitError` (`INVALID_ARGUMENT`) on Unknown or Nested Config Keys

0.13 validates config keys before calling the model instead of silently dropping typos or nested 0.12 dicts:

```python
from genkit_google_genai import GeminiConfig

# Fails in 0.13: config={'thinking_config': {'thinking_level': 'HIGH'}, 'temprature': 0.2}
# Fix: use flat typed config; put unmodeled provider-native keys in `extra`
cfg = GeminiConfig(
    temperature=0.2,
    thinking_level='HIGH',
    include_thoughts=True,
    extra={'seed': 7},
)
```

`tool_choice` is also no longer a config field — pass `tool_choice='required'` (`'auto' | 'required' | 'none'`) directly on `ai.generate(...)`.

---

## `TypeError: takes N positional arguments`

Constructors (`Genkit`, plugins, `GenkitError`) and options after an action's single input on `.run(...)` are keyword-only:

```python
ai = Genkit(plugins=[GoogleAI()], model=GoogleAI.gemini('gemini-flash-latest'))
res = await my_flow.run(payload, on_chunk=handle_chunk, context={'uid': 'u1'})
```

Also ensure every `@ai.flow()` and `@ai.tool()` declares **at most one input parameter** (plus an optional `ctx: FlowContext` or `ctx: ToolContext`). Wrap multi-field inputs in a single Pydantic `BaseModel`.

---

## `GenkitError` (`INVALID_ARGUMENT`) Passing `api_key` in `config`

Every provider plugin rejects `api_key` inside `config`. Configure the key on the plugin or pass a per-request key in `context`:

```python
# Whole app: OpenAI(api_key=...)
# Per request:
await ai.generate(prompt='Hello', context={'secrets': {'api_key': user_key}})
```

---

## Served Flow Returns `500 {"status": "INTERNAL", "message": "Internal Error"}`

Over HTTP (`serve_flow`, `serve_agent`, `genkit_fastapi_handler`, `handle_genkit_request`), Genkit redacts `GenkitError` and Python exceptions to `500 Internal Error` so provider errors and stack traces never leak. Raise `PublicError` for errors intended for the client:

```python
from genkit import PublicError

@ai.flow()
async def get_invoice(invoice_id: str) -> dict:
    inv = await find_invoice(invoice_id)
    if inv is None:
        raise PublicError('NOT_FOUND', f'Invoice {invoice_id} not found')  # HTTP 404
    return inv
```

The same rule applies in HTTP `context_provider` functions (`raise PublicError('UNAUTHENTICATED', 'Missing token')` -> HTTP 401).

---

## `response.output` Is `None` on Structured Output

When a JSON response hits `max_output_tokens` or fails schema parsing, `response.output` returns `None` instead of a partial object, and `response.error` (`Failure`) sets `reason == ErrorReason.INVALID_OUTPUT`:

```python
from genkit import ErrorReason

res = await ai.generate(prompt='...', output_schema=InvoiceSummary)
if res.output is None:
    if res.error and res.error.reason == ErrorReason.INVALID_OUTPUT:
        # Retry with higher max_output_tokens or handle parse failure
        ...
```

---

## `{{variable}}` Sent Literally in `ai.generate(prompt=...)`

`ai.generate(prompt=..., system=...)` sends strings verbatim without Handlebars rendering. Use `ai.define_prompt` or a `.prompt` file when using `{{...}}` templates:

```python
greet = ai.define_prompt(name='greet', prompt='Say hello to {{name}}.')
res = await greet({'name': 'Sam'})
```

---

## Streaming `TypeError` or Leaked Background Flow on `break`

1. Do not `await` `.generate_stream(...)`, `.stream(...)`, or `chat.send_stream(...)` — iterate `.stream` (or the `StreamResponse`) and `await` `.response`:
   ```python
   sr = ai.generate_stream(prompt='...')
   async for chunk in sr.stream:
       ...
   final = await sr.response
   ```
2. When stopping a flow's `.stream(...)` early with `break`, wrap it in `async with` (or call `await stream.aclose()`); otherwise the background flow keeps running:
   ```python
   async with my_flow.stream(payload) as stream:
       async for chunk in stream:
           if done_early(chunk):
               break  # cancels my_flow cleanly
   ```

---

## Unprefixed Model String (`NOT_FOUND`) vs Model Refs

Plain string model names must include the `<plugin>/` prefix (`'googleai/gemini-flash-latest'`, `'openai/gpt-4o'`). Model ref helpers (`GoogleAI.gemini('gemini-flash-latest')`, `Anthropic.claude('claude-sonnet-4-6')`, `OpenAI.gpt('gpt-5.2')`) stamp the prefix automatically.

---

## Missing `.json` on Response / Old `GenkitError` Fields

- Plain text -> `response.text`; structured output -> `response.output`; message -> `response.message` (`Candidate` is removed).
- `GenkitError` exposes `e.message`, `e.status`, `e.details`, `e.reason`, and `e.__cause__` (`original_message`, `http_code`, `trace_id`, and `e.cause` are removed).

---

## Event Loop / Reflection Exit Under `genkit start`

Use `ai.run_main(main())` for standalone scripts and CLIs so the process stays alive for the Dev UI under `genkit start`. For FastAPI servers, see [FastAPI](fastapi.md).

---

## Interrupts & Agent Session Pitfalls

- **`Interrupt` bypasses `except Exception:`**: `Interrupt` subclasses `BaseException` so a tool's catch-all cannot swallow approval interrupts. Put partial side-effect cleanup in `finally`.
- **Approval resume**: build restart parts via `i.restart(resumed_metadata={'tool_approved': True})` from `res.interrupts` (see [agents-human-in-the-loop.md](agents-human-in-the-loop.md)).
- **Turn errors (`AgentError` removed)**: `AgentError` no longer exists. Inspect `res.error` (`Failure`) for failed turns; a call that produces no turn raises `GenkitError`. Prefer returning a structured error dict from tools when the model can recover.
- **No `snapshot_id` after a turn**: attach a `store` (e.g. `InMemorySessionStore()`) to the agent (see [agents.md](agents.md)).
- **Cannot send state to a server-managed agent**: store-backed chats resume by ID; mutate state inside the turn (see [agents-state.md](agents-state.md)).
- **Ambiguous session after a fork**: resume using a leaf `snapshot_id`, not `session_id` (see [agents-branching.md](agents-branching.md)).
- **Abort seems to do nothing**: `await` the abort (`await turn.abort()`, `await chat.abort()`, or `await task.abort()` — see [agents-background.md](agents-background.md)).
- **Remote client mismatches**: align `state_management` with the server and omit trailing slashes on the base URL (see [agents-http.md](agents-http.md)).
