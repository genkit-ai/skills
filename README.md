# Genkit Agent Skills

This repository contains "Agent Skills" designed to teach AI agents how to build applications using the [Genkit](https://genkit.dev) framework.

## Available Skills

-   **[developing-genkit-js](skills/developing-genkit-js/SKILL.md)**: For developing Genkit applications with Node.js and TypeScript.

## Installation

You can install skills in various ways (in your project workspace):

### Using [skills.sh](https://skills.sh) (Recommended) 

```bash
npx skills add genkit-ai/skills
```

### Using tool-specific command

For example (if using [Gemini CLI](https://geminicli.com/docs/cli/skills/#from-the-terminal)):

```bash
gemini skills install https://github.com/genkit-ai/skills.git --path skills/developing-genkit-js
```

### Manual Installation

Copy-paste the skills folder in the appropriate location for your tool of choice.

## Usage

These skills follow the [Agent Skills Specification](https://agentskills.io/specification). Point your agent environment to the relevant skill directory to enable Genkit-specific capabilities.
