# Working with Artifacts (Beta)

> **Beta / preview API.** `Artifacts` middleware from `genkit_middleware`.
> See [agents.md](agents.md).

Named deliverables (files, reports, code) on the session — deduped by name,
exposed as `chat.artifacts` / `res.artifacts`.

## Middleware tools

`Artifacts()` exposes `write_artifact` / `read_artifact` to the model. Same
`name` again replaces the artifact.

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

## From a custom agent

Inside [`handle_turn`](agents-custom.md):

```python
from genkit import Part, TextPart
from genkit.agent import Artifact

await sess.add_artifacts(
    Artifact(name='report.md', parts=[Part(TextPart(text=body))])
)
# mid-turn: await sess.get_artifacts()
```

## Client

- `chat.artifacts` — session cumulative
- `res.artifacts` — this turn only

Over HTTP, see [HTTP](agents-http.md) (`state_management`).
