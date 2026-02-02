# Unified Strategy (JS Context)

## Overview
This guide defines the "Unified" strategy for Genkit skills. Skills are organized by **Feature**, with language-specific details in `references/`.

## Structure
```
genkit-flows/
├── SKILL.md            # Concept: What is a Flow?
└── references/
    └── nodejs.md       # Implementation: How to write a Flow in Node.js
```

## Core Skills

### 1. `genkit-basics`
*   **Purpose**: Setup and configuration.
*   **JS Implementation**:
    *   Initialize with `genkit init`.
    *   `src/index.ts` is the entry point.
    *   `configureGenkit` sets up plugins and log levels.

### 2. `genkit-flows`
*   **Purpose**: Defining executable logic.
*   **JS Implementation**:
    *   Use `ai.defineFlow`.
    *   Schemas defined using Zod (`z`).
    *   Supports streaming via `streamingCallback`.

### 3. `genkit-models`
*   **Purpose**: Generating content.
*   **JS Implementation**:
    *   `ai.generate` for text generation.
    *   Use `googleAI` plugin models (e.g., `gemini15Flash`).

### 4. `genkit-plugins`
*   **Purpose**: Extensions.
*   **JS Implementation**:
    *   Import plugins (e.g., `@genkit-ai/google-genai`).
    *   Add to `plugins` array in `configureGenkit`.
