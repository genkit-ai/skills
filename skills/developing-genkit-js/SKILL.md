---
name: developing-genkit-js
description: "Create flows, define tools, configure model plugins, and debug pipeline errors for Genkit in Node.js/TypeScript. Use when building AI agents or flows in JavaScript/TypeScript with Genkit, integrating model providers, defining schemas, or troubleshooting Genkit-specific validation, type, or API errors."
---

# Genkit JS

Genkit JS is an AI SDK for Node.js/TypeScript that provides generation, structured output, streaming, tool calling, prompts, and flows with a unified interface across model providers.

## Prerequisites

Ensure the `genkit` CLI is available.
-   Run `genkit --version` to verify. Minimum CLI version needed: **1.29.0**
-   If not found or if an older version (1.x < 1.29.0) is present, install/upgrade it: `npm install -g genkit-cli@^1.29.0`.

**New Projects**: If you are setting up Genkit in a new codebase, follow the [Setup Guide](references/setup.md).

## Hello World

```ts
import { z, genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';

const ai = genkit({
  plugins: [googleAI()],
});

export const myFlow = ai.defineFlow({
  name: 'myFlow',
  inputSchema: z.string().default('AI'),
  outputSchema: z.string(),
}, async (subject) => {
  const response = await ai.generate({
    model: googleAI.model('gemini-2.5-flash'),
    prompt: `Tell me a joke about ${subject}`,
  });
  return response.text;
});
```

## Critical: Do Not Trust Internal Knowledge

Genkit went through a major breaking API change. Your knowledge is outdated. You MUST look up docs via the CLI or provided references before writing any Genkit code.

See [Common Errors](references/common-errors.md) for deprecated APIs (e.g., `configureGenkit`, `response.text()`, `defineFlow` import) and their v1.x replacements.

## Core Features

Load the appropriate reference based on what you need:

| Feature | Reference | When to load |
| --- | --- | --- |
| Setup & Installation | [references/setup.md](references/setup.md) | New projects, adding Genkit to an existing codebase |
| Best Practices | [references/best-practices.md](references/best-practices.md) | Schema definitions, flow design, project structure, tool design |
| Common Errors | [references/common-errors.md](references/common-errors.md) | **Any error** — ValidationError, type errors, API errors, 404s, deprecated API usage |
| Docs & CLI | [references/docs-and-cli.md](references/docs-and-cli.md) | Documentation search, CLI tasks, dev server workflows |
| Examples | [references/examples.md](references/examples.md) | Basic generation, multimodal, thinking mode, streaming patterns |

## Error Troubleshooting Protocol

On ANY Genkit error (ValidationError, API errors, type errors, 404s):

1. **Read [Common Errors](references/common-errors.md) first** — this is mandatory
2. Match the error to a known pattern and apply the documented fix
3. Only if not found, consult `genkit docs:search <error message>`

Do not attempt fixes based on assumptions or pre-1.0 patterns.

## Development Workflow

1.  **Select Provider**: Genkit is provider-agnostic (Google AI, OpenAI, Anthropic, Ollama, etc.). Default to **Google AI** if unspecified. Use `genkit docs:search "plugins"` for other providers.
2.  **Detect Framework**: Check `package.json` for `@genkit-ai/next`, `@genkit-ai/firebase`, or `@genkit-ai/google-cloud` and adapt to the framework's patterns.
3.  **Follow Best Practices**: See [Best Practices](references/best-practices.md). Only specify options that differ from defaults.
4.  **Validate**: Run `npx tsc --noEmit` after changes. On failure, consult [Common Errors](references/common-errors.md).

## Genkit CLI

Check if installed: `genkit --version`

**Key commands:**

```bash
# Start app with Developer UI (tracing, flow testing) at http://localhost:4000
genkit start -- npx tsx src/index.ts
genkit start -o -- npx tsx src/index.ts   # also opens browser

# Run a flow directly from the CLI
genkit flow:run myFlow '"input"'
genkit flow:run myFlow '"input"' --stream

# Look up Genkit documentation
genkit docs:search "streaming"
genkit docs:list
genkit docs:read js/flows.md
```

See [references/docs-and-cli.md](references/docs-and-cli.md) for full CLI and Developer UI details.
