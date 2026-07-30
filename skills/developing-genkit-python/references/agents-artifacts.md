# Working with Artifacts (Beta)

> **Beta / preview API.** `Artifacts` middleware is from `genkit_middleware`.
> See [agents.md](agents.md).

**Artifacts** are named, content-bearing deliverables an agent produces during a
session — files, reports, code, etc. They live in the session (deduplicated by
name) and are tracked on `chat.artifacts` / `res.artifacts`.

## Give the model artifact tools

```python
from genkit_google_genai import GoogleAI
from genkit_middleware import Artifacts, Middleware

from genkit import Genkit
from genkit.agent import InMemorySessionStore

ai = Genkit(plugins=[GoogleAI(), Middleware()])

agent = ai.define_agent(
    name='workspaceAgent',
    model='googleai/gemini-flash-latest',
    system=(
        'Code generation assistant. Use write_artifact to create files '
        '(name + content). Use read_artifact to review prior files.'
    ),
    use=[Artifacts()],
    store=InMemorySessionStore(),
)

chat = agent.chat()
await chat.send('Write poem.txt with a short poem about Python agents.')
assert any(a.name == 'poem.txt' for a in chat.artifacts)
```

Writing the same `name` again **replaces** the artifact.

## Programmatic access (custom agents)

```python
from genkit import Part, TextPart
from genkit.agent import Artifact

await sess.add_artifacts(
    Artifact(name='notes.md', parts=[Part(TextPart(text='# Notes'))])
)
all_artifacts = await sess.get_artifacts()
```

## Reading on the client

After each turn, inspect `chat.artifacts` or `res.artifacts`. Over HTTP,
`remote_agent` tracks the same list on the chat when `state_management` is set
appropriately (see [HTTP clients](agents-http.md)).
