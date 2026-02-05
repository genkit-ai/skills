# Implementation Guide: Updating Skills for Genkit

This document serves as a persistent guide and roadmap for updating the `skills` folder to align with Agent Skills specifications and the latest Genkit framework guidelines.

## Project Goal

Update the `skills` folder to be standardized "Agent Skills" that leverage Genkit documentation and tools. We aim to support multi-platform usage (Node.js, Go, Python) using a **Language-Centric Discovery Strategy**.

## Concepts & Best Practices

### Agent Skills Specification

- **Directory Structure**:
  ```
  skill-name/
  ├── SKILL.md          # Entry point (Metadata + High-level instructions)
  ├── references/       # Essential references only (e.g., common errors)
  └── assets/           # Static resources
  ```

### Design Principles

- **Discovery over Documentation**: Instead of embedding all documentation into the skill, the skill guides the agent to **discover** the right information from authoritative sources (local docs, source code).
- **Mistrust Internal Knowledge**: Explicitly instruct the agent that its training data may be outdated and it must verify against provided docs.
- **Language Centric**: Separate skills for each language ecosystem (`genkit-js`, `genkit-go`, `genkit-py`) to provide focused environments.

### Design Rationale

- **Language-Based Split**: Since Genkit is an SDK, organizing skills by language (JS, Go, Python) allows all relevant information to be discoverable under a single, focused skill context.
- **Discovery vs. Documentation**: Skills are not a replacement for documentation. Documentation is volatile, and keeping static references updated is inefficient. Enabling discovery (guiding the agent to authoritative local docs) ensures the agent always uses the most current information.

## Structural Strategy

### Language-Centric Skills

We organize skills by **Language** to provide a coherent environment for the agent.

**Structure:**

```
genkit-js/
├── SKILL.md            # Discovery instructions for Node.js
└── references/
    └── best-practices.md # recommended patterns
    └── common-errors.md # Critical "gotchas" or pitfalls
└── assets/
    └── docs-bundle.json
```

### Discovery Pattern

The `SKILL.md` for each language should follow this pattern:

1.  **Prerequisites**: Check for local docs/tools.
2.  **Warning**: "Do not trust internal knowledge."
3.  **Discovery Instructions**: How to find docs in `$HOME/.genkit/docs/<ver>` or via Genkit MCP server. Best if the docs can be bundled directly in the skill (`/assets/` or accessible via the CLI). If bundled directly, discoverability can be updated to to use local tools like `grep` to lookup specific terms in the docs (keyword search).
4.  **References**: Extra specifications on common pitfalls and best practices.

## Target Skill List

1.  **`genkit-js`**: P0 - For Node.js/TypeScript development.
2.  **`genkit-go`**: For Go development.
3.  **`genkit-py`**: For Python development.
