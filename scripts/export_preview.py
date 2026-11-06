"""Export real engine results. Browser only formats these rows, never aggregates."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_service import MetricRequest, PERIODS, DASH_METRICS, catalog, query

def export():
    cat = catalog()
    bundle = {'catalog': cat, 'scenarios': {}, 'kind': 'executed_metricflow_snapshot'}
    for org in ['all', *cat['filters']['organization']]:
        for period, (start, end) in PERIODS.items():
            base = dict(metrics=DASH_METRICS, start=start, end=end,
                        filters={} if org == 'all' else {'organization': org})
            bundle['scenarios'][org + '|' + period] = {
                'summary': query(MetricRequest(**base)),
                'trend': query(MetricRequest(**base, group_by=['day'])),
                'breakdowns': {g: query(MetricRequest(**base, group_by=[g]))
                               for g in ('organization', 'repository', 'agent')},
            }
            print(f'Exported {org} / {period}', flush=True)
    dest = ROOT / 'output'
    dest.mkdir(exist_ok=True)
    payload = json.dumps(bundle, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    (dest / 'metricflow_results.json').write_text(payload, encoding='utf-8')
    html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
    html = html.replace('/*__SNAPSHOT__*/', 'window.DEMO_SNAPSHOT=' + payload.replace('<', '\\u003c') + ';')
    (dest / 'MetricFlow_AI_LOC_Demo.html').write_text(html, encoding='utf-8')
    print('Saved output/MetricFlow_AI_LOC_Demo.html and metricflow_results.json')

if __name__ == '__main__':
    export()
