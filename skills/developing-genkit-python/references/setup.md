# Setup — Genkit Python

## New project

**Always use a virtual environment** — never install Genkit into the system interpreter. With **uv**, the project’s **`.venv`** is created and used by `uv sync` / `uv run` automatically once you add dependencies.

```bash
mkdir my-app && cd my-app
uv init
uv venv --python 3.12 .venv
# Unix: source .venv/bin/activate
# Windows: .venv\Scripts\activate
uv add genkit genkit-google-genai
export GEMINI_API_KEY=your_key_here
```

Import the Google AI plugin as:

```python
from genkit_google_genai import GoogleAI
```

`uv init` creates `pyproject.toml`. Add your app under something like `src/main.py` (or match whatever layout `uv` generated) and point `genkit start` at that entrypoint.

## pyproject.toml

Minimal `[project]` block with unpinned Genkit deps (resolver picks compatible releases):

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = [
    "genkit",
    "genkit-google-genai",
]
```

## Plugins

Packages are **`genkit-*`** on PyPI, e.g. `genkit-google-genai`, `genkit-vertexai`,
`genkit-anthropic`, `genkit-fastapi`, `genkit-middleware`, `genkit-evaluators`.
Install with `uv add genkit-<name>`.

Import modules use underscores (e.g. `genkit_google_genai`, `genkit_middleware`).
See [Examples](examples.md) and [Agents](agents.md).

## Python version

**3.10+**. Prefer a project venv: `uv venv --python 3.12 .venv` (or newer) before you run commands.
