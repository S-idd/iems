#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
usage() {
  cat <<'HELP'
Usage: ./scripts/dcg.sh <command> [arguments]
  help                         Show this help
  cli <arguments...>           Forward arguments to the packaged DCG CLI
  lint                         Lint all IEMS event contracts
  check [sqlite|postgres|mysql] Check v1 against candidate for all contracts
  demo [sqlite|postgres|mysql]  Record an expected PASS and expected FAIL
  demo-all                     Run demo against each of the three stores

Default store: sqlite. Exit codes: 0 success, 1 incompatible contract,
2 configuration/persistence error. demo returns 0 only for a recorded PASS
and a recorded compatibility FAIL; infrastructure errors fail the demo.
Set DCG_HOME to an extracted release, or install with scripts/dcg/install.sh.
PostgreSQL/MySQL require DCG_<POSTGRES|MYSQL>_JDBC_URL, _USER and _PASSWORD.
Use a dedicated DCG database: recording applies DCG Flyway migrations.
HELP
}
die() { echo "IEMS DCG: $*" >&2; exit 2; }
COMMAND=${1:-help}; [[ $# -eq 0 ]] || shift
case "$COMMAND" in help|-h|--help) usage; exit 0;; esac
if [[ -z "${DCG_HOME:-}" ]]; then
  case "$(uname -s)-$(uname -m)" in
    Darwin-arm64) PLATFORM=macos-arm64;; Linux-x86_64) PLATFORM=linux-x64;;
    *) die 'Set DCG_HOME to a supported extracted package.';;
  esac
  DCG_HOME="$ROOT/.dcg/runtime/dcg-4.0.0-rc.1-$PLATFORM"
fi
BIN="$DCG_HOME/bin/dcg"
[[ -x "$BIN" ]] || die 'Binary missing. Run scripts/dcg/install.sh ARCHIVE or set DCG_HOME.'
# Do not source .env files: credentials are inherited from the caller.
configure_store() {
  local store=$1 url user_var password_var
  RECORD=()
  case "$store" in
    sqlite)
      umask 077
      mkdir -p "$ROOT/.dcg/data"
      RECORD=(--record-db "${DCG_SQLITE_PATH:-$ROOT/.dcg/data/checks.db}") ;;
    postgres|mysql)
      if [[ "$store" == postgres ]]; then
        url=${DCG_POSTGRES_JDBC_URL:-}; user_var=DCG_POSTGRES_USER; password_var=DCG_POSTGRES_PASSWORD
        [[ "$url" == jdbc:postgresql://* ]] || die 'Set DCG_POSTGRES_JDBC_URL to a PostgreSQL JDBC URL.'
      else
        url=${DCG_MYSQL_JDBC_URL:-}; user_var=DCG_MYSQL_USER; password_var=DCG_MYSQL_PASSWORD
        [[ "$url" == jdbc:mysql://* ]] || die 'Set DCG_MYSQL_JDBC_URL to a MySQL JDBC URL.'
      fi
      [[ -n "${!user_var:-}" && -n "${!password_var:-}" ]] || die "Export $user_var and $password_var."
      RECORD=(--record-jdbc-url "$url" --record-db-user-env "$user_var" --record-db-password-env "$password_var") ;;
    *) die "Unknown store: $store";;
  esac
}
check_pair() {
  "$BIN" check-compat --base "$1" --candidate "$2" --mode BACKWARD \
    --contract-id "$3" --commit-sha "$(git -C "$ROOT" rev-parse HEAD)" "${RECORD[@]}"
}
run_demo() {
  configure_store "$1"
  echo "IEMS enrollment demo: $1 — compatible optional field"
  check_pair "$ROOT/contracts/iems.enrollment/v1.json" "$ROOT/scripts/dcg/fixtures/compatible.json" iems.enrollment || return $?
  echo "IEMS enrollment demo: $1 — incompatible studentId type"
  local rc=0
  check_pair "$ROOT/contracts/iems.enrollment/v1.json" "$ROOT/scripts/dcg/fixtures/breaking.json" iems.enrollment || rc=$?
  [[ "$rc" == 1 ]] || { echo "Expected compatibility exit 1; got $rc" >&2; return 2; }
  echo "Demo verified: PASS and intentional FAIL recorded in $1."
}
case "$COMMAND" in
  cli) exec "$BIN" "$@";;
  lint)
    [[ $# -eq 0 ]] || die 'lint takes no arguments.'
    for dir in "$ROOT"/contracts/iems.*; do "$BIN" lint --path "$dir"; done;;
  check)
    [[ $# -le 1 ]] || die 'check accepts one store.'
    configure_store "${1:-sqlite}"
    rc=0
    for dir in "$ROOT"/contracts/iems.*; do
      result=0
      check_pair "$dir/v1.json" "$dir/candidate.json" "${dir##*/}" || result=$?
      if [[ "$result" -gt "$rc" ]]; then rc=$result; fi
    done
    exit "$rc";;
  demo)
    [[ $# -le 1 ]] || die 'demo accepts one store.'
    run_demo "${1:-sqlite}";;
  demo-all)
    [[ $# -eq 0 ]] || die 'demo-all takes no arguments.'
    # Validate all configurations before recording any results.
    for store in sqlite postgres mysql; do configure_store "$store"; done
    for store in sqlite postgres mysql; do run_demo "$store"; done;;
  *) die "Unknown command: $COMMAND";;
esac
