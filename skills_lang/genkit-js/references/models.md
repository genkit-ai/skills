# Models

Generate content using `ai.generate`.

```ts
const { text } = await ai.generate({
  model: googleAI.model('gemini-2.5-flash'),
  prompt: "Hello Genkit",
});
```

## Structured Output

```ts
const { output } = await ai.generate({
  prompt: "Generate a character",
  output: { schema: z.object({ name: z.string() }) },
});
```
