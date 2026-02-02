# Evaluation Guide: Agent Skills Strategy Comparison

This document defines the strategy for objectively evaluating two competing structures for the `skills` repository:
1.  **Unified / Feature-Centric (JS Simplified)** (defined in `docs/context_unified_js.md`)
2.  **Language-Centric (JS Simplified)** (defined in `docs/context_lang_js.md`)

## Objective
Determine which documentation strategy enables an AI agent to most accurately and efficiently implement Genkit features. We are measuring the "usability" of the documentation for an LLM.

## Methodology
We will use the `evals-app` to perform A/B testing. We will run the same set of developer tasks against two different "contexts" (the guides).

### Test Setup
-   **Subject**: An AI Agent (Gemini via `evals-app`).
-   **Variables**:
    -   **Control (Context A)**: `docs/context_unified_js.md` (Unified Strategy - JS Only).
    -   **Test (Context B)**: `docs/context_lang_js.md` (Language-Centric Strategy - JS Only).
-   **Task**: "Act as a developer. Using the provided implementation guide as your primary reference, perform the following task..."

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

### 1. Context Injection Support
**Goal**: Allow passing a text file (the Guide) to the agent as "System Knowledge".

*   **Modify `TestSchema`** (in `src/index.ts`):
    ```typescript
    const TestSchema = z.object({
      name: z.string(),
      contextFilePath: z.string().optional(), // New field
      // ... existing fields
    });
    ```
*   **Update `runAgent`**:
    *   Read `input.test.contextFilePath`.
    *   If present, read the file content.
    *   Prepend to prompt:
        ```text
        SYSTEM CONTEXT:
        The following text is the official Implementation Guide you must follow.
        
        [FILE CONTENT]
        
        TASK:
        [USER PROMPT]
        ```

### 2. New Evaluators
**Goal**: Verify file structure existence.

*   **Create `src/evaluators.ts`**:
    *   `fileExistsEval`: Checks if a specific file path exists in the output workspace.

## Execution Plan
1.  **Refactor App**: Implement `contextFilePath` support in `evals-app`.
2.  **Create Datasets**:
    *   `datasets/unified_strategy.json` (pointing to `IMPLEMENTATION_GUIDE.md`).
    *   `datasets/lang_strategy.json` (pointing to `IMPLEMENTATION_GUIDE_LANGUAGE_VARIANT.md`).
3.  **Run Evals**: Execute both datasets.
4.  **Compare**: Analyze pass rates and output quality.
