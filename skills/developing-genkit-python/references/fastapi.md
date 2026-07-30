# FastAPI — Genkit Python

## Install

```bash
uv add genkit-fastapi fastapi uvicorn
```

Import from `genkit_fastapi`:

- `serve_agent` / `serve_flow` — mount an agent or flow as a router (preferred for new code)
- `genkit_fastapi_handler` — decorator stack on a FastAPI route

For agents, see also [Agent HTTP](agents-http.md).

---

## Serve an agent or flow (preferred)

```python
import uvicorn
from fastapi import FastAPI
from genkit import Genkit
from genkit.agent import InMemorySessionStore
from genkit_fastapi import serve_agent, serve_flow
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')

agent = ai.define_agent(
    name='weatherAgent',
    system='Weather assistant. Be concise.',
    store=InMemorySessionStore(),
)

@ai.flow()
async def hello(name: str) -> str:
    return f'Hello, {name}'

app = FastAPI()
app.include_router(serve_agent(agent), prefix='/api')          # /api/weatherAgent (+ getSnapshot/abort)
app.include_router(serve_flow(hello), prefix='/api')           # /api/hello
# Optional: app.include_router(serve_flow(hello, base_path='/hi'), prefix='/api')

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)
```

---

## Streaming by default

`serve_flow` / `genkit_fastapi_handler` stream when the client sends
`Accept: text/event-stream`.

**Wire format (SSE):**
```
data: {"message": "<chunk text>"}   ← one per ctx.send_chunk() call
data: {"message": "<chunk text>"}
data: {"result": <final output>}    ← sent once when flow completes
```

**Frontend (JS EventSource):**
```js
const res = await fetch('/flow/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' },
  body: JSON.stringify({ data: { topic: 'quantum computing' } }),
});
const reader = res.body.getReader();
// decode and parse each `data: {...}` line
```

**curl test:**
```bash
curl -N -X POST http://localhost:8080/flow/chat \
  -H 'Content-Type: application/json' \
  -H 'Accept: text/event-stream' \
  -d '{"data": {"topic": "quantum computing"}}'
```

---

## Minimal streaming FastAPI app

```python
import uvicorn
from pydantic import BaseModel
from fastapi import FastAPI
from genkit import Genkit
from genkit import ActionRunContext
from genkit_fastapi import genkit_fastapi_handler
from genkit_google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-flash-latest')
app = FastAPI()

class ChatInput(BaseModel):
    topic: str

@app.post('/flow/chat', response_model=None)
@genkit_fastapi_handler(ai)
@ai.flow()
async def chat(input: ChatInput, ctx: ActionRunContext) -> str:
    sr = ai.generate_stream(prompt=f'Tell me about {input.topic}.')
    full = ''
    async for chunk in sr.stream:
        if chunk.text:
            ctx.send_chunk(chunk.text)   # each chunk → SSE event on the wire
            full += chunk.text
    return full

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8080)
```

**Key:** flow must accept `ctx: ActionRunContext` and call `ctx.send_chunk(text)` to emit SSE chunks.
Without `ctx.send_chunk`, the flow runs but streams nothing — client waits for the final result.

---

## Advanced Use Cases

### Nested flow streaming

Chain flows so a child's chunks surface on the parent's HTTP stream. Call the
child with `.run(..., on_chunk=ctx.send_chunk)` — do **not** pass `ctx` as a
second positional argument to `await child(input, ctx)` (that raises `TypeError`).

```python
class ResearchInput(BaseModel):
    topic: str

@ai.flow()
async def research(input: ResearchInput, ctx: ActionRunContext) -> str:
    sr = ai.generate_stream(prompt=f'Explain {input.topic} in depth.')
    full = ''
    async for chunk in sr.stream:
        if chunk.text:
            ctx.send_chunk(chunk.text)
            full += chunk.text
    return full


class HeadlineInput(BaseModel):
    text: str

@ai.flow()
async def make_headline(input: HeadlineInput) -> str:
    response = await ai.generate(prompt=f'One-line headline for: {input.text}')
    return response.text.strip()


class ReportInput(BaseModel):
    topic: str

@app.post('/flow/report', response_model=None)
@genkit_fastapi_handler(ai)
@ai.flow()
async def report(input: ReportInput, ctx: ActionRunContext) -> str:
    headline = await make_headline(HeadlineInput(text=input.topic))
    ctx.send_chunk(f'# {headline}\n\n')

    body = (
        await research.run(
            ResearchInput(topic=input.topic),
            on_chunk=ctx.send_chunk,
        )
    ).response

    return f'# {headline}\n\n{body}'
```

