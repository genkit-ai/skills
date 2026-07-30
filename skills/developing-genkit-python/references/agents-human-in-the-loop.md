# Agent Human-in-the-Loop / Interrupts (Beta)

> **Beta / preview API.** Read [agents.md](agents.md) first.

An **interrupt** pauses an agent mid-turn and hands control back to your code (or
a human) — e.g. to approve a sensitive tool before it runs. You then **resume**
from the exact point it paused.

Interrupts are **orthogonal to persistence** — they work the same whether the
agent uses a [session store](agents-sessions.md) or
[client-managed state](agents.md#client-managed-state-no-server-store).

Flow: `chat.send(...)` → response has `finish_reason == INTERRUPTED` and
`res.interrupts` → collect human input → `chat.resume(...)`.

## ToolApproval middleware (common path)

`ToolApproval` interrupts before tools run. Tools listed in `allowed_tools` run
without prompting; everything else pauses. An empty list means **every** tool
needs approval.

```python
from uuid import uuid4

from pydantic import BaseModel, Field
from genkit_google_genai import GoogleAI
from genkit_middleware import Middleware, ToolApproval

from genkit import Genkit, ToolRequestPart
from genkit.agent import AgentFinishReason, InMemorySessionStore

ai = Genkit(plugins=[GoogleAI(), Middleware()])
tool_approval = ToolApproval(allowed_tools=[])  # approve all tools


class TransferInput(BaseModel):
    amount: float
    to_account: str = Field(alias='toAccount')


class TransferOutput(BaseModel):
    success: bool
    transaction_id: str = Field(alias='transactionId')


@ai.tool(name='transferMoney', description='Transfer money between accounts.')
async def transfer_money(input: TransferInput) -> TransferOutput:
    return TransferOutput(success=True, transactionId=f'txn-{uuid4().hex[:12]}')


agent = ai.define_agent(
    name='bankingAgent',
    model='googleai/gemini-flash-latest',
    system='Banking assistant. Call transferMoney when the user asks to transfer money.',
    tools=[transfer_money],
    use=[tool_approval],
    store=InMemorySessionStore(),
)
```

## Detect and resume

```python
chat = agent.chat()

out1 = await chat.send('Transfer $500 to account 12345 for rent.').response
assert out1.finish_reason == AgentFinishReason.INTERRUPTED
# transferMoney is pending — it has NOT executed yet.

# Approve each pending tool call, then one resume continues the turn.
restart_parts: list[ToolRequestPart] = [
    intr.restart(resumed_metadata={'tool_approved': True}) for intr in out1.interrupts
]
out2 = await chat.resume(restart=restart_parts).response
assert out2.finish_reason == AgentFinishReason.STOP
```

Notes on resume helpers:

- `interrupt.restart(...)` — re-issues the original tool request so the tool
  actually runs (used by ToolApproval after human OK). Accepts
  `resumed_metadata={'tool_approved': True}` (camelCase `toolApproved` also works).
- `interrupt.respond(output)` — supplies a tool response **without** executing
  the tool (useful for custom interrupt tools that collect human input).
- Both are **builders**. They return parts; you still call `chat.resume(...)`.

You can mix respond and restart:

```python
await chat.resume(
    respond=[a.respond({'approved': True})],
    restart=[b.restart(resumed_metadata={'tool_approved': True})],
).response
```

Streaming works the same way — `chat.resume(...)` returns an `AgentTurn`:

```python
turn = chat.resume(restart=restart_parts)
async for chunk in turn.stream:
    if chunk.text:
        print(chunk.text, end='', flush=True)
final = await turn.response
```

## Without a store

Interrupts still work. Keep the same `chat` object across send → resume, or
round-trip `messages` / `state` / `artifacts` yourself when opening a new chat
(see [client-managed state](agents.md#client-managed-state-no-server-store)).

## Gotchas

- Always build resume parts from `res.interrupts` — hand-rolled parts are
  rejected by resume validation.
- After resuming, the new response may interrupt again; loop until
  `finish_reason` is no longer `INTERRUPTED`.
- Don't treat an interrupted turn as a final model reply in the UI — show the
  approval UI from `interrupt` input, then render the reply after resume.
