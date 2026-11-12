# Genkit Firebase AI Plugin (`genkit_firebase_ai`)

Calls Gemini models directly from Flutter apps through
[Firebase AI Logic](https://firebase.google.com/docs/ai-logic) (`firebase_ai`
SDK), authenticating via your Firebase project and Firebase App Check rather
than embedding an API key in the client binary.

Use `genkit_firebase_ai` when generation runs on-device/in-app inside Flutter.
If your AI workflows run on a backend server that Flutter calls over HTTP, use
`genkit_google_genai` or `genkit_vertexai` on the server and
`package:genkit/client.dart` in Flutter instead.

- [Installation and App Check setup](#installation-and-app-check-setup): Lines 26-69
- [Basic usage and Remote Config](#basic-usage-and-remote-config): Lines 71-110
- [Plugin configuration and providers](#plugin-configuration-and-providers): Lines 112-149
- [Model options and type names](#model-options-and-type-names): Lines 151-200
- [Grounding (Search, URL context, Maps)](#grounding-search-url-context-maps): Lines 202-228
- [Structured output and tool calling](#structured-output-and-tool-calling): Lines 230-257
- [Images, speech, and media resolution](#images-speech-and-media-resolution): Lines 259-324
- [Errors, retries, and cancellation](#errors-retries-and-cancellation): Lines 326-345
- [Live API (experimental)](#live-api-experimental): Lines 347-383
- [Pre-1.0 migration breaks and Flutter Dev UI](#pre-10-migration-breaks-and-flutter-dev-ui): Lines 385-415

---

## Installation and App Check setup

```bash
flutter pub add genkit genkit_firebase_ai firebase_core firebase_ai firebase_app_check
```

1. Configure Firebase in the project (`flutterfire configure`) and enable
   Firebase AI Logic in the Firebase console.
2. **Enable and activate App Check before the first model call.** Firebase
   enforces App Check for Firebase AI Logic starting November 2, 2026 (blocking
   unverified requests, including already-shipped app versions). Moreover,
   `firebase_ai` caches its `FirebaseAI` instance per `FirebaseApp` (and per
   `location` on Agent Platform) on first use, reading `FirebaseAppCheck` and
   `FirebaseAuth` only at creation time.

```dart
import 'package:firebase_app_check/firebase_app_check.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';

import 'firebase_options.dart';

Future<void> main() async {
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
  // Safe to construct Genkit and make model calls after App Check is active.
}
```

Never ship debug providers in release builds. On first run, each debug provider
logs a debug token (browser console on web) that you register under **App Check
> Apps > Manage debug tokens** in the Firebase console.

## Basic usage and Remote Config

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

- `firebaseAI.gemini('<name>')` returns a typed `ModelRef<GeminiOptions>` for a
  bare model ID (do **not** include the `'firebaseai/'` prefix). Any Gemini
  model Firebase AI Logic serves resolves dynamically.
- **Model IDs by backend:** `gemini-flash-latest`, `gemini-3.7-flash`, and
  `gemini-3.6-flash` are registered for `FirebaseAiProvider.googleAI()` only
  (`-latest` aliases do not exist on Agent Platform). Versioned models such as
  `gemini-4-argon`, `gemini-3.8-flash`, `gemini-3.5-flash`,
  `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, and
  `gemini-3.1-pro-preview` work on both backends.
- **Shipped apps should load model IDs from Firebase Remote Config** so you can
  migrate away from retiring models without an app store release:

```dart
import 'package:firebase_remote_config/firebase_remote_config.dart';

final remoteConfig = FirebaseRemoteConfig.instance;
await remoteConfig.setDefaults({'model_name': 'gemini-3.8-flash'});
await remoteConfig.fetchAndActivate();

final response = await ai.generate(
  model: firebaseAI.gemini(remoteConfig.getString('model_name')),
  prompt: 'Summarize these release notes.',
);
```

## Plugin configuration and providers

```dart
final ai = Genkit(
  plugins: [
    firebaseAI(
      app: Firebase.app('my-app'), // default: Firebase.app()
      provider: const FirebaseAiProvider.agentPlatform(), // default: .googleAI()
      useLimitedUseAppCheckTokens: true, // for App Check replay protection
      httpClient: customClient, // optional, caller-owned (not used by Live WS)
    ),
  ],
);
```

- `FirebaseAiProvider.googleAI()` (default): Gemini Developer API.
- `FirebaseAiProvider.agentPlatform({String? location})`: Agent Platform
  (Gemini Enterprise, formerly Vertex AI). `location` defaults to `'global'`.
- **Regional location vs `global` gotcha:** On `agentPlatform()`, standard text
  models are served on `'global'` and can fail with `NOT_FOUND` on regional
  endpoints, whereas Agent Platform Live models (`gemini-3.8-live`,
  `gemini-live-2.5-flash-native-audio`) require a regional location such as
  `'us-central1'`. Because a plugin instance has one location, create **two
  `Genkit` instances** if an app uses both text and Live models on Agent
  Platform:

```dart
final textAi = Genkit(
  plugins: [firebaseAI(provider: const FirebaseAiProvider.agentPlatform())],
);
final liveAi = Genkit(
  plugins: [
    firebaseAI(
      provider: const FirebaseAiProvider.agentPlatform(location: 'us-central1'),
    ),
  ],
);
```

## Model options and type names

**Type naming difference from `genkit_google_genai` / `genkit_vertexai`:** In
`genkit_firebase_ai`, nested thinking, speech, function-calling, and Live
config types are **unprefixed**:

- Unprefixed: `ThinkingConfig`, `SpeechConfig`, `VoiceConfig`,
  `PrebuiltVoiceConfig`, `MultiSpeakerVoiceConfig`, `SpeakerVoiceConfig`,
  `FunctionCallingConfig`, `LiveGenerationConfig`.
- `Gemini`-prefixed: `GeminiOptions`, `GeminiSafetySettings`,
  `GeminiGoogleSearch`, `GeminiUrlContext`, `GeminiGoogleMaps`,
  `GeminiRetrievalConfig`, `GeminiLatLng`, `GeminiImageConfig`.

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-3.8-flash'),
  prompt: 'Plan a three-day trip to Lisbon.',
  config: GeminiOptions(
    maxOutputTokens: 2048,
    thinkingConfig: ThinkingConfig(
      thinkingLevel: 'HIGH', // uppercase: 'MINIMAL' | 'LOW' | 'MEDIUM' | 'HIGH'
      includeThoughts: true,
    ),
    safetySettings: [
      GeminiSafetySettings(
        category: 'HARM_CATEGORY_HARASSMENT',
        threshold: 'BLOCK_ONLY_HIGH',
      ),
    ],
  ),
);
print(response.reasoning);
```

Key option rules:

- **Gemini 3+ sampling:** Gemini 3 and newer models ignore `temperature`,
  `topP`, and `topK`, do not support `candidateCount`, and may reject
  `presencePenalty` and `frequencyPenalty` with `400`.
- **Thinking:** Gemini 3+ uses uppercase `thinkingLevel` (`gemini-3.8-flash`
  rejects `'MINIMAL'`). Older models use `thinkingBudget` (int). Setting both
  throws `INVALID_ARGUMENT` locally. Gemini 3 thought signatures are preserved
  in `part.metadata['thoughtSignature']` and round-tripped automatically when
  you pass response messages into later turns.
- **Safety settings:** `HARM_CATEGORY_IMAGE_*` and `method` (`'SEVERITY'` /
  `'PROBABILITY'`) work on `agentPlatform()` only and fail with
  `INVALID_ARGUMENT` on `googleAI()`.
- **Code execution:** `codeExecution: true` returns `executableCode` and
  `codeExecutionResult` custom parts (use `firebase_ai` >= 5.0.0 so generated
  files return as `MediaPart`).

## Grounding (Search, URL context, Maps)

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-3.8-flash'),
  prompt: 'Who won the most recent Formula 1 race?',
  config: GeminiOptions(
    googleSearch: GeminiGoogleSearch(),
    // Also available:
    // urlContext: GeminiUrlContext(),
    // googleMaps: GeminiGoogleMaps(),
    // retrievalConfig: GeminiRetrievalConfig(
    //   latLng: GeminiLatLng(latitude: 38.72, longitude: -9.14),
    // ),
  ),
);

final grounding = response.custom?['groundingMetadata'] as Map?;
final queries = grounding?['webSearchQueries'] as List?;
final renderedHtml =
    (grounding?['searchEntryPoint'] as Map?)?['renderedContent'] as String?;
```

- `retrievalConfig.latLng` requires both `latitude` and `longitude`.
- Use `firebase_ai` >= 5.1.0 so `webSearchQueries` is populated.
- Google Search grounding requires displaying `searchEntryPoint.renderedContent`
  and source links in your UI.

## Structured output and tool calling

Both `outputSchema` (sent as `responseJsonSchema`) and tool `inputSchema` (sent
as `parametersJsonSchema`) forward the full JSON Schema unchanged to Gemini,
preserving `enum`, `anyOf`, `$ref`, `minimum`/`maximum`, `additionalProperties`,
and `required`:

```dart
final colors = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'List three primary colors.',
  outputSchema: .list(.string()),
);
print(colors.output); // List<String>

ai.defineTool(
  name: 'getWeather',
  description: 'Get the weather for a city',
  inputSchema: WeatherInput.$schema,
  fn: (input, context) async => .response('72F and sunny in ${input.city}'),
);

final weather = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'What is the weather in Boston?',
  toolNames: ['getWeather'],
);
```

## Images, speech, and media resolution

**Image generation** (`gemini-nano-banana-2.1`, `gemini-3.1-flash-image`,
`gemini-3.1-flash-lite-image`, `gemini-3-pro-image`):

```dart
final response = await ai.generate(
  model: firebaseAI.gemini('gemini-3.1-flash-image'),
  prompt: 'A watercolor of a lighthouse at dawn.',
  config: GeminiOptions(
    responseModalities: ['TEXT', 'IMAGE'],
    imageConfig: GeminiImageConfig(aspectRatio: '16:9', imageSize: '2K'),
  ),
);
final image = response.media; // Media(url: 'data:image/png;base64,...')
```

**Text-to-speech** (`gemini-3.8-flash-tts`, `gemini-3.8-flash-lite-tts`):
supports single-voice `voiceConfig` or two-speaker `multiSpeakerVoiceConfig`.
For two speakers, pass `promptParts` and set `metadata['speechMetadata']` on
every `TextPart` with a `speaker` name matching `speakerVoiceConfigs` (optional
`style`):

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

**Media resolution:** set `mediaResolution` on `GeminiOptions`
(`'MEDIA_RESOLUTION_LOW'`, `'MEDIA_RESOLUTION_MEDIUM'`,
`'MEDIA_RESOLUTION_HIGH'`) or per `MediaPart` via
`metadata: {'mediaResolution': 'MEDIA_RESOLUTION_ULTRA_HIGH'}`.

## Errors, retries, and cancellation

`ai.generate` does **not** throw for backend, quota, network, or safety errors;
it returns `response.finishReason == FinishReason.failed` with status details in
`response.error` and the `GenkitException` in `response.cause`:

```dart
final controller = CancellationController();

final response = await ai.generate(
  model: firebaseAI.gemini('gemini-flash-latest'),
  prompt: 'Write a short poem.',
  use: [retry(maxRetries: 2)], // retries UNAVAILABLE / RESOURCE_EXHAUSTED
  cancel: controller.token, // controller.cancel() -> FinishReason.aborted
);

if (response.finishReason == FinishReason.failed) {
  print('${response.error?.status}: ${response.error?.message}');
}
```

## Live API (experimental)

Import `package:genkit/experimental.dart` for bidirectional WebSocket audio and
text via `ai.generateBidi`. Note that `generateBidi` takes a prefixed `String`
model name (`'firebaseai/gemini-3.8-live'`), not a `ModelRef`:

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
  system: 'You are a friendly assistant.', // only allowed at session start
);

session.send('Hello');
session.stream.listen((chunk) {
  // Audio media parts arrive as data: URLs.
});
```

Live caveats:

- On `agentPlatform()`, configure `location: 'us-central1'` (or another region
  serving Live); `'global'` closes the session immediately.
- On **Flutter web**, Live sessions fail when App Check is enforced because
  `firebase_ai` does not attach the App Check token to browser WebSockets
  (`flutterfire#18938`). Android, iOS, and macOS work with App Check enforced.
- Passing a system message after the initial `generateBidi(system: ...)` call
  fails with `INVALID_ARGUMENT`.

## Pre-1.0 migration breaks and Flutter Dev UI

1.0 breaking changes vs older `0.x` snippets:

- `FirebaseAiProvider.vertexAI` -> `FirebaseAiProvider.agentPlatform` (default
  `location` is now `'global'`, not `'us-central1'`).
- `firebaseAI(appCheck: ..., auth: ...)` parameters removed; configure
  `FirebaseAppCheck` and `FirebaseAuth` on the `FirebaseApp` before first model
  use (use `firebase_ai` >= 5.1.0 when setting `useLimitedUseAppCheckTokens`).
- `GeminiOptions.responseSchema` removed -> use `outputSchema` on `ai.generate`
  or `GeminiOptions.responseJsonSchema`.
- Internal `toGemini*` / `fromGemini*` / `runLiveSession` helpers are no longer
  exported.

To connect a Flutter app to the Genkit Developer UI (both live traces and the
action/model playground via WebSocket reflection v2), use `genkit start:flutter`
and pass any `flutter run` flags after `--`:

```bash
genkit start:flutter -- -d chrome
```

If you need to launch `flutter run` separately (e.g. from an IDE or a second
terminal), write the dev config to an env file (`genkit.env` should be
gitignored) and pass `--dart-define-from-file`:

```bash
genkit start --write-env-file=genkit.env --experimental-reflection-v2
# In a second terminal:
flutter run --dart-define-from-file=genkit.env -d chrome
```
