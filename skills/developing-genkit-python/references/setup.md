# Setup — Genkit Python

## New project

```bash
mkdir my-app && cd my-app
uv init
uv add genkit genkit-plugin-google-genai
export GEMINI_API_KEY=your_key_here
```

`uv init` creates `pyproject.toml`. Add your app under something like `src/main.py` (or match whatever layout `uv` generated) and point `genkit start` at that entrypoint.

## pyproject.toml

Minimal `[project]` block with unpinned Genkit deps (resolver picks compatible releases):

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.14"
dependencies = [
    "genkit",
    "genkit-plugin-google-genai",
]
```

## Plugins

Packages are **`genkit-plugin-*`** on PyPI, e.g. `genkit-plugin-google-genai`, `genkit-plugin-vertex-ai`, `genkit-plugin-anthropic`, `genkit-plugin-fastapi`. Install with `uv add genkit-plugin-<name>`.

## Python version

**3.14+**. Use `uv python pin 3.14` or `uv venv --python 3.14 .venv` if you need a fixed interpreter.
