"""Self-hosted demonstration API, intended for localhost only."""
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from semantic_service import MetricRequest, catalog, dashboard, query

app = FastAPI(title='AI Code Metrics · MetricFlow', version='1.0.0')
ROOT = Path(__file__).resolve().parent

@app.get('/', include_in_schema=False)
def index():
    return FileResponse(ROOT / 'web/index.html')

@app.get('/api/catalog')
def get_catalog():
    return catalog()

@app.get('/api/definition', response_class=PlainTextResponse)
def definition():
    return (ROOT / 'models/metrics.yml').read_text(encoding='utf-8')

@app.post('/api/query')
def metric_query(request: MetricRequest):
    try:
        return query(request)
    except Exception as exc:
        logging.exception('MetricFlow query failed')
        raise HTTPException(500, 'MetricFlow 조회에 실패했습니다. 서버 로그와 dbt build 상태를 확인하세요.') from exc

@app.get('/api/dashboard')
def get_dashboard(organization: str = 'all', period: str = '28d', group_by: str = 'organization'):
    try:
        return dashboard(organization, period, group_by)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        logging.exception('MetricFlow dashboard failed')
        raise HTTPException(500, 'MetricFlow 조회에 실패했습니다. 서버 로그를 확인하세요.') from exc
