"""Focused policy and real-build evidence checks for the official opt-in Maven gate."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET

import maven_gate_demo as demo

ROOT = demo.ROOT
EVIDENCE = os.environ.get('IEMS_MAVEN_GATE_EVIDENCE')
NS = {'m': 'http://maven.apache.org/POM/4.0.0'}


class GateConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pom = ET.parse(ROOT / 'pom.xml').getroot()

    def test_profile_explicit_and_not_auto_activated(self):
        profiles = [p for p in self.pom.findall('m:profiles/m:profile', NS)
                    if p.findtext('m:id', namespaces=NS) == 'dcg-demo']
        self.assertEqual(len(profiles), 1)
        self.assertIsNone(profiles[0].find('m:activation', NS))
        self.assertEqual([p.findtext('m:id', namespaces=NS) for p in self.pom.findall('m:profiles/m:profile', NS)], ['dev', 'prod', 'dcg-demo'])

    def test_official_plugin_four_executions_at_validate(self):
        profile = next(p for p in self.pom.findall('m:profiles/m:profile', NS) if p.findtext('m:id', namespaces=NS) == 'dcg-demo')
        plugin = profile.find('m:build/m:plugins/m:plugin', NS)
        self.assertEqual(plugin.findtext('m:groupId', namespaces=NS), 'com.ideas.contracts')
        self.assertEqual(plugin.findtext('m:artifactId', namespaces=NS), 'contract-maven-plugin')
        self.assertEqual(plugin.findtext('m:version', namespaces=NS), '4.0.0-rc.1')
        self.assertEqual(plugin.findtext('m:configuration/m:remoteReportingMode', namespaces=NS), 'DISABLED')
        executions = plugin.findall('m:executions/m:execution', NS)
        self.assertEqual(len(executions), 4)
        self.assertEqual([x.findtext('m:configuration/m:contractId', namespaces=NS) for x in executions],
                         [f'iems.{name}' for name in ('accessibility', 'enrollment', 'notification', 'scholarship')])
        for execution in executions:
            self.assertEqual(execution.findtext('m:phase', namespaces=NS), 'validate')
            self.assertEqual([g.text for g in execution.findall('m:goals/m:goal', NS)], ['check-compat'])

    def test_disposable_candidates_reset_on_success_failure_and_interrupt(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp)
            shutil.copytree(ROOT / 'contracts', app / 'contracts')
            before = demo.inventory(app / 'contracts')
            for error in (None, RuntimeError('Maven failure'), KeyboardInterrupt(), InterruptedError('SIGTERM')):
                with self.subTest(error=type(error).__name__):
                    try:
                        with demo.breaking(app, ['iems.enrollment', 'iems.scholarship']):
                            if error: raise error
                    except (RuntimeError, KeyboardInterrupt, InterruptedError):
                        pass
                    self.assertEqual(demo.inventory(app / 'contracts'), before)

    def test_packaging_proof_rejects_stale_or_reached_artifacts(self):
        with self.assertRaisesRegex(RuntimeError, 'stale artifacts'):
            demo.assert_no_packaging({'old.jar': 'hash'}, {}, '')
        with self.assertRaisesRegex(RuntimeError, 'produced an application artifact'):
            demo.assert_no_packaging({}, {'bad.jar': 'hash'}, '')
        with self.assertRaisesRegex(RuntimeError, 'Packaging goal reached'):
            demo.assert_no_packaging({}, {}, '[INFO] --- jar:3.3.0:jar (default-jar)')

    def test_existing_evidence_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):
                demo.run(Path(tmp), ROOT / '.dcg/maven-repository', ROOT / '.dcg/runtime/dcg-4.0.0-phase1-no-ai-dev.20260917-macos-arm64')


@unittest.skipUnless(EVIDENCE, 'Set IEMS_MAVEN_GATE_EVIDENCE to the completed live rehearsal')
class LiveBuildEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(EVIDENCE)
        cls.report = json.loads((cls.root / 'results.json').read_text())
        cls.scenarios = {x['scenario']: x for x in cls.report['scenarios']}

    def test_compatible_and_normal_build_both_package(self):
        for name in ('compatible', 'profile-off'):
            item = self.scenarios[name]
            self.assertEqual(item['exit'], 0)
            self.assertTrue(item['packaging_reached'])
            self.assertFalse(item['artifacts_before'])
            self.assertIn('inclusive-education-management-system-1.0.0-SNAPSHOT.jar', item['artifacts_after'])
        self.assertEqual(len(self.scenarios['compatible']['verdicts']), 4)
        self.assertEqual(self.scenarios['profile-off']['verdicts'], {})

    def test_breaking_builds_fail_before_package_and_propagate(self):
        for name in ('single-breaking', 'multiple-breaking', 'missing-ai-breaking'):
            item = self.scenarios[name]
            self.assertNotEqual(item['exit'], 0)
            self.assertFalse(item['packaging_reached'])
            self.assertFalse(item['artifacts_before'])
            self.assertFalse(item['artifacts_after'])
            self.assertEqual(item['verdicts'], {'iems.accessibility': 'PASS', 'iems.enrollment': 'FAIL'})
            self.assertIn('BUILD FAILURE', (self.root / name / 'build.log').read_text())
        self.assertEqual(self.scenarios['multiple-breaking']['not_evaluated'], ['iems.notification', 'iems.scholarship'])

    def test_reset_recovery_ai_absence_and_preservation(self):
        for name in ('single-recovery', 'multiple-recovery'):
            item = self.scenarios[name]
            self.assertEqual(item['exit'], 0)
            self.assertEqual(set(item['verdicts'].values()), {'PASS'})
        self.assertTrue(self.report['single_reset_exact'])
        self.assertTrue(self.report['multiple_reset_exact'])
        self.assertTrue(self.report['missing_ai_reset_exact'])
        self.assertEqual(self.scenarios['missing-ai-compatible']['exit'], 0)
        self.assertFalse(self.report['ai_enabled'])
        self.assertFalse(self.report['rust_or_iems_startup_observations'])
        for name in ('contracts', 'package', 'rc'):
            self.assertTrue(self.report[name + '_unchanged'])


if __name__ == '__main__':
    unittest.main()
