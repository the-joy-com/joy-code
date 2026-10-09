# Roadmap

Planned capabilities for the Joy coding agent. Nothing here is built yet.

## Permission rule system

Joy will need a permission rule system in the spirit of [Claude Code's](https://docs.claude.com/en/docs/claude-code/iam): rules, set by a human in a settings file, that allow, deny or ask before each tool call the agent makes (running a shell command, reading or writing a file), and that the agent cannot change itself.

Why: some harness rules only hold today because the agent obeys `AGENTS.md`. For example, nothing technical stops an agent from editing `harness/state/tasks*.json` directly, or from faking the interactive terminal that `joy task add`, `joy task drop` and `joy task wip` ask for. Deny rules such as "never write `harness/state/tasks*`" and "never run `joy task add`, `joy task drop` or `joy task wip`" would enforce them outside the agent's reach.

The agent must also never be able to modify a bootstrap script (`init.sh`, Joy's or a target application's). `joy task pass` trusts that script to decide whether a task is `passing`, so an agent that can edit it can make any task pass. A deny rule such as "never write `init.sh`" would close that gap.

## SCOPE check: intent or files mode

Today the SCOPE check that `joy task pass` runs (see `README.md`, SCOPE check) is in files mode: the work passes only when every file it changed is listed in the task's approved **SCOPE**. An intent-or-files mode would also accept a change to a file outside SCOPE when that change clearly serves the task's approved **TASK**. Files listed in SCOPE would pass as they do today, so the work passes when each changed file is either in SCOPE (files) or justified by TASK (intent).

Who judges intent: never the agent doing the work, since it would be judging its own changes. The judge is a separate reviewer: a human, or a reviewer model that the working agent cannot configure. It gets TASK, SCOPE and the diff of the files outside SCOPE, and answers for each file whether its change serves TASK, with a reason. `joy task pass` refuses the work if any file is not accepted.

Who turns it on: files mode stays the default. Only a human switches a ledger to intent-or-files mode, or back, with a confirmation typed at an interactive terminal, like `joy task wip`.

What is recorded: each file accepted on intent, with the reviewer's reason, goes into the task's evidence (and the EVIDENCE section of its spec), so the human review sees what went beyond SCOPE and why.

Why: files mode refuses small, useful changes that a SCOPE written in advance could not foresee, such as a shared helper or a test fixture, and each one costs a dropped task and a new draft. The cost: this mode is weaker than files mode. It trades a mechanical check for a judgment that can be wrong, or be argued with in the code itself, which is why it is opt-in, set by a human, and recorded.
