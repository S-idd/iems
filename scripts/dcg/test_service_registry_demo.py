#!/usr/bin/env python3
"""Safety tests plus assertions over one real packaged-service rehearsal."""
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

import service_registry_demo as demo

EVIDENCE = os.environ.get('IEMS_DCG_SERVICE_EVIDENCE')


class SafetyTests(unittest.TestCase):
    def test_existing_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'already exists'):
                with patch('sys.argv', ['demo', '--evidence', directory]):
                    demo.main()

    def test_reset_refuses_foreign_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, 'Not a DCG rehearsal'):
                demo.reset(Path(directory))

    def test_health_timeout_is_clear(self):
        class DeadProcess:
            def poll(self):
                return 1
        with self.assertRaisesRegex(RuntimeError, 'exited before health'):
            demo.wait_health('http://127.0.0.1:1', DeadProcess(), timeout=.01)

    def test_interrupted_startup_stops_child_before_handle_is_returned(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / 'package'
            (package / 'config').mkdir(parents=True)
            (package / 'config/application-local-demo.properties.example').write_text('server.port=0\n')
            runtime = root / 'runtime'
            runtime.mkdir()
            child = object()
            with patch.dict(os.environ, {'JAVA_HOME': '/unused/java21'}), \
                 patch.object(demo.subprocess, 'Popen', return_value=child), \
                 patch.object(demo, 'wait_health', side_effect=InterruptedError('stop')), \
                 patch.object(demo, 'stop_owned') as stop:
                with self.assertRaisesRegex(InterruptedError, 'stop'):
                    demo.start_service(package, runtime, 12345, 'demo', 'secret', root / 'service.log')
            stop.assert_called_once_with(child)

    def test_stop_only_owned_group(self):
        class Process:
            pid = 314159
            def poll(self):
                return None
            def wait(self, timeout):
                return 0
        with patch.object(demo.os, 'killpg') as killpg:
            demo.stop_owned(Process())
        killpg.assert_called_once_with(314159, demo.signal.SIGTERM)


@unittest.skipUnless(EVIDENCE, 'Set IEMS_DCG_SERVICE_EVIDENCE to the completed real rehearsal')
class RealEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(EVIDENCE).resolve()
        cls.report = json.loads((cls.root / 'results.json').read_text())

    def test_registry_versions_and_storage(self):
        r = self.report
        self.assertEqual(r['result'], 'PASS')
        self.assertEqual(set(r['contracts']), {'iems.accessibility', 'iems.enrollment', 'iems.notification', 'iems.scholarship'})
        self.assertEqual({v['versions'][0] for v in r['contracts'].values()}, {'v1'})
        for row in r['contracts'].values():
            self.assertEqual(row['retrieved_schema_canonical_sha256'], row['submitted_schema_canonical_sha256'])
        self.assertTrue(r['storage']['metadata_sqlite'].startswith(str(self.root / 'runtime')))
        self.assertTrue((self.root / 'runtime/checks.db').is_file())
        self.assertEqual(r['storage']['iems_application_database'], 'not used')

    def test_rest_runs_logs_ui_and_restart(self):
        r = self.report
        a, b = r['runs']['compatible'], r['runs']['breaking']
        self.assertNotEqual(a['run_id'], b['run_id'])
        self.assertEqual((a['http_accepted'], b['http_accepted']), (202, 202))
        self.assertEqual((a['final']['status'], b['final']['status']), ('PASS', 'FAIL'))
        self.assertGreater(a['log_count'], 0)
        self.assertGreater(b['log_count'], 0)
        self.assertIn('studentId (integer -> string)', ' '.join(b['final']['breakingChanges']))
        self.assertEqual(r['post_restart']['run_ids'], sorted([a['run_id'], b['run_id']]))
        self.assertTrue(r['post_restart']['no_new_runs'])
        for stage in ('ui_before_restart', 'ui_after_restart'):
            self.assertTrue(r[stage]['compatible']['visible_pass_id'])
            self.assertTrue(r[stage]['breaking']['visible_fail_id'])
            self.assertTrue(r[stage]['breaking']['visible_fail'])
            self.assertEqual(r[stage]['dashboard']['http'], 200)
        self.assertEqual(r['post_restart']['contract_count'], 4)

    def test_newman_ai_cleanup_and_secrets(self):
        r = self.report
        self.assertFalse(r['ai_enabled'])
        self.assertEqual(r['rust_after'], [])
        self.assertTrue(r['port_released'])
        for field in ('source_contracts_unchanged', 'package_unchanged', 'accepted_rc_unchanged'):
            self.assertTrue(r[field])
        for stage in ('newman_before_restart', 'newman_after_restart'):
            self.assertEqual(r[stage]['exit_code'], 0)
        for file in self.root.rglob('*'):
            self.assertEqual(stat.S_IMODE(file.stat().st_mode), 0o700 if file.is_dir() else 0o600)
        for file in (self.root / 'postman').glob('*.log'):
            self.assertNotIn('Authorization: Basic', file.read_text())
        env = json.loads((demo.ROOT / 'postman/dcg-governance-environment.json').read_text())
        self.assertEqual([v['value'] for v in env['values'] if v['key'] in ('dcg_username', 'dcg_password')], ['', ''])


if __name__ == '__main__':
    unittest.main()
