# Setup — Genkit Python

## New project

```bash
mkdir my-app && cd my-app
uv init
uv add genkit genkit-plugin-google-genai
export GEMINI_API_KEY=your_key_here
```

## Plugin naming pattern

All plugins follow `genkit-plugin-*` and are published on PyPI, for example:
- `genkit-plugin-google-genai` — Google AI (Gemini API key)
- `genkit-plugin-vertex-ai` — Vertex AI (GCP credentials)
- `genkit-plugin-anthropic` — Anthropic
- `genkit-plugin-fastapi` — FastAPI HTTP server

Install any of them with `uv add genkit-plugin-<name>` (or `pip install genkit-plugin-<name>`).

## pyproject.toml

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

## Python version

Requires Python 3.14+. Use `uv python pin 3.14` or `uv venv --python 3.14 .venv` if you need a specific interpreter.
