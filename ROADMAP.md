# Roadmap

Planned capabilities for the Joy coding agent. Nothing here is built yet.

## Permission rule system

Joy will need a permission rule system in the spirit of [Claude Code's](https://docs.claude.com/en/docs/claude-code/iam): rules, set by a human in a settings file, that allow, deny or ask before each tool call the agent makes (running a shell command, reading or writing a file), and that the agent cannot change itself.

Why: some harness rules only hold today because the agent obeys `AGENTS.md`. For example, nothing technical stops an agent from editing `harness/state/tasks*.json` directly, or from faking the interactive terminal that `joy task add`, `joy task drop` and `joy task wip` ask for. Deny rules such as "never write `harness/state/tasks*`" and "never run `joy task add`, `joy task drop` or `joy task wip`" would enforce them outside the agent's reach.

The agent must also never be able to modify a bootstrap script (`init.sh`, Joy's or a target application's). `joy task pass` trusts that script to decide whether a task is `passing`, so an agent that can edit it can make any task pass. A deny rule such as "never write `init.sh`" would close that gap.

## Scope check

`joy task pass` will compare the files the work changed (`git diff` since the task was activated) with the **SCOPE** section of the task's approved spec, and refuse to mark the task `passing` when the work went outside it.

Why: SCOPE is approved and frozen with the spec, but today only `AGENTS.md` asks the agent to stay inside it.
