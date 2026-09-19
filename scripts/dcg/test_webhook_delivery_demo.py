#!/usr/bin/env python3
"""Safety checks and assertions on one real DCG→IEMS webhook rehearsal."""
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest

import webhook_delivery_demo as demo

EVIDENCE = os.environ.get('IEMS_DCG_WEBHOOK_EVIDENCE')


class SafetyTests(unittest.TestCase):
    def test_refuses_to_overwrite_existing_rehearsal(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                demo.run(Path(directory))


@unittest.skipUnless(EVIDENCE, 'Set IEMS_DCG_WEBHOOK_EVIDENCE to a real completed rehearsal')
class RealEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(EVIDENCE).resolve()
        cls.report = json.loads((cls.root / 'results.json').read_text())

    def test_online_delivery_correlates(self):
        r = self.report
        self.assertEqual(r['result'], 'PASS')
        online = r['runs']['delivered']
        self.assertEqual(online['check_status'], 'FAIL')
        self.assertEqual(online['delivery_status_before_recovery'], 'DELIVERED')
        self.assertEqual(online['event_id'], online['inbox_before_restart']['eventId'])
        self.assertEqual(online['run_id'], online['inbox_before_restart']['runId'])
        self.assertEqual(online['inbox_before_restart']['contractId'], 'iems.enrollment')

    def test_outage_restart_retry_and_no_duplicate(self):
        r = self.report
        first, retry = r['runs']['delivered'], r['runs']['retry']
        self.assertNotEqual(first['run_id'], retry['run_id'])
        self.assertNotEqual(first['delivery_id'], retry['delivery_id'])
        self.assertEqual(retry['delivery_status_before_recovery'], 'FAILED_RETRYABLE')
        self.assertEqual(retry['delivery_status_after_recovery'], 'DELIVERED')
        self.assertEqual(retry['attempt_count_before_recovery'], 1)
        self.assertGreaterEqual(retry['attempt_count_after_recovery'], 2)
        self.assertEqual(retry['event_id'], retry['inbox_after_recovery']['eventId'])
        self.assertEqual(retry['run_id'], retry['inbox_after_recovery']['runId'])
        self.assertEqual(r['user_notification_rows'], 0)
        self.assertTrue(r['ui']['retry_run_id_visible'])
        self.assertTrue(r['ui']['delivery_status_visible'])
        self.assertEqual(r['newman']['exit_code'], 0)

    def test_isolation_cleanup_and_no_exported_secrets(self):
        r = self.report
        self.assertFalse(r['ai_enabled'])
        self.assertEqual(r['rust_after'], [])
        for field in ('dcg_port_released', 'iems_port_released', 'package_unchanged',
                      'contracts_unchanged', 'iems_jar_unchanged'):
            self.assertTrue(r[field])
        storage = r['storage']
        self.assertEqual(len(set(storage.values())), 4)
        self.assertTrue(all(Path(path).is_relative_to(self.root / 'runtime') for path in storage.values()))
        self.assertTrue((self.root / 'runtime/iems-dcg-inbox.db').is_file())
        self.assertTrue((self.root / 'runtime/iems-app.db').is_file())
        self.assertTrue((self.root / 'runtime/checks.db').is_file())
        self.assertTrue(all(stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600)
                            for path in self.root.rglob('*')))
        env = json.loads((demo.ROOT / 'postman/dcg-webhook-environment.json').read_text())
        self.assertTrue(all(value['value'] == '' for value in env['values']))
        report_text = (self.root / 'results.json').read_text()
        self.assertNotIn('IEMS_DCG_WEBHOOK_AUTH=', report_text)
        self.assertNotIn('DCG_DEMO_WEBHOOK_AUTH=', report_text)


if __name__ == '__main__':
    unittest.main()
