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

## Genkit CLI (recommended)

`genkit start` unintrusively wraps any Python program that uses the Genkit library, running it unchanged while discreetly collecting traces from every Genkit action.

**Primary pattern:** prefix your normal run command. Collects telemetry from any Genkit code your program runs, whether triggered from the dev UI, your own web server/web UI, or a plain script. Useful for all local development and testing, even when you never open the dev UI. Starts the Developer UI (usually http://localhost:4000):
```bash
genkit start -- uv run src/main.py
genkit start --noui -- uv run src/main.py   # trace collection only, lighter, no UI
```

**Debugging with traces:** the fastest way to see prompts, model inputs/outputs, tool calls, latencies, and errors. Inspect from the terminal after any run under `genkit start`:
```bash
genkit trace:list          # find recent trace IDs
genkit trace:get <traceId> # full trace details (inputs, outputs, tool calls, errors)
```

**Secondary pattern:** run a single flow without your program's normal entrypoint:
```bash
genkit flow:run myFlow '{"data": "input"}' -- uv run src/main.py
```

See [Dev Workflow](references/dev-workflow.md) for the full checklist and Dev UI walkthrough.

## References

- [Examples](references/examples.md): Structured output, streaming, flows, tools, embeddings.
- [Setup](references/setup.md): New project bootstrap and plugins.
- [Common Errors](references/common-errors.md): Read first when something breaks.
- [FastAPI](references/fastapi.md): HTTP, `genkit_fastapi_handler`, parallel flows.
- [Dotprompt](references/dotprompt.md): `.prompt` files and helpers.
- [Evals](references/evals.md): Evaluators and datasets.
- [Dev Workflow](references/dev-workflow.md): `genkit start`, Dev UI, checklist.
- [Agents (Beta)](references/agents.md): Multi-turn API.
