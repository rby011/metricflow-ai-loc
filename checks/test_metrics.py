import csv
import unittest
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from app import app
from semantic_service import MetricRequest, query

ROOT = Path(__file__).resolve().parents[1]

def reference_rows():
    with (ROOT / 'seeds/raw_commits.csv').open(encoding='utf-8') as f:
        events = list(csv.DictReader(f))
    latest = {}
    for row in sorted(events, key=lambda r: (r['ingested_at'], r['event_id'])):
        latest[(row['repository'], row['commit_sha'])] = row
    return [r for r in latest.values() if r['is_merge'] == 'False' and r['is_bot'] == 'False']

class MetricsChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = reference_rows()
        cls.full = query(MetricRequest())['rows'][0]
        cls.client = TestClient(app)

    def test_01_known_totals_dedup_merge_bot(self):
        self.assertEqual(len(self.rows), 463)
        expected = dict(commit_loc=118571, ai_loc=65417, human_loc=53154,
                        commit_count=463, deleted_loc=30727, churn_loc=149298)
        for key, value in expected.items():
            self.assertEqual(self.full[key], value, key)
        self.assertAlmostEqual(self.full['loc_per_commit'], 118571 / 463)

    def test_02_ratio_is_sum_over_sum_not_average_of_ratios(self):
        ratio = self.full['ai_share']
        self.assertAlmostEqual(ratio, 65417 / 118571)
        per_commit = [int(r['ai_added_loc']) / int(r['added_loc']) for r in self.rows if int(r['added_loc'])]
        naive = sum(per_commit) / len(per_commit)
        self.assertGreater(abs(naive - ratio), 0.0001)
        by_org = query(MetricRequest(group_by=['organization']))['rows']
        self.assertAlmostEqual(sum(r['ai_loc'] for r in by_org) / sum(r['commit_loc'] for r in by_org), ratio)

    def test_03_period_org_repo_filter_matches_raw_reference(self):
        request = MetricRequest(start='2026-10-26', end='2026-11-01',
            filters={'organization': '모바일개발', 'repository': 'mobile-core'})
        result = query(request)['rows'][0]
        records = [r for r in self.rows if r['organization'] == '모바일개발'
                   and r['repository'] == 'mobile-core' and '2026-10-26' <= r['committed_at'][:10] <= '2026-11-01']
        self.assertEqual(result['commit_loc'], sum(int(r['added_loc']) for r in records))
        self.assertEqual(result['ai_loc'], sum(int(r['ai_added_loc']) for r in records))
        self.assertEqual(result['commit_count'], len(records))

    def test_04_final_day_includes_2359_kst(self):
        result = query(MetricRequest(start='2026-11-01', end='2026-11-01',
            filters={'commit_sha': 'zeroadded001'}))['rows'][0]
        self.assertEqual(result['commit_count'], 1)
        self.assertEqual(result['deleted_loc'], 75)

    def test_05_zero_denominator_is_null(self):
        result = query(MetricRequest(filters={'commit_sha': 'zeroadded001'}))['rows'][0]
        self.assertEqual(result['commit_loc'], 0)
        self.assertEqual(result['ai_loc'], 0)
        self.assertIsNone(result['ai_share'])

    def test_06_empty_period_has_no_false_zero_share(self):
        result = query(MetricRequest(start='2026-01-01', end='2026-01-02'))['rows'][0]
        self.assertEqual(result['commit_count'], 0)
        self.assertIsNone(result['ai_share'])
        self.assertIsNone(result['loc_per_commit'])
        self.assertEqual(query(MetricRequest(start='2026-01-01', end='2026-01-02', group_by=['organization']))['rows'], [])

    def test_07_invalid_or_injected_requests_rejected(self):
        for body in [
            {'metrics': ['sum(added_loc)']},
            {'filters': {'organization': "' OR 1=1 --"}},
            {'group_by': ['raw_sql']},
            {'start': '2026-11-01', 'end': '2026-10-01'},
            {'limit': 1000000},
        ]:
            self.assertEqual(self.client.post('/api/query', json=body).status_code, 422, body)

    def test_08_api_catalog_and_real_metricflow_sql(self):
        cat = self.client.get('/api/catalog').json()
        self.assertEqual(len(cat['metrics']), 8)
        result = self.client.post('/api/query', json={'metrics': ['ai_share'], 'group_by': ['repository']})
        self.assertEqual(result.status_code, 200)
        body = result.json()
        self.assertEqual(body['engine'], 'MetricFlow')
        self.assertEqual(len(body['rows']), 6)
        self.assertIn('NULLIF', body['sql'])
        self.assertIn('fct_commits', body['sql'])

    def test_09_dashboard_filters_and_counts(self):
        response = self.client.get('/api/dashboard', params={'organization': 'TV개발', 'period': '7d', 'group_by': 'repository'})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(len(body['breakdown']['rows']), 2)
        self.assertEqual(body['summary']['rows'][0]['commit_loc'], sum(r['commit_loc'] for r in body['trend']['rows']))
        self.assertEqual(self.client.get('/api/dashboard?organization=unknown').status_code, 422)

    def test_10_ratio_unchanged_when_queried_alone(self):
        ratio = query(MetricRequest(metrics=['ai_share']))['rows'][0]['ai_share']
        self.assertAlmostEqual(ratio, self.full['ai_share'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
