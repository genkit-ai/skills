# Common Errors — Genkit Python

## Before anything else: read this file when you hit any error.

---

## ModuleNotFoundError: No module named 'genkit.plugins.google_genai'

**Cause:** Stale import path. The Google AI plugin is no longer under
`genkit.plugins.google_genai`.

**Fix:**
```python
from genkit_google_genai import GoogleAI  # correct
```
```bash
uv add genkit genkit-google-genai
```

---

## TypeError / wrong shape from `chat.send`

**Cause:** `send` returns `AgentResponse`; streaming is `send_stream`.

**Fix:**
```python
res = await chat.send('hi')
turn = chat.send_stream('hi')
async for chunk in turn.stream:
    ...
res = await turn.response  # no need to drain .stream; unread chunks stay on this turn
```

---

## snapshot_id / session_id is None after a turn

**Cause:** Agent was defined **without** a `store`. Ids are only minted when a
session store is attached.

**Fix:** Pass `store=InMemorySessionStore()` (or `FileSessionStore`). Without a store,
resume by round-tripping `chat.messages`, `chat.state`, and `chat.artifacts`.

---

## detach / chat.abort() fails or does nothing useful

**Cause:** Background detach and **server-side** abort require a session store.

**Also:** `turn.abort()` is a **client** detach (stop listening; server may
still finish). `chat.abort()` / `task.abort()` cancel on the server.

---

## FAILED_PRECONDITION on session_id lookup after branching

**Cause:** The session has multiple leaves; "latest" is ambiguous
(`reject_ambiguous_session=True`).

**Fix:** Resume with the specific leaf `snapshot_id`, not `session_id`.

---

## ToolApproval: tool still doesn't run after resume

**Cause:** Resume parts missing approval metadata, or built by hand instead of
from `res.interrupts`.

**Fix:**
```python
restart_parts = [
    intr.restart(resumed_metadata={'tool_approved': True})
    for intr in out.interrupts
]
await chat.resume(restart=restart_parts)
```

---

## 400 INVALID_ARGUMENT: functionDeclaration parameters schema should be of type OBJECT

**Cause:** Tool function has bare scalar parameters (e.g. `city: str`). Gemini requires object schema.

**Fix:** Wrap parameters in a Pydantic BaseModel:
```python
from pydantic import BaseModel

# Wrong
@ai.tool()
async def get_weather(city: str) -> str: ...

# Right
class WeatherInput(BaseModel):
    city: str

@ai.tool()
async def get_weather(input: WeatherInput) -> str: ...
```

---

## AttributeError: 'Genkit' object has no attribute 'define_tool'

**Cause:** Wrong decorator name.

**Fix:** Use `@ai.tool()`, not `@ai.define_tool()`.

---

## RuntimeError / event loop errors when using asyncio.run()

**Cause:** For apps you start with **`genkit start`**, Genkit runs your entrypoint with an event loop suited to the framework (including uvloop where used). There is no “default” loop for you to manage in that mode.

**Fix:** For long-running Genkit apps (servers, flows served under `genkit start`), use **`ai.run_main(main())`** as your entrypoint instead of `asyncio.run(main())`. For one-off scripts that exit when done, using `asyncio.run()` can still be appropriate when you are not using `genkit start`.

---

## Wrong model ID (no plugin prefix)

**Cause:** `model='gemini-flash-latest'` — missing plugin prefix.

**Fix:** `model='googleai/gemini-flash-latest'`

---

## response.json / response.message AttributeError

- Use `response.text` for plain text output
- Use `response.output` for structured (JSON) output

---

## await ai.generate_stream(...) fails or returns wrong type

**Cause:** `generate_stream` is synchronous — do not await it.

**Fix:**
```python
sr = ai.generate_stream(prompt='...')   # no await
async for chunk in sr.stream: ...
final = await sr.response
```
