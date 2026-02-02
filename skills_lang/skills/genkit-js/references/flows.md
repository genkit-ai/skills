# Flows

Define flows to encapsulate logic, validation, and streaming.

```ts
const myFlow = ai.defineFlow(
  {
    name: "myFlow",
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (input) => {
    // Logic here
    return "result";
  }
);
```

Support for streaming:
```ts
const streamingFlow = ai.defineFlow(
  {
    name: "streamingFlow",
    inputSchema: z.string(),
    streamSchema: z.string(),
  },
  async (input, { sendChunk }) => {
    sendChunk("part 1");
    return "complete";
  }
);
```
