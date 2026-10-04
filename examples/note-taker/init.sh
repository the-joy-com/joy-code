#!/usr/bin/env bash
# Bootstrap for the note-taker example app. Contract: BOOTSTRAP.md. Idempotent.
set -uo pipefail
cd "$(dirname "$0")"

INSTALL_CMD=(uv sync --locked)
START_CMD=(uv run --locked note-taker --help)
VERIFY_CMD=(uv run --locked pytest)
LOCK_FILE=uv.lock
PROGRESS_FILE=../../harness/state/note-taker/PROGRESS.md

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
# note-taker progress

## Current verified state

- Nothing recorded yet.

## Next step

- None recorded: ask a human what to work on.
MD
fi

echo "==> Verifying bootstrap contract"

if ! "${START_CMD[@]}" >/dev/null 2>&1; then
  echo "FAIL: can-start (${START_CMD[*]})"; exit 11
fi

if ! "${VERIFY_CMD[@]}" >/dev/null 2>&1; then
  echo "FAIL: can-test (${VERIFY_CMD[*]})"; exit 12
fi

if ! grep -Eqi '^## .*next step' "$PROGRESS_FILE"; then
  echo "FAIL: can-see-progress ($PROGRESS_FILE has no next step section)"; exit 13
fi

if [ ! -f README.md ] || [ ! -f ARCHITECTURE.md ]; then
  echo "FAIL: can-pick-next-steps (README.md or ARCHITECTURE.md missing)"; exit 14
fi

echo "OK: bootstrap contract holds"
echo "    can-start           PASS"
echo "    can-test            PASS"
echo "    can-see-progress    PASS"
echo "    can-pick-next-steps PASS"
echo
echo "Next step (from $PROGRESS_FILE):"
awk 'tolower($0) ~ /^## .*next step/{flag=1; next} /^## /{flag=0} flag && NF{print "    " $0}' "$PROGRESS_FILE" | head -3
