#!/usr/bin/env python3
"""Focused safeguards and live SQLite/DCG coverage for the IEMS migration gate."""

import json
import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

import iems_migration_gate as gate


class MigrationGateTest(unittest.TestCase):
    def test_real_flyway_schools_ddl_and_required_column(self):
        ddl = gate.schools_ddl()
        self.assertIn("create table schools", ddl.lower())
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "school.sqlite"
            gate.initialize_table(db, ddl)
            columns = {row["name"]: row for row in gate.table_info(db)}
            self.assertEqual(1, columns["name"]["notnull"])
            self.assertEqual({"row": list(gate.SENTINEL), "rowCount": 1}, gate.sentinel(db))

    def test_negative_control_never_calls_executor_on_fail(self):
        executor = Mock()
        self.assertFalse(gate.apply_after_pass(1, executor, Path("unused"), Path("rejected.sql"), "hash"))
        executor.execute.assert_not_called()
        self.assertTrue(gate.apply_after_pass(0, executor, Path("unused"), Path("approved.sql"), "hash"))
        executor.execute.assert_called_once()

    def test_reviewed_sql_hash_mismatch_stops_before_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            sql = Path(directory) / "changed.sql"
            sql.write_bytes(gate.SAFE_SQL + b"-- changed\n")
            executor = gate.ObservedExecutor(["unused-java"])
            with self.assertRaisesRegex(ValueError, "changed between review and execution"):
                executor.execute(Path(directory) / "unused.sqlite", sql, gate.sha256(gate.SAFE_SQL))
            self.assertEqual(0, executor.attempts)

    def test_evidence_directory_refuses_overwrite_and_outside_path(self):
        evidence = gate.make_evidence()
        self.addCleanup(lambda: __import__("shutil").rmtree(evidence))
        with self.assertRaises(FileExistsError):
            gate.make_evidence(evidence)
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "direct child"):
                gate.make_evidence(Path(directory) / "database-migration-gate-unsafe")

    def test_setup_failure_never_calls_executor(self):
        evidence = gate.make_evidence()
        self.addCleanup(lambda: __import__("shutil").rmtree(evidence))
        package = Path(os.environ.get("DCG_HOME", gate.ROOT / ".dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"))
        with patch.object(gate, "schools_ddl", side_effect=ValueError("setup failed")), \
             patch.object(gate.ObservedExecutor, "execute") as execute:
            with self.assertRaisesRegex(ValueError, "setup failed"):
                gate.run_rehearsal(evidence, package)
            execute.assert_not_called()

    def test_live_gate_on_disposable_real_table_ignores_external_jdbc_target(self):
        evidence = gate.make_evidence()
        # Retain this integration evidence for inspection.
        package = Path(os.environ.get("DCG_HOME", gate.ROOT / ".dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64"))
        with tempfile.TemporaryDirectory() as directory:
            forbidden = Path(directory) / "normal.sqlite"
            with closing(sqlite3.connect(forbidden)) as conn:
                with conn:
                    conn.execute("CREATE TABLE untouched (id INTEGER PRIMARY KEY)")
            before = gate.file_hash(forbidden)
            with patch.dict(os.environ, {"IEMS_JDBC_URL": "jdbc:sqlite:" + str(forbidden),
                                          "DCG_AI_ENABLED": "false"}):
                result = gate.run_rehearsal(evidence, package)
            self.assertEqual(before, gate.file_hash(forbidden))
        self.assertEqual("COMPLETE", result["result"])
        self.assertEqual(1, result["safe"]["executorAttempts"])
        self.assertEqual(0, result["breaking"]["executorAttempts"])
        self.assertEqual(result["safe"]["reviewedSqlSha256"], result["safe"]["offeredSqlSha256"])
        self.assertEqual(result["breaking"]["preSchemaSha256"], result["breaking"]["postSchemaSha256"])
        self.assertEqual(result["breaking"]["preDatabaseSha256"], result["breaking"]["postDatabaseSha256"])
        self.assertTrue(result["breaking"]["sentinelPreserved"])
        self.assertTrue(result["normalIemsDatabaseUntouched"])
        self.assertTrue(result["safe"]["optionalColumnPresent"])
        self.assertEqual([], json.loads((evidence / "executor-observation.json").read_text())["breaking"]["statements"])
        self.assertTrue(result["aiDisabled"])
        self.assertFalse(result["rustStarted"])
        print("Retained integration evidence:", evidence)


if __name__ == "__main__":
    unittest.main()
