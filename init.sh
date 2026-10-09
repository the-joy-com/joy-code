#!/usr/bin/env bash
# Bootstrap for the harness itself (the joy CLI). Contract: BOOTSTRAP.md. Idempotent.
set -uo pipefail
cd "$(dirname "$0")"

INSTALL_CMD=(uv sync --locked --project cli)
START_CMD=(uv run --locked --project cli joy --help)
VERIFY_CMD=(uv run --locked --project cli pytest cli)
LOCK_FILE=cli/uv.lock
PROGRESS_FILE=harness/state/PROGRESS.md
TASKS_FILE=harness/state/tasks.json
STATUS_CMD=(uv run --locked --project cli joy task status --state harness/state)

echo "==> Installing dependencies (${INSTALL_CMD[*]})"
LOCK_BEFORE=$(sha256sum "$LOCK_FILE" 2>/dev/null)
if ! "${INSTALL_CMD[@]}"; then
  echo "FAIL: install (${INSTALL_CMD[*]}): $LOCK_FILE is missing or out of date"; exit 10
fi
if [ "$(sha256sum "$LOCK_FILE")" != "$LOCK_BEFORE" ]; then
  echo "FAIL: install (${INSTALL_CMD[*]} rewrote $LOCK_FILE)"; exit 10
fi

if [ ! -f "$PROGRESS_FILE" ]; then
  echo "==> Creating $PROGRESS_FILE (none found)"
  cat > "$PROGRESS_FILE" <<'MD'
# joy progress

## Current verified state

- Nothing recorded yet.

## Next step

- None recorded: ask a human what to work on.
MD
fi

if [ ! -f "$TASKS_FILE" ]; then
  echo "==> Creating $TASKS_FILE (none found)"
  cat > "$TASKS_FILE" <<'JSON'
{
  "version": 1,
  "bootstrap": "./init.sh",
  "next_id": 1,
  "archived": {"passing": 0, "dropped": 0},
  "tasks": []
}
JSON
fi

echo "==> Verifying bootstrap contract"

if ! "${START_CMD[@]}" >/dev/null 2>&1; then
  echo "FAIL: can-start (${START_CMD[*]})"; exit 11
fi

if ! "${VERIFY_CMD[@]}" >/dev/null 2>&1; then
  echo "FAIL: can-test (${VERIFY_CMD[*]})"; exit 12
fi

if ! TASK_STATUS=$("${STATUS_CMD[@]}" 2>&1); then
  echo "FAIL: can-see-progress (${STATUS_CMD[*]}):"; echo "$TASK_STATUS"; exit 13
fi

if ! grep -Eqi '^## .*next step' "$PROGRESS_FILE"; then
  echo "FAIL: can-see-progress ($PROGRESS_FILE has no next step section)"; exit 13
fi

if [ ! -f AGENTS.md ]; then
  echo "FAIL: can-pick-next-steps (AGENTS.md missing)"; exit 14
fi

echo "OK: bootstrap contract holds"
echo "    can-start           PASS"
echo "    can-test            PASS"
echo "    can-see-progress    PASS"
echo "    can-pick-next-steps PASS"
echo
echo "Tasks (from $TASKS_FILE):"
echo "$TASK_STATUS" | sed 's/^/    /'
echo "Next step (from $PROGRESS_FILE):"
awk 'tolower($0) ~ /^## .*next step/{flag=1; next} /^## /{flag=0} flag && NF{print "    " $0}' "$PROGRESS_FILE" | head -3
