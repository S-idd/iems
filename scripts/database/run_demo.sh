#!/usr/bin/env bash
# Start IEMS on one database after DCG CLI checks. Requires Java 21 and local DBs.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
STORE=${1:-sqlite}
[[ $# -le 1 ]] || { echo 'Usage: run_demo.sh [sqlite|postgres|mysql]' >&2; exit 2; }
case "$STORE" in sqlite|postgres|mysql) ;; *) echo 'Choose sqlite, postgres or mysql.' >&2; exit 2;; esac
: "${IEMS_JWT_SECRET:?Set a private IEMS_JWT_SECRET of at least 32 bytes}"
: "${IEMS_DEMO_ADMIN_PASSWORD:?Set a private IEMS_DEMO_ADMIN_PASSWORD of at least 16 characters}"
if [[ "$STORE" != sqlite ]]; then
  : "${IEMS_JDBC_URL:?Set IEMS_JDBC_URL for a fresh, dedicated IEMS demo database}"
  : "${IEMS_DB_USER:?Set IEMS_DB_USER}"
  : "${IEMS_DB_PASSWORD:?Set IEMS_DB_PASSWORD}"
fi
if [[ "$STORE" == sqlite && -z "${IEMS_JDBC_URL:-}" ]]; then
  umask 077
  mkdir -p "$ROOT/.dcg/data"
  export IEMS_JDBC_URL="jdbc:sqlite:$ROOT/.dcg/data/iems.db"
fi
"$ROOT/scripts/dcg.sh" lint
"$ROOT/scripts/dcg.sh" check "$STORE"
JAR="$ROOT/target/inclusive-education-management-system-1.0.0-SNAPSHOT.jar"
[[ -f "$JAR" ]] || { echo 'Build first with mvn -DskipTests package.' >&2; exit 2; }
cd "$ROOT"
exec java -jar "$JAR" --spring.profiles.active="db-demo,db-$STORE"
