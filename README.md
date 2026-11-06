# AI LOC · Commit LOC — MetricFlow 실행 샘플

가상 커밋 데이터로 **dbt 정제 → MetricFlow 지표 정의 → DuckDB 실행 → REST API → 조회 화면**을 구현한 샘플입니다. 수치는 실제 회사 실적이 아닙니다.

## 바로 보기

`output/MetricFlow_AI_LOC_Demo.html`을 브라우저로 엽니다. 별도 설치 없이 조직 4개 선택지(전체 포함), 기간 3개, 집계 기준 3개를 전환하고 결과·정의 YAML·실제 생성 SQL을 확인할 수 있습니다. CSV 다운로드도 가능합니다.

이 HTML은 **실제 MetricFlow가 실행한 60개 조회 결과를 내장한 미리보기**입니다. 브라우저에서 MetricFlow가 실행되지는 않습니다. 임의 조건으로 새로 조회하거나 지표 정의를 바꾸려면 아래 로컬 API를 실행합니다.

## 실행

검증 환경: Python 3.12.14 / dbt Core 1.12.6 / dbt-metricflow 0.15.0 / MetricFlow 0.213.0 / dbt-duckdb 1.11.1 / DuckDB 2.0.0. Python 3.12를 권장합니다. 첫 설치 때 패키지 다운로드가 필요하며 dbt Cloud 계정이나 별도 DB 서버는 필요하지 않습니다.

저장소를 복제하고 프로젝트 디렉터리로 이동합니다. ZIP으로 받았다면 압축을 풀고 이 README가 있는 디렉터리에서 실행합니다.

```bash
git clone https://github.com/rby011/metricflow-ai-loc.git
cd metricflow-ai-loc
```

비공개 저장소이므로 복제할 때 GitHub 계정 인증이 필요합니다.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python demo.py setup
python demo.py serve
```

브라우저: <http://127.0.0.1:8000> · API 문서: <http://127.0.0.1:8000/docs>

Windows PowerShell에서는 첫 두 줄 대신 다음을 사용합니다. 이후 `python -m pip ...`부터 동일합니다.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

서버 종료: `Ctrl+C`. 8000번 포트가 사용 중이면 `python demo.py serve --port 8001`.

## 지표의 의미

| 지표 | MetricFlow 유형 | 계산 / 해석 |
|---|---|---|
| `commit_loc` | simple | 커밋에 추가된 코드 행의 합계. 삭제 행 미포함 |
| `ai_loc` | simple | 추가 행 중 AI 작성으로 식별된 행의 합계 |
| `human_loc` | derived | `commit_loc - ai_loc` |
| `ai_share` | ratio | `ai_loc / commit_loc`, 집계된 합계끼리 나눔 |
| `commit_count` | simple | `(repository, commit_sha)` 조합의 고유 커밋 수 |
| `loc_per_commit` | ratio | `commit_loc / commit_count` |
| `deleted_loc` | simple | 삭제 코드 행의 합계 |
| `churn_loc` | derived | 추가 + 삭제 코드 행 |

`ai_share`는 0~1의 값이며 화면에서만 %로 표시합니다. 커밋별·조직별 비율을 단순 평균하지 않습니다. 분모가 0인 비율은 NULL이며 화면에는 `—`로 표시합니다. 원천이 없는 기간의 합계는 NULL, 커밋 수는 0입니다.

샘플의 AI LOC는 **커밋에 반영된 AI 추가 행**입니다. AI가 생성만 하고 버린 행은 포함하지 않습니다. Commit LOC는 코드 재고나 순증분이 아니며, 서로 다른 커밋에서 다시 작성된 행은 다시 집계됩니다. 커밋 단계의 기여를 측정하므로 제품 탑재율·공수 절감률로 해석하지 않습니다.

## 샘플 데이터

- 2026-10-05~2026-11-01, 28일, 가상 조직 3개, 저장소 6개.
- 도구는 Claude Code / Cline / Human. 실제 조직·도구 성능을 비교한 실험이 아닙니다.
- 원천 이벤트 470건: 정상 커밋 463건 + 중복 수집 5건 + merge 1건 + bot 1건.
- 재수집은 `(repository, commit_sha)`별 최신 `ingested_at` 한 건을 선택합니다.
- merge·bot을 제외합니다. 날짜는 커밋 시각을 `Asia/Seoul`로 변환하여 집계합니다.
- `added_loc`, `deleted_loc`, `ai_added_loc`는 수집기가 코드 파일 기준으로 정규화해 보낸 값이라는 가정입니다. Git diff에서 주석·공백·vendor·생성 파일을 제외하는 수집기는 구현 범위에 포함되지 않습니다.
- 모든 추가 행의 AI/Human 귀속을 안다고 가정합니다. 실데이터의 미식별 행을 Human으로 자동 처리하면 안 됩니다.
- 커밋당 대표 도구 하나를 사용합니다. 여러 도구가 함께 작성한 커밋은 별도의 행 단위 귀속 모델이 필요합니다.
- `zeroadded001`은 11월 1일 23:59 KST의 삭제 전용 커밋으로, 0분모와 종료일 포함을 검증합니다.

## 실행 결과

전체 기간, 전체 조직의 MetricFlow 조회 결과입니다.

| 지표 | 값 |
|---|---:|
| Commit LOC | 118,571 |
| AI LOC | 65,417 |
| Human LOC | 53,154 |
| AI 비중 | 55.1711632693% |
| Commit 수 | 463 |
| LOC / Commit | 256.0928725702 |
| Deleted LOC | 30,727 |
| 변경 LOC | 149,298 |

| 조직 | Commit LOC | AI LOC | AI 비중 | Commit 수 |
|---|---:|---:|---:|---:|
| 모바일개발 | 40,160 | 22,669 | 56.45% | 152 |
| TV개발 | 38,752 | 17,129 | 44.20% | 149 |
| 공통플랫폼 | 39,659 | 25,619 | 64.60% | 162 |

## 직접 조회

CLI에서는 실제 MetricFlow 차원 이름을 사용합니다. 반드시 프로젝트 루트에서 실행합니다.

```bash
mf list metrics
mf query --metrics commit_loc,ai_loc,ai_share --group-by commit__organization
mf query --metrics ai_loc,commit_loc --group-by metric_time__week
mf query --metrics ai_share --group-by commit__repository --explain
mf query --metrics ai_loc,commit_loc,ai_share --start-time 2026-10-26 --end-time 2026-11-01 --where "{{ Dimension('commit__organization') }} = '모바일개발'"
```

REST API는 편의상 `organization`, `repository`, `agent`, `day`, `week`, `commit_sha`라는 짧은 이름을 받습니다. 이것을 MetricFlow 차원 이름으로 매핑하며 계산식은 만들지 않습니다.

```bash
curl http://127.0.0.1:8000/api/query \
  -H 'Content-Type: application/json' \
  -d '{"metrics":["commit_loc","ai_loc","ai_share"],"group_by":["repository"],"start":"2026-10-26","end":"2026-11-01","filters":{"organization":"모바일개발"}}'
