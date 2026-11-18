# A2UI (Agent-to-UI) generative UI

The `genkit_a2ui` package brings
> [A2UI](https://a2ui.org/), a transport-agnostic, JSON-based streaming UI
> protocol, to Genkit Dart agents.
>
> A2UI builds on the agent client. Server APIs come from
> `package:genkit/genkit.dart`; the Flutter client uses
> `package:genkit/client.dart` plus the `a2ui_flutter` renderer. Read
> [Agents](agents.md) first if you have not.

An A2UI-enabled agent streams more than prose. It streams interactive UI
**surfaces** (cards, lists, forms, buttons) that a client renders incrementally
as the model responds. The entire server-side integration is a single model
middleware: add `a2ui()` to an agent's `use` list and nothing else changes.

This reference targets `genkit_a2ui` **0.6** (A2UI protocol **v1.0** by
default). 0.5 and 0.6 were breaking releases; see
[Upgrading from 0.4 and 0.5](#upgrading-from-04-and-05) if you find code using
`genui`, `package:genkit_a2ui/client.dart`, fenced `a2ui` JSON, or
`data.envelopes`.

- [Install](#install): Lines 36-59
- [Server: add the a2ui() middleware](#server-add-the-a2ui-middleware): Lines 61-195
- [Client: render surfaces (Flutter and a2ui_flutter)](#client-render-surfaces-flutter-and-a2ui_flutter): Lines 197-396
- [Handling user actions](#handling-user-actions): Lines 398-421
- [Basic catalog](#basic-catalog): Lines 423-451
- [Custom catalogs](#custom-catalogs): Lines 453-585
- [Wire format](#wire-format): Lines 587-626
- [Security and the trust boundary](#security-and-the-trust-boundary): Lines 628-648
- [How it works](#how-it-works): Lines 650-666
- [Upgrading from 0.4 and 0.5](#upgrading-from-04-and-05): Lines 668-694

---

## Install

On the **server** (the app that hosts the agent), add `genkit_a2ui` alongside
the packages the agent already needs. List `genkit` explicitly even though
`genkit_a2ui` pulls it in transitively, otherwise `dart analyze` warns with
`depend_on_referenced_packages`:

```bash
dart pub add genkit genkit_a2ui genkit_google_genai
```

`genkit_a2ui` is **server-side only**. The Flutter **client** does not depend
on it: it needs `genkit`, the [`a2ui_flutter`](https://pub.dev/packages/a2ui_flutter)
renderer, and [`a2ui_core`](https://pub.dev/packages/a2ui_core) (message
processing and surface state):

```bash
flutter pub add genkit 'a2ui_flutter:^0.3.0' 'a2ui_core:^0.7.0' url_launcher
```

`url_launcher` backs the basic catalog's `openUrl` function. Pin `a2ui_core`:
it is pre-1.0 and makes breaking releases, and the snippets below target 0.7.
Keeping the agent in its own server package (as the `a2ui` testapp does) stops
`genkit_a2ui`'s `a2ui_core` constraint from holding back the client's renderer.

## Server: add the `a2ui()` middleware

Add `a2ui()` to your agent's `use` list. That is the whole server-side setup.

**Dart specific:** Dart middleware is resolved by name from the registry, so you
MUST register `A2uiPlugin()` in `Genkit(plugins: [...])` before referencing it
via `a2ui()`.

```dart
import 'package:genkit/experimental.dart'; // defineAgent, InMemorySessionStore
import 'package:genkit/experimental_io.dart'; // GenkitRouter.addAgent
import 'package:genkit/genkit.dart';
import 'package:genkit/io.dart'; // GenkitRouter, CorsOptions
import 'package:genkit_a2ui/a2ui.dart';
import 'package:genkit_google_genai/genkit_google_genai.dart';

// A2uiPlugin() registers the a2ui() middleware so `use: [a2ui()]` resolves.
final ai = Genkit(plugins: [googleAI(), A2uiPlugin()]);

final uiAgent = ai.defineAgent(
  name: 'uiAgent',
  model: googleAI.gemini('gemini-flash-latest'),
  system: 'You help users. Render UI when it is clearer than prose.',
  use: [a2ui()], // A2UI v1.0 basic catalog; a2ui(catalog: 'basic-v0.9') keeps v0.9
  store: InMemorySessionStore(),
);

// Serves /api/uiAgent plus /getSnapshot and /abort.
void main() async {
  final genkit = GenkitRouter()..addAgent(uiAgent, path: '/api/uiAgent');
  await genkit.serve(
    port: 8080,
    cors: const CorsOptions(), // Flutter web runs on another origin.
  );
}
```

It also works on a one-shot `ai.generate`. On the server,
`a2uiEnvelopesFromParts` (exported by `genkit_a2ui`) reads the A2UI messages
out of a response:

```dart
final res = await ai.generate(
  model: googleAI.gemini('gemini-flash-latest'),
  prompt: 'Show me the weather in Tokyo',
  use: [a2ui()],
);
for (final message in a2uiEnvelopesFromParts(res.message?.content)) {
  print(message);
}
```

See [Deploying agents](agents-deployment.md) for more on `GenkitRouter`.

### Options

| Option         | Default        | Description                                                                                                                                                  |
| -------------- | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `catalog`      | `'basic'`      | Catalog lookup id in the registry. `'basic'` is the A2UI v1.0 basic catalog; `'basic-v0.9'` keeps v0.9.                                                      |
| `instructions` | `'system'`     | Where to inject catalog capabilities. `'none'` injects nothing; build your own prompt starting from `renderCatalogInstructions(catalog)`.                     |
| `validate`     | `'warn'`       | Block that fails to compile/validate: `'warn'` logs and drops it; `'strict'` throws; `'off'` only checks that it compiles, not the component tree.            |
| `repair`       | `true`         | Ask the model once to fix a block that failed to compile. Extra model call on the failure path only. See [Self-repair](#self-repair).                         |
| `version`      | _from catalog_ | Optional assertion (`'1.0'` or `'v0.9'`). The catalog decides the protocol version; passing `version` throws if the resolved catalog targets another one.    |

There is no `surfaceId` option: the model names surfaces (see below). Use
`validate: 'strict'` during development to fail fast.

### When the model renders

The injected instructions ask for a surface when the answer is data the user
will look at or act on (structured tool results, comparisons, choices, forms),
and for prose otherwise. They yield to your system prompt, so steer from there:

```dart
ai.defineAgent(
  name: 'dashboard',
  // More surfaces:
  system: 'Answer with an A2UI surface whenever you can, explanations included.',
  // Or fewer: 'Only render a surface when the user asks for one.'
  use: [a2ui()],
);
```

### Surfaces: create, replace, and update

The model writes each surface in
[A2UI Express](https://a2ui.org/specification/proposals/express/a2ui_express/)
inside `<a2ui>` blocks, a compact positional notation that costs far fewer
tokens than JSON. The middleware compiles it into A2UI messages:

```text
surface("tokyo-weather")
root = Card(Column([title, refresh]))
title = Text("## Weather in Tokyo")
refresh = Button(Text("Refresh"), "primary", Event("refresh", {city: "Tokyo"}))
```

- **The model owns surface ids**, and they reach the client unchanged.
- **Rendering an id again replaces that surface.** The middleware emits a
  `deleteSurface` before every `createSurface` (renderers reject a second
  `createSurface` for a live id). Custom renderers must treat `deleteSurface`
  for an unknown id as a no-op.
- **A block without `root` updates a live surface** with only what changed
  (`updateComponents` / `updateDataModel`):

  ```text
  surface("tokyo-weather")
  $/temp = "21C"
  ```

Because a part can carry only updates for a surface an earlier part or turn
created, clients MUST feed every message from every part, in order, into **one
renderer per conversation**, and render each surface once, keyed by id.

Unless `validate` is `'off'`, each block is checked against the surfaces the
conversation's history left on the client (an update must target a live
surface). This relies on A2UI parts being sent back with history, which
`remoteAgent` and session stores do.

### Self-repair

When a block doesn't compile (most often a label where a component id belongs:
`Button("Refresh", ...)` instead of `Button(Text("Refresh"), ...)`), the
middleware sends one follow-up call with the error, the Express contract, and
the failed block. If the fix compiles the surface renders; otherwise it is
dropped (or `'strict'` throws). Limits: one call per distinct broken block, 3
per model call, 30 seconds total. A repaired surface arrives as the **last
chunk** of the stream, its usage is added to the turn's `usage`, and cancelling
the turn cancels the repair.

To see the model's own mistakes while developing:

```dart
use: [a2ui(validate: 'strict', repair: false)]
```

## Client: render surfaces (Flutter and `a2ui_flutter`)

A2UI arrives as plain, spec-shaped `data` parts, so the client needs only
`package:genkit` and a renderer. Two copy-in helpers (from the `genkit_a2ui`
README and `testapps/a2ui/client/lib/a2ui_helpers.dart`) do the glue.

**Interop:** this Flutter client only works against a **Genkit Dart** agent
today. The JS, Go, and Python A2UI plugins still emit v0.9 under
`data.envelopes` and read actions only from that key, while these helpers send
actions as `{messages: [...]}`. Likewise the JS `@genkit-ai/a2ui/client` web
helpers do not render a Dart agent's surfaces yet.

### 1. Copy the A2UI helpers

`a2uiMessagesFrom` reads A2UI messages out of a chunk's or message's parts;
`a2uiActionToMessage` wraps a surface action as the next agent input.

```dart
import 'package:a2ui_core/a2ui_core.dart'
    show ActionMessage, RendererToAgentMessagePayload;
import 'package:genkit/client.dart';

const a2uiMimeType = 'application/a2ui+json';

const _envelopeKeys = {'checks', 'accessibility', 'catalogId', 'metadata'};

/// The A2UI messages carried by a chunk's or message's parts.
Iterable<Map<String, dynamic>> a2uiMessagesFrom(List<Part>? parts) sync* {
  for (final part in parts ?? const <Part>[]) {
    if (part.metadata?['mimeType'] != a2uiMimeType) continue;
    // `envelopes` is the pre-spec key, still written by older agents. Malformed
    // payloads are skipped rather than throwing mid-stream.
    final data = part.data;
    if ((data?['messages'] ?? data?['envelopes']) case final List messages) {
      yield* messages.whereType<Map>().map(
        (m) => _normalizeEnvelopeKeys(
          m is Map<String, dynamic> ? m : m.cast<String, dynamic>(),
        ),
      );
    }
  }
}

bool _hasAtEnvelopeKey(Object? c) =>
    c is Map &&
    c.keys.any(
      (k) =>
          k is String &&
          k.startsWith('@') &&
          _envelopeKeys.contains(k.substring(1)) &&
          !c.containsKey(k.substring(1)),
    );

/// Rewrites `@checks`, `@accessibility`, `@catalogId` and `@metadata` on v1.0
/// components to the bare names that `a2ui_core` 0.7 expects, so this client
/// keeps rendering if the agent moves to a newer SDK first. Delete it once your
/// `a2ui_core` reads the `@` keys itself.
Map<String, dynamic> _normalizeEnvelopeKeys(Map<String, dynamic> message) {
  if (message['version'] != '1.0') return message;
  for (final kind in const ['createSurface', 'updateComponents']) {
    if (message[kind] case final Map body) {
      if (body['components'] case final List components
          when components.any(_hasAtEnvelopeKey)) {
        return <String, dynamic>{
          ...message,
          kind: <String, dynamic>{
            ...body.cast<String, dynamic>(),
            'components': <Object?>[
              for (final c in components)
                if (c is Map)
                  <String, dynamic>{
                    for (final MapEntry(:key, :value) in c.entries)
                      if (key is String &&
                          key.startsWith('@') &&
                          _envelopeKeys.contains(key.substring(1)) &&
                          !c.containsKey(key.substring(1)))
                        key.substring(1): value
                      else
                        '$key': value,
                  }
                else
                  c,
            ],
          },
        };
      }
    }
  }
  return message;
}

/// Wraps a surface action (e.g. a button press) as the next agent input.
///
/// `a2ui_core` writes the `{messages: [...]}` wrapper the agent reads, with
/// the action in a spec-shaped `{version, action}` message, so it is forwarded
/// as is.
Message a2uiActionToMessage(ActionMessage action) => Message(
  role: .user,
  content: [
    DataPart(
      data: RendererToAgentMessagePayload.of(action).toJson(),
      metadata: {'mimeType': a2uiMimeType},
    ),
  ],
);
```

### 2. Set up the message processor and stream turns

Connect with `remoteAgent` and feed every A2UI message, in order, into one
`a2ui_core` `MessageProcessor` per conversation. A2UI travels as `data` parts on
the raw model chunk, so read them from `chunk.raw.modelChunk?.content`:

```dart
import 'package:a2ui_core/a2ui_core.dart';
import 'package:a2ui_flutter/a2ui_flutter.dart';
import 'package:a2ui_flutter/basic_catalog.dart';
import 'package:genkit/experimental_client.dart'; // remoteAgent, AgentTurn
import 'package:url_launcher/url_launcher.dart';

// remoteAgent returns an AgentApi<State> (not a `RemoteAgent`).
final agent = remoteAgent(
  url: 'http://localhost:8080/api/uiAgent',
  getSnapshotUrl: 'http://localhost:8080/api/uiAgent/getSnapshot',
  abortUrl: 'http://localhost:8080/api/uiAgent/abort',
);
final chat = agent.chat();

// The renderer rejects a surface whose catalog id it doesn't hold.
// a2ui_flutter's `basicCatalog()` has the same id as the plugin's bundled
// v1.0 basic catalog.
final processor = MessageProcessor<ComponentImplementation>(
  catalogs: [basicCatalog(openUrl: (uri) => launchUrl(uri))],
  // Deliver actions to `outboundListener` as typed, versioned messages.
  unifiedOutbound: true,
  // A surface action becomes the next turn. Ignore presses while a turn is
  // running (`busy` is your app's flag), otherwise two turns interleave.
  outboundListener: (message) {
    if (message is ActionMessage && !busy) {
      runTurn(chat.sendStream(message: a2uiActionToMessage(message)));
    }
  },
  onError: (error) => print('A2UI renderer error: ${error.message}'),
);

Future<void> runTurn(AgentTurn turn) async {
  await for (final chunk in turn.stream) {
    if (chunk.text.isNotEmpty) appendProse(chunk.text);
    for (final m in a2uiMessagesFrom(chunk.raw.modelChunk?.content)) {
      // One message the renderer can't take (a newer protocol version, say)
      // must not stop the rest of the turn.
      try {
        processor.processMessages([m]);
      } on Object catch (e) {
        print('Skipping an A2UI message: $e');
      }
    }
  }
  await turn.response;
}

await runTurn(chat.sendStream(text: 'What is the weather in Tokyo?'));
```

`remoteAgent` manages the session id, so a single `chat` keeps the whole
conversation server-side and sends A2UI parts back with history (with their
`metadata.a2uiExpress` intact, which the model needs on later turns). Clients
that manage history themselves must do the same.

To accept surfaces from both v1.0 and v0.9 agents, also register the v0.9
basic catalog from `package:a2ui_flutter/v0_9/basic_catalog.dart`; the ids
differ, so both can coexist in one processor.

### 3. Mount the surfaces

Listen to `processor.model.onSurfaceCreated` / `onSurfaceDeleted` and render
each surface with an `A2uiSurface` widget. Key the chat log by surface id, so a
replaced surface re-renders where it first appeared and an updated one changes
in place:

```dart
final surfaceIds = <String>[];

// In initState:
processor.model.onSurfaceCreated.subscribe((surface) {
  setState(() {
    if (!surfaceIds.contains(surface.id)) surfaceIds.add(surface.id);
  });
});
processor.model.onSurfaceDeleted.subscribe((_) => setState(() {}));

// In build, for each id in surfaceIds:
Widget buildSurface(String surfaceId) {
  final surface = processor.model.getSurface(surfaceId);
  // Deleted: keep the slot in case the agent renders the id again.
  if (surface == null) return const SizedBox.shrink();
  // A replaced surface is a new model, so key by it to start fresh.
  return A2uiSurface(key: ObjectKey(surface), surface: surface);
}
```

## Handling user actions

The `outboundListener` above already handles actions: when a user presses a
`Button`, `a2ui_core` emits an `ActionMessage`, and `a2uiActionToMessage` sends
it back as an A2UI data part. The middleware turns it into a line the model can
read, so no accompanying text is needed:

```text
[UI action "refresh" from refreshBtn on surface tokyo-weather context={"city":"Tokyo"}]
```

### Forms

Input components (`TextField`, `CheckBox`, `Slider`, `ChoicePicker`,
`DateTimeInput`) do **not** send their values automatically. To capture what
the user entered, the model must:

1. Bind each input's value to a data-model path:
   `email = TextField("Email", $/email)`.
2. Echo those same paths in the submit button's event context:
   `Event("submit", {email: $/email})`.

The injected instructions already tell the model to do this. Without both
steps, the action arrives with an empty `context`.

## Basic catalog

The bundled `basicCatalog` is the A2UI v1.0 basic catalog (18 components).
Express is positional: argument order is property order, `?` marks optional.

| Component       | Arguments                                                                                   |
| --------------- | ------------------------------------------------------------------------------------------- |
| `Row`, `Column` | `children`, `justify?`, `align?`                                                            |
| `List`          | `children`, `direction?` (`vertical`, `horizontal`), `align?`                               |
| `Card`          | `child` (group several elements with a `Column` or `Row`)                                   |
| `Tabs`          | `tabs` (a list of `{title, child}`)                                                         |
| `Modal`         | `trigger`, `content`                                                                        |
| `Divider`       | `axis?`                                                                                     |
| `Text`          | `text` (inline Markdown; use `"## Title"` for headings, no `h1`..`h5`), `variant?` (`caption`, `body`) |
| `Image`         | `url`, `description?`, `fit?`, `variant?`                                                   |
| `Icon`          | `name` (one of `basicIconNames`)                                                            |
| `Video`         | `url`, `posterUrl?`                                                                         |
| `AudioPlayer`   | `url`, `description?`                                                                       |
| `Button`        | `child` (a component id, usually a `Text`), `variant?`, `action` (`Event(name, context?)`)  |
| `TextField`     | `label`, `value`, `placeholder?`, `variant?` (`shortText`, `longText`, `number`, `obscured`) |
| `CheckBox`      | `label`, `value`                                                                            |
| `ChoicePicker`  | `label?`, `variant?`, `options` (list of `{label, value}`), `value`, `displayStyle?`, `filterable?` |
| `Slider`        | `label?`, `min?`, `max`, `value`, `steps?`                                                  |
| `DateTimeInput` | `value`, `enableDate?`, `enableTime?`, `min?`, `max?`, `label?`                             |

Text-like and value arguments accept a literal or a data binding (`$/path`).
For v0.9, use `a2ui(catalog: 'basic-v0.9')` or extend `basicCatalogV09` (12
components, without `Tabs`, `Modal`, `Video`, `AudioPlayer`, `ChoicePicker`,
`DateTimeInput`).

## Custom catalogs

A custom catalog has two halves that MUST agree: the **server** catalog (what
the model is told it may render, and validated against) and the **client**
`CatalogImplementation` (the widgets that paint it). They match on the catalog's
`catalogId` URI and on each component name.

### Catalog format

Catalogs use the A2UI spec's
[`catalog.json`](https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json)
shape, so a published catalog loads unmodified:

- `catalogId`: globally unique URI, sent on `createSurface`; the client must
  register a catalog under the same id.
- `protocolVersion`: `"1.0"` for v1.0 (omitted on v0.9 catalogs). Decides what
  the middleware emits.
- `components`: object keyed by component name, each value a JSON Schema. The
  schema's `description` and property descriptions are what the model sees.
- `functions` (optional): client functions (checks, formatters), keyed by name.

**Property order matters:** Express is positional, so for
`MetricCard("Revenue", "$1.2M", "up")` the order of properties decides which
argument is which.

### Server: define and register

Either load JSON (`./catalogs/dashboard.json` in the shape above):

```dart
await loadCatalog(ai, id: 'dashboard', file: './catalogs/dashboard.json');
```

or build it in code. `basicCatalog.extend` keeps the basic components (and
v1.0), and `A2uiCatalogComponent.simple` builds the JSON Schema from a param
list:

```dart
import 'package:genkit_a2ui/a2ui.dart';

const dashboardCatalogId = 'https://example.com/catalogs/dashboard.json';

final dashboardCatalog = basicCatalog.extend(
  id: dashboardCatalogId,
  components: [
    A2uiCatalogComponent.simple(
      name: 'MetricCard',
      description: 'Displays a key metric with a title, value, and trend indicator.',
      params: [
        // A literal or a data binding (`$/path`).
        const A2uiParam.dynamicValue('title', required: true),
        const A2uiParam.dynamicValue('value', required: true),
        // A literal only, restricted to these values.
        const A2uiParam.string('trend', enumValues: ['up', 'down', 'neutral']),
      ],
    ),
  ],
);

// Call once at startup, before the agent handles a turn.
await loadCatalog(ai, id: 'dashboard', catalog: dashboardCatalog);

final dashboardAgent = ai.defineAgent(
  name: 'dashboardAgent',
  model: googleAI.gemini('gemini-flash-latest'),
  use: [a2ui(catalog: 'dashboard', validate: 'strict')],
  store: InMemorySessionStore(),
);
```

Param kinds: `A2uiParam.dynamicValue` (string unless `type:` is
`A2uiDynamicType.number` / `.boolean` / `.stringList` / `.value`),
`.string`, `.number`, `.boolean`, `.child` (one component id), `.children`
(list of ids), `.action` (event fired on interaction), and `.schema` (raw JSON
Schema). Pass `checkable: true` to `A2uiCatalogComponent.simple` for inputs
that accept validation checks. Extend `basicCatalogV09` for a v0.9 catalog.

The `loadCatalog` **lookup id** (`'dashboard'`, used in `a2ui(catalog: ...)`)
is separate from the **`catalogId` URI** (what the client matches). Catalogs
live in the registry under value type `a2ui-catalog`.

### Client: register matching widgets

Implement each custom component as an `a2ui_flutter` `ComponentImplementation`
and build a `CatalogImplementation` holding the basic components plus yours
under the server's `catalogId`:

```dart
import 'package:a2ui_core/a2ui_core.dart'
    show A2uiProtocolVersion, BasicCatalog, CommonSchemasV1;
import 'package:a2ui_flutter/a2ui_flutter.dart';
import 'package:a2ui_flutter/basic_catalog.dart';
import 'package:json_schema_builder/json_schema_builder.dart';
import 'package:url_launcher/url_launcher.dart';

final metricCard = ComponentImplementation(
  name: 'MetricCard', // MUST match the server component name
  schema: Schema.object(
    properties: {
      // A literal or a `{"@path": "/..."}` data binding.
      'title': CommonSchemasV1.dynamicString,
      'value': CommonSchemasV1.dynamicString,
      'trend': Schema.string(enumValues: ['up', 'down', 'neutral']),
    },
    required: ['title', 'value'],
  ),
  // `props` holds resolved values; the builder reruns when bound data changes.
  builder: (context, node, props, buildChild) => MetricCardWidget(
    title: props.string('title') ?? '',
    value: props.string('value') ?? '',
    trend: props.string('trend'),
  ),
);

final dashboardCatalog = CatalogImplementation(
  id: 'https://example.com/catalogs/dashboard.json', // MUST match server catalogId
  protocolVersion: A2uiProtocolVersion.v1_0,
  components: [...BasicComponents.all, metricCard],
  functions: BasicCatalog.v1_0(
    openUrl: (uri) => launchUrl(uri),
  ).functions.values.toList(),
  definitions: BasicComponents.api.definitions,
);

final processor = MessageProcessor<ComponentImplementation>(
  catalogs: [dashboardCatalog],
  // ...
);
```

`Schema` comes from `json_schema_builder` (`flutter pub add
json_schema_builder`). If the ids disagree, `processMessages` throws an
`A2uiCatalogError` for that `createSurface` and the surface never appears.

## Wire format

A2UI rides on its own part channel, following the
[A2UI extension spec](https://a2ui.org/specification/v1.0-a2ui-extension-specification/):
a Genkit `data` part with `metadata.mimeType` `application/a2ui+json` and
`data: {"messages": [...]}`. `metadata.a2uiExpress` holds the Express source,
which is what the model sees of the surface on later turns.

Agent to client:

```json
{
  "data": {
    "messages": [
      { "version": "1.0", "deleteSurface": { "surfaceId": "tokyo-weather" } },
      {
        "version": "1.0",
        "createSurface": {
          "surfaceId": "tokyo-weather",
          "catalogId": "https://a2ui.org/specification/v1_0/catalogs/basic/catalog.json",
          "components": [{ "id": "root", "component": "Text", "text": "Sunny, 18C" }]
        }
      }
    ]
  },
  "metadata": {
    "mimeType": "application/a2ui+json",
    "a2uiExpress": "surface(\"tokyo-weather\")\nroot = Text(\"Sunny, 18C\")"
  }
}
```

Client to agent (a user action):
`{"data": {"messages": [{"version": "1.0", "action": {"name": "refresh",
"surfaceId": "tokyo-weather", "sourceComponentId": "refreshBtn", "timestamp":
"...", "context": {"city": "Tokyo"}}}]}, "metadata": {"mimeType":
"application/a2ui+json"}}`.

Pre-0.5 agents used `envelopes` instead of `messages`; the middleware still
reads `envelopes` when replaying history.

## Security and the trust boundary

Treat every surface an agent emits as **untrusted input**. Every block is
compiled and checked against the catalog's schemas (component names, property
types, enum values, component references), but that only means it is
*well-formed*. Model-controlled values such as `Image.url` and `Text` (inline
Markdown) pass through as written. Validation is not a security boundary.

- **The renderer/catalog owns prop sanitization.** Whatever renders a surface
  (`a2ui_flutter` plus your Markdown renderer, and your custom components) must
  escape and sanitize prop values.
- **Restrict remote sources at the host.** On the web, use a Content Security
  Policy that limits `img-src` and other fetch directives to trusted origins.
- **Do not put secrets in the data model.** Anything bound into a surface's data
  model can be echoed back through an action's `context`.

For server-side control over props (for example, allow-listing image hosts),
add your own model middleware **before** `a2ui()` in `use`. Middleware listed
first wraps the ones after it, so it sees the parts `a2ui()` emits. If you
change a part's `data.messages`, also update or remove its
`metadata.a2uiExpress`.

## How it works

On each model call inside the agent's tool loop, `a2ui()`:

1. Injects the catalog's component signatures and the Express contract into the
   system prompt (unless `instructions: 'none'`).
2. Intercepts streamed chunks and the final message and extracts `<a2ui>`
   blocks from the model's text.
3. Compiles each block into A2UI messages (via `a2ui_agent`) and checks it
   against the catalog and the conversation's live surfaces; failures go
   through [self-repair](#self-repair).
4. Rewrites each block into a canonical A2UI data part (Express source in
   `metadata.a2uiExpress`). Prose outside blocks passes through.

Inbound A2UI parts (history, user actions) are turned back into text before the
model sees them: a rendered surface replays as its original Express block, and
an action becomes a `[UI action ...]` line.

## Upgrading from 0.4 and 0.5

Old code and training data often show APIs that no longer compile. Replace:

| Old (0.4 / 0.5)                                                         | Now (0.6)                                                                  |
| ----------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| `genui` (`SurfaceController`, `CatalogItem`, `Surface`)                 | `a2ui_flutter` + `a2ui_core` 0.7 (`MessageProcessor`, `ComponentImplementation`, `A2uiSurface`) |
| `package:genkit_a2ui/client.dart` (`a2uiEnvelopesFromParts`, `actionToMessage`, `A2uiClientAction`) | Copy-in `a2uiMessagesFrom` / `a2uiActionToMessage`; clients don't depend on `genkit_a2ui` |
| `a2uiSubmitToMessage` (0.5 helper)                                      | `a2uiActionToMessage`                                                      |
| Fenced `a2ui` JSON blocks                                               | A2UI Express in `<a2ui>` blocks                                            |
| `data.envelopes`                                                        | `data.messages`                                                            |
| `a2ui(surfaceId: ...)`                                                  | Removed; the model names surfaces                                          |
| `a2ui(version: ...)` picks the version                                  | Version comes from the catalog; `version` only asserts                     |
| `a2uiVersion`                                                           | `catalog.protocolVersion`                                                  |
| `A2uiCatalog(components: [...basicCatalog.components, ...])`            | `basicCatalog.extend(id: ..., components: [...])`                          |
| `A2uiCatalogComponent(props: '...')` text props                         | `A2uiCatalogComponent.simple(params: [...])` or JSON Schema                |
| `{ "path": "/x" }` bindings, `Text` variants `h1`..`h5`                 | `{"@path": "/x"}` (`$/x` in Express), Markdown heading lines               |

To stay on A2UI v0.9 (for example, while some clients only render v0.9), use
`a2ui(catalog: 'basic-v0.9')`, extend `basicCatalogV09`, or pass
`protocolVersion: 'v0.9'` to `A2uiCatalog(...)`. Upgrade the agent and its
clients together.

For a complete, runnable example (a `dart:io` server with a custom `Gauge`
catalog plus a Flutter `a2ui_flutter` client), see
[`testapps/a2ui`](https://github.com/genkit-ai/genkit-dart/tree/main/testapps/a2ui)
in the Genkit Dart repo.
