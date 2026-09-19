"""Real packaged CLI history/explain regressions; no service or AI process."""
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import cli_explain as explain
import multiple_contract_demo as demo


class ExplainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get('DCG_HOME'):
            raise unittest.SkipTest('Set DCG_HOME to the installed development package')
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.package = Path(os.environ['DCG_HOME'])
        cls.env = dict(os.environ, DCG_AI_ENABLED='false')
        cls.db = cls.root / 'original.sqlite'
        for name in ('enrollment', 'scholarship'):
            result = subprocess.run([str(cls.package / 'bin/dcg'), 'check-compat', '--base',
                                     str(demo.ROOT / f'contracts/iems.{name}/v1.json'), '--candidate',
                                     str(demo.FIXTURES / f'{name}.json'), '--contract-id', f'iems.{name}',
                                     '--record-db', str(cls.db)], env=cls.env, capture_output=True, text=True)
            if result.returncode != 1:
                raise RuntimeError(result.stdout + result.stderr)
        cls.rows = explain.read_failures(cls.db)

    def setUp(self):
        self.temp_case = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_case.cleanup)
        self.evidence = Path(self.temp_case.name)
        self.evidence.chmod(0o700)
        self.db = self.evidence / 'history.sqlite'
        explain.retain_history(type(self).db, self.db)

    def test_ids_survive_snapshot_and_explain_both_after_writer_exit(self):
        self.assertEqual(explain.read_failures(self.db), self.rows)
        self.assertNotEqual(self.rows[0][0], self.rows[1][0])
        summary = explain.explain_failures(self.db, self.package, self.evidence, self.env)
        self.assertEqual([x['run_id'] for x in summary['failures']], [row[0] for row in self.rows])
        for item in summary['failures']:
            self.assertEqual(item['explain_exit'], 1)
            self.assertTrue(item['lookup_resolved'])
            self.assertIn('Recorded status: FAIL', item['stdout'])
            self.assertTrue((self.evidence / item['raw_output']).is_file())
        self.assertEqual([x['changes'][0]['previous_type'] for x in summary['failures']], ['integer', 'number'])

    def test_explain_only_queries_retained_history_without_new_checks(self):
        before = demo.sha(self.db.read_bytes())
        with patch.object(explain.subprocess, 'run', wraps=subprocess.run) as invoked:
            explain.explain_failures(self.db, self.package, self.evidence, self.env)
        self.assertEqual(invoked.call_count, 2)
        for call in invoked.call_args_list:
            self.assertEqual(call.args[0][1], 'explain')
            self.assertNotIn('check-compat', call.args[0])
        self.assertEqual(demo.sha(self.db.read_bytes()), before)
        self.assertEqual(explain.read_failures(self.db), self.rows)

    def test_private_permissions(self):
        explain.explain_failures(self.db, self.package, self.evidence, self.env)
        self.assertEqual(self.evidence.stat().st_mode & 0o777, 0o700)
        for p in self.evidence.iterdir():
            self.assertEqual(p.stat().st_mode & 0o777, 0o600, str(p))

    def test_existing_evidence_and_history_never_overwritten(self):
        before = self.db.read_bytes()
        with self.assertRaises(FileExistsError):
            demo.run(self.evidence, self.package, True)
        with self.assertRaises(FileExistsError):
            explain.retain_history(type(self).db, self.db)
        self.assertEqual(self.db.read_bytes(), before)

    def test_missing_and_corrupt_history_fail_clearly(self):
        missing = self.evidence / 'missing.sqlite'
        with self.assertRaisesRegex(RuntimeError, 'history missing'):
            explain.explain_failures(missing, self.package, self.evidence, self.env)
        self.assertFalse(missing.exists())
        self.db.write_bytes(b'corrupt database')
        with self.assertRaisesRegex(RuntimeError, 'history unreadable'):
            explain.explain_failures(self.db, self.package, self.evidence, self.env)
        for path in (self.evidence / 'absent-directory/missing.sqlite', self.db):
            result = subprocess.run([str(self.package / 'bin/dcg'), 'explain', '--db', str(path), '--run', self.rows[0][0]], env=self.env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Explain failed:', result.stderr)

    def test_cli_failure_cannot_be_replaced_by_summary(self):
        for code, output in ((2, 'Explain failed'), (1, 'Run not found'), (0, 'success')):
            with self.subTest(code=code, output=output):
                with patch.object(explain.subprocess, 'run', return_value=subprocess.CompletedProcess([], code, output, '')):
                    with self.assertRaisesRegex(RuntimeError, 'CLI explain did not resolve'):
                        explain.explain_failures(self.db, self.package, self.evidence, self.env)
                self.assertFalse((self.evidence / 'explain-summary.json').exists())


if __name__ == '__main__':
    unittest.main()
