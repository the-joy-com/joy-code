"""Machine-readable task ledger enforcing a WIP limit through the Verified Completion Rate.

The ledger is `<state>/tasks.json`. VCR = passing / activated, where activated tasks are the
`active`, `blocked` and `passing` ones (`dropped` ones do not count, and 0/0 is 1.0). The gap
between the two is the work in progress, so with the default WIP limit of 1 a task can only be
activated while VCR is 1.0. Only a human can change the limit (`wip`), and only `pass` can mark a
task `passing`: it runs the ledger's bootstrap script itself and records the evidence.

Every task starts from a spec a human approved (`add --spec`): `<instructions>/<id>.md`, whose
TASK, SCOPE and DONE WHEN sections are fingerprinted at approval and must not change afterwards,
and whose verification command must fail at approval and pass, with the bootstrap, at `pass`.
`joy task` rewrites the spec's STATE and EVIDENCE sections from the ledger on every save.

To keep the ledger the size of the current work, every save moves `passing` and `dropped` tasks to
the append-only `<state>/tasks.archive.jsonl` and keeps only their counts, which is all VCR needs.
"""

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

VERSION = 1
STATES = ("not_started", "active", "blocked", "passing", "dropped")
ACTIVATED = ("active", "blocked", "passing")
IN_PROGRESS = ("active", "blocked")
FINISHED = ("passing", "dropped")
OUTPUT_TAIL_LINES = 3
DEFAULT_WIP_LIMIT = 1
SPEC_SECTIONS = ("TASK", "SCOPE", "DONE WHEN", "STATE", "EVIDENCE")
FROZEN_END = "\n## STATE\n"


class LedgerError(Exception):
    pass


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger_path(state: str) -> Path:
    return Path(state) / "tasks.json"


def archive_path(state: str) -> Path:
    return Path(state) / "tasks.archive.jsonl"


def instructions_dir(state: str) -> Path:
    # The instructions folder mirrors the state folder: harness/state/<app> -> harness/instructions/<app>.
    parts = list(Path(state).parts)
    if "state" not in parts:
        raise LedgerError(f"cannot find the instructions folder of {state}: it has no `state` folder")
    i = len(parts) - 1 - parts[::-1].index("state")
    parts[i] = "instructions"
    return Path(*parts)


def task_number(tid: str) -> int:
    return int(tid[2:]) if tid.startswith("T-") and tid[2:].isdigit() else 0


def validate(ledger: dict) -> list[str]:
    if not isinstance(ledger, dict) or ledger.get("version") != VERSION:
        return [f"version must be {VERSION}"]
    errors = []
    if not isinstance(ledger.get("bootstrap"), str) or not ledger["bootstrap"]:
        errors.append("bootstrap must name the bootstrap script")
    wip_limit = ledger.get("wip_limit", DEFAULT_WIP_LIMIT)
    if not isinstance(wip_limit, int) or isinstance(wip_limit, bool) or wip_limit < 1:
        errors.append("wip_limit must be a whole number of at least 1")
        wip_limit = DEFAULT_WIP_LIMIT
    archived = ledger.get("archived", {})
    if not isinstance(archived, dict) or any(
        not isinstance(archived.get(k, 0), int) or archived.get(k, 0) < 0 for k in FINISHED
    ):
        errors.append("archived must count passing and dropped tasks")
    tasks = ledger.get("tasks")
    if not isinstance(tasks, list):
        return errors + ["tasks must be a list"]
    ids = set()
    for task in tasks:
        tid = task.get("id") if isinstance(task, dict) else None
        if not isinstance(tid, str) or tid in ids:
            errors.append(f"task id {tid!r} is missing or duplicated")
            continue
        ids.add(tid)
        state = task.get("state")
        if state not in STATES:
            errors.append(f"{tid}: unknown state {state!r}")
        if state == "blocked" and not task.get("blocker"):
            errors.append(f"{tid}: blocked without a blocker")
        if state == "dropped" and not task.get("dropped_reason"):
            errors.append(f"{tid}: dropped without a reason")
        if state == "passing" and (task.get("evidence") or {}).get("exit_code") != 0:
            errors.append(f"{tid}: passing without evidence of a successful bootstrap run")
        if state == "passing" and "spec" in task and (
            ((task.get("evidence") or {}).get("verification") or {}).get("exit_code") != 0
        ):
            errors.append(f"{tid}: passing without evidence of a successful verification command")
    in_progress = [t["id"] for t in tasks if isinstance(t, dict) and t.get("state") in IN_PROGRESS]
    if len(in_progress) > wip_limit:
        errors.append(f"WIP={wip_limit} broken: {', '.join(in_progress)} are all active or blocked")
    return errors


