"""Focused safety checks for the maintained Phase 2 rehearsal."""
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
from unittest.mock import patch

import phase2_integrated_demo as demo
import phase2_service_demo as service


class Phase2SafeguardsTest(unittest.TestCase):
    def evidence(self):
        demo.p1.REHEARSALS.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix='phase2-integrated-test-', dir=demo.p1.REHEARSALS))
        self.addCleanup(lambda: shutil.rmtree(directory, ignore_errors=True))
        return directory

    def test_existing_evidence_refused(self):
        with self.assertRaises(FileExistsError):
            demo.prepare(self.evidence())

    def test_prepare_creates_private_rehearsal_parent_on_fresh_checkout(self):
        root = Path(tempfile.mkdtemp(prefix='phase2-fresh-root-'))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        rehearsals = root / '.dcg/rehearsals'
        evidence = rehearsals / 'phase2-integrated-linux-test'
        with patch.object(demo.p1, 'REHEARSALS', rehearsals):
            self.assertEqual(evidence.resolve(), demo.prepare(evidence))
        self.assertEqual(0o700, rehearsals.stat().st_mode & 0o777)
        self.assertTrue((evidence / '.phase2-integrated-marker').is_file())

    def test_wrong_phase2_package_refused(self):
        with self.assertRaisesRegex(ValueError, 'does not exist'):
            demo.verify_selected_package(Path('/tmp/not-the-package'))

    def test_missing_scenario_or_evidence_prevents_pass(self):
        evidence = self.evidence()
        (evidence / 'proof.json').write_text('{}')
        base = {'overall_result': 'PASS', 'scenarios': {},
                'preservation': {'source_contracts_unchanged': True},
                'cleanup': {'ports_released': True, 'processes_released': True,
                            'rust_processes_after': []}}
        for name in demo.REQUIRED:
            base['scenarios'][name] = {'result': 'PASS', 'evidence': str(evidence / 'proof.json'),
                                       'boundary_proof': 'validated proof'}
        demo.validate_index(base)
        missing = copy.deepcopy(base)
        missing['scenarios']['faults']['evidence'] = str(evidence / 'missing.json')
        with self.assertRaisesRegex(RuntimeError, 'missing result'):
            demo.validate_index(missing)
        missing = copy.deepcopy(base)
        missing['scenarios']['startup_gate']['boundary_proof'] = ''
        with self.assertRaisesRegex(RuntimeError, 'boundary proof'):
            demo.validate_index(missing)

    def test_fault_cannot_fabricate_prediction_or_convert_decision(self):
        run = {'runId': 'r1', 'status': 'FAIL'}
        advice = {'runId': 'r1', 'advisoryOnly': True, 'testOnlyAdapter': True,
                  'status': 'TIMEOUT', 'predictionLabel': None, 'probabilities': None,
                  'agreement': 'NOT_AVAILABLE'}
        service.validate_advisory(run, advice, 'TIMEOUT', test_only=True)
        fabricated = dict(advice, predictionLabel='SAFE')
        with self.assertRaisesRegex(RuntimeError, 'Fabricated'):
            service.validate_advisory(run, fabricated, 'TIMEOUT', test_only=True)
        altered = dict(run, status='PASS')
        with self.assertRaisesRegex(RuntimeError, 'Run/advisory mismatch|Incorrect advisory'):
            service.validate_advisory(dict(altered, status='QUEUED'), advice, 'TIMEOUT', test_only=True)

    def test_test_only_prediction_must_be_marked(self):
        run = {'runId': 'r2', 'status': 'FAIL'}
        advice = {'runId': 'r2', 'advisoryOnly': True, 'testOnlyAdapter': True,
                  'status': 'AVAILABLE', 'predictionLabel': 'SAFE', 'probabilities': {'SAFE': 1},
                  'seedPredictions': [{}, {}, {}], 'agreement': 'DISAGREES'}
        service.validate_advisory(run, advice, 'AVAILABLE', test_only=True)
        with self.assertRaisesRegex(RuntimeError, 'Test-only provenance'):
            service.validate_advisory(run, advice, 'AVAILABLE', test_only=False)

    def test_disposable_targets_reject_source_and_normal_database(self):
        evidence = self.evidence()
        app = evidence / 'runtime/app'
        database = evidence / 'runtime/iems.sqlite'
        history = evidence / 'runtime/history.sqlite'
        demo.p1.assert_disposable_targets(evidence, app, database, history)
        with self.assertRaisesRegex(RuntimeError, 'non-disposable'):
            demo.p1.assert_disposable_targets(evidence, demo.ROOT, database, history)
        with self.assertRaisesRegex(RuntimeError, 'non-disposable'):
            demo.p1.assert_disposable_targets(evidence, app, demo.ROOT / '.dcg/data/iems.db', history)

    def test_recorded_cleanup_stops_only_owned_process_and_releases_port(self):
        evidence = self.evidence()
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                   start_new_session=True)
        try:
            time.sleep(.1)
            demo.p1.active_marker(evidence, process, 'time.sleep(30)', 'cleanup-test')
            self.assertTrue(demo.p1.stop_recorded_process(evidence))
            process.wait(timeout=5)
            self.assertFalse((evidence / 'active-process.json').exists())
        finally:
            if process.poll() is None:
                demo.p1.stop_child(process)

    def test_service_cleanup_checks_process_identity(self):
        evidence = self.evidence()
        service_dir = evidence / 'service'; service_dir.mkdir()
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                   start_new_session=True)
        try:
            time.sleep(.1)
            demo.p1.write_json(service_dir / 'active-processes.json', [{
                'pid': process.pid, 'startedAt': demo.p1.process_identity(process.pid),
                'identity': 'time.sleep(30)'}])
            self.assertTrue(service.cleanup_owned(service_dir))
            process.wait(timeout=5)
            self.assertFalse((service_dir / 'active-processes.json').exists())
        finally:
            if process.poll() is None:
                demo.p1.stop_child(process)


