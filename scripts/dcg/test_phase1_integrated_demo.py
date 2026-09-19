#!/usr/bin/env python3
"""Focused orchestration safeguards; live checks use retained integrated evidence."""

import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

import phase1_integrated_demo as demo


LIVE = os.environ.get('IEMS_PHASE1_INTEGRATED_EVIDENCE')


class IntegratedSafeguardsTest(unittest.TestCase):
    def evidence(self):
        demo.REHEARSALS.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='phase1-integrated-test-', dir=demo.REHEARSALS))
        self.addCleanup(lambda: shutil.rmtree(directory, ignore_errors=True))
        return directory

    def test_existing_evidence_refused(self):
        evidence = self.evidence()
        with self.assertRaises(FileExistsError):
            demo.prepare_evidence(evidence)

    def test_missing_or_wrong_development_package_refused(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            demo.verify_development_package(Path('/tmp/missing-dcg-package'))

    def test_real_contract_and_normal_database_targets_refused(self):
        evidence = self.evidence()
        owned_app = evidence / 'runtime/api-project'
        owned_db = evidence / 'runtime/api.sqlite'
        owned_history = evidence / 'runtime/history.sqlite'
        demo.assert_disposable_targets(evidence, owned_app, owned_db, owned_history)
        with self.assertRaisesRegex(RuntimeError, 'non-disposable|real IEMS'):
            demo.assert_disposable_targets(evidence, demo.ROOT, owned_db, owned_history)
        with self.assertRaisesRegex(RuntimeError, 'non-disposable|real IEMS'):
            demo.assert_disposable_targets(evidence, owned_app, demo.ROOT / '.dcg/data/iems.db', owned_history)

    def test_isolated_project_contains_runtime_validation_contract(self):
        evidence = self.evidence()
        app = demo.isolated_project(evidence)
        runtime_contract = app / 'runtime-contracts/iems.scholarship.applied/v1.json'
        self.assertEqual(
            (demo.ROOT / 'runtime-contracts/iems.scholarship.applied/v1.json').read_bytes(),
            runtime_contract.read_bytes(),
        )

    def test_required_subprocess_failure_propagates_and_cleans_marker(self):
        evidence = self.evidence()
        with self.assertRaisesRegex(RuntimeError, 'exited 7'):
            demo.run_child(evidence, 'failure-probe', [sys.executable, '-c', 'raise SystemExit(7)'],
                           dict(os.environ, DCG_AI_ENABLED='false'), [], timeout=5)
        self.assertFalse((evidence / 'active-process.json').exists())

    def test_timeout_stops_owned_process_and_cleans_marker(self):
        evidence = self.evidence()
        with self.assertRaises(subprocess.TimeoutExpired):
            demo.run_child(evidence, 'timeout-probe', [sys.executable, '-c', 'import time; time.sleep(30)'],
                           dict(os.environ, DCG_AI_ENABLED='false'), [], timeout=.2)
        self.assertFalse((evidence / 'active-process.json').exists())

    def test_cleanup_stops_only_recorded_process(self):
        evidence = self.evidence()
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                   start_new_session=True)
        try:
            time.sleep(.1)
            demo.active_marker(evidence, process, 'time.sleep(30)', 'cleanup-probe')
            self.assertTrue(demo.stop_recorded_process(evidence))
            process.wait(timeout=5)
            self.assertFalse((evidence / 'active-process.json').exists())
        finally:
            if process.poll() is None:
                demo.stop_child(process)

    def test_breaking_proof_requires_zero_executor_and_blocked_dispatch(self):
        multiple = {'blocking_exit': 1, 'blocked_java_dispatch_count': 1}
        with self.assertRaisesRegex(RuntimeError, 'did not block Java'):
            demo.check_multiple(multiple)
        migration = {'safe': {'gateVerdict': 'PASS', 'executorAttempts': 1,
                              'executorExitCode': 0, 'optionalColumnPresent': True,
                              'reviewedSqlSha256': 'a', 'offeredSqlSha256': 'a'},
                     'breaking': {'gateVerdict': 'FAIL', 'executorAttempts': 1},
                     'normalIemsDatabaseUntouched': True}
        with self.assertRaisesRegex(RuntimeError, 'Breaking migration'):
            demo.check_migration(migration)


@unittest.skipUnless(LIVE, 'Set IEMS_PHASE1_INTEGRATED_EVIDENCE to a completed live rehearsal')
class RetainedIntegratedEvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(LIVE)
        cls.report = json.loads((cls.root / 'results.json').read_text())

    def test_index_has_real_links_and_cannot_pass_when_missing(self):
        demo.validate_index(self.report)
        self.assertEqual(0o700, self.root.stat().st_mode & 0o777)
        changed = copy.deepcopy(self.report)
        del changed['scenarios']['migration_gate']
        with self.assertRaisesRegex(RuntimeError, 'scenario missing'):
            demo.validate_index(changed)
        changed = copy.deepcopy(self.report)
        changed['scenarios']['webhook_delivery']['evidence'] = str(self.root / 'missing.json')
        with self.assertRaisesRegex(RuntimeError, 'sub-evidence'):
            demo.validate_index(changed)

    def test_no_ai_and_exact_expected_boundary_proofs(self):
        self.assertFalse(self.report['ai_enabled'])
        self.assertEqual([], self.report['rust_processes_before'])
        self.assertEqual([], self.report['rust_processes_after'])
        for name, field in (('maven_gate', 'ai_enabled'), ('service_dashboard', 'ai_enabled'),
                            ('webhook_delivery', 'ai_enabled')):
            sub = json.loads(Path(self.report['scenarios'][name]['evidence']).read_text())
            self.assertFalse(sub[field], name)
        migration_ai = json.loads(Path(self.report['scenarios']['migration_gate']['evidence']).read_text())
        self.assertTrue(migration_ai['aiDisabled'])
        multiple = json.loads(Path(self.report['scenarios']['multiple_breaking_contracts']['evidence']).read_text())
        migration = json.loads(Path(self.report['scenarios']['migration_gate']['evidence']).read_text())
        demo.check_multiple(multiple)
        demo.check_migration(migration)
        self.assertEqual(1, multiple['blocking_exit'])
        self.assertEqual(0, migration['breaking']['executorAttempts'])
        self.assertTrue(self.report['source_contracts_unchanged'])
        self.assertTrue(self.report['normal_iems_database_unchanged'])

    def test_default_cleanup_released_ports_and_owned_processes(self):
        self.assertTrue(self.report['ports_released'])
        self.assertTrue(self.report['task_process_released'])
        self.assertEqual(len(self.report['ports']), len(set(self.report['ports'])))
        self.assertFalse((self.root / 'active-process.json').exists())
        self.assertTrue(all(demo.port_released(port) for port in self.report['ports']))
        self.assertEqual(0, next(c['exit'] for c in self.report['commands'] if c['stage'] == 'webhook-delivery'))


if __name__ == '__main__':
    unittest.main()
