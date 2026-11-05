# Dev Workflow — Genkit Python

## Agent Responsibility

After generating or migrating code:
1. Run the project's type checker (`pyright`, `mypy`, or `ty`) in `.venv` so typed configs (`GeminiConfig`), generic contexts (`FlowContext[T]`, `ToolContext[T]`), keyword-only signatures, and `OutputT | None` checks pass before handing off.
2. Give the developer:
   - Copy-paste setup commands with absolute paths
   - The `genkit start` command to run in their foreground terminal (expected to block)
   - Exact Dev UI steps to exercise the flow or agent and inspect traces

Do not run `genkit start` as an interactive blocking command on the developer's behalf unless explicitly asked; use `genkit flow:run` for automated one-shot verification.

---

## Step 1 — Get a Gemini API Key

If the developer needs a key, create one at `https://aistudio.google.com/apikey`.

---

## Step 2 — Export the API Key

```bash
export GEMINI_API_KEY=your-api-key-here
```

Persist across shell sessions if desired:

```bash
echo 'export GEMINI_API_KEY=your-api-key-here' >> ~/.zshrc && source ~/.zshrc
```

---

## Step 3 — Install Dependencies

Replace `/path/to/your-project` with the project's absolute path:

```bash
cd /path/to/your-project
uv add 'genkit==0.13.*' 'genkit-google-genai==0.13.*'
```

(Run `uv init` first if `pyproject.toml` does not exist yet — see [Setup](setup.md).)

---

## Step 4 — Start the Dev UI

Run in a foreground terminal (blocks until stopped with `Ctrl+C`):

```bash
cd /path/to/your-project
GEMINI_API_KEY=your-api-key-here genkit start -- uv run src/main.py
```

For FastAPI apps, `GENKIT_ENV=dev` (set by `genkit start`) automatically starts the reflection server on a background thread, so hot-reload works too:

```bash
GEMINI_API_KEY=your-api-key-here genkit start -- uv run uvicorn main:app --reload
```

Wait for the CLI to print the Dev UI URL (typically `http://localhost:4000`).

---

## Step 5 — Test in the Dev UI

1. Open **`http://localhost:4000`** in a browser.
2. Select **Run** in the left sidebar and pick the registered flow, prompt, or model.
3. Paste JSON matching the flow's single input parameter, e.g.:
   ```json
   {"text": "hello world"}
   ```
4. Click **Run** and inspect the validated output on the right.
5. Open **Traces** in the left sidebar to inspect every span, rendered prompt, tool call, token count, latency, and unwrapped error stack trace.

---

## CLI Commands

`genkit start` wraps any Python program using Genkit, capturing local traces from every Genkit action while forwarding `stdin`/`stdout`. Running `uv run` directly skips local trace capture.

**Persistent dev runtime:**
```bash
genkit start -- uv run src/main.py
genkit start --noui -- uv run src/main.py                 # headless persistent runtime (still blocks)
genkit start --non-interactive -- uv run src/main.py      # skip first-run CLI prompts in CI/agents
```

**One-shot flow execution (`flow:run`):** spins up the runtime, executes one `@ai.flow()`, prints the `Trace ID`, and exits cleanly:
```bash
genkit flow:run myFlow '{"data": "input"}' -- uv run src/main.py
```
Note: `flow:run` runs `@ai.flow()` actions, not `ai.define_agent` directly. Wrap one agent turn inside a small `@ai.flow()` to test it via `flow:run` (see [Agents](agents.md)).

**Inspecting traces from the terminal:**
```bash
genkit trace:list                        # list recent trace IDs
genkit trace:get <traceId>               # human-readable trace view
genkit trace:get <traceId> --format json # clean JSON for jq / automated checks
```
Always use `--format json` when piping into `jq` or scripts; default output includes human-oriented formatting and may truncate large payloads.

**Built-in CLI documentation lookup:**
```bash
genkit docs:search "streaming" python
genkit docs:list python
genkit docs:read python/flows.md
```

---

## Troubleshooting

- `genkit: command not found` — `npm install -g genkit-cli`
- `GEMINI_API_KEY` missing — `export GEMINI_API_KEY=your-key`
- Port 4000 busy — `genkit start --port 4001 -- uv run src/main.py`
- `uv: command not found` — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Action missing in Dev UI — ensure standalone scripts enter via `ai.run_main(main())` and check terminal output for startup import or validation errors (see [Common Errors](common-errors.md)).
