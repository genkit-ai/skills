# Agent Branching (Beta)

> **Beta / preview API.** Requires a [session store](agents-sessions.md). Read
> [agents.md](agents.md) first.

A `snapshot_id` is an **immutable checkpoint**, like a git commit. You can fork
as many independent timelines as you want from the same snapshot — each turn
from a snapshot creates a new, independent snapshot; the original is unchanged.

To branch, load a chat attached to an earlier snapshot via
`load_chat(snapshot_id=...)`.

## Fork sibling timelines

```python
from genkit.agent import InMemorySessionStore

# After a fork, session_id lookup is ambiguous — raise instead of guessing.
store = InMemorySessionStore(reject_ambiguous_session=True)

agent = ai.define_agent(
    name='designer',
    model='googleai/gemini-flash-latest',
    system='You help design a product landing page. Reply briefly.',
    store=store,
)

root = agent.chat()
await root.send('Plan a landing page for a note-taking app.').response
checkpoint = root.snapshot_id
session_id = root.session_id

# Two independent branches from the same checkpoint.
minimal = await agent.load_chat(snapshot_id=checkpoint)
await minimal.send('Direction: minimal.').response

bold = await agent.load_chat(snapshot_id=checkpoint)
await bold.send('Direction: bold.').response
chosen_leaf = bold.snapshot_id

# session_id can no longer mean "the latest turn" — Genkit raises
# FAILED_PRECONDITION rather than silently picking a branch.
# Resolve by resuming the specific leaf you want:
resumed = await agent.load_chat(snapshot_id=chosen_leaf)
await resumed.send('Add a pricing section.').response
```

## Time travel

Same idea for "edit and resubmit": keep the earlier snapshot id, open a new chat
from it, and send a different follow-up. The first answer remains as its own
sibling leaf in the store.

## Prefer snapshot_id after forks

Once a session has multiple leaves, prefer `snapshot_id` over `session_id` for
resume. With `reject_ambiguous_session=True`, ambiguous `session_id` lookups
fail loudly (recommended for branching UIs).

Abandoned branches simply remain in the store as immutable snapshots; nothing
is overwritten when you branch.
