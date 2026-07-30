---
name: developing-genkit-python
description: Develop AI-powered applications using Genkit in Python. Use when the user asks about Genkit, AI agents, flows, or tools in Python, or when encountering Genkit errors, import issues, or API problems.
---

# Genkit Python

Build AI features in Python — generate, stream, tools, flows, and multi-turn
agents — with one SDK.

## Prerequisites

- Python **3.10+** and **`uv`** ([install](https://docs.astral.sh/uv/getting-started/installation/))
- Genkit CLI: `npm install -g genkit-cli` if `genkit --version` is missing

New app? [Setup](references/setup.md). Patterns? [Examples](references/examples.md).

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

Multi-turn chats with history, typed state, human approval, branching, and
background work. Start here: [Agents](references/agents.md).

```python
chat = agent.chat()
res = await chat.send('Hello')           # AgentResponse
turn = chat.send_stream('Hello')         # AgentTurn — .stream / .response
```

More: [sessions](references/agents-sessions.md) ·
[HITL](references/agents-human-in-the-loop.md) ·
[branching](references/agents-branching.md) ·
[background](references/agents-background.md) ·
[state](references/agents-state.md) ·
[artifacts](references/agents-artifacts.md) ·
[custom](references/agents-custom.md) ·
[HTTP](references/agents-http.md)

## Imports

- Google AI: `from genkit_google_genai import GoogleAI`
- Agents: `from genkit.agent import InMemorySessionStore, ...`
- Middleware: `from genkit_middleware import Middleware, ToolApproval, ...`
- FastAPI: `from genkit_fastapi import serve_agent, serve_flow`
- Evals: `from genkit_evaluators import register_genkit_evaluators`

## Workflow

1. Set **`GEMINI_API_KEY`**. Use prefixed model ids (`googleai/gemini-flash-latest`).
2. Enter via **`ai.run_main(main())`** for Genkit apps (especially under
   `genkit start`). See [Common Errors](references/common-errors.md).
3. Run with [Dev Workflow](references/dev-workflow.md) (`genkit start` + Dev UI).
4. Stuck? [Common Errors](references/common-errors.md) first.

## References

- [Examples](references/examples.md) — structured output, streaming, tools, flows
- [Setup](references/setup.md) — bootstrap and plugins
- [Common Errors](references/common-errors.md) — when something breaks
- [FastAPI](references/fastapi.md) — serve agents and flows
- [Dotprompt](references/dotprompt.md) — `.prompt` files
- [Evals](references/evals.md) — evaluators and datasets
- [Dev Workflow](references/dev-workflow.md) — CLI and Dev UI
- [Agents (Beta)](references/agents.md) — multi-turn API
