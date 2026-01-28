# Implementation Guide: Updating Skills for Genkit

This document serves as a persistent guide and roadmap for updating the `skills` folder to align with Agent Skills specifications and the latest Genkit framework guidelines.

## Project Goal
Update the `skills` folder to be standardized "Agent Skills" that leverage Genkit documentation and tools. We aim to support multi-platform usage (Node.js, Go, Python) efficiently using progressive disclosure.

## Concepts & Best Practices

### Agent Skills Specification
- **Directory Structure**:
    ```
    skill-name/
    ├── SKILL.md          # Entry point (Metadata + High-level instructions)
    ├── references/       # Detailed documentation (Loaded on demand)
    └── assets/           # Static resources
    ```
- **Token Limits**:
    -   **Metadata**: ~100 tokens (Loaded at startup).
    -   **Instructions (`SKILL.md`)**: < 5000 tokens (Loaded on activation).
    -   **References**: Concise, domain-specific files.

### Design Principles
- **Progressive Disclosure**: Use `references/` to separate implementation details (e.g., by language). The agent reads `SKILL.md` first, then loads specific references only when needed.
- **Naming**: Use descriptive, action-oriented names (e.g., `genkit-flows`, `genkit-models`).
- **Standalone Capability**: Skills should be usable even if the Genkit MCP server is not available. Do not hardcode dependencies on MCP tools unless they are guaranteed to be present or the skill is specifically *about* using that tool.

## Structural Strategy

### Unified Skills with Language References
We organize skills by **Feature/Topic** and use the `references/` folder to handle language-specific implementations.

**Structure:**
```
genkit-flows/
├── SKILL.md            # Overview & Navigation ("For Node.js, see references/nodejs.md")
└── references/
    ├── nodejs.md       # Node.js implementation
    ├── go.md           # Go implementation
    └── python.md       # Python implementation
```

**Benefits**: Unified discovery (one skill per concept) and high context efficiency (loading only relevant language docs).

### Plugin Strategy Analysis
We evaluated two approaches for handling the extensive Genkit Plugin ecosystem (18+ plugins like `google-genai`, `firebase`, `chroma`, `ollama`, etc.).

| Criteria | Single Skill (`genkit-plugins`) | Individual Skills (`genkit-plugin-x`) |
| :--- | :--- | :--- |
| **Discovery** | **High**. 1 unified skill for "Plugins". Requires 1 metadata slot in system prompt. | **Low**. 18+ skills. Floods the agent's system prompt with 18+ descriptions, diluting core skills. |
| **Context Usage** | **Efficient**. Lightweight `SKILL.md`. Loads specific plugin ref (`references/google-genai.md`) on demand. | **Specific**. Loads specific `SKILL.md`. Efficient if only 1 plugin is needed, but costly if exploring options. |
| **Maintenance** | **Centralized**. "How to install" guide is written once. Specific configs live in Refs. | **Duplicated**. "How to install" instructions repeated across 18 files. |
| **Pattern Match** | **High**. All plugins share the same `configureGenkit` init pattern. | **Medium**. Separates logically related integrations. |
| **Example: `google-genai`** | `genkit-plugins/references/google-genai.md` | `genkit-plugin-google-genai/SKILL.md` |

**Decision**: We will use **`genkit-plugins` (Single Skill)**. The uniform initialization pattern of Genkit plugins makes a unified catalog with progressive disclosure the superior choice for maintainability and discoverability.

### Content Strategy (Growth & Neutrality)
-   **Gemini-First Defaults**: In `genkit-basics` and `genkit-models`, use **Gemini** (via `google-genai`) for primary code examples to support growth OKRs.
-   **Vendor-Neutral Structure**: Maintain a flat, peer-based list in `genkit-plugins/references/` to ensure the platform remains publicly neutral.

## Target Skill List

1.  **`genkit-basics`**: Installation, configuration, project structure (single-file rule).
2.  **`genkit-flows`**: Defining flows, schemas, streaming.
3.  **`genkit-models`**: Generating content, multi-modal inputs, model configuration.
4.  **`genkit-tools`**: Tool definitions and calling.
5.  **`genkit-plugins`**: Directory and configuration for all plugins.
6.  **`genkit-tooling`**: CLI commands, Developer UI, and MCP Server management.

## Roadmap

- [x] **Phase 1: Analysis & Strategy**
    - [x] Define Agent Skills and Genkit requirements.
    - [x] Select "Unified Strategy" and "Single Plugin Skill".
    - [x] Define Content Strategy.

- [ ] **Phase 2: Implementation**
    - [ ] **Refactor `genkit-js` -> `genkit-basics`**: Move JS-specifics to `references/nodejs.md`. Add Project Structure guidance.
    - [ ] **Create `genkit-flows`**: Implement Unified structure.
    - [ ] **Create `genkit-models`**: Implement Unified structure (Gemini-first examples).
    - [ ] **Create `genkit-tools`**: Implement Unified structure.
    - [ ] **Create `genkit-plugins`**: Implement structure. Migrate existing references (`gemini.md`) to this skill.
    - [ ] **Create `genkit-tooling`**: Implement structure (CLI, Dev UI, MCP).
    - [ ] **Populate Content**: Extract relevant content from Genkit Usage Guide.

- [ ] **Phase 3: Validation**
    - [ ] Verify structure matches Agent Skills spec.
    - [ ] Verify progressive disclosure (navigation from `SKILL.md` to `references/`).
    - [ ] Verify token limits and standalone usage.