def load(state: str) -> dict:
    path = ledger_path(state)
    if not path.is_file():
        raise LedgerError(f"no ledger at {path}; create it with: joy task init --state {state} --bootstrap <init.sh>")
    try:
        ledger = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{path} is not valid JSON: {exc}") from exc
    errors = validate(ledger)
    if errors:
        raise LedgerError(f"{path} is invalid:\n" + "\n".join(f"  - {e}" for e in errors))
    # Ledgers written before archiving existed lack these keys; the next save adds them.
    archived = ledger.setdefault("archived", {})
    for k in FINISHED:
        archived.setdefault(k, 0)
    if "next_id" not in ledger:
        ledger["next_id"] = 1 + max(map(task_number, archived_ids(state) + [t["id"] for t in ledger["tasks"]]), default=0)
    return ledger


def archived_ids(state: str) -> list[str]:
    path = archive_path(state)
    if not path.is_file():
        return []
    return [json.loads(line)["id"] for line in path.read_text().splitlines() if line.strip()]


def save(state: str, ledger: dict) -> None:
    path = ledger_path(state)
    for t in ledger["tasks"]:
        if "spec" in t:
            write_spec_tail(state, t)
    finished = [t for t in ledger["tasks"] if t["state"] in FINISHED]
    if finished:
        # Archive first: a crash in between can duplicate an archive line but never lose a task.
        with archive_path(state).open("a") as f:
            for t in finished:
                f.write(json.dumps(t) + "\n")
                ledger["archived"][t["state"]] += 1
        ledger["tasks"] = [t for t in ledger["tasks"] if t["state"] not in FINISHED]
    # Write to a temp file then rename, so a crash never leaves a half-written ledger.
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tasks.", suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(ledger, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def vcr(ledger: dict, tasks: list[dict]) -> tuple[int, int]:
    archived = ledger["archived"]["passing"]
    activated = sum(t["state"] in ACTIVATED for t in tasks)
    passing = sum(t["state"] == "passing" for t in tasks)
    return archived + passing, archived + activated


def wip_limit(ledger: dict) -> int:
    return ledger.get("wip_limit", DEFAULT_WIP_LIMIT)


def confirm_by_human(expected: str, prompt: str, action: str) -> None:
    # An agent running commands has no interactive terminal, so this is a human-only gate.
    if not sys.stdin.isatty():
        raise LedgerError(f"{action} needs a human at an interactive terminal; ask a human to run it")
    if input(f"type {expected} {prompt}: ").strip() != expected:
        raise LedgerError("confirmation did not match; nothing changed")


def find(ledger: dict, tid: str) -> dict:
    for task in ledger["tasks"]:
        if task["id"] == tid:
            return task
    raise LedgerError(f"no open task {tid} (finished tasks are in tasks.archive.jsonl)")


def require_state(task: dict, *states: str) -> None:
    if task["state"] not in states:
        raise LedgerError(f"{task['id']} is {task['state']}, expected {' or '.join(states)}")


def fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def frozen_part(text: str) -> str:
    # Everything above STATE (title, TASK, SCOPE, DONE WHEN) is what the human approved.
    return text.split(FROZEN_END, 1)[0]