@unittest.skipUnless(os.environ.get('IEMS_PHASE2_INTEGRATED_EVIDENCE'),
                     'Set IEMS_PHASE2_INTEGRATED_EVIDENCE to a completed live rehearsal')
class RetainedPhase2EvidenceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(os.environ['IEMS_PHASE2_INTEGRATED_EVIDENCE'])
        cls.report = json.loads((cls.root / 'results.json').read_text())

    def test_complete_index_and_private_evidence(self):
        demo.validate_index(self.report)
        self.assertEqual(0o700, self.root.stat().st_mode & 0o777)
        self.assertEqual(set(demo.REQUIRED), set(self.report['scenarios']))

    def test_no_ai_and_real_model_are_separate(self):
        self.assertEqual('DISABLED/absent', self.report['scenarios']['baseline']['advisory_status'])
        self.assertEqual('PASS', self.report['scenarios']['real_compatible']['deterministic_result'])
        self.assertEqual('FAIL', self.report['scenarios']['real_breaking']['deterministic_result'])
        self.assertEqual('AVAILABLE', self.report['scenarios']['real_breaking']['advisory_status'])
        self.assertEqual([], self.report['cleanup']['rust_processes_after'])

    def test_service_faults_preserve_pass_and_fail(self):
        service_report = json.loads((self.root / 'service/results.json').read_text())
        self.assertEqual('PASS', service_report['result'])
        for mode in ('unavailable', 'timeout', 'invalid-output'):
            compatible = service_report['runs'][mode + '-compatible']
            breaking = service_report['runs'][mode + '-breaking'] if mode == 'unavailable' else service_report['runs'][mode]
            self.assertEqual('PASS', compatible['run']['status'])
            self.assertEqual('FAIL', breaking['run']['status'])
            self.assertIsNone(compatible['advisory']['predictionLabel'])
            self.assertIsNone(breaking['advisory']['predictionLabel'])
        self.assertTrue(service_report['normalRuntimeAdapterRejected']['portReleased'])

    def test_real_advisories_persist_across_service_restart(self):
        service_report = json.loads((self.root / 'service/results.json').read_text())
        for name in ('real-compatible', 'real-breaking'):
            proof = service_report['persistenceAfterRestart'][name]
            self.assertEqual(service_report['runs'][name]['run']['runId'], proof['runId'])
            self.assertTrue(proof['run'] and proof['advisory'] and proof['logs'])
            self.assertEqual(200, proof['dashboard']['http'])
            self.assertTrue(proof['dashboard']['runIdVisible'])

    def test_owned_processes_and_ports_released(self):
        self.assertTrue(self.report['cleanup']['ports_released'])
        self.assertTrue(self.report['cleanup']['processes_released'])
        self.assertTrue(all(demo.p1.port_released(port) for port in self.report['ports']))
        self.assertFalse((self.root / 'active-process.json').exists())
        self.assertFalse((self.root / 'service/active-processes.json').exists())

if __name__ == '__main__':
    unittest.main()
