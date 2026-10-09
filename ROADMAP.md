# Roadmap

Planned capabilities for the harness overlay. Nothing here is built yet.


## Permission rule system

The harness does not run the agent: the coding tool does. So it will ship permission rules for the tools it overlays, written in each tool's own permission settings (for example [Claude Code's](https://docs.claude.com/en/docs/claude-code/iam) deny rules in its settings file): rules, set by a human, that allow, deny or ask before each tool call the agent makes (running a shell command, reading or writing a file), and that the agent cannot change itself.

Why: some harness rules only hold today because the agent obeys `AGENTS.md`. For example, nothing technical stops an agent from editing `harness/state/tasks*.json` directly, or from faking the interactive terminal that `joy task add`, `joy task drop` and `joy task wip` ask for. Deny rules such as "never write `harness/state/tasks*`" and "never run `joy task add`, `joy task drop` or `joy task wip`" would enforce them outside the agent's reach.

The agent must also never be able to modify a bootstrap script (`init.sh`, the harness's own or a target application's). `joy task pass` trusts that script to decide whether a task is `passing`, so an agent that can edit it can make any task pass. A deny rule such as "never write `init.sh`" would close that gap.


## SCOPE check: intent or files mode

Today the SCOPE check that `joy task pass` runs (see `README.md`, SCOPE check) is in files mode: the work passes only when every file it changed is listed in the task's approved **SCOPE**. An intent-or-files mode would also accept a change to a file outside SCOPE when that change clearly serves the task's approved **TASK**. Files listed in SCOPE would pass as they do today, so the work passes when each changed file is either in SCOPE (files) or justified by TASK (intent).

Who judges intent: never the agent doing the work, since it would be judging its own changes. The judge is a separate reviewer: a human, or a reviewer model that the working agent cannot configure. It gets TASK, SCOPE and the diff of the files outside SCOPE, and answers for each file whether its change serves TASK, with a reason. `joy task pass` refuses the work if any file is not accepted.

Who turns it on: files mode stays the default. Only a human switches a ledger to intent-or-files mode, or back, with a confirmation typed at an interactive terminal, like `joy task wip`.

What is recorded: each file accepted on intent, with the reviewer's reason, goes into the task's evidence (and the EVIDENCE section of its spec), so the human review sees what went beyond SCOPE and why.

Why: files mode refuses small, useful changes that a SCOPE written in advance could not foresee, such as a shared helper or a test fixture, and each one costs a dropped task and a new draft. The cost: this mode is weaker than files mode. It trades a mechanical check for a judgment that can be wrong, or be argued with in the code itself, which is why it is opt-in, set by a human, and recorded.

## Interactive integrations: Claude Code and OpenCode

Today the overlay is passive: the coding tool reads `AGENTS.md`, and the routine (clock in, task status, drafts, clock out) only happens if the agent follows the text, or if the human types the `joy task` commands. An integration makes that routine part of the tool itself, so the human and the agent see the task state and the next step without asking for them, and the rules that matter most hold even when the agent forgets them.

1) Claude Code integration, shipped as a Claude Code plugin or as project files the overlay provides:

- Slash commands for the routine: `/clock-in` (bootstrap script, progress, decisions and handoff files, `joy task status`), `/task-status`, `/draft-task` (a spec draft from `instruction_template.md`, in the right drafts folder) and `/clock-out` (verification, progress file, staging, review request).
- Hooks: a session start hook that runs the bootstrap script and shows `joy task status` and the next step from the progress file; a pre tool use hook that refuses writes to harness task JSON files and to `init.sh`; a stop hook that reminds the agent of the clock out steps when it ends a session with work unstaged or a task still `active`.
- Permission deny rules in its settings for the human-only commands (`joy task add`, `joy task drop`, `joy task wip`), as planned in the permission rule system above.

2) OpenCode integration, with the same routine through OpenCode's own extension points: custom commands for `/clock-in`, `/task-status`, `/draft-task` and `/clock-out`, a plugin reacting to tool execution events for the same refusals as the Claude Code hooks, and permission rules in its configuration that deny the human-only commands.

What stays the same: `AGENTS.md` stays the single entry point and `joy task` stays the single way to change the ledger. The integrations call them; they never copy their rules, so a rule changes in one place only. A coding tool without an integration keeps working with `AGENTS.md` alone.
