# Evaluation Guide: Agent Skills Strategy Comparison

This document defines the strategy for objectively evaluating two competing structures for the `skills` repository:
1.  **Unified / Feature-Centric (JS Simplified)** (defined in `docs/context_unified_js.md`)
2.  **Language-Centric (JS Simplified)** (defined in `docs/context_lang_js.md`)

## Objective
Determine which documentation strategy enables an AI agent to most accurately and efficiently implement Genkit features. We are measuring the "usability" of the documentation for an LLM.

## Methodology
We will use the `evals-app` to perform A/B testing. We will run the same set of developer tasks against two different "strategies".

### Test Setup
-   **Subject**: An AI Agent (Gemini via `evals-app`).
-   **Variables**:
    -   **Control (Strategy: Unified)**: Injects skills from `skills_unified/`.
    -   **Test (Strategy: Lang)**: Injects skills from `skills_lang/`.
-   **Task**: "Act as a developer. Use the available skills to perform the following task..."

### Success Metrics
1.  **Code Correctness (Compilability)**:
    -   **Metric**: `npx tsc --noEmit` exits with 0.
    -   **Why**: Ensures the agent understood the syntax examples in the guide.
2.  **Structure Adherence (Compliance)**:
    -   **Metric**: Does the generated file structure match the guide's specific rules (e.g., specific folder names or file placement)?
    -   **Why**: Tests if the agent can follow the organizational philosophy of the strategy.
3.  **Completeness**:
    -   **Metric**: Does the output contain the required components (e.g., `model`, `inputSchema`, `outputSchema` for a flow)?

## Test Cases

We will evaluate 6 scenarios covering the core Genkit development lifecycle (Flows, Models, Plugins).

1.  **Project Init**: Initialize a Genkit JS project (Baseline test).
2.  **Simple Flow**: Define a basic flow (Hello World).
3.  **Schema Flow**: Define a flow with Zod input/output schemas.
4.  **Streaming Flow**: Define a flow that supports streaming.
5.  **Model Usage**: Create a flow that uses `ai.generate` with the Google GenAI plugin.
6.  **Plugin Config**: Configure a secondary plugin (e.g., Pinecone or Chroma) in the project configuration.

## Application Updates (`evals-app`)

To support this evaluation, the `evals-app` requires the following updates:

### 1. Skill Injection Support
**Goal**: Provide the agent with the appropriate skills for the selected strategy.

*   **Modify `TestSchema`** (in `src/index.ts`):
    ```typescript
    const TestSchema = z.object({
      name: z.string(),
      strategy: z.enum(['unified', 'lang']), // New field
      // ... existing fields
    });
    ```
*   **Update `runAgent`**:
    *   Read `input.test.strategy`.
    *   **Install Skills**: Use `gemini skills install` to install skills from the local repository into the test workspace.
        *   **Unified**: Install all skills in `skills_unified/`.
        *   **Lang**: Install `skills_lang/genkit-js`.
    *   **Prompt Update**: Instruct the agent to "Use the available skills to perform the task".

### 2. New Evaluators
**Goal**: Verify file structure existence.

*   **Update `src/eval-actions.ts`**:
    *   `fileExistsEval`: Checks if a specific file path exists in the output workspace.

## Execution Plan
1.  **Refactor App**: Implement `strategy` support and skill installation in `evals-app`.
2.  **Create Datasets**:
    *   `datasets/unified_strategy.json` (using `strategy: "unified"`).
    *   `datasets/lang_strategy.json` (using `strategy: "lang"`).
3.  **Run Evals**: Execute both datasets.
4.  **Compare**: Analyze pass rates and output quality.
