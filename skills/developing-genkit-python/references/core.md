# Core APIs — Genkit Python

## Public API imports only

**Never import from internal modules** (`genkit._core`, `genkit._ai`, etc.).
Only import from the public surface:

```python
from genkit import (
    Genkit,
    ActionRunContext,   # ← correct, not from genkit._core._action
    ModelResponse,
    ModelResponseChunk,
    EmbedRequest,
    EmbedResponse,
    Embedding,
    Document,
    GenkitError,
    Tool,
    ToolRunContext,
    tool_response,
)
from genkit.plugins.google_genai import GoogleAI
from genkit.plugins.google_genai import GeminiEmbeddingModels, EmbeddingTaskType
```

If something you need isn't importable from `genkit` or `genkit.plugins.*`, it's not a public API — don't use it.

---

## Structured output

```python
from pydantic import BaseModel
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-flash')

class CityInfo(BaseModel):
    name: str
    population: int
    country: str

response = await ai.generate(
    prompt='Give facts about Tokyo.',
    output_format='json',
    output_schema=CityInfo,
)
city = response.output   # CityInfo instance
```

For lists:
```python
from pydantic import TypeAdapter
schema = TypeAdapter(list[CityInfo]).json_schema()
response = await ai.generate(
    prompt='List 3 cities.',
    output_format='array',
    output_schema=schema,
)
```

Output format values: `'text'`, `'json'`, `'array'`, `'enum'`, `'jsonl'`

---

## Streaming plain text

`generate_stream` is **not awaited**. Iterate `.stream` with `async for`.

```python
sr = ai.generate_stream(prompt='Tell me a story.')
async for chunk in sr.stream:
    if chunk.text:
        print(chunk.text, end='', flush=True)
final = await sr.response
```

---

## Text and media on the final response

Streamed text arrives on each `chunk.text`. After the stream ends, `await sr.response` gives a `ModelResponse` with `.text` and `.media`: non-text parts (for example images) are exposed on **`final.media`** as `Media` objects (`url`, `content_type`).

```python
sr = ai.generate_stream(prompt='Describe this concept and output an image if supported.')
async for chunk in sr.stream:
    if chunk.text:
        print(chunk.text, end='', flush=True)
final = await sr.response
for media in final.media:
    # Often a data URI or URL; inspect content_type (e.g. image/png)
    _ = media.url
```

---

## Streaming + structured output

Stream tokens while still getting typed output at the end:

```python
from pydantic import BaseModel

class StoryAnalysis(BaseModel):
    title: str
    genre: str
    summary: str

sr = ai.generate_stream(
    prompt='Write a short story then analyze it.',
    output_format='json',
    output_schema=StoryAnalysis,
)
async for chunk in sr.stream:
    if chunk.text:
        print(chunk.text, end='', flush=True)   # tokens stream live
final = await sr.response
analysis = final.output   # StoryAnalysis instance, available once stream completes
```

---

## Flows

```python
from pydantic import BaseModel

class SummarizeInput(BaseModel):
    text: str

@ai.flow()
async def summarize(input: SummarizeInput) -> str:
    response = await ai.generate(prompt=f'Summarize: {input.text}')
    return response.text

result = await summarize(SummarizeInput(text='...'))
```

---

## Streaming flows

```python
from genkit import ActionRunContext   # public import — not from genkit._core

@ai.flow()
async def stream_story(subject: str, ctx: ActionRunContext) -> str:
    sr = ai.generate_stream(prompt=f'Story about {subject}.')
    full = ''
    async for chunk in sr.stream:
        if chunk.text:
            ctx.send_chunk(chunk.text)
            full += chunk.text
    return full
```

---

## Tools

Tool parameters **must** be a Pydantic `BaseModel`. Bare scalars fail with a 400 from Gemini.

```python
from pydantic import BaseModel

class WeatherInput(BaseModel):
    city: str

@ai.tool()
async def get_weather(input: WeatherInput) -> str:
    """Return current weather for a city."""
    return f'Sunny, 72°F in {input.city}'

response = await ai.generate(
    prompt='Weather in Paris?',
    tools=[get_weather],
)
```

The decorator is `@ai.tool()` — not `@ai.define_tool()`.

---

## Embeddings

Embed a single string or document:

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI, GeminiEmbeddingModels, EmbeddingTaskType

ai = Genkit(plugins=[GoogleAI()], model='googleai/gemini-3-flash')

# Single embed
embeddings = await ai.embed(
    embedder=f'googleai/{GeminiEmbeddingModels.GEMINI_EMBEDDING_001}',
    content='The sky is blue.',
)
vector = embeddings[0].embedding   # list[float]

# Batch embed
embeddings = await ai.embed_many(
    embedder=f'googleai/{GeminiEmbeddingModels.GEMINI_EMBEDDING_001}',
    content=['The sky is blue.', 'Grass is green.'],
)
vectors = [e.embedding for e in embeddings]
```

Common embedding models:
- `googleai/gemini-embedding-001` — recommended default (3072 dims)
- `googleai/gemini-embedding-exp-03-07` — experimental, may have higher quality
