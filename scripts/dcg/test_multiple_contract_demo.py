"""Reset guarantees independent of Java; live rehearsal uses the real engine."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('demo', Path(__file__).with_name('multiple_contract_demo.py'))
demo = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(demo)


class ResetTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.app = Path(self.tmp.name) / 'iems'
        shutil.copytree(demo.ROOT / 'contracts', self.app / 'contracts')
        # A candidate need not be byte-identical to v1; restore its exact bytes.
        self.candidate = self.app / 'contracts/iems.enrollment/candidate.json'
        self.candidate.write_bytes(self.candidate.read_bytes() + b'\n  \n')
        self.before = demo.inventory(self.app / 'contracts')

    def test_success_restores_exact_candidates_and_never_changes_baselines(self):
        with demo.candidates(self.app):
            changed = demo.inventory(self.app / 'contracts')
            names = {k for k in changed if changed[k] != self.before[k]}
            self.assertEqual(names, {'iems.enrollment/candidate.json', 'iems.scholarship/candidate.json'})
        self.assertEqual(demo.inventory(self.app / 'contracts'), self.before)

    def test_exception_and_interrupt_restore_exact_bytes(self):
        for error in (RuntimeError('failed check'), KeyboardInterrupt(), InterruptedError('SIGTERM')):
            with self.subTest(error=type(error).__name__):
                with self.assertRaises(type(error)):
                    with demo.candidates(self.app):
                        raise error
                self.assertEqual(demo.inventory(self.app / 'contracts'), self.before)

    def test_stale_baseline_rejected_before_any_candidate_mutation(self):
        base = self.app / 'contracts/iems.scholarship/v1.json'
        base.write_bytes(base.read_bytes() + b'\n')
        before = demo.inventory(self.app / 'contracts')
        with self.assertRaisesRegex(RuntimeError, 'Baseline changed'):
            with demo.candidates(self.app):
                self.fail('Stale fixture accepted')
        self.assertEqual(demo.inventory(self.app / 'contracts'), before)

    def test_tampered_fixture_rejected_before_mutation(self):
        fixtures = Path(self.tmp.name) / 'fixtures'
        shutil.copytree(demo.FIXTURES, fixtures)
        with (fixtures / 'scholarship.json').open('ab') as file:
            file.write(b'\n')
        with self.assertRaisesRegex(RuntimeError, 'Fixture integrity'):
            with demo.candidates(self.app, fixtures):
                self.fail('Tampered fixture accepted')
        self.assertEqual(demo.inventory(self.app / 'contracts'), self.before)


if __name__ == '__main__':
    unittest.main()
