---
name: developing-genkit-go
description: Develop AI-powered applications using Genkit in Go. Use when the user asks to build AI features, agents, flows, or tools in Go using Genkit, or when working with Genkit Go code involving generation, prompts, streaming, tool calling, or model providers.
---

# Genkit Go

Genkit Go is an AI SDK for Go that provides generation, structured output, streaming, tool calling, prompts, and flows with a unified interface across model providers.

## Hello World

```go
package main

import (
	"context"
	"fmt"
	"log"
	"net/http"

	"github.com/genkit-ai/genkit/go/ai"
	"github.com/genkit-ai/genkit/go/genkit"
	"github.com/genkit-ai/genkit/go/plugins/googlegenai"
	"github.com/genkit-ai/genkit/go/plugins/server"
)

func main() {
	ctx := context.Background()
	g := genkit.Init(ctx, genkit.WithPlugins(&googlegenai.GoogleAI{}))

	genkit.DefineFlow(g, "jokeFlow", func(ctx context.Context, topic string) (string, error) {
		return genkit.GenerateText(ctx, g,
			ai.WithModelName("googleai/gemini-3-flash-preview"),
			ai.WithPrompt("Tell me a joke about %s", topic),
		)
	})

	mux := http.NewServeMux()
	for _, f := range genkit.ListFlows(g) {
		mux.HandleFunc("POST /"+f.Name(), genkit.Handler(f))
	}
	log.Fatal(server.Start(ctx, "127.0.0.1:8080", mux))
}
```

## Core Features

Load the appropriate reference based on what you need:

| Feature | Reference | When to load |
| --- | --- | --- |
| Initialization | [references/getting-started.md](references/getting-started.md) | Setting up `genkit.Init`, plugins, the `*Genkit` instance pattern |
| Generation | [references/generation.md](references/generation.md) | `Generate`, `GenerateText`, `GenerateData`, streaming, output formats |
| Prompts | [references/prompts.md](references/prompts.md) | `DefinePrompt`, `DefineDataPrompt`, `.prompt` files, schemas |
| Tools | [references/tools.md](references/tools.md) | `DefineTool`, tool interrupts, `RestartWith`/`RespondWith` |
| Flows & HTTP | [references/flows-and-http.md](references/flows-and-http.md) | `DefineFlow`, `DefineStreamingFlow`, `genkit.Handler`, HTTP serving |
| Model Providers | [references/providers.md](references/providers.md) | Google AI, Vertex AI, Anthropic, OpenAI-compatible, Ollama setup |

## Genkit CLI

Check if installed: `genkit --version`

**Installation:**
```bash
curl -sL cli.genkit.dev | bash
```

**Usage:**
```bash
genkit start -- go run .
```

This launches the Genkit developer UI with tracing at `http://localhost:4000`.

## Best Practices

- Always pass the `*Genkit` instance (`g`) to Genkit functions; do not use globals.
- Use `genkit.DefineSchemaFor[T](g)` to register Go types for use in `.prompt` files.
- Use `jsonschema:"description=..."` struct tags to give the model field-level guidance.
- Prefer `GenerateText` for simple text, `GenerateData[T]` for structured output, and `Generate` only when you need the full `*ModelResponse`.
- Use flows to wrap AI logic for observability, tracing, and HTTP deployment.
- Run `go vet ./...` after making changes to catch issues early.
