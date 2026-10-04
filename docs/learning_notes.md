# notes on [hands on harness engineering course](https://hands-on-harness-engineering.com/)

## general principles

- A coding agent's reliability hinges on five things outside the model: 
    - a sane execution environment
    - clear instructions
    - durable state
    - the right tools
    - verification feedback
- AI coding agents are capable. The problem is making them _reliable_. 
- Anthropic found that agents confidently praise their own work, and the solution is to separate "the agent who does the work" from "the agent who checks the work."
- Common problems in harness engineering are:
    - Definition of Done: A set of machine-verifiable conditions — tests pass, lint is clean, type checks pass. Without an explicit definition of done, the agent will invent its own.
    - Verification Gap: The gap between the agent's confidence in its output and actual correctness. The agent says "I'm done" when it's not done — this is the most common failure mode.
- **Harness** definition: Everything outside the model — instructions, tools, environment, state management, verification feedback. If it's not model weights, it's harness.
- In harness engineering, a diagnostic loop consists of executing, observing, and attributing the failure to one of the 5 harness layers, to fix that layer, and to re-execute.
- In harness engineering, a system of record (SoR) is the central, authoritative data source that serves as the "single source of truth" for a project. This is absolutely mandatory for an AI coding agent: the repository at hand should be the self-contained source of information on how to build stuff. It's called the "repo as spec" principle.
- one good methodology in testing harness quality is to stay "iso-model", meaning, don't swap models to get better results, improve each subsystem to the max before deciding to upgrade the model; also one good approach in improving a harness is to distinguish between:
    - "gulf of execution": agent does not know _how_ to do something
    - "gulf of verification": agent does not if what it built is _right_
- OpenAI distills the engineer's core job into three things: designing environments, expressing intent, and building feedback loops.
- The 5 defense layers in developing a good agentic application are: 
    - context provision
        - e.g. a `CLAUDE.md` at the repo root saying "use `pnpm`, not `npm`; tests live in `tests/`", so the agent doesn't have to guess
    - execution environment
        - e.g. the agent runs inside a Docker container with only the project folder mounted and no network access, so a bad `rm -rf` can't touch the host
    - state management
        - e.g. the agent keeps a `progress.md` checklist ("[x] add model, [ ] add API route") and commits after each step, so it can resume after a crash or context reset
    - task specification
        - e.g. instead of "fix the login", the task says "login with a wrong password must return HTTP 401 and show 'Invalid credentials'; don't touch the signup flow"
    - verification feedback
        - e.g. after each change the agent runs `pnpm test && pnpm lint` and reads the failures, looping until everything is green before saying it's done

## the five-subsystem harness model

![the five-subsystem harness model](./five-subsystem_harness_model.png)

In harnessing a coding agent, you'd have 5 subsystems:

- instruction
- tooling
- running environment
- state
- feedback

Usually, modifying a layer of the harness means adapting the other layers in some way.

### the instructions subsystem

It's the one that contains the project rules, materialized by the `AGENTS.md` file.

`AGENTS.md` (or `CLAUDE.md`) should contain:
    - a project overview and purpose (in one sentence)
    - first-run commands (e.g. `make setup`, `make test`, etc.)
    - non-negotiable hard constraints (for instance "All APIs must use OAuth 2.0")
    - tech stack and versions (e.g. Python 3.11, FastAPI 0.100+, PostgreSQL 1, etc.)
    - links to more detailed documentation for everything that does not fit the above

### the tooling subsystem

Ensure the agent has sufficient tool access. Don't disable shell for "security" — if the agent can't even run `pip install`, how is it supposed to work? But don't open everything either — follow least-privilege principles.

Usually, a tooling subsystem is expressed in terms of verbs for the coding agent.

### the running environement subsystem

Environment subsystem: Make the environment state self-describing and deterministic. 

This can span over things like using `pyproject.toml` or `package.json` to lock dependencies, `.nvmrc` or `.python-version` for runtime versions, Docker or dev containers for reproducibility, etc.

### the state subsystem

Long tasks need progress tracking. This mean each task needs to produce a durable artifact that the next session can read.

You can get by with a simple `PROGRESS.md` file recording: what's done, what's in progress, what's blocked. This is to be updated before each session ends and to be read when the next session starts. Cross-session knowledge recoverability directly determines task success rates with coding agents, this state must exist in the repository — because that's the only stable, accessible storage the agent has.

#### the "repo as spec" principle

Knowledge not in the repo doesn't exist for the agent. Putting critical decisions in the repo is the most basic harness investment.

You can quickly try if your repo as spec works well by asking these types of questions as a _cold start_ (can a fresh session answer five basic questions using only repo contents?) =>

![state subsystem checklist](./state-subsystem-checklist.png)

If it can't answer, the map has blank spots. Where the map is blank, the agent guesses — wrong guesses become bugs, excessive guessing wastes context. And every new session guesses all over again. The cost of guessing is always higher than the cost of drawing the map properly in the first place.

One gotcha => _knowledge Decay Rate_: the proportion of knowledge entries that become stale per unit of time. Documentation going out of sync with code is the biggest enemy — worse than no documentation at all.

A few guidelines to live by when setting up the state subsystem:
- knowledge lives next to code in digestable fragments instead of being in a giant document
- the entry file of your state subsystem (`AGENTS.md` or `CLAUDE.md`) should be concise
- each piece of knowledge should be minimal and have a clear use-case; if removing content in a given piece of docs does not change agent's decision quality then the information is probably useless... however you should always be able to answer the _cold start_ questions easily and with speed using your agent, this is a delicate equilibrium to reach
- docs should update with code => knowlege updates should be bound to code updates _systematically_, ideally this should be checked via the CI automatically


#### analogy of agent state management with ACID principles

- **Atomicity**:  Each "logical operation" (e.g., "add new endpoint and update tests") gets one git commit or git add. If it fails midway, agent should be able to roll back using git as well. All or nothing — no "half done".
- **Consistency**: Define "consistent state" verification predicates — all tests pass, lint reports zero errors. The agent runs verification after each operation; inconsistent intermediate states don't get added. Like a bank transfer — you can't debit without crediting.
- **Isolation**: When sub agents work concurrently, design state files to avoid race conditions. Simple approach: each agent uses its own progress file, or use git branches for isolation. Two chefs can't season the same pot simultaneously — who takes responsibility when it's over-salted?
- **Durability**: Critical project knowledge lives in git-tracked files. Temporary state can stay in session memory, but cross-session knowledge must be persisted to files. What's in your head doesn't count — only what's on paper counts.


### the feedback subsystem

This is the highest-ROI subsystem. It should consist of a list of verification commands referenced in `AGENTS.md`. 

The feedback subsystme checks for verification signals (exit codes, stdout,` node --test output`, etc.).
It is also constitued by plain automatic testing.


Example below

```txt
Verification commands:
- Tests: pytest tests/ -x
- Type check: mypy src/ --strict
- Lint: ruff check src/
- Full verification: make check (includes all above)
```

...
