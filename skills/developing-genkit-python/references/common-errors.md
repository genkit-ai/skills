# Common Errors — Genkit Python
<!-- version: py-skill-2026-04-13-iter-1 -->

## Before anything else: read this file when you hit any error.

---

## ModuleNotFoundError: No module named 'genkit.plugins.google_genai'

**Cause:** Plugin package not installed.

**Fix:** Install from git:
```bash
uv pip install genkit genkit-plugin-google-genai
```

---

## 400 INVALID_ARGUMENT: functionDeclaration parameters schema should be of type OBJECT

**Cause:** Tool function has bare scalar parameters (e.g. `city: str`). Gemini requires object schema.

**Fix:** Wrap parameters in a Pydantic BaseModel:
```python
# ❌ Wrong
@ai.tool()
async def get_weather(city: str) -> str: ...

# ✅ Right
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

**Cause:** Genkit manages its own event loop via uvloop.

**Fix:** Always use `ai.run_main(main())` instead of `asyncio.run(main())`.

---

## Wrong model ID (no plugin prefix)

**Cause:** `model='gemini-2.0-flash'` — missing plugin prefix.

**Fix:** `model='googleai/gemini-2.0-flash'`

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
