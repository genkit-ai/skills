# Genkit Vertex AI Plugin (`genkit_vertexai`)

Gemini models and embedders through Vertex AI (Gemini Enterprise API), with
Google Cloud authentication instead of an API key. Same model surface and option
types as [genkit_google_genai](genkit_google_genai.md), which it re-exports
(`GeminiOptions`, `GeminiThinkingConfig`, `GoogleGenAiEmbedderOptions`, ...).

```bash
dart pub add genkit genkit_vertexai
```

## Setup

```dart
import 'package:genkit/genkit.dart';
import 'package:genkit_vertexai/genkit_vertexai.dart';

void main() async {
  final ai = Genkit(
    plugins: [
      vertexAI(
        projectId: 'my-project', // default: $GOOGLE_CLOUD_PROJECT / $GCLOUD_PROJECT
        location: 'us-central1', // default: 'global'
      ),
    ],
  );

  final response = await ai.generate(
    model: vertexAI.gemini('gemini-3.6-flash'),
    prompt: 'Tell me a joke about a developer.',
    use: [retry()],
  );
  print(response.text);
}
```

- **Auth:** Application Default Credentials. Locally run
  `gcloud auth application-default login`; on Cloud Run and other Google Cloud
  runtimes it is automatic. The account needs `roles/aiplatform.user`.
- **No API key.** For API-key access use `genkit_google_genai` (`googleAI()`).
- `authClient:` takes your own authenticated `http.Client`; the plugin never
  closes it.

## Model IDs

Use versioned Vertex model IDs (`gemini-3.6-flash`, `gemini-3.1-pro-preview`,
`gemini-3.5-flash-lite`, ...). The Gemini API's `-latest` aliases
(`gemini-flash-latest`, `gemini-pro-latest`) **do not exist on Vertex** and
fail at request time. Vertex TTS models use their own IDs (e.g.
`gemini-2.5-flash-tts`), not the Gemini API TTS names.

```dart
final response = await ai.generate(
  model: vertexAI.gemini('gemini-3.6-flash'),
  prompt: 'What are the top tech news stories this week?',
  config: GeminiOptions(
    thinkingConfig: GeminiThinkingConfig(thinkingLevel: 'LOW'),
    googleSearch: GeminiGoogleSearch(),
  ),
);
```

## Embeddings

`text-embedding-*`, `gemini-embedding-*` and `multimodalembedding` all go
through `vertexAI.textEmbedding`:

```dart
final embeddings = await ai.embed(
  embedder: vertexAI.textEmbedding('gemini-embedding-001'),
  documents: [DocumentData(content: [TextPart(text: 'Hello world')])],
  options: GoogleGenAiEmbedderOptions(
    outputDimensionality: 256,
    taskType: 'RETRIEVAL_DOCUMENT',
  ),
);
```

`multimodalembedding` embeds text, images and video (`MediaPart` with a `data:`,
`gs://` or `https` URL plus `contentType`). One document can yield several
embeddings (one per modality / video segment); map them back with
`embedding.metadata?['documentIndex']`, `['modality']`, `['partIndex']`,
`['segmentIndex']`.
