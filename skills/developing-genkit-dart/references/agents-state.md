# Working with Agent State

> Read [agents.md](agents.md) first.

Beyond message history, an agent session can hold typed **custom state** — your
own structured data (a task list, a workflow status, counters, etc.). Tools read
and mutate it during a turn, and it is automatically synced to the
[`remoteAgent`](agents.md#consume-an-agent-from-a-client-remoteagent) client via
`customPatch` chunks (so the client's tracked state stays live mid-stream).

## Declare the state shape

Pass a `stateSchema` (a schemantic `.$schema`) to `defineAgent`. It's validated
when a snapshot is loaded.

```dart
import 'package:genkit/genkit.dart';
import 'package:schemantic/schemantic.dart';

import 'genkit.dart';

part 'task_agent.g.dart';

@Schema()
abstract class $TaskItem {
  int get id;
  String get title;
  bool get done;
}

@Schema()
abstract class $TaskState {
  List<$TaskItem> get tasks;
  int get nextId;
}

final taskAgent = ai.defineAgent(
  name: 'taskAgent',
  stateSchema: TaskState.$schema,
  system: "You manage the user's task list. Use the tools to modify it.",
  tools: [addTask /*, toggleTask, removeTask */],
  use: [retry()],
);
```

`stateSchema` works with the standard `defineAgent` — you do **not** need
`defineCustomAgent` for custom state.

## Read & mutate state inside tools

Tools call `ai.currentSession()` to access the live session, then
`session.getCustom()` / `session.updateCustom(mutator)`. `updateCustom` takes
`(dynamic custom) => dynamic` and returns the new state. Each call auto-emits a
`customPatch` chunk to the client.

```dart
@Schema()
abstract class $AddTaskInput {
  @Field(description: 'Short description of the task')
  String get title;
}

Map<String, dynamic> _stateOrEmpty(dynamic custom) {
  if (custom is Map) {
    final map = Map<String, dynamic>.from(custom);
    map['tasks'] = (map['tasks'] as List?)?.toList() ?? <dynamic>[];
    map['nextId'] = map['nextId'] ?? 1;
    return map;
  }
  return {'tasks': <dynamic>[], 'nextId': 1};
}

final addTask = ai.defineTool(
  name: 'addTask',
  description: 'Add a new task. Returns the created task.',
  inputSchema: AddTaskInput.$schema,
  outputSchema: TaskItem.$schema,
  fn: (input, _) async {
    final session = ai.currentSession()!;
    late Map<String, dynamic> newTask;
    session.updateCustom((custom) {
      final s = _stateOrEmpty(custom);
      newTask = {'id': s['nextId'], 'title': input.title, 'done': false};
      (s['tasks'] as List).add(newTask);
      s['nextId'] = (s['nextId'] as int) + 1;
      return s;
    });
    return TaskItem.fromJson(newTask);
  },
);
```

`ai.currentSession()` returns `null` when called outside an active session (e.g.
a tool invoked without a running agent turn), so only use it inside agent tools.

## Seed and read state (server-side)

Seed initial custom state when opening a chat. The `state` argument is a
`SessionState`: custom data goes under `.custom` (alongside `messages` and
`artifacts`).

```dart
final chat = taskAgent.chat(
  state: SessionState(
    custom: {'tasks': <dynamic>[], 'nextId': 1},
    messages: [],
    artifacts: [],
  ),
);

final res = await chat.sendText('Add a task: buy groceries');
print(res.state); // res.state returns the custom state directly
```

> **Typed state.** When you supply a `stateSchema`, `res.state` / `chat.state`
> (and `snapshot.custom`) are **parsed into the typed `State` object** (here a
> `TaskState`), not a raw `Map`. `Agent`/`AgentChat`/`AgentResponse` are generic
> over `State`, so the type flows through automatically. Without a `stateSchema`,
> `state` is an untyped view over the JSON.

## Auto-sync to the `remoteAgent` client

When you talk to the agent over HTTP, the `remoteAgent` client tracks custom
state for you. Seed it the same way (`state.custom`), read live updates off each
streamed chunk (`chunk.custom`), and read the authoritative state off
`chat.state` after the turn completes.

```dart
import 'package:genkit/client.dart';

final agent = remoteAgent(url: '/api/taskAgent');
final chat = agent.chat(
  state: SessionState(
    custom: {'tasks': <dynamic>[], 'nextId': 1},
    messages: [],
    artifacts: [],
  ),
);

final turn = chat.sendTextStream('Add buy groceries, then mark it done');
await for (final chunk in turn.stream) {
  // Live custom state arrives via customPatch chunks:
  if (chunk.custom != null) {
    // e.g. render (chunk.custom as Map)['tasks']
  }
  // chunk.text for model output
}
final res = await turn.response;

// Authoritative state after the turn:
print(res.state);
print(chat.state);
```

State updates ride on the streamed chunks — there is no `onStateChange`
subscription. For live mid-stream status updates from a multi-step custom agent,
see [advanced custom agents](agents-custom.md), which emit `customPatch` chunks as
state changes.
