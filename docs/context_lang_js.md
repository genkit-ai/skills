# Language-Centric Strategy (JS Context)

## Overview
This guide defines the "Language-Centric" strategy for Genkit skills. All Node.js/TypeScript functionality is consolidated into a single `genkit-js` skill.

## Structure
```
genkit-js/
├── SKILL.md            # Entry Point: Setup & Config
└── references/
    ├── flows.md        # How to write Flows
    ├── models.md       # How to generate content
    └── plugins.md      # How to configure Plugins
```

## Core Components

### 1. Setup (`SKILL.md`)
*   Initialize with `genkit init`.
*   Entry point: `src/index.ts`.
*   Configuration: `configureGenkit` in `src/index.ts`.

### 2. Flows (`references/flows.md`)
*   Use `ai.defineFlow`.
*   Input/Output schemas via Zod (`z`).
*   Streaming support.

### 3. Models (`references/models.md`)
*   Use `ai.generate`.
*   Standard plugin: `@genkit-ai/google-genai`.

### 4. Plugins (`references/plugins.md`)
*   Install via `npm install`.
*   Configure in `configureGenkit` plugins array.
