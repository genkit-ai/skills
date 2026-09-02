# Genkit Agent Skills

This repository contains "Agent Skills" designed to teach AI agents how to build applications using the [Genkit](https://genkit.dev) framework.

## Available Skills

- **[developing-genkit-js](skills/developing-genkit-js/SKILL.md)**: For developing Genkit applications with Node.js and TypeScript.
- **[developing-genkit-dart](skills/developing-genkit-dart/SKILL.md)**: For developing Genkit applications with Dart.
- **[developing-genkit-go](skills/developing-genkit-go/SKILL.md)**: For developing Genkit applications with Go.
- **[developing-genkit-python](skills/developing-genkit-python/SKILL.md)**: For developing Genkit applications with Python.

## Installation

### Using [skills.sh](https://skills.sh)

Install skills into your project workspace:

**For Node.js / TypeScript:**

```bash
npx skills add genkit-ai/skills --skill developing-genkit-js
```

**For Dart:**

```bash
npx skills add genkit-ai/skills --skill developing-genkit-dart
```

**For Go:**

```bash
npx skills add genkit-ai/skills --skill developing-genkit-go
```

**For Python:**

```bash
npx skills add genkit-ai/skills --skill developing-genkit-python
```

### Manual Installation

Copy the relevant skill folder into the appropriate location for your tool of choice.

## Usage

These skills follow the [Agent Skills Specification](https://agentskills.io/specification). Point your agent environment to the relevant skill directory to enable Genkit-specific capabilities.
