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

## Google GenAI Plugin

### Installation

To use Gemini models with Genkit, you need to install the Google GenAI plugin:

```bash
npm i @genkit-ai/google-genai
```

and configure it for the Gemini API or Vertex AI API depending on the user's needs:

```ts
import { googleAI } from '@genkit-ai/google-genai'; // for Gemini API
import { vertexAI } from '@genkit-ai/google-genai'; // for Vertex AI API

const ai = genkit({
  // ...
  plugins: [
    googleAI(), // for Gemini API, GEMINI_API_KEY env variable must be set
    vertexAI({ location: 'global' }), // for Vertex AI, Google Application Default Credentials must be available
  ],
});

googleAI.model('gemini-3-flash-preview'); // specify models for Gemini API
vertexAI.model('gemini-3-pro-preview'); // specify models for Vertex AI API
```
