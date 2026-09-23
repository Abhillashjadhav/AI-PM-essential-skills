"""Runner regressions using synthetic wrappers, never independent sealed cases.

The existing S1/S2 inputs and candidates are read without changing their gold
files. APPROVED below only exercises the runner gate in a temporary fixture; it
is not a new owner adjudication. No model calls or sealed cases are involved.

This finding is auto-discovered by run_checks.py and run_reproductions.py.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

CATALOG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CATALOG))
from run_sealed_cases import compare_publication  # noqa: E402


class SealedRunnerExpectations(unittest.TestCase):
    def case(self, name='S1', **expectations):
        gold = json.loads((CATALOG / 'gold' / f'{name}.json').read_text())
        case = {
            'case_id': 'SYNTHETIC-RUNNER-REGRESSION',
            'input': gold['input'],
            'candidate': gold['candidate'],
            'expected_verdict': 'PASS',
            'expected_publication': None,
            'owner_approval': 'APPROVED',
            'review_status': 'SETTLED',
            'reason': 'Synthetic runner mechanics check; not an owner adjudication.',
        }
        case.update(expectations)
        return case

    def invoke(self, case):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary) / 'cases'
            folder.mkdir()
            (folder / 'synthetic.json').write_text(json.dumps(case))
            output = Path(temporary) / 'report.json'
            process = subprocess.run(
                [sys.executable, str(CATALOG / 'run_sealed_cases.py'),
                 str(folder), '--json', str(output)],
                capture_output=True, text=True, check=False,
            )
            self.assertTrue(output.exists(), process.stdout + process.stderr)
            receipt = json.loads(output.read_text())
        self.assertNotIn('Traceback', process.stderr)
        return process, receipt

    def cli(self, case):
        process, receipt = self.invoke(case)
        self.assertEqual(receipt['load_errors'], [])
        self.assertEqual(len(receipt['results']), 1)
        return process, receipt['results'][0]

    def test_mixed_schema_error_fails_and_preserves_verdict_denominator(self):
        process, row = self.cli(self.case(expected_publication='malformed'))
        self.assertEqual(process.returncode, 1)
        self.assertEqual(row['status'], 'CASE_SCHEMA_ERROR')
        self.assertEqual(row['checked'], ['verdict'])
        self.assertTrue(row['verdict_scored'])
        self.assertTrue(row['verdict_agrees'])
        self.assertFalse(row['publication_scored'])
        self.assertIn('expected_publication', row['schema_errors'][0])
        self.assertIn('CANDIDATE GRADING    denominator 1', process.stdout)
        self.assertIn('PUBLICATION          denominator 0', process.stdout)
        self.assertNotIn('EXCLUDED FROM EVERY DENOMINATOR', process.stdout)

    def test_schema_only_case_reports_and_writes_json_without_crashing(self):
        process, row = self.cli(self.case(
            expected_verdict=None, expected_publication='malformed'))
        self.assertEqual(process.returncode, 1)
        self.assertEqual(row['status'], 'CASE_SCHEMA_ERROR')
        self.assertEqual(row['checked'], [])
        self.assertIn('expected_publication', row['schema_errors'][0])
        self.assertIn('EXCLUDED FROM EVERY DENOMINATOR: 1', process.stdout)

    def test_invalid_guidance_is_a_schema_error_with_other_axes_preserved(self):
        invalid = [
            ['warn'],
            {'required': [None]},
            {'must_not_warn': [1]},
            {'required': 'warn'},
            {'must_not_warn': None},
            [{'sku': 'C1'}],
            [{'sku': 'C1', 'field': 'material', 'must_reference_evidence': [None]}],
            [{'sku': 'C1', 'field': 'material', 'must_reference_evidence': None}],
            '', False, 0,
        ]
        for guidance in invalid:
            with self.subTest(guidance=guidance):
                process, row = self.cli(self.case(
                    expected_publication={'sku_ids': ['P1', 'C1']},
                    expected_seller_guidance=guidance))
                self.assertEqual(process.returncode, 1)
                self.assertEqual(row['status'], 'CASE_SCHEMA_ERROR')
                self.assertTrue(row['verdict_scored'])
                self.assertTrue(row['publication_scored'])
                self.assertTrue(row['publication_agrees'])
                self.assertFalse(row['guidance_scored'])
                self.assertIn('expected_seller_guidance', row['schema_errors'][0])
                self.assertNotIn('EXCLUDED FROM EVERY DENOMINATOR', process.stdout)

    def test_schema_error_does_not_hide_other_measurement_disagreement(self):
        process, row = self.cli(self.case(
            expected_verdict='FAIL', expected_publication='malformed'))
        self.assertEqual(process.returncode, 1)
        self.assertEqual(row['status'], 'CASE_SCHEMA_ERROR')
        self.assertEqual(row['direction'], 'incorrect_approval')
        self.assertFalse(row['verdict_agrees'])
        self.assertIn('INCORRECT APPROVALS  : 1', process.stdout)

    def test_invalid_publication_parts_preserve_other_valid_measurements(self):
        invalid = [
            {'sku_ids': 1},
            {'sku_ids': 'P1'},
            {'sku_ids': ['P1', None]},
            {'withheld_fields': []},
            {'withheld_fields': {'P1': None}},
            {'withheld_fields': {'P1': 'description'}},
            {'withheld_fields': {'P1': ['description', None]}},
            {'parent_links': []},
            {'parent_links': [['P1', None]]},
            {'parent_links': {'P1': 0}},
            {'parent_links': {'P1': []}},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': 'false'},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': 0},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': 1},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': None},
        ]
        for publication in invalid:
            with self.subTest(publication=publication):
                process, row = self.cli(self.case(
                    'S2', expected_publication=publication,
                    expected_seller_guidance={
                        'must_not_warn': [{'sku': 'P1', 'field': 'price'}]}))
                self.assertEqual(process.returncode, 1)
                self.assertEqual(row['status'], 'CASE_SCHEMA_ERROR')
                self.assertTrue(row['verdict_scored'])
                self.assertTrue(row['verdict_agrees'])
                self.assertTrue(row['guidance_scored'])
                self.assertTrue(row['guidance_agrees'])
                self.assertFalse(row['publication_scored'])
                self.assertIn('expected_publication', row['schema_errors'][0])
                self.assertNotIn('EXCLUDED FROM EVERY DENOMINATOR', process.stdout)

    def test_valid_publication_shapes_remain_comparable(self):
        for publication in (
            {'sku_ids': ['P1']},
            {'withheld_fields': {}},
            {'withheld_fields': {'P1': []}},
            {'parent_links': {}},
            {'parent_links': {'P1': None}},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': False},
            {'parent_links': {'P1': None}, 'parent_links_exhaustive': True},
        ):
            with self.subTest(publication=publication):
                process, row = self.cli(self.case('S2', expected_publication=publication))
                self.assertEqual(process.returncode, 0)
                self.assertTrue(row['publication_scored'])
                self.assertTrue(row['publication_agrees'])
                self.assertEqual(row['schema_errors'], [])
        process, row = self.cli(self.case(expected_publication={
            'sku_ids': None, 'withheld_fields': None, 'parent_links': None}))
        self.assertEqual(process.returncode, 0)
        self.assertFalse(row['publication_scored'])
        self.assertEqual(row['checked'], ['verdict'])
        process, row = self.cli(self.case(expected_publication={
            'parent_links': {'P1': None, 'C1': 'P1'}, 'parent_links_exhaustive': True}))
        self.assertEqual(process.returncode, 0)
        self.assertTrue(row['publication_agrees'])

    def test_valid_publication_mismatches_are_scored_not_schema_errors(self):
        for publication in ({'sku_ids': []}, {'withheld_fields': {'P1': ['description']}}):
            with self.subTest(publication=publication):
                process, row = self.cli(self.case(expected_publication=publication))
                self.assertEqual(process.returncode, 1)
                self.assertEqual(row['status'], 'SCORED')
                self.assertTrue(row['publication_scored'])
                self.assertFalse(row['publication_agrees'])
                self.assertEqual(row['schema_errors'], [])

    def test_exhaustive_flag_without_parent_map_remains_malformed(self):
        for exhaustive in (False, True):
            with self.subTest(exhaustive=exhaustive):
                process, row = self.cli(self.case(expected_publication={
                    'parent_links': None, 'parent_links_exhaustive': exhaustive}))
                self.assertEqual(process.returncode, 1)
                self.assertEqual(row['status'], 'MALFORMED')
                self.assertEqual(row['checked'], [])
                self.assertIn('EXCLUDED FROM EVERY DENOMINATOR: 1', process.stdout)

    def test_non_object_cases_are_load_errors_without_crashing(self):
        for raw in (None, [], list(self.case()), 'scalar', 7, True):
            with self.subTest(raw=raw):
                process, receipt = self.invoke(raw)
                self.assertEqual(process.returncode, 1)
                self.assertEqual(receipt['results'], [])
                self.assertEqual(len(receipt['load_errors']), 1)
                self.assertIn('must be an object', receipt['load_errors'][0])
                self.assertIn('CASES THAT COULD NOT BE LOADED: 1', process.stdout)

    def test_valid_guidance_list_and_wrapper_preserve_structured_comparison(self):
        entry = {
            'sku': 'C1', 'field': 'material',
            'must_reference_evidence': ['C1.material', 'P1.material'],
            'warning_meaning': 'This prose is deliberately not compared.',
        }
        for guidance in ([entry], {'required': [entry],
                                  'must_not_warn': [{'sku': 'P1', 'field': 'price'}]}):
            with self.subTest(guidance=guidance):
                process, row = self.cli(self.case(
                    'S2', expected_publication={'sku_ids': ['P1']},
                    expected_seller_guidance=guidance))
                self.assertEqual(process.returncode, 0)
                self.assertEqual(row['status'], 'SCORED')
                self.assertTrue(row['guidance_scored'])
                self.assertTrue(row['guidance_agrees'])
                self.assertEqual(row['schema_errors'], [])
                self.assertTrue(any('guided_help' in x for x in row['guidance_parts_checked']))
                self.assertEqual(len(row['guidance_not_compared']), 1)
                self.assertIn('warning_meaning', row['guidance_not_compared'][0])

    def test_empty_or_unasserted_guidance_adds_no_measurement(self):
        for guidance in (None, [], {}, {'required': [], 'must_not_warn': []}):
            with self.subTest(guidance=guidance):
                process, row = self.cli(self.case(expected_seller_guidance=guidance))
                self.assertEqual(process.returncode, 0)
                self.assertEqual(row['schema_errors'], [])
                self.assertEqual(row['checked'], ['verdict'])
                self.assertFalse(row['guidance_scored'])

    def test_missing_sku_cannot_satisfy_expected_null_parent(self):
        for exhaustive in (False, True):
            with self.subTest(exhaustive=exhaustive):
                process, row = self.cli(self.case(expected_publication={
                    'parent_links': {'SKU_NOT_PUBLISHED': None},
                    'parent_links_exhaustive': exhaustive,
                }))
                self.assertEqual(process.returncode, 1)
                self.assertTrue(row['publication_scored'])
                self.assertFalse(row['publication_agrees'])
                self.assertTrue(any('SKU_NOT_PUBLISHED' in m for m in row['mismatches']))

    def test_published_null_parent_passes_without_asserting_other_skus(self):
        process, row = self.cli(self.case(
            expected_publication={'parent_links': {'P1': None}}))
        self.assertEqual(process.returncode, 0)
        self.assertTrue(row['publication_agrees'])
        self.assertEqual(row['publication_parts_checked'], ['parent_links'])

    def test_exhaustive_parent_map_rejects_unnamed_existing_link(self):
        process, row = self.cli(self.case(expected_publication={
            'parent_links': {'P1': None}, 'parent_links_exhaustive': True,
        }))
        self.assertEqual(process.returncode, 1)
        self.assertFalse(row['publication_agrees'])
        self.assertTrue(any('parent_links_exhaustive' in m for m in row['mismatches']))

    def test_null_and_empty_parent_maps_keep_distinct_meanings(self):
        process, row = self.cli(self.case(expected_publication={'parent_links': None}))
        self.assertEqual(process.returncode, 0)
        self.assertFalse(row['publication_scored'])
        process, row = self.cli(self.case(expected_publication={'parent_links': {}}))
        self.assertEqual(process.returncode, 1)
        self.assertTrue(row['publication_scored'])
        self.assertFalse(row['publication_agrees'])
        for record in ({'sku': 'P1', 'parent_sku': None}, {'sku': 'P1'}):
            result = {'publication_payload': {'records': [record]}}
            self.assertEqual(compare_publication({'parent_links': {}}, result),
                             (['parent_links'], []))
            self.assertEqual(compare_publication({'parent_links': {'P1': None}}, result),
                             (['parent_links'], []))

    def test_report_does_not_certify_independence(self):
        process, _ = self.cli(self.case())
        self.assertEqual(process.returncode, 0)
        self.assertNotIn('initial independent check', process.stdout)
        self.assertIn('independence is not verified by this runner', process.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
