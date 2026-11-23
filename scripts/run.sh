#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -f .env ]]; then
  echo 'Missing .env. Copy .env.example to .env and fill in real provider keys.' >&2
  exit 2
fi
if [[ "${1:-}" == "--all" ]]; then
  ARGS=(--all --stop-on-qc-failure --confirm-live-calls)
elif [[ -n "${1:-}" ]]; then
  ARGS=("$1" --confirm-live-calls)
else
  echo 'Usage: ./scripts/run.sh <scenario-key> OR ./scripts/run.sh --all' >&2
  exit 2
fi
python -m patientprobe.cli doctor
mkdir -p artifacts
python -m patientprobe.agent start > artifacts/worker.log 2>&1 &
WORKER_PID=$!
cleanup() { kill "$WORKER_PID" 2>/dev/null || true; wait "$WORKER_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
# Allow the local agent server to register before dispatching an authorized test job.
sleep 8
if ! kill -0 "$WORKER_PID" 2>/dev/null; then
  echo 'Agent worker failed to start. Inspect artifacts/worker.log' >&2
  exit 1
fi
python -m patientprobe.cli run "${ARGS[@]}"
