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

Preview multi-turn API under `genkit.agent`: sessions, snapshots, interrupts,
branching, detach. `await chat.send(...)` → `AgentResponse`;
`chat.send_stream(...)` → `AgentTurn` (`.stream` / `.response`). Same split for
`resume` / `resume_stream`. No need to drain the stream when you only await
the response.

Start at [Agents](references/agents.md). Also: [sessions](references/agents-sessions.md),
[HITL](references/agents-human-in-the-loop.md),
[branching](references/agents-branching.md),
[background](references/agents-background.md),
[state](references/agents-state.md),
[artifacts](references/agents-artifacts.md),
[custom](references/agents-custom.md),
[HTTP](references/agents-http.md).

## Verify against references

The Python SDK changes often — check imports and APIs against the references
here or upstream docs. On errors, see [Common Errors](references/common-errors.md)
first.

**Common import traps:**

- Google AI: `from genkit_google_genai import GoogleAI`
- Agents: `from genkit.agent import InMemorySessionStore, ...`
- Middleware: `from genkit_middleware import Middleware, ToolApproval, ...`
- FastAPI: `from genkit_fastapi import serve_agent, serve_flow, handle_genkit_request`
- Evaluators: `from genkit_evaluators import register_genkit_evaluators`

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
- [FastAPI](references/fastapi.md): `serve_agent` / `serve_flow` / `handle_genkit_request`, parallel flows.
- [Dotprompt](references/dotprompt.md): `.prompt` files and helpers.
- [Evals](references/evals.md): Evaluators and datasets.
- [Dev Workflow](references/dev-workflow.md): `genkit start`, Dev UI, checklist.
- [Agents (Beta)](references/agents.md): define/chat/client-managed state + links to deeper topics.
