from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'scripts'
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from eval_ir import calculate_ir_metrics, cases_to_scored_docs, load_doc_judgments  # noqa: E402


class EvalMemoryQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.run_path = ROOT / 'tests' / 'fixtures' / 'd1_sample.run.json'
        cls.judgments_path = ROOT / 'tests' / 'fixtures' / 'd1_sample.judgments.csv'
        cls.run_payload = json.loads(cls.run_path.read_text(encoding='utf-8'))
        cls.labels = load_doc_judgments(cls.judgments_path)

    def test_sample_metrics_match_expected(self) -> None:
        metrics, per_query = calculate_ir_metrics(self.run_payload['cases'], self.labels)
        self.assertAlmostEqual(metrics['hit_at_5'], 1.0, places=4)
        self.assertAlmostEqual(metrics['mrr_at_10'], 0.4167, places=4)
        self.assertAlmostEqual(metrics['ndcg_at_10'], 0.6202, places=4)
        self.assertAlmostEqual(metrics['bad_hit_rate_at_5'], 0.5, places=4)
        self.assertEqual(per_query, {'D01': 1.0, 'D02': 1.0})

    def test_doc_centric_judgments_ignore_stale_rank_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            altered = Path(tmp) / 'judgments.csv'
            with self.judgments_path.open(newline='', encoding='utf-8') as src, altered.open('w', newline='', encoding='utf-8') as dst:
                rows = list(csv.DictReader(src))
                fieldnames = rows[0].keys()
                writer = csv.DictWriter(dst, fieldnames=fieldnames)
                writer.writeheader()
                for idx, row in enumerate(rows, start=1):
                    row['rank'] = str(((idx + 4) % 10) + 1)
                    writer.writerow(row)
            labels = load_doc_judgments(altered)
            metrics, _ = calculate_ir_metrics(self.run_payload['cases'], labels)
            self.assertAlmostEqual(metrics['hit_at_5'], 1.0, places=4)
            self.assertAlmostEqual(metrics['mrr_at_10'], 0.4167, places=4)
            self.assertAlmostEqual(metrics['ndcg_at_10'], 0.6202, places=4)
            self.assertAlmostEqual(metrics['bad_hit_rate_at_5'], 0.5, places=4)

    def test_duplicate_judgment_conflict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / 'judgments.csv'
            bad.write_text(
                'run_id,query_id,rank,chunk_id,doc_id,grade,labeler,notes\n'
                'D1,D01,1,3,3,2,x,one\n'
                'D1,D01,9,3,3,0,x,two\n',
                encoding='utf-8',
            )
            with self.assertRaisesRegex(ValueError, 'conflicting grades'):
                load_doc_judgments(bad)

    def test_duplicate_run_doc_fails(self) -> None:
        dup_run = json.loads(json.dumps(self.run_payload))
        dup_hit = json.loads(json.dumps(dup_run['cases'][0]['hits'][0]))
        dup_run['cases'][0]['hits'][1] = dup_hit
        with self.assertRaisesRegex(ValueError, 'duplicate chunk_id in run'):
            cases_to_scored_docs(dup_run['cases'])

    def test_judged_only_false_treats_unjudged_as_nonrelevant(self) -> None:
        synthetic_cases = [
            {
                'query_id': 'Q1',
                'bucket': 'procedure',
                'latency_ms': 10.0,
                'hits': [
                    {'chunk_id': '100', 'rrf_score': 5.0},
                    {'chunk_id': '200', 'rrf_score': 4.0},
                ],
            }
        ]
        synthetic_labels = {('Q1', '200'): 2}
        metrics, per_query = calculate_ir_metrics(synthetic_cases, synthetic_labels)
        self.assertAlmostEqual(metrics['hit_at_5'], 1.0, places=4)
        self.assertAlmostEqual(metrics['mrr_at_10'], 0.5, places=4)
        self.assertAlmostEqual(per_query['Q1'], 1.0, places=4)

    def test_bucket_floor_logic_via_score_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_path = Path(tmp) / 'run.json'
            judgments_path = Path(tmp) / 'judgments.csv'
            out_path = Path(tmp) / 'score.json'
            run_payload = {
                'run_id': 'T1',
                'params': {},
                'cases': [
                    {
                        'query_id': 'Q1',
                        'bucket': 'exact_lookup',
                        'evidence_polarity': 'support',
                        'latency_ms': 10.0,
                        'hits': [
                            {'chunk_id': '11', 'doc_id': '11', 'rrf_score': 10.0},
                            {'chunk_id': '12', 'doc_id': '12', 'rrf_score': 9.0},
                        ],
                    },
                    {
                        'query_id': 'Q2',
                        'bucket': 'policy_contract',
                        'evidence_polarity': 'support',
                        'latency_ms': 20.0,
                        'hits': [
                            {'chunk_id': '21', 'doc_id': '21', 'rrf_score': 10.0},
                            {'chunk_id': '22', 'doc_id': '22', 'rrf_score': 9.0},
                        ],
                    },
                ],
            }
            run_path.write_text(json.dumps(run_payload), encoding='utf-8')
            judgments_path.write_text(
                'run_id,query_id,rank,chunk_id,doc_id,grade,labeler,notes\n'
                'T1,Q1,1,11,11,2,redacted,redacted\n'
                'T1,Q2,1,21,21,0,redacted,redacted\n'
                'T1,Q2,2,22,22,2,redacted,redacted\n',
                encoding='utf-8',
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts' / 'eval_memory_quality.py'),
                    'score',
                    '--run-json',
                    str(run_path),
                    '--judgments',
                    str(judgments_path),
                    '--out',
                    str(out_path),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            scored = json.loads(out_path.read_text(encoding='utf-8'))
            self.assertEqual(scored['bucket_hit_at_5_support']['exact_lookup'], 1.0)
            self.assertEqual(scored['bucket_hit_at_5_support']['policy_contract'], 1.0)
            self.assertTrue(scored['gates']['bucket_floor'])

    def test_compare_backcompat_with_old_style_score_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / 'base.json'
            cand = Path(tmp) / 'cand.json'
            out = Path(tmp) / 'compare.json'
            base.write_text(json.dumps({'metrics': {'hit_at_5': 0.5, 'mrr_at_10': 0.2, 'ndcg_at_10': 0.3, 'bad_hit_rate_at_5': 0.6, 'p95_latency_ms': 100.0}}), encoding='utf-8')
            cand.write_text(json.dumps({'metrics_support': {'hit_at_5': 0.9, 'mrr_at_10': 0.7, 'ndcg_at_10': 0.8}, 'metrics': {'bad_hit_rate_at_5': 0.3, 'p95_latency_ms': 80.0}, 'metrics_disconfirm': {'hit_at_5': 0.67}}), encoding='utf-8')
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / 'scripts' / 'eval_memory_quality.py'),
                    'compare',
                    '--baseline',
                    str(base),
                    '--candidate',
                    str(cand),
                    '--out',
                    str(out),
                ],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            report = json.loads(out.read_text(encoding='utf-8'))
            self.assertAlmostEqual(report['delta']['hit_at_5'], 0.4, places=4)
            self.assertAlmostEqual(report['delta']['disconfirm_hit_at_5'], 0.67, places=4)


if __name__ == '__main__':
    unittest.main()