**Rules:**
- Streaming children accept `ctx: ActionRunContext` and call `ctx.send_chunk`
- Parents forward chunks with `child.run(input, on_chunk=ctx.send_chunk)`
- Non-streaming children: `await child(input)` is fine

### Executing flows in parallel

Use `asyncio.gather` to run multiple flows concurrently. Only makes sense when children don't need to stream.

```python
import asyncio

class AnalysisInput(BaseModel):
    text: str

class CheckResult(BaseModel):
    issues: list[str]

class CombinedAnalysis(BaseModel):
    issues: list[str]

@ai.flow()
async def check_security(input: AnalysisInput) -> CheckResult:
    # Here the model reviews the text; replace with your real prompt/schema as needed.
    r = await ai.generate(
        prompt=f'List security concerns as a short comma-separated line (or "none"): {input.text[:2000]}',
    )
    raw = (r.text or '').strip()
    issues = [s.strip() for s in raw.split(',') if s.strip() and s.strip().lower() != 'none']
    return CheckResult(issues=issues)

@ai.flow()
async def check_bugs(input: AnalysisInput) -> CheckResult:
    # Model lists possible bugs; tune prompt for your codebase.
    r = await ai.generate(
        prompt=f'List likely bugs or correctness issues as a short comma-separated line (or "none"): {input.text[:2000]}',
    )
    raw = (r.text or '').strip()
    issues = [s.strip() for s in raw.split(',') if s.strip() and s.strip().lower() != 'none']
    return CheckResult(issues=issues)

@ai.flow()
async def check_style(input: AnalysisInput) -> CheckResult:
    # Model suggests style/clarity issues; optional: use output_schema for structured rows.
    r = await ai.generate(
        prompt=f'List style or clarity issues as a short comma-separated line (or "none"): {input.text[:2000]}',
    )
    raw = (r.text or '').strip()
    issues = [s.strip() for s in raw.split(',') if s.strip() and s.strip().lower() != 'none']
    return CheckResult(issues=issues)

@app.post('/flow/analyze', response_model=None)
@genkit_fastapi_handler(ai)
@ai.flow()
async def analyze(input: AnalysisInput) -> CombinedAnalysis:
    security, bugs, style = await asyncio.gather(
        check_security(input),
        check_bugs(input),
        check_style(input),
    )
    return CombinedAnalysis(issues=security.issues + bugs.issues + style.issues)
```

---

## Structured output endpoint (non-streaming)

```python
class SentimentResult(BaseModel):
    sentiment: str        # positive / negative / neutral
    confidence: float     # 0.0–1.0
    key_phrases: list[str]

@app.post('/flow/sentiment', response_model=None)
@genkit_fastapi_handler(ai)
@ai.flow()
async def sentiment(input: AnalysisInput) -> SentimentResult:
    response = await ai.generate(
        prompt=f'Analyze sentiment: {input.text}',
        output_format='json',
        output_schema=SentimentResult,
    )
    return response.output
```

Client calls this without `Accept: text/event-stream` — gets `{"result": {...}}` back.

---

## Decorator order

Must be exactly: `@app.post` → `@genkit_fastapi_handler(ai)` → `@ai.flow()`

```python
@app.post('/flow/chat', response_model=None)   # 1. FastAPI route
@genkit_fastapi_handler(ai)                    # 2. Genkit wire format + streaming
@ai.flow()                                     # 3. Flow registration
async def chat(input: ChatInput, ctx: ActionRunContext) -> str:
    ...
```

---

## Run with Dev UI

```bash
GEMINI_API_KEY=your-key genkit start -- uv run src/main.py
```

Leave the process running until the CLI prints something like:

```
Genkit Developer UI: http://localhost:4000
```

Open that URL. Port may differ if 4000 is busy.