```

응답의 `rows`에 결과가, `sql`에 MetricFlow가 생성한 SQL이 담깁니다. `definition_sha256`는 사용한 지표 파일의 해시입니다. `elapsed_ms`는 엔진 준비 이후 조회에 걸린 시간이며 벤치마크가 아닙니다.

요청 제한: 등록된 지표·차원·필터 값만 허용, 최대 2,000행, 조회 범위 최대 367일. 자유 SQL이나 임의 Jinja 표현식을 API 입력으로 받지 않습니다.

## 지표 변경

1. `models/metrics.yml` 수정. dbt 1.12+ YAML 문법을 사용합니다.
2. 서버를 종료한 후 `dbt parse --profiles-dir .` 실행. SQL 모델·원천 데이터까지 바꿨다면 `python demo.py setup` 대신 변경 데이터에 맞게 `dbt build --profiles-dir .`를 실행합니다. `setup`은 가상 CSV를 다시 생성합니다.
3. `python demo.py serve`로 재시작합니다. Python 어댑터는 시작 때 지표 정의·필터 목록을 읽습니다.
4. 오프라인 미리보기도 갱신하려면 서버를 종료하고 `python demo.py export`.

예를 들어 AI 비중의 분자·분모를 변경해도 화면에 계산식을 중복 구현할 필요가 없습니다. 새 지표의 자유 조회는 `/api/query`로 가능하며, 기본 화면의 고정 KPI 항목을 교체하려면 `DASH_METRICS`와 해당 표시 요소도 수정합니다.

## 파일 구성

| 파일 | 역할 |
|---|---|
| `seeds/raw_commits.csv` | 가상 원천 이벤트 |
| `models/fct_commits.sql` | 중복 제거, 제외 규칙, KST 날짜 정규화 |
| `models/metrics.yml` | 의미 모델과 8개 지표의 단일 정의 |
| `models/time_spine.sql` | 일 단위 날짜 테이블 |
| `semantic_service.py` | MetricFlow 엔진 호출, 요청 검증, 결과·SQL 반환 |
| `app.py` | FastAPI 및 HTML 제공 |
| `web/index.html` | 로컬 API에 연결하는 조회 화면 |
| `demo.py` | setup / serve / check / export 실행 도우미 |
| `checks/test_metrics.py` | 지표 정확성·필터·경계조건·API 검증 |
| `output/MetricFlow_AI_LOC_Demo.html` | 설치 없이 보는 실제 결과 미리보기 |
| `output/metricflow_results.json` | 60개 실제 MetricFlow 조회 결과와 SQL |

## 검증

```bash
python demo.py setup    # dbt 모델 생성 및 데이터 테스트 9개
python demo.py check    # 실제 MetricFlow/API 검증 10개
python demo.py export   # 12개 조건 × 5개 조회 = 60개 결과 저장
```

합계·중복 제외, 합계 기반 비율, 조직/저장소/날짜 필터, 23:59 KST 커밋, 0분모, 빈 기간, 잘못된 API 요청, 단독/복합 지표 결과 일치를 검증합니다.

검증 기록: `output/validation.json`. dbt 테스트 9개, 실제 MetricFlow/API 검증 10개와 HTTP 호출이 통과했습니다. 화면 스크립트는 DOM 환경에서 36개 필터 조합·탭·복사·CSV 생성을 확인했습니다. 실행 환경의 제한으로 실제 브라우저 시각 검수는 완료하지 못했습니다.

이 API는 로컬 데모용이며 인증·조직별 접근 권한·운영 캐시·수집 스케줄러를 포함하지 않습니다. 서버는 기본적으로 `127.0.0.1`에만 바인딩합니다. MetricFlow의 `CLIConfiguration` Python 어댑터는 내부 인터페이스이므로 패키지 버전을 고정했습니다. 버전 변경 시 검증을 다시 실행해야 합니다.

## 공식 문서

- [MetricFlow 명령과 자체 실행](https://docs.getdbt.com/docs/build/metricflow-commands)
- [Semantic model YAML](https://docs.getdbt.com/docs/build/semantic-models)
- [Ratio metric](https://docs.getdbt.com/docs/build/ratio)
- [Derived metric](https://docs.getdbt.com/docs/build/derived)
- [DuckDB adapter](https://github.com/duckdb/dbt-duckdb)

화면·API·테스트는 이 샘플을 위해 작성했습니다. 외부 패키지는 각 패키지의 라이선스를 따릅니다.
