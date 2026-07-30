---
name: developing-genkit-python
description: Develop AI-powered applications using Genkit in Python. Use when the user asks about Genkit, AI agents, flows, or tools in Python, or when encountering Genkit errors, import issues, or API problems.
---

# Genkit Python

## Prerequisites

- **Runtime**: Python **3.10+**, **`uv`** for deps ([install](https://docs.astral.sh/uv/getting-started/installation/)).
- **CLI**: `genkit --version` — install via `npm install -g genkit-cli` if missing.

**New projects:** [Setup](references/setup.md) (bootstrap + env). **Patterns and code samples:** [Examples](references/examples.md).

## Hello World

```python
from genkit import Genkit
from genkit_google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],
    model='googleai/gemini-flash-latest',
)

async def main():
    response = await ai.generate(prompt='Tell me a joke about Python.')
    print(response.text)

if __name__ == '__main__':
    ai.run_main(main())
```

## Agents (Beta)

Genkit Python has a preview **agent** API for persistent, multi-turn
conversations (sessions, snapshots, interrupts, branching, background
execution). Types live under `genkit.agent`.

**Requires a Genkit Python build that includes agents.** Stable PyPI `genkit`
0.8.x does not yet export `define_agent` — install from the agents branch /
checkout your team specifies until a release ships.

For more details see:

- [Agents](references/agents.md): defining/chatting with an agent and client-managed state (start here).
- [Sessions & persistence](references/agents-sessions.md): session stores (`InMemory`/`File`/`Firestore`).
- [Human-in-the-loop / interrupts](references/agents-human-in-the-loop.md): pausing for approval/input and resuming.
- [Branching](references/agents-branching.md): forking a conversation from a snapshot.
- [Background agents](references/agents-background.md): detaching long-running turns and polling.
- [Working with state](references/agents-state.md): typed custom session state streamed to the client.
- [Artifacts](references/agents-artifacts.md): producing and reading named deliverables.
- [Advanced custom agents](references/agents-custom.md): `define_custom_agent` for full turn control.
- [HTTP clients](references/agents-http.md): `remote_agent` / `HttpAgentTransport`.

## Critical: Do Not Trust Internal Knowledge

The Python SDK changes often — verify imports and APIs against the references here or upstream docs. On **any** error, read [Common Errors](references/common-errors.md) first.

**Common import traps:**

- Google AI plugin: `from genkit_google_genai import GoogleAI` (not `genkit.plugins.google_genai`).
- Agents: `from genkit.agent import InMemorySessionStore, ...`
- Middleware: `from genkit_middleware import Middleware, ToolApproval, ...` (agents branch; older PyPI may still use `genkit.plugins.middleware`).

## Development Workflow

1. Default provider: **Google AI** (`GoogleAI()`), **`GEMINI_API_KEY`** in the environment.
2. Model IDs: always prefixed, e.g. **`googleai/gemini-flash-latest`**.
3. Entrypoint: **`ai.run_main(main())`** for Genkit-driven apps (not `asyncio.run()` for long-lived servers started with `genkit start` — see [Common Errors](references/common-errors.md)).
4. After generating code, follow [Dev Workflow](references/dev-workflow.md) for `genkit start` and the Dev UI.
5. On errors: step 1 is always [Common Errors](references/common-errors.md).

## References

- [Examples](references/examples.md): Structured output, streaming, flows, tools, embeddings.
- [Setup](references/setup.md): New project bootstrap and plugins.
- [Common Errors](references/common-errors.md): Read first when something breaks.
- [FastAPI](references/fastapi.md): HTTP, `genkit_fastapi_handler`, parallel flows.
- [Dotprompt](references/dotprompt.md): `.prompt` files and helpers.
- [Evals](references/evals.md): Evaluators and datasets.
- [Dev Workflow](references/dev-workflow.md): `genkit start`, Dev UI, checklist.
- [Agents (Beta)](references/agents.md): Agent basics and client-managed state. Deeper topics: [sessions](references/agents-sessions.md), [human-in-the-loop](references/agents-human-in-the-loop.md), [branching](references/agents-branching.md), [background](references/agents-background.md), [state](references/agents-state.md), [artifacts](references/agents-artifacts.md), [custom agents](references/agents-custom.md), [HTTP](references/agents-http.md).
