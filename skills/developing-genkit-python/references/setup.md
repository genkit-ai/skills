# Setup — Genkit Python
<!-- version: py-skill-2026-04-13-iter-1 -->

## New project

```bash
mkdir my-app && cd my-app
uv venv --python 3.12 .venv
uv pip install "genkit @ git+https://github.com/firebase/genkit.git#subdirectory=py/packages/genkit"
uv pip install "genkit-plugin-google-genai @ git+https://github.com/firebase/genkit.git#subdirectory=py/plugins/google-genai"
export GEMINI_API_KEY=your_key_here
```

## Plugin naming pattern

All plugins follow `genkit-plugin-*`:
- `genkit-plugin-google-genai` — Google AI (Gemini API key)
- `genkit-plugin-vertex-ai` — Vertex AI (GCP credentials)
- `genkit-plugin-anthropic` — Anthropic
- `genkit-plugin-fastapi` — FastAPI HTTP server

None are on PyPI yet. Install from git using `#subdirectory=py/plugins/<plugin-dir>`.

## pyproject.toml

```toml
[project]
name = "my-app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "genkit>=0.5",
    "genkit-plugin-google-genai>=0.5",
]
```

## Python version

Requires Python 3.12+. Use `uv venv --python 3.12` to ensure correct version.