def parse_draft(text: str) -> tuple[str, str, str]:
    """Check a spec draft and return its title, its frozen body below the title and its verification command."""
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("# ")), None)
    if start is None:
        raise LedgerError("the draft has no `# <title>` heading")
    title = lines[start][2:].strip()
    body = "\n".join(lines[start + 1:]) + "\n"
    names = re.findall(r"^## (.+?)\s*$", body, flags=re.M)
    if tuple(names) != SPEC_SECTIONS:
        raise LedgerError(f"the draft must have the sections {', '.join(SPEC_SECTIONS)} in this order, not {', '.join(names) or 'none'}")
    frozen = frozen_part("# " + title + "\n" + body)
    prose = re.sub(r"^```.*?^```", "", frozen, flags=re.M | re.S)
    placeholders = re.findall(r"<[^<>\n]+>", prose)
    if placeholders:
        raise LedgerError(f"the draft still has placeholders: {', '.join(placeholders)}")
    sections = dict(zip(names, re.split(r"^## .+$", body, flags=re.M)[1:]))
    if not sections["TASK"].strip():
        raise LedgerError("the draft's TASK section is empty")
    if not re.search(r"^- \S", sections["SCOPE"], flags=re.M):
        raise LedgerError("the draft's SCOPE section must list the files the task may change, one `- ` item each")
    commands = re.findall(r"^```bash\n(.*?)^```", sections["DONE WHEN"], flags=re.M | re.S)
    if len(commands) != 1 or not commands[0].strip():
        raise LedgerError("the draft's DONE WHEN section must hold exactly one ```bash verification command block")
    return title, frozen.split("\n", 1)[1], commands[0].strip()


def run_command(command: list[str]) -> dict:
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return {"exit_code": result.returncode, "ran_at": now(), "output_tail": result.stdout.splitlines()[-OUTPUT_TAIL_LINES:]}


def run_verification(task: dict) -> dict:
    return {"command": task["spec"]["verify"], **run_command(["bash", "-c", task["spec"]["verify"]])}


def check_spec(task: dict) -> None:
    path = Path(task["spec"]["path"])
    if not path.is_file() or fingerprint(frozen_part(path.read_text())) != task["spec"]["sha256"]:
        raise LedgerError(
            f"{path} changed since it was approved (TASK, SCOPE or DONE WHEN): restore it, "
            f"or ask a human to drop {task['id']} and approve a new draft"
        )


def write_spec_tail(state: str, task: dict) -> None:
    path = Path(task["spec"]["path"])
    if not path.is_file():
        return
    lines = [
        f"- Ledger: `{ledger_path(state)}`, task `{task['id']}`",
        f"- Current state: `{task['state']}`",
    ]
    if task.get("blocker"):
        lines.append(f"- Blocker: {task['blocker']}")
    if task.get("dropped_reason"):
        lines.append(f"- Dropped: {task['dropped_reason']}")
    evidence = [("Before", task["before"])]
    if "evidence" in task:
        evidence.append(("After", {**task["evidence"]["verification"], "commit": task["evidence"]["commit"]}))
    out = []
    for label, run in evidence:
        commit = f", commit `{run['commit']}`" if run.get("commit") else ""
        summary = f"- {label} ({run['ran_at']}{commit}): the verification command exited {run['exit_code']}"
        if not any(line.strip() for line in run["output_tail"]):
            out += [f"{summary}, with no output", ""]
            continue
        out += [summary, "", "  ```text", *(f"  {line}" for line in run["output_tail"]), "  ```", ""]
    path.write_text(
        frozen_part(path.read_text()) + FROZEN_END
        + "\nWritten by `joy task` from the ledger on every change: do not edit.\n\n" + "\n".join(lines)
        + "\n\n## EVIDENCE\n\n" + "\n".join(out).rstrip() + "\n"
    )


def head_commit() -> str | None:
    result = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def cmd_init(args) -> int:
    path = ledger_path(args.state)
    if path.exists():
        raise LedgerError(f"{path} already exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    save(args.state, {
        "version": VERSION,
        "bootstrap": args.bootstrap,
        "next_id": 1,
        "archived": {k: 0 for k in FINISHED},
        "tasks": [],
    })
    print(f"created {path} (bootstrap: {args.bootstrap})")
    return 0


