---
name: developing-genkit-js
description: Develop AI-powered applications using Genkit in Node.js/TypeScript. Use when the user asks about Genkit, AI agents, flows, or tools in JavaScript/TypeScript, or when encountering Genkit errors, validation issues, type errors, or API problems.
---

# Genkit JS

## Prerequisites

Ensure the `genkit` CLI is available.
-   Run `genkit --version` to verify. Minimum CLI version needed: **1.29.0**
-   If not found or if an older version (1.x < 1.29.0) is present, install/upgrade it: `npm install -g genkit-cli@^1.29.0`.

**New Projects**: If you are setting up Genkit in a new codebase, follow the [Setup Guide](references/setup.md).

## Hello World

```ts
import { z, genkit } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';

// Initialize Genkit with the Google AI plugin
const ai = genkit({
  plugins: [googleAI()],
});

export const myFlow = ai.defineFlow({
  name: 'myFlow',
  inputSchema: z.string().default('AI'),
  outputSchema: z.string(),
}, async (subject) => {
  const response = await ai.generate({
    model: googleAI.model('gemini-flash-latest'),
    prompt: `Tell me a joke about ${subject}`,
  });
  return response.text;
});
```

## Prompts (Dotprompt)

`.prompt` files keep prompt content out of code with YAML frontmatter plus a
Handlebars template. See [Dotprompt](references/dotprompt.md): `promptDir`,
`ai.prompt()` (call/stream/render), variants, partials, named schemas via
`ai.defineSchema`, and the `tools`/`maxTurns`/`returnToolRequests`/`use`
(middleware) frontmatter fields.

## Agents (Beta)

Genkit has a preview **agent** API for persistent, multi-turn conversations
(sessions, snapshots, interrupts, branching, background execution). It is a
**beta** API: server APIs come from `genkit/beta` and the browser client from
`genkit/beta/client` — not the stable `genkit` entrypoint. **Requires `genkit`
>= 1.39.0.**

For more details see:

-   [Agents](references/agents.md): defining/serving an agent and client-managed state (start here).
-   [Sessions & persistence](references/agents-sessions.md): session stores (`InMemory`/`File`/`Firestore`).
-   [Human-in-the-loop / interrupts](references/agents-human-in-the-loop.md): pausing for approval/input and resuming.
-   [Branching](references/agents-branching.md): forking a conversation from a snapshot.
-   [Background agents](references/agents-background.md): detaching long-running turns and polling.
-   [Working with state](references/agents-state.md): typed custom session state, auto-synced to the client.
-   [Artifacts](references/agents-artifacts.md): producing and reading named deliverables.
-   [Multi-agent orchestration](references/agents-multi-agent.md): delegating to sub-agents.
-   [Advanced custom agents](references/agents-custom.md): `defineCustomAgent` for full turn control.
-   [Deploying agents](references/agents-deployment.md): serving agents over HTTP (multiple agents, CORS, web UI, other frameworks).

## Middleware

Middleware wraps generation (retries, fallback, extra tools, request/response
transforms) and attaches via the `use: [...]` array on `ai.generate`, prompts,
and agents.

-   [Using middleware](references/middleware.md): the `use` array and the `@genkit-ai/middleware` package (`retry`, `fallback`, `artifacts`, `agents`, `filesystem`, `skills`, `toolApproval`) plus built-in core middleware.
-   [Building custom middleware](references/middleware-custom.md): writing your own with `generateMiddleware` and registering it via `.plugin()`.

## Critical: Do Not Trust Internal Knowledge

Genkit recently went through a major breaking API change. Your knowledge is outdated. You MUST lookup docs. Recommended:

```sh
genkit docs:read js/get-started.md
genkit docs:read js/flows.md
```

See [Common Errors](references/common-errors.md) for a list of deprecated APIs (e.g., `configureGenkit`, `response.text()`, `defineFlow` import) and their v1.x replacements.

