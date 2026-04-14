---
name: developing-genkit-python
description: Develop AI-powered applications using Genkit in Python. Use when the user asks about Genkit, AI agents, flows, or tools in Python, or when encountering Genkit errors, import issues, or API problems.
---

# Genkit Python

## Critical: Do Not Trust Internal Knowledge

The Genkit Python SDK is new and actively changing. Your weights are likely wrong about imports, decorator names, and method signatures. **Verify everything against the references below before generating code.**

When you hit an error, read [Common Errors](references/common-errors.md) first — do not guess.

## Install

```bash
mkdir my-app && cd my-app
uv init
uv add genkit genkit-plugin-google-genai
```

Plugin packages follow the `genkit-plugin-*` pattern: `genkit-plugin-google-genai`, `genkit-plugin-vertex-ai`, `genkit-plugin-fastapi`, etc.

## Hello World

```python
from genkit import Genkit
from genkit.plugins.google_genai import GoogleAI

ai = Genkit(
    plugins=[GoogleAI()],               # reads GEMINI_API_KEY from env
    model='googleai/gemini-3-flash',    # always prefix with "googleai/"
)

async def main():
    response = await ai.generate(prompt='Tell me a joke about Python.')
    print(response.text)

if __name__ == '__main__':
    ai.run_main(main())   # never use asyncio.run()
```

## Core APIs

For detailed, verified examples covering flows, structured output, streaming, and tools, see [references/core.md](references/core.md).

## Development Workflow

1. **Select provider**: Default to Google AI (`GoogleAI()`). Requires `GEMINI_API_KEY` in env.
2. **Model IDs**: Always prefix with plugin name — `'googleai/gemini-3-flash'`. Never bare model names.
3. **Run scripts**: Use `ai.run_main(main())`, never `asyncio.run()`.
4. **After generating code**: Follow [Dev Workflow](references/dev-workflow.md) — give the developer the full run checklist and offer to run it for them.
5. **Errors**: Read [Common Errors](references/common-errors.md) before doing anything else.

## References

- [Core APIs](references/core.md): Verified examples for flows, structured output, streaming, tools.
- [Common Errors](references/common-errors.md): Known gotchas and fixes — read this first on any error.
- [Setup](references/setup.md): New project setup and pyproject.toml.
- [FastAPI](references/fastapi.md): Serving flows over HTTP, `genkit_fastapi_handler`, parallel flows.
- [Dotprompt](references/dotprompt.md): `.prompt` files, variants, helpers, streaming from prompts.
- [Evals](references/evals.md): Built-in + BYO evaluators, dataset format, LLM-judge pattern.
- [Dev Workflow](references/dev-workflow.md): Pre-run checklist, `genkit start`, Dev UI link + testing steps. **Read this after generating any code.**
