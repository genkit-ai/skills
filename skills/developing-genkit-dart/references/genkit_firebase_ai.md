# Genkit Firebase AI Plugin (`genkit_firebase_ai`)

Calls Gemini **directly from Flutter apps** through
[Firebase AI Logic](https://firebase.google.com/docs/ai-logic) (built on the
`firebase_ai` SDK). Requests authenticate through the Firebase project and
**App Check**, so no model API key ships in the client binary. Targets
`genkit_firebase_ai` **1.0**. Platforms: Android, iOS, macOS, web (same as
`firebase_ai`).

Use it when generation, tool calling, or Live audio runs **on the client**. If
the Flutter app calls a backend over HTTP, use `genkit_google_genai` or
`genkit_vertexai` on the server instead.

- [Setup](#setup): Lines 27-71
- [Basic usage](#basic-usage): Lines 73-87
- [Models](#models): Lines 89-120
- [Configuration](#configuration): Lines 122-155
- [Model options (GeminiOptions)](#model-options-geminioptions): Lines 157-247
- [Structured output and tools](#structured-output-and-tools): Lines 249-266
- [Errors and cancellation](#errors-and-cancellation): Lines 268-295
- [Live API (experimental)](#live-api-experimental): Lines 297-326
- [Dev UI and traces](#dev-ui-and-traces): Lines 328-345
- [Migrating from 0.x](#migrating-from-0x): Lines 347-366

---

## Setup

1. [Set up Firebase AI Logic](https://firebase.google.com/docs/ai-logic/get-started?platform=flutter)
   and run `flutterfire configure`.
2. Set up [App Check](https://firebase.google.com/docs/ai-logic/app-check).
   Firebase **enforces App Check for AI Logic starting November 2, 2026**
   (delayable in the console, but not past January 21, 2027). Requests without
   a valid token are blocked, including already-released app versions.

```bash
flutter pub add genkit genkit_firebase_ai firebase_core firebase_ai firebase_app_check
```

Activate App Check **before the first model call**. The plugin reads App Check
and Firebase Auth from the `FirebaseApp` (there are no `appCheck` / `auth`
plugin params). Use debug providers only in debug builds:

- [Setup](#setup): Lines 24-68
- [Basic usage](#basic-usage): Lines 70-84
- [Models](#models): Lines 86-115
- [Configuration](#configuration): Lines 117-151
- [Model options (GeminiOptions)](#model-options-geminioptions): Lines 153-252
- [Structured output and tools](#structured-output-and-tools): Lines 254-271
- [Errors and cancellation](#errors-and-cancellation): Lines 273-301
- [Live API (experimental)](#live-api-experimental): Lines 303-331
- [Dev UI and traces](#dev-ui-and-traces): Lines 333-349
- [Migrating from 0.x](#migrating-from-0x): Lines 351-378

## Setup

1. [Set up Firebase AI Logic](https://firebase.google.com/docs/ai-logic/get-started?platform=flutter)
   and run `flutterfire configure`.
2. Set up [App Check](https://firebase.google.com/docs/ai-logic/app-check).
   Firebase **enforces App Check for AI Logic starting November 2, 2026**
   (delayable in the console, but not past January 21, 2027). Requests without
   a valid token are blocked, including already-released app versions.

```bash
flutter pub add genkit genkit_firebase_ai firebase_core firebase_ai firebase_app_check
```

Activate App Check **before the first model call**. The plugin reads App Check
and Firebase Auth from the `FirebaseApp` (there are no `appCheck` / `auth`
plugin params). Use debug providers only in debug builds:

```dart
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import 'firebase_options.dart';

Future<void> initFirebase() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  await FirebaseAppCheck.instance.activate(
    providerAndroid: kDebugMode
        ? const AndroidDebugProvider()
        : const AndroidPlayIntegrityProvider(),
    providerApple: kDebugMode
        ? const AppleDebugProvider()
        : const AppleAppAttestWithDeviceCheckFallbackProvider(),
    providerWeb: kDebugMode
        ? WebDebugProvider()
        : ReCaptchaEnterpriseProvider('your-recaptcha-site-key'),
  );
}
```

Never ship debug providers in release builds. Each debug provider logs a debug
token on first run (browser console on web); register it under **App Check >
Apps > Manage debug tokens** in the Firebase console.

## Basic usage

```dart
import 'package:genkit/genkit.dart';
import 'package:genkit_firebase_ai/genkit_firebase_ai.dart';

final ai = Genkit(plugins: [firebaseAI()]);

final response = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'Tell me a joke about a developer.',
  use: [retry(maxRetries: 2)],
);
print(response.text);
```

## Models

`firebaseAI.gemini('<model-id>')` resolves names dynamically, so any model
Firebase AI Logic serves works, including ones newer than the plugin. Current
models are also pre-registered (so they show in the Dev UI with capabilities):

- Text/multimodal: `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash`,
  `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.1-pro-preview`.
  On `FirebaseAiProvider.googleAI()` only: `gemini-flash-latest`,
  `gemini-3.7-flash`, `gemini-3.6-flash` (**`-latest` aliases are not
  available on Agent Platform**).
- Image: `gemini-nano-banana-2.1`, `gemini-3.1-flash-image`,
  `gemini-3.1-flash-lite-image`, `gemini-3-pro-image`.
- TTS: `gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`.
- Live: `gemini-3.8-live` (both providers);
  `gemini-live-2.5-flash-native-audio` (Agent Platform only).

**Shipped apps: read the model name from Remote Config.** A model id compiled
into a mobile binary breaks when that model retires. Firebase recommends
[changing the model name remotely](https://firebase.google.com/docs/ai-logic/change-model-name-remotely)
(`flutter pub add firebase_remote_config`):

```dart
final remoteConfig = FirebaseRemoteConfig.instance;
await remoteConfig.setDefaults({'model_name': 'gemini-3.8-flash'});
await remoteConfig.fetchAndActivate();

final response = await ai.generate(
  model: firebaseAI.gemini(remoteConfig.getString('model_name')),
  prompt: 'Tell me a joke about a developer.',
);
```

## Configuration

```dart
final ai = Genkit(plugins: [
  firebaseAI(
    app: Firebase.app('my-app'), // optional, defaults to the default app
    provider: const FirebaseAiProvider.agentPlatform(), // default: .googleAI()
    useLimitedUseAppCheckTokens: true, // for App Check replay protection
    httpClient: myHttpClient, // optional; never closed by the plugin
  ),
]);
```

- `FirebaseAiProvider.googleAI()` (default): Gemini Developer API.
- `FirebaseAiProvider.agentPlatform({String? location})`: Gemini Enterprise
  (Agent Platform, formerly Vertex AI). `location` defaults to `'global'`.
  Text models live on `'global'` and can fail with `NOT_FOUND` on regional
  endpoints; **Live models need a regional location** (e.g. `'us-central1'`).
  One plugin instance targets one location, so apps using both create two
  `Genkit` instances:

  ```dart
  final ai = Genkit(
    plugins: [firebaseAI(provider: const FirebaseAiProvider.agentPlatform())],
  );
  final liveAi = Genkit(plugins: [
    firebaseAI(
      provider: const FirebaseAiProvider.agentPlatform(location: 'us-central1'),
    ),
  ]);
  ```

- `httpClient` routes `generateContent` / `streamGenerateContent` (proxies,
  logging, test mocks). Live uses a WebSocket and ignores it.

## Model options (`GeminiOptions`)

**Naming gotcha:** this plugin's `GeminiOptions` uses `ThinkingConfig` and
`SpeechConfig` (unprefixed), unlike `genkit_google_genai`'s
`GeminiThinkingConfig` / `GeminiSpeechConfig`. Safety, search, maps, and image
config are prefixed (`GeminiSafetySettings`, `GeminiGoogleSearch`,
`GeminiUrlContext`, `GeminiGoogleMaps`, `GeminiImageConfig`).

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-3.8-flash'),
  prompt: 'Compare two approaches to offline sync in mobile apps.',
  config: GeminiOptions(
    maxOutputTokens: 2048,
    thinkingConfig: ThinkingConfig(thinkingLevel: 'HIGH', includeThoughts: true),
  ),
);
print(response.message?.content.map((p) => p.reasoning).nonNulls.join('\n'));
```

- **Thinking:** Gemini 3+ takes uppercase `thinkingLevel` (`'MINIMAL'`,
  `'LOW'`, `'MEDIUM'`, `'HIGH'`; varies by model, `gemini-3.8-flash` rejects
  `'MINIMAL'`). Older models use `thinkingBudget`. Setting both fails with
  `INVALID_ARGUMENT`. Thought signatures round-trip automatically via
  `metadata['thoughtSignature']` when you pass response messages back.
- **Sampling on Gemini 3+:** `temperature`, `topP`, `topK` are ignored,
  `candidateCount` is unsupported, `presencePenalty` / `frequencyPenalty` may
  400.
- **Safety:** `safetySettings: [GeminiSafetySettings(category:
  'HARM_CATEGORY_HARASSMENT', threshold: 'BLOCK_ONLY_HIGH')]`.
  `HARM_CATEGORY_IMAGE_*` and `method` are Agent Platform only.
- **Grounding:** `googleSearch: GeminiGoogleSearch()`,
  `urlContext: GeminiUrlContext()`, and
  `googleMaps: GeminiGoogleMaps()` with
  `retrievalConfig: GeminiRetrievalConfig(latLng: GeminiLatLng(latitude: ...,
  longitude: ...))`. Metadata is in `response.custom?['groundingMetadata']`
  (`webSearchQueries`, `groundingChunks`, `groundingSupports`,
  `searchEntryPoint`) and `urlContextMetadata`. With Google Search grounding
  you MUST display `searchEntryPoint.renderedContent` and the sources.
- **Image generation:** `responseModalities: ['TEXT', 'IMAGE']`,
  `imageConfig: GeminiImageConfig(aspectRatio: '16:9', imageSize: '2K')`;
  read `response.media` (a `data:` URL).
- **Media resolution:** `mediaResolution: 'MEDIA_RESOLUTION_LOW' | _MEDIUM |
  _HIGH`; per-part override via `MediaPart(metadata: {'mediaResolution':
  'MEDIA_RESOLUTION_ULTRA_HIGH'})`.
- **Code execution:** `codeExecution: true`; results come back as custom parts
  (`executableCode`, `codeExecutionResult`).

Multi-speaker TTS (attach `speechMetadata` to each `TextPart`, matching the
speaker names):

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-3.8-flash-tts'),
  promptParts: [
    TextPart(
      text: 'Did we ship it?',
      metadata: {'speechMetadata': {'speaker': 'Joe', 'style': 'nervous'}},
    ),
    TextPart(
      text: 'We shipped it.',
      metadata: {'speechMetadata': {'speaker': 'Jane'}},
    ),
  ],
  config: GeminiOptions(
    responseModalities: ['AUDIO'],
    speechConfig: SpeechConfig(
      multiSpeakerVoiceConfig: MultiSpeakerVoiceConfig(
        speakerVoiceConfigs: [
          SpeakerVoiceConfig(
            speaker: 'Joe',
            voiceConfig: VoiceConfig(
              prebuiltVoiceConfig: PrebuiltVoiceConfig(voiceName: 'Kore'),
            ),
          ),
          SpeakerVoiceConfig(
            speaker: 'Jane',
            voiceConfig: VoiceConfig(
              prebuiltVoiceConfig: PrebuiltVoiceConfig(voiceName: 'Puck'),
            ),
          ),
        ],
      ),
      languageCode: 'en-US',
    ),
  ),
);
final audio = response.media; // Media(url: 'data:audio/...;base64,...')
```

Single-speaker: `SpeechConfig(voiceConfig: VoiceConfig(...))`.

## Structured output and tools

`outputSchema` is forwarded **unchanged** as `responseJsonSchema` (keeps
`enum`, `anyOf`, `$ref`, `additionalProperties`, etc.); tool input schemas go
unchanged as `parametersJsonSchema`. Use `schemantic` types as usual
([schemantic.md](schemantic.md)):

```dart
final colors = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'List three primary colors.',
  outputSchema: .list(.string()),
);
print(colors.output); // List<String>
```

Tools: `ai.defineTool(...)` then `toolNames: ['getWeather']` on `generate`,
same as any other model (see [genkit.md](genkit.md)).

## Errors and cancellation

Errors map to `GenkitException` with a `StatusCode` (`RESOURCE_EXHAUSTED` for
quota, `UNAVAILABLE` for transient failures, `FAILED_PRECONDITION` for a
safety-blocked prompt); the original `firebase_ai` / network exception is its
`cause`. `ai.generate()` reports model errors **in the response** rather than
throwing:

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'Hello',
  use: [retry(maxRetries: 2)], // retries transient statuses, not safety blocks
);
if (response.finishReason == FinishReason.failed) {
  print('${response.error?.status}: ${response.error?.message}');
  // response.cause is the GenkitException
}

// Stop button:
final controller = CancellationController();
final future = ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'Write a long story.',
  cancel: controller.token,
);
controller.cancel('user pressed stop'); // finishes with FinishReason.aborted
```

## Live API (experimental)

Bidirectional audio/text/video over a WebSocket via `ai.generateBidi()` from
`package:genkit/experimental.dart`. Note it takes a **string** model id with
the `firebaseai/` prefix:

```dart
import 'package:genkit/experimental.dart';

final session = await ai.generateBidi(
  model: 'firebaseai/gemini-3.8-live',
  config: LiveGenerationConfig(
    responseModalities: ['AUDIO'],
    speechConfig: SpeechConfig(
      voiceConfig: VoiceConfig(
        prebuiltVoiceConfig: PrebuiltVoiceConfig(voiceName: 'Algenib'),
      ),
    ),
  ),
  system: 'You are a friendly assistant.', // only at session open
);
session.send('Hello');
session.stream.listen((chunk) {/* audio media parts as data: URLs */});
```

- Agent Platform: Live needs a regional `location` (`'global'` closes the
  session).
- Flutter **web** + enforced App Check: Live fails (browser WebSockets can't
  carry the App Check header, flutterfire#18938). Mobile/macOS work.
- Sending a system message mid-session fails with `INVALID_ARGUMENT`.

## Dev UI and traces

`genkit start:flutter` launches the Flutter app with the Dev UI
(http://localhost:4000, `-o` opens it) and passes the needed `--dart-define`
flags, so traces and registered models/flows/tools show up:

```bash
genkit start:flutter
genkit start:flutter -- -d chrome   # flutter run flags after --
```

If Flutter is launched separately (IDE debugger), write the env to a file
(gitignore it) and pass it in:

```bash
genkit start --write-env-file=genkit.env --experimental-reflection-v2
flutter run --dart-define-from-file=genkit.env -d chrome
```

## Migrating from 0.x

| Old                                                  | 1.0                                                                                  |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `FirebaseAiProvider.vertexAI` (default `us-central1`) | `FirebaseAiProvider.agentPlatform` (default `'global'`; pass `location: 'us-central1'` for the old endpoint) |
| `firebaseAI(appCheck: ..., auth: ...)`               | Removed; activate `FirebaseAppCheck` / `FirebaseAuth` on the `FirebaseApp` before the first call (`firebase_ai` >= 5.1.0) |
| `GeminiOptions.responseSchema`                       | `outputSchema` on `generate`, or `responseMimeType` + `responseJsonSchema`           |
| `toGemini*`, `fromGemini*`, `extractUsage`, `runLiveSession` | Private; use `ai.generate()` / `ai.generateBidi()`                            |
| `firebaseAiModelInfo`                                | Removed; each model has `metadata['model']`                                          |
| `GeminiOptions.responseLogprobs`, `logprobs`         | Removed (unsupported by AI Logic)                                                    |
| `firebase_ai` finish reason enum names               | `FinishReason.stop` / `length` / `blocked` / `other` / `unknown`; raw value in `response.custom?['finishReason']` |

Behavior changes: schemas are no longer converted to OpenAPI-style (keywords
like `enum`, `oneOf`, `additionalProperties`, `default` now reach the model, so
output can differ); errors are `GenkitException`s; server-closed Live sessions
end with an error instead of a normal stop.

Full runnable sample (chat, structured streaming, grounding, tools, Live
audio):
[`testapps/firebase_ai`](https://github.com/genkit-ai/genkit-dart/tree/main/testapps/firebase_ai).
