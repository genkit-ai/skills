# Deploying / Serving Agents over HTTP (Experimental)

> **Experimental / preview API.** Uses `genkit.Handler` and the agent's companion
> actions. Read [agents.md](agents.md) first.

An agent is an `api.BidiAction`, so `genkit.Handler(agent)` serves it as a
standard HTTP action — **one turn per request**. Most agents also expose two
companion actions:

- `agent.GetSnapshotAction()` — read a snapshot's state. Needed for
  [snapshot restore](agents-branching.md) and [background](agents-background.md)
  polling. `nil` for a client-managed agent (no store).
- `agent.AbortAction()` — cancel a [background](agents-background.md) turn.
  `nil` unless the store implements `aix.SnapshotSubscriber` (both `localstore`
  stores do).

## Request/response shape

The handler accepts `{"data": <AgentInput>, "init": <AgentInit>}`:

- `data` — the turn's `aix.AgentInput` (message, resume, or `detach`). Required
  for one-shot (non-streaming) requests.
- `init` — the session source: `{"sessionId": ...}` or `{"snapshotId": ...}` for
  server-managed agents, `{"state": ...}` for client-managed ones. Omit for a
  fresh conversation.

Responses come back as `{"result": <AgentOutput>}`. Set
`Accept: text/event-stream` to stream chunks (`modelChunk`, `turnEnd`, then the
final `result`). Turn-tier failures return **200** with a failed `AgentOutput`
(so the caller keeps its last-good state); init-tier failures (a rejected session
source) are hard HTTP errors (400/404).

## A reusable helper for several agents

`exp.ListAgents(g)` returns every registered agent, so you can mount them
uniformly. A small helper keeps companion wiring consistent.

```go
func exposeAgent[State any](mux *http.ServeMux, agent *aix.Agent[State]) {
	base := "/api/" + agent.Name()
	mux.HandleFunc("POST "+base, genkit.Handler(agent))
	if snap := agent.GetSnapshotAction(); snap != nil {
		mux.HandleFunc("POST "+base+"/getSnapshot", genkit.Handler(snap))
	}
	if abort := agent.AbortAction(); abort != nil {
		mux.HandleFunc("POST "+base+"/abort", genkit.Handler(abort))
	}
}

mux := http.NewServeMux()
exposeAgent(mux, weatherAgent)    // plain chat: no companions registered
exposeAgent(mux, branchingAgent)  // has a store: getSnapshot registered
exposeAgent(mux, backgroundAgent) // store + subscriber: getSnapshot + abort

log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
```

To mount every agent generically (companions are typed on the concrete
`*aix.Agent[State]`, so from `exp.ListAgents` you serve the run action directly;
pluck companions off the typed value where you have it):

```go
for _, a := range exp.ListAgents(g) {
	mux.HandleFunc("POST /api/"+a.Name(), genkit.Handler(a))
}
```

Which companions to enable:

| Agent capability                          | `getSnapshot` | `abort` |
| ----------------------------------------- | ------------- | ------- |
| Plain chat (client- or server-state)      | –             | –       |
| Snapshot restore / [branching](agents-branching.md) | ✓   | –       |
| [Background](agents-background.md) / detach | ✓           | ✓       |

## CORS for browser clients

A browser calling a different origin (e.g. a Vite dev server) needs CORS.
Streaming uses Server-Sent Events, so allow the `Accept` header and handle
preflight.

```go
func withCORS(h http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Accept")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		h.ServeHTTP(w, r)
	})
}

log.Fatal(server.Start(ctx, "127.0.0.1:8080", withCORS(mux)))
```

## Registering agents

Agents register with Genkit when their `genkitx.DefineAgent` (or
`DefineCustomAgent` / `DefinePromptAgent`) call runs, so make sure the code that
defines them executes during startup. Keep a reference to the returned
`*aix.Agent[State]` to reach `RunText`, `GetSnapshot`, `Abort`, and the companion
actions from your own code.

## Verifying locally

Run under the Genkit CLI so turns are traced, and drive the endpoint with `curl`:

```bash
genkit start -- go run .
```

```bash
# One-shot turn:
curl -s localhost:8080/api/weatherAgent \
  -H 'Content-Type: application/json' \
  -d '{"data":{"message":{"role":"user","content":[{"text":"Weather in Tokyo?"}]}}}'

# Resume a server-managed session:
curl -s localhost:8080/api/weatherAgent \
  -H 'Content-Type: application/json' \
  -d '{"data":{"message":{"role":"user","content":[{"text":"And Paris?"}]}},"init":{"sessionId":"<id>"}}'
```

You can also exercise an agent from the CLI by wrapping one turn in a throwaway
flow and using `genkit flow:run` (see [agents.md](agents.md#verify-an-agent-from-the-cli-flowrun)).
