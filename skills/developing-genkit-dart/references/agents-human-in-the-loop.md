# Agent Human-in-the-Loop / Interrupts

> Read [agents.md](agents.md) first.

An **interrupt** pauses an agent mid-turn and hands control back to your code (or
a human) — e.g. to approve a sensitive action, collect missing input, or confirm
a plan. Internally it's a **tool call used as control flow**: the interrupt tool
never runs to completion on the server; it pauses the turn. You then **resume**
from the exact point it paused.

> **Dart has no `defineInterrupt`.** Model an interrupt as a normal tool whose
> body calls `ctx.interrupt(...)`. Because the tool never returns a value, omit
> `outputSchema` — the output is supplied by the caller on resume.

Interrupts are **orthogonal to persistence** — they work the same whether the
agent uses a [session store](agents-sessions.md) or
[client-managed state](agents.md#client-managed-state-no-server-store). Just
resume on the same `chat` (or, for raw calls, carry the returned state/snapshot
back into the resume).

Flow: `chat.sendText(...)` → response has `res.interrupts` → collect human input
→ `chat.resume(AgentResume(respond: [...]))`.

## Define an interrupt (a tool that interrupts)

Define it like a tool and add it to the agent's `tools`. `ctx.interrupt(...)`
pauses the turn; its argument is the data shown to the human.

```dart
import 'package:genkit/genkit.dart';
import 'package:schemantic/schemantic.dart';

import 'genkit.dart';

part 'banking_agent.g.dart';

@Schema()
abstract class $UserApprovalInput {
  @Field(description: 'The action to be approved')
  String get action;
  @Field(description: 'Details about the action')
  String get details;
}

@Schema()
abstract class $TransferMoneyInput {
  double get amount;
  String get toAccount;
}

@Schema()
abstract class $TransferMoneyOutput {
  bool get success;
  String get transactionId;
}

/// Interrupt: always pauses. The caller provides `{ approved, feedback }` on
/// resume. No `outputSchema` — the output comes from the resume call.
final userApproval = ai.defineTool(
  name: 'userApproval',
  description: 'Ask the user for approval before a sensitive action.',
  inputSchema: UserApprovalInput.$schema,
  fn: (input, ctx) async => ctx.interrupt(),
);

/// Executes the transfer. Only reached after the user approves.
final transferMoney = ai.defineTool(
  name: 'transferMoney',
  description: 'Transfer money to a specified account.',
  inputSchema: TransferMoneyInput.$schema,
  outputSchema: TransferMoneyOutput.$schema,
  fn: (input, _) async => TransferMoneyOutput(
    success: true,
    transactionId: 'txn-${DateTime.now().millisecondsSinceEpoch}',
  ),
);

final bankingAgent = ai.defineAgent(
  name: 'bankingAgent',
  system: 'You are a banking assistant. ALWAYS use the userApproval interrupt '
      'to confirm before executing transferMoney.',
  tools: [userApproval, transferMoney],
  use: [retry()],
  store: InMemorySessionStore(),
);
```

## Detect and resume (server-side)

`res.interrupts` is non-empty when the agent paused. Each `AgentInterrupt`
exposes:

- `.name` — the interrupt's name.
- `.input` — the data the model passed in.
- `.respond(output)` — **builder** returning a resume entry that supplies the
  tool's output (without executing it). Does **not** send.
- `.restart()` — **builder** re-issuing the original tool request (retry / let
  the tool actually run). Does **not** send.

Resume the **same** chat with `chat.resume(...)` / `chat.resumeStream(...)`,
passing an `AgentResume`:

```dart
final chat = bankingAgent.chat();
var res = await chat.sendText('Transfer \$500 to my savings account.');

final approval =
    res.interrupts.where((i) => i.name == 'userApproval').firstOrNull;
if (approval != null) {
  print(approval.input); // { action, details } — show this to the human

  // Collect the human decision, then resume with the interrupt's output:
  res = await chat.resume(
    AgentResume(
      respond: [
        approval.respond({'approved': true, 'feedback': 'Looks good'}),
      ],
    ),
  );
}
print(res.text); // final confirmation
```

Streaming variant:

```dart
final turn = chat.resumeStream(
  AgentResume(respond: [approval.respond({'approved': true})]),
);
await for (final chunk in turn.stream) {
  stdout.write(chunk.text);
}
final res = await turn.response;
```

You can resume multiple interrupts at once by passing several builders, and mix
`respond` (supply output) with `restart` (re-run the tool):

```dart
await chat.resume(
  AgentResume(
    respond: [a.respond({'approved': true})],
    restart: [b.restart()],
  ),
);
```

## Client-side (browser) interrupts

The same pattern works over HTTP with `remoteAgent` from
`package:genkit/client.dart`. The client tracks the snapshot, so resuming the
same `chat` continues exactly where it paused.

```dart
import 'package:genkit/client.dart';

final agent = remoteAgent(url: '/api/bankingAgent');
final chat = agent.chat();

// 1. Send and detect the pause.
final res = await chat.sendText('Transfer \$500 to savings.');
final pending =
    res.interrupts.where((i) => i.name == 'userApproval').firstOrNull;

if (pending != null) {
  // pending.input → { action, details }; render an approval dialog.

  // 2. After the human approves/denies, resume the SAME chat.
  final turn = chat.resumeStream(
    AgentResume(
      respond: [pending.respond({'approved': true, 'feedback': 'ok'})],
    ),
  );
  await for (final chunk in turn.stream) {
    /* render chunk.text */
  }
  final finalRes = await turn.response;
  // If finalRes.interrupts is non-empty, the agent paused again — repeat.
}
```

## Interrupts with tool-approval middleware

The [`toolApproval`](genkit_middleware.md) middleware turns selected tools into
approval interrupts without any custom interrupt code. The middleware gates each
tool call itself: a tool is allowed to run only if it is in the `approved` list
or its request carries top-level metadata `{ 'tool-approved': true }`. To let an
approved tool through on resume, re-issue the paused `ToolRequestPart` with that
metadata added:

```dart
final approved = ToolRequestPart(
  toolRequest: interrupt.toolRequest,
  metadata: {...?interrupt.metadata, 'tool-approved': true},
);
// Pass `approved` back as the restart entry when resuming.
```

If instead you write your own `ctx.interrupt(...)` gate inside a tool (as in the
`coding_agent` sample), you inspect the resume payload yourself:

```dart
final resumed = ctx.toolRequest?.metadata?['resumed'];
final isApproved = resumed is Map && resumed['toolApproved'] == true;
```

## Notes & gotchas

- **No store required.** Interrupts work with either a
  [session store](agents-sessions.md) or
  [client-managed state](agents.md#client-managed-state-no-server-store).
- **`respond`/`restart` are builders.** They return resume entries; they do not
  send. You still call `chat.resume(...)`.
- **Resume validation.** The server validates each `respond`/`restart` entry
  against the conversation history — always build entries from the interrupt
  objects in the response, not hand-rolled parts.
- **Re-pausing.** After resuming, the new response may interrupt again; loop
  until `res.interrupts` is empty.
- **UX tip:** don't render a model message bubble for an interrupted turn; show
  the approval UI from `interrupt.input` instead, then render the model's reply
  after resuming.