def cmd_add(args) -> int:
    ledger = load(args.state)
    draft = Path(args.spec)
    if not draft.is_file():
        raise LedgerError(f"no draft at {draft}")
    drafts = instructions_dir(args.state) / "drafts"
    if draft.resolve().parent != drafts.resolve():
        raise LedgerError(f"{draft} is not in the drafts folder of {args.state}: write it directly inside {drafts}")
    title, body, verify = parse_draft(draft.read_text())
    tid = f"T-{ledger['next_id']}"
    frozen = f"# {tid}. {title}\n{body}"
    print(frozen)
    print(f"==> approving makes this {tid}; the verification command above then runs and must fail")
    # Only humans approve: a spec decides what "done" means for the task.
    confirm_by_human(tid, "to approve this task", "add")
    task = {"id": tid, "title": title, "state": "not_started", "added_at": now()}
    task["spec"] = {"path": str(instructions_dir(args.state) / f"{tid}.md"), "sha256": fingerprint(frozen), "verify": verify}
    before = run_verification(task)
    print("\n".join(before["output_tail"]))
    if before["exit_code"] == 0:
        raise LedgerError("the verification command already passes, so it cannot prove the work; nothing changed")
    task["before"] = before
    spec = Path(task["spec"]["path"])
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(frozen + FROZEN_END)
    ledger["next_id"] += 1
    ledger["tasks"].append(task)
    save(args.state, ledger)
    draft.unlink()
    print(f"added {tid} (not_started): {title}, spec in {spec}")
    return 0


def cmd_activate(args) -> int:
    ledger = load(args.state)
    task = find(ledger, args.id)
    require_state(task, "not_started", "blocked")
    if "spec" in task:
        check_spec(task)
    elif task["state"] == "not_started":
        raise LedgerError(f"{task['id']} has no approved spec; ask a human to approve one with joy task add --spec")
    # The gate: once the task being (re)activated is set aside, the work in progress
    # (activated - passing) must be under the WIP limit. With WIP=1 that means VCR is 1.0, so
    # resuming a blocked task is allowed but starting a second one is not.
    others = [t for t in ledger["tasks"] if t["id"] != task["id"]]
    passing, activated = vcr(ledger, others)
    if activated - passing >= wip_limit(ledger):
        busy = ", ".join(f"{t['id']} is {t['state']}" for t in others if t["state"] in IN_PROGRESS)
        print(f"refused: VCR is {passing}/{activated} < 1.0 ({busy}). "
              f"WIP limit is {wip_limit(ledger)}. Get it passing (joy task pass) or ask a human.", file=sys.stderr)
        return 1
    task["state"] = "active"
    task["activated_at"] = now()
    task.pop("blocker", None)
    save(args.state, ledger)
    print(f"{task['id']} is active: {task['title']}")
    return 0


def cmd_block(args) -> int:
    ledger = load(args.state)
    task = find(ledger, args.id)
    require_state(task, "active")
    task["state"] = "blocked"
    task["blocker"] = args.reason
    save(args.state, ledger)
    print(f"{task['id']} is blocked: {args.reason}")
    return 0


def cmd_drop(args) -> int:
    ledger = load(args.state)
    task = find(ledger, args.id)
    require_state(task, "not_started", "active", "blocked")
    # Only humans drop: dropping lifts the VCR gate.
    confirm_by_human(task["id"], "to drop it", "drop")
    task["state"] = "dropped"
    task["dropped_reason"] = args.reason
    task.pop("blocker", None)
    save(args.state, ledger)
    print(f"{task['id']} is dropped: {args.reason}")
    return 0


def cmd_wip(args) -> int:
    ledger = load(args.state)
    if args.limit < 1:
        raise LedgerError("the WIP limit must be at least 1")
    in_progress = [t["id"] for t in ledger["tasks"] if t["state"] in IN_PROGRESS]
    if len(in_progress) > args.limit:
        raise LedgerError(f"{', '.join(in_progress)} are active or blocked; finish or drop some first")
    # Only humans change the limit: raising it lifts the gate like a drop does.
    confirm_by_human(str(args.limit), "to set the WIP limit", "wip")
    old = wip_limit(ledger)
    ledger["wip_limit"] = args.limit
    save(args.state, ledger)
    print(f"WIP limit is {args.limit} (was {old})")
    return 0


