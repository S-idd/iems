#!/usr/bin/env bash
# Run a command only after the packaged DCG CLI approves the supplied schema pair.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
[[ $# -ge 4 && "$3" == -- ]] || { echo 'Usage: gate.sh BASE.json CANDIDATE.json -- COMMAND [ARGS...]' >&2; exit 2; }
BASE=$1; CANDIDATE=$2; shift 3
umask 077
mkdir -p "$ROOT/.dcg/data"
HISTORY=${DCG_SCHEMA_GATE_HISTORY:-$ROOT/.dcg/data/schema-gates.db}
mkdir -p "$(dirname "$HISTORY")"
"$ROOT/scripts/dcg.sh" cli check-compat --base "$BASE" --candidate "$CANDIDATE" \
  --mode BACKWARD --contract-id iems.database \
  --record-db "$HISTORY" \
  --commit-sha "$(git -C "$ROOT" rev-parse HEAD)"
echo 'DCG PASS: executing the gated command.'
exec "$@"
