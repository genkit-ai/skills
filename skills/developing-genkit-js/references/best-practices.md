# Genkit Best Practices

## Project Structure
-   **Organized Layout**: Keep flows and tools in separate directories (e.g., `src/flows`, `src/tools`) to maintain a clean codebase.
-   **Index Exports**: Use `index.ts` files to export flows and tools, making it easier to import them into your main configuration.

## Model Selection
-   **Gemini Models**: ALWAYS use the latest generation (`gemini-3-*` or `gemini-2.5-*`).
    -   **NEVER** use `gemini-2.0-*` or `gemini-1.5-*` series, as they are older generations.
    -   **Recommended**: `gemini-2.5-flash` for general use, `gemini-3-pro-preview` for complex tasks.

## Schema Definition
-   **Use `z` from `genkit`**: Always import `z` from the `genkit` package to ensure compatibility.
    ```ts
    import { z } from "genkit";
    ```
-   **Descriptive Schemas**: Use `.describe()` on Zod fields. LLMs use these descriptions to understand how to populate the fields.

## Flow & Tool Design
-   **Modularize**: Keep flows and tools in separate files/modules and import them into your main Genkit configuration.
-   **Single Responsibility**: Tools should do one thing well. Complex logic should be broken down.

## Configuration
-   **Environment Variables**: Store sensitive keys (like API keys) in environment variables or `.env` files. Do not hardcode them.

## Development
-   **Use Dev Mode**: Run your app with `genkit start` to enable the Developer UI and hot reloading (if configured with a watcher).
