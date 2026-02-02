# Plugins

Install and configure plugins.

```bash
npm install @genkit-ai/google-genai
```

Configure in `genkit({...})`:

```ts
import { googleAI } from "@genkit-ai/google-genai";

const ai = genkit({
  plugins: [googleAI()],
});
```
