"""Binary integration tests; requires installed DCG, Java 21 and Python 3 only.
Run: python3 scripts/dcg/test_cli.py
"""
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BinaryIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="iems dcg ")
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "checks.db"
        self.env = dict(os.environ, DCG_SQLITE_PATH=str(self.db))
        for key in list(self.env):
            if key.startswith(("DCG_POSTGRES_", "DCG_MYSQL_")):
                self.env.pop(key)

    def run_cli(self, *args, expected=0):
        result = subprocess.run(
            [str(ROOT / "scripts/dcg.sh"), *args], cwd=self.temp.name,
            env=self.env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_all_contracts_recorded_from_another_working_directory(self):
        self.run_cli("lint")
        self.run_cli("check", "sqlite")
        with sqlite3.connect(self.db) as conn:
            rows = conn.execute("select contract_id,status from check_runs").fetchall()
        self.assertEqual(set(rows), {(f"iems.{name}", "PASS") for name in
                                   ("accessibility", "enrollment", "notification", "scholarship")})
        self.assertEqual(len(rows), 4)

    def test_demo_records_both_outcomes(self):
        self.run_cli("demo", "sqlite")
        with sqlite3.connect(self.db) as conn:
            rows = conn.execute("select status from check_runs order by status").fetchall()
        self.assertEqual(rows, [("FAIL",), ("PASS",)])

    def test_breaking_cli_preserves_exit_one(self):
        self.run_cli("cli", "check-compat", "--base",
                     str(ROOT / "contracts/iems.enrollment/v1.json"), "--candidate",
                     str(ROOT / "scripts/dcg/fixtures/breaking.json"), expected=1)

    def test_missing_server_configuration_is_error(self):
        self.run_cli("demo", "postgres", expected=2)
        self.run_cli("demo", "mysql", expected=2)
        self.run_cli("demo-all", expected=2)
        self.assertFalse(self.db.exists())

    def test_persistence_failure_is_not_expected_breaking_result(self):
        self.env["DCG_SQLITE_PATH"] = self.temp.name  # A directory cannot be a DB file.
        result = self.run_cli("demo", "sqlite", expected=2)
        self.assertNotIn("Demo verified", result.stdout)

    def test_unknown_store_and_extra_arguments(self):
        self.run_cli("check", "oracle", expected=2)
        self.run_cli("demo", "sqlite", "extra", expected=2)


if __name__ == "__main__":
    unittest.main()