**ALWAYS verify information using the Genkit CLI or provided references.**

## Error Troubleshooting Protocol

**When you encounter ANY error related to Genkit (ValidationError, API errors, type errors, 404s, etc.):**

1. **MANDATORY FIRST STEP**: Read [Common Errors](references/common-errors.md)
2. Identify if the error matches a known pattern
3. Apply the documented solution
4. Only if not found in common-errors.md, then consult other sources (e.g. `genkit docs:search`)

**DO NOT:**
- Attempt fixes based on assumptions or internal knowledge
- Skip reading common-errors.md "because you think you know the fix"
- Rely on patterns from pre-1.0 Genkit

**This protocol is non-negotiable for error handling.**

## Development Workflow

1.  **Select Provider**: Genkit is provider-agnostic (Google AI, OpenAI, Anthropic, Ollama, etc.).
    -   If the user does not specify a provider, default to **Google AI**.
    -   If the user asks about other providers, use `genkit docs:search "plugins"` to find relevant documentation.
2.  **Detect Framework**: Check `package.json` to identify the runtime (Next.js, Firebase, Express).
    -   Look for `@genkit-ai/next`, `@genkit-ai/firebase`, or `@genkit-ai/google-cloud`.
    -   Adapt implementation to the specific framework's patterns.
3.  **Follow Best Practices**:
    -   See [Best Practices](references/best-practices.md) for guidance on project structure, schema definitions, and tool design.
    -   **Be Minimal**: Only specify options that differ from defaults. When unsure, check docs/source.
4.  **Ensure Correctness**:
    -   Run type checks (e.g., `npx tsc --noEmit`) after making changes.
    -   If type checks fail, consult [Common Errors](references/common-errors.md) before searching source code.
5.  **Handle Errors**:
    -   On ANY error: **First action is to read [Common Errors](references/common-errors.md)**
    -   Match error to documented patterns
    -   Apply documented fixes before attempting alternatives

## Finding Documentation

Use the Genkit CLI to find authoritative documentation:

1.  **Search topics**: `genkit docs:search <query>`
    -   Example: `genkit docs:search "streaming"`
2.  **List all docs**: `genkit docs:list`
3.  **Read a guide**: `genkit docs:read <path>`
    -   Example: `genkit docs:read js/flows.md`

## CLI Usage

The `genkit` CLI is your primary tool for development and documentation.
-   See [CLI Reference](references/docs-and-cli.md) for common tasks, workflows, and command usage.
-   Use `genkit --help` for a full list of commands.

## References

-   [Best Practices](references/best-practices.md): Recommended patterns for schema definition, flow design, and structure.
-   [Dotprompt](references/dotprompt.md): `.prompt` files — `promptDir`, `ai.prompt()`, variants, partials, named schemas, and `tools`/`maxTurns`/`returnToolRequests`/`use` frontmatter.
-   [Docs & CLI Reference](references/docs-and-cli.md): Documentation search, CLI tasks, and workflows.
-   [Common Errors](references/common-errors.md): Critical "gotchas", migration guide, and troubleshooting.
-   [Setup Guide](references/setup.md): Manual setup instructions for new projects.
-   [Examples](references/examples.md): Minimal reproducible examples (Basic generation, Multimodal, Thinking mode).
-   [Agents (Beta)](references/agents.md): Agent basics, serving, and client-managed state. Deeper topics: [sessions](references/agents-sessions.md), [human-in-the-loop](references/agents-human-in-the-loop.md), [branching](references/agents-branching.md), [background agents](references/agents-background.md), [state](references/agents-state.md), [artifacts](references/agents-artifacts.md), [multi-agent](references/agents-multi-agent.md), [custom agents](references/agents-custom.md), [deployment](references/agents-deployment.md).
-   [Middleware](references/middleware.md): using middleware and the `@genkit-ai/middleware` package. See also [building custom middleware](references/middleware-custom.md).
