# Roadmap

Planned capabilities for the Joy coding agent. Nothing here is built yet.

## Permission rule system

Joy will need a permission rule system in the spirit of [Claude Code's](https://docs.claude.com/en/docs/claude-code/iam): rules, set by a human in a settings file, that allow, deny or ask before each tool call the agent makes (running a shell command, reading or writing a file), and that the agent cannot change itself.

Why: some harness rules only hold today because the agent obeys `AGENTS.md`. For example, nothing technical stops an agent from editing `harness/state/tasks*.json` directly, or from faking the interactive terminal that `joy task drop` and `joy task wip` ask for. Deny rules such as "never write `harness/state/tasks*`" and "never run `joy task drop` or `joy task wip`" would enforce them outside the agent's reach.
