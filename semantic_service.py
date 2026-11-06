"""Thin, validated Python adapter to the REAL MetricFlow engine.

No metric arithmetic or aggregation SQL lives in this API layer. The dbt-metricflow
CLIConfiguration helper is version-pinned because it is not a stable public API.
"""
from __future__ import annotations

import csv
import hashlib
import math
import threading
import time
from datetime import date, datetime, time as dt_time
from decimal import Decimal
from functools import lru_cache
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

ROOT = Path(__file__).resolve().parent
METRICS_YAML = ROOT / 'models/metrics.yml'
SOURCE = yaml.safe_load(METRICS_YAML.read_text(encoding='utf-8'))
METRIC_DEFS = [m for model in SOURCE['models'] for m in model.get('metrics', [])] + SOURCE['metrics']
METRIC_NAMES = [m['name'] for m in METRIC_DEFS]
DASH_METRICS = ['commit_loc', 'ai_loc', 'human_loc', 'ai_share', 'commit_count', 'loc_per_commit', 'deleted_loc', 'churn_loc']
DIMENSIONS = {'organization': 'commit__organization', 'repository': 'commit__repository',
              'agent': 'commit__agent', 'day': 'metric_time__day', 'week': 'metric_time__week',
              'commit_sha': 'commit__commit_sha'}
PERIODS = {'28d': ('2026-10-05', '2026-11-01'), '14d': ('2026-10-19', '2026-11-01'),
           '7d': ('2026-10-26', '2026-11-01')}
LOCK = threading.RLock()
_config = None

with (ROOT / 'seeds/raw_commits.csv').open(encoding='utf-8') as f:
    _source_rows = list(csv.DictReader(f))
FILTER_VALUES = {key: sorted({row[key] for row in _source_rows})
                 for key in ('organization', 'repository', 'agent', 'commit_sha')}

class MetricRequest(BaseModel):
    metrics: list[str] = Field(default_factory=lambda: DASH_METRICS.copy(), min_length=1, max_length=8)
    group_by: list[Literal['organization', 'repository', 'agent', 'day', 'week', 'commit_sha']] = Field(default_factory=list, max_length=4)
    start: date = date(2026, 10, 5)
    end: date = date(2026, 11, 1)
    filters: dict[str, str] = Field(default_factory=dict)
    limit: int = Field(default=2000, ge=1, le=2000)

    @model_validator(mode='after')
    def validate_request(self):
        if len(set(self.metrics)) != len(self.metrics) or not set(self.metrics).issubset(METRIC_NAMES):
            raise ValueError('등록된 지표를 중복 없이 선택하세요.')
        if len(set(self.group_by)) != len(self.group_by):
            raise ValueError('조회 기준이 중복되었습니다.')
        if self.start > self.end or (self.end - self.start).days > 366:
            raise ValueError('시작일~종료일은 순서가 올바르고 367일 이내여야 합니다.')
        for name, value in self.filters.items():
            if name not in FILTER_VALUES or value not in FILTER_VALUES[name]:
                raise ValueError(f'등록되지 않은 필터: {name}')
        return self

def config():
    global _config
    if _config is None:
        if not (ROOT / 'target/semantic_manifest.json').exists():
            raise RuntimeError('먼저 python demo.py setup을 실행하세요.')
        from dbt_metricflow.cli.cli_configuration import CLIConfiguration
        _config = CLIConfiguration()
        _config.setup(dbt_profiles_path=ROOT, dbt_project_path=ROOT)
    return _config

def scalar(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value

def catalog():
    return {
        'metrics': METRIC_DEFS, 'dimensions': DIMENSIONS,
        'filters': {k: v for k, v in FILTER_VALUES.items() if k != 'commit_sha'},
        'periods': PERIODS, 'definition_yaml': METRICS_YAML.read_text(encoding='utf-8'),
        'definition_sha256': hashlib.sha256(METRICS_YAML.read_bytes()).hexdigest(),
        'versions': {p: version(p) for p in ('dbt-core', 'dbt-metricflow', 'metricflow', 'dbt-duckdb', 'duckdb')},
        'data_note': '재현 가능한 가상 데이터 · 2026-10-05~11-01 · Asia/Seoul · 실제 회사 실적 아님',
    }

def query(request: MetricRequest):
    # Bind parameters are not supported by this dbt adapter. Both the key and
    # value are allowlisted above; escaping is still applied as a second guard.
    from metricflow.engine.metricflow_engine import MetricFlowQueryRequest
    constraints = []
    for name, value in sorted(request.filters.items()):
        escaped = value.replace("'", "''")
        constraints.append("{{ Dimension('" + DIMENSIONS[name] + "') }} = '" + escaped + "'")
    groups = [DIMENSIONS[g] for g in request.group_by]
    mf_request = MetricFlowQueryRequest.create(
        metric_names=request.metrics,
        group_by_names=groups,
        time_constraint_start=datetime.combine(request.start, dt_time.min),
        time_constraint_end=datetime.combine(request.end, dt_time.min),
        where_constraints=constraints or None,
        order_by_names=groups or None,
        limit=request.limit,
    )
    # A single worker / serialized engine keeps dbt adapter state predictable.
    with LOCK:
        engine = config().mf
        started = time.perf_counter()
        result = engine.query(mf_request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    table = result.result_df
    rows = [] if table is None else [dict(zip(table.column_names, [scalar(v) for v in r])) for r in table.rows]
    return {
        'engine': 'MetricFlow', 'request': request.model_dump(mode='json'),
        'columns': list(table.column_names) if table else [], 'rows': rows,
        'sql': result.sql, 'elapsed_ms': elapsed_ms,
        'definition_sha256': hashlib.sha256(METRICS_YAML.read_bytes()).hexdigest(),
    }

def dashboard(organization='all', period='28d', group_by='organization'):
    if period not in PERIODS or group_by not in ('organization', 'repository', 'agent'):
        raise ValueError('지원하지 않는 기간 또는 조회 기준입니다.')
    filters = {} if organization == 'all' else {'organization': organization}
    start, end = PERIODS[period]
    base = dict(metrics=DASH_METRICS, start=start, end=end, filters=filters)
    return {
        'summary': query(MetricRequest(**base)),
        'trend': query(MetricRequest(**base, group_by=['day'])),
        'breakdown': query(MetricRequest(**base, group_by=[group_by])),
    }
