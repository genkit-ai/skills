# Genkit Documentation & CLI

This reference lists common tasks and workflows using the `genkit` CLI. For authoritative command details, always run `genkit --help` or `genkit <command> --help`.

## Prerequisites:

Ensure that the CLI is on `genkit-cli` version >= 1.29.0. If not, or if an older version (1.x < 1.29.0) is present, update the Genkit CLI version. Alternatively, to run commands with a specific version or without global installation, prefix them with `npx -y genkit-cli@^1.29.0`.

## Documentation

-   **Search docs**: `genkit docs:search <query>`
    -   Example: `genkit docs:search "streaming"`
    -   Example: `genkit docs:search "rag retrieval"`
-   **Read doc**: `genkit docs:read <path>`
    -   Example: `genkit docs:read js/overview.md`
-   **List docs**: `genkit docs:list`

## Development Workflow (recommended)

`genkit start` unintrusively wraps any Node.js program that uses the Genkit library, running it unchanged while discreetly collecting traces from every Genkit action. It forwards stdio, so interactive CLI tools that rely on stdin/stdout work without issues.

**Primary pattern:** prefix your normal run command. Collects telemetry from any Genkit code your program runs, whether triggered from the dev UI, your own web server/web UI, or a plain script. Useful for all local development and testing, even when you never open the dev UI. Starts the Developer UI (usually http://localhost:4000):

-   **Node.js (TypeScript)**:
    ```bash
    genkit start -- npx tsx --watch src/index.ts
    ```
-   **Next.js**:
    ```bash
    genkit start -- npx next dev
    ```
-   **Trace collection only** (lighter, no UI):
    ```bash
    genkit start --noui -- npx tsx src/index.ts
    ```

## Flow Execution (secondary)

-   **Run a flow**: `genkit flow:run <flowName> '<inputJSON>'`
    -   Executes a single flow directly from the CLI without driving your program's normal entrypoint. Useful for testing. Traces for the run can be inspected with the tracing commands below.
    -   **Simple Input**:
        ```bash
        genkit flow:run tellJoke '"chicken"'
        ```
    -   **Object Input**:
        ```bash
        genkit flow:run generateStory '{"subject": "robot", "genre": "sci-fi"}'
        ```
    -   **Single Command (spin up runtime & run flow)**:
        ```bash
        genkit flow:run tellJoke '"chicken"' -- npx tsx src/index.ts
        ```

## Evaluation


-   **Evaluate a flow**: `genkit eval:flow <flowName> [data]`
    -   Runs a flow and evaluates the output against configured evaluators.
    -   **Example (Single Input)**:
        ```bash
        genkit eval:flow answerQuestion '[{"testCaseId": "1", "input": {"question": "What is Genkit?"}}]'
        ```
    -   **Example (Batch Input)**:
        ```bash
        genkit eval:flow answerQuestion --input inputs.json
        ```
    -   **Single Command (spin up runtime & evaluate flow)**:
        ```bash
        genkit eval:flow answerQuestion --input inputs.json -- npx tsx src/index.ts
        ```

-   **Run Evaluation**: `genkit eval:run <dataset>`
    -   Evaluates a dataset against configured evaluators.
    -   **Example**:
        ```bash
        genkit eval:run dataset.json --output results.json
        ```

## Tracing

-   **Get a trace**: `genkit trace:get <traceId>`
    -   Retrieves detailed information for a specific trace by its ID. This is particularly useful for debugging failed model calls, inspecting tool execution, or analyzing the exact inputs and outputs of a specific step in your flow.
-   **List traces**: `genkit trace:list [options]`
    -   Lists recent traces. Use this to find trace IDs from recent executions.