def cmd_pass(args) -> int:
    ledger = load(args.state)
    task = find(ledger, args.id)
    require_state(task, "active")
    if "spec" in task:
        check_spec(task)
    command = ledger["bootstrap"]
    print(f"==> running {command} for {task['id']}")
    bootstrap = {"command": command, **run_command([command])}
    if bootstrap["exit_code"] != 0:
        print("\n".join(bootstrap["output_tail"]), file=sys.stderr)
        print(f"refused: {command} exited {bootstrap['exit_code']}; {task['id']} stays active", file=sys.stderr)
        return 1
    evidence = {**bootstrap, "commit": head_commit()}
    # Tasks added before specs existed only have the bootstrap to pass.
    if "spec" in task:
        print(f"==> running the verification command of {task['id']}")
        verification = run_verification(task)
        if verification["exit_code"] != 0:
            print("\n".join(verification["output_tail"]), file=sys.stderr)
            print(f"refused: the verification command exited {verification['exit_code']}; {task['id']} stays active", file=sys.stderr)
            return 1
        evidence["verification"] = verification
    task["state"] = "passing"
    task["passed_at"] = evidence["ran_at"]
    task["evidence"] = evidence
    save(args.state, ledger)
    print(f"{task['id']} is passing")
    return 0


def cmd_status(args) -> int:
    ledger = load(args.state)
    tasks = ledger["tasks"]
    passing, activated = vcr(ledger, tasks)
    current = [t for t in tasks if t["state"] in IN_PROGRESS]
    if args.json:
        # Compact on purpose: open work only, no history or evidence (see tasks.archive.jsonl).
        print(json.dumps({
            "vcr": {"passing": passing, "activated": activated},
            "wip_limit": wip_limit(ledger),
            "current": current,
            "not_started": [{"id": t["id"], "title": t["title"]} for t in tasks if t["state"] == "not_started"],
        }, indent=2))
        return 0
    gate = "new activations allowed" if len(current) < wip_limit(ledger) else "new activations blocked"
    print(f"VCR {passing}/{activated}, WIP limit {wip_limit(ledger)} ({gate})")
    if not current:
        print("no active task")
    for t in current:
        extra = f" (blocker: {t['blocker']})" if t["state"] == "blocked" else ""
        print(f"{t['state']}: {t['id']} {t['title']}{extra}")
    print(f"not_started: {sum(t['state'] == 'not_started' for t in tasks)}")
    for state in FINISHED:
        print(f"{state}: {ledger['archived'][state] + sum(t['state'] == state for t in tasks)}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--state", default="harness/state", help="state folder holding tasks.json")
    parser = argparse.ArgumentParser(prog="joy task", description="WIP-limited task ledger")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("init", parents=[common], help="create the ledger")
    p.add_argument("--bootstrap", required=True, help="bootstrap script `pass` runs, e.g. ./init.sh")
    p.set_defaults(func=cmd_init)
    p = sub.add_parser("add", parents=[common], help="approve a spec draft as a not_started task (humans only: asks to type the new id at an interactive terminal)")
    p.add_argument("--spec", required=True, help="spec draft based on instruction_template.md; becomes <instructions>/<id>.md")
    p.set_defaults(func=cmd_add)
    p = sub.add_parser("activate", parents=[common], help="activate a task (refused at the WIP limit, VCR < 1.0 with WIP=1)")
    p.add_argument("id")
    p.set_defaults(func=cmd_activate)
    p = sub.add_parser("block", parents=[common], help="block the active task")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_block)
    p = sub.add_parser("pass", parents=[common], help="run the bootstrap and mark the task passing")
    p.add_argument("id")
    p.set_defaults(func=cmd_pass)
    p = sub.add_parser("drop", parents=[common], help="drop a task (humans only: asks to type the id at an interactive terminal)")
    p.add_argument("id")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_drop)
    p = sub.add_parser("wip", parents=[common], help="set the WIP limit (humans only: asks to type it at an interactive terminal)")
    p.add_argument("limit", type=int)
    p.set_defaults(func=cmd_wip)
    p = sub.add_parser("status", parents=[common], help="print VCR and the active task; fails if the ledger is invalid")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_status)
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
