# Genkit Flows (Node.js)

Flows are the building blocks of Genkit applications. They wrap your AI logic to provide type safety, streaming, observability, and deployment capabilities.

## Defining Flows

Use `ai.defineFlow` to create a flow. It's best practice to use Zod objects for input and output schemas.

```ts
import { genkit, z } from 'genkit';
import { googleAI } from '@genkit-ai/google-genai';

const ai = genkit({
  plugins: [googleAI()],
});

export const menuSuggestionFlow = ai.defineFlow(
  {
    name: 'menuSuggestionFlow',
    inputSchema: z.object({ theme: z.string() }),
    outputSchema: z.object({ menuItem: z.string() }),
  },
  async ({ theme }) => {
    const { text } = await ai.generate({
      model: googleAI.model('gemini-2.5-flash'),
      prompt: `Invent a menu item for a ${theme} themed restaurant.`,
    });
    return { menuItem: text };
  },
);
```

## Flow Steps

Wrap operations in `ai.run` to create distinct steps in the trace viewer.

```ts
const menu = await ai.run('retrieve-menu', async () => {
  // Perform retrieval logic here
  return "Menu data";
});
```

## Streaming Flows

Flows support streaming partial results using `streamSchema` and the `sendChunk` callback.

```ts
export const menuSuggestionStreamingFlow = ai.defineFlow(
  {
    name: 'menuSuggestionStreamingFlow',
    inputSchema: z.object({ theme: z.string() }),
    streamSchema: z.string(), // Type of streamed chunks
    outputSchema: z.object({ menuItem: z.string() }), // Type of final output
  },
  async ({ theme }, { sendChunk }) => {
    const { stream, response } = ai.generateStream({
      model: googleAI.model('gemini-2.5-flash'),
      prompt: `Invent a menu item for a ${theme} themed restaurant.`,
    });

    for await (const chunk of stream) {
      sendChunk(chunk.text); // Send data to the client
    }

    const { text } = await response;
    return { menuItem: text };
  },
);
```

### Calling Streaming Flows

```ts
const response = menuSuggestionStreamingFlow.stream({ theme: 'bistro' });

for await (const chunk of response.stream) {
  console.log('chunk:', chunk);
}

const finalOutput = await response.output;
```

## Running and Debugging

**CLI**: Run flows directly from the terminal.
```bash
genkit flow:run menuSuggestionFlow '{"theme": "French"}' -s
```

**Developer UI**: Inspect traces and debug steps.
```bash
genkit start -- npx tsx --watch src/index.ts
```
