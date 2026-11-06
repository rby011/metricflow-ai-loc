"""Deterministic, synthetic commit / attribution events. No real company data."""
import csv
import hashlib
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['event_id', 'repository', 'commit_sha', 'organization', 'agent', 'author_id',
          'committed_at', 'ingested_at', 'added_loc', 'deleted_loc', 'ai_added_loc', 'is_merge', 'is_bot']
REPOS = [
    ('모바일개발', 'mobile-core', 0.62), ('모바일개발', 'mobile-ui', 0.55),
    ('TV개발', 'tv-platform', 0.43), ('TV개발', 'tv-app', 0.48),
    ('공통플랫폼', 'platform-api', 0.68), ('공통플랫폼', 'developer-tools', 0.72),
]

def generate():
    rng = random.Random(20261106)
    rows = []
    start = datetime(2026, 10, 5, tzinfo=timezone(timedelta(hours=9)))
    for d in range(28):
        for org, repo, base in REPOS:
            for j in range(rng.randint(2, 5) if (start + timedelta(days=d)).weekday() < 5 else 1):
                ts = start + timedelta(days=d, hours=9 + j * 2, minutes=rng.randrange(60))
                agent = rng.choices(['Claude Code', 'Cline', 'Human'], [0.65, 0.20, 0.15])[0]
                added = rng.randint(18, 480)
                share = min(0.94, max(0.10, base + 0.10 * d / 27 + rng.uniform(-0.18, 0.18)))
                ai = round(added * share) if agent != 'Human' else 0
                sha = hashlib.sha256(f'{repo}-{d}-{j}'.encode()).hexdigest()[:12]
                rows.append(dict(zip(FIELDS, [f'evt-{len(rows)+1:04d}', repo, sha, org, agent,
                    f'dev-{rng.randrange(1, 25):02d}', ts.isoformat(),
                    (ts + timedelta(minutes=5)).isoformat(), added, rng.randint(0, 130), ai, False, False])))
    # A deletion-only commit tests denominator=0, with a known stable SHA.
    ts = start + timedelta(days=27, hours=23, minutes=59)
    rows.append(dict(zip(FIELDS, ['edge-zero', 'mobile-core', 'zeroadded001', '모바일개발', 'Human',
        'dev-01', ts.isoformat(), (ts + timedelta(minutes=1)).isoformat(), 0, 75, 0, False, False])))
    # Same raw event may be delivered twice: these must not inflate metrics.
    for i in (0, 17, 83, 151, 233):
        duplicate = dict(rows[i])
        duplicate['event_id'] += '-retry'
        duplicate['ingested_at'] = (datetime.fromisoformat(duplicate['ingested_at']) + timedelta(hours=1)).isoformat()
        rows.append(duplicate)
    for label in ('merge', 'bot'):
        excluded = dict(rows[1])
        excluded.update(event_id=f'excluded-{label}', commit_sha=f'excluded{label}',
                        added_loc=9000, ai_added_loc=8000, is_merge=label == 'merge', is_bot=label == 'bot')
        rows.append(excluded)
    (ROOT / 'seeds').mkdir(exist_ok=True)
    (ROOT / 'data').mkdir(exist_ok=True)
    with (ROOT / 'seeds/raw_commits.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f'Wrote {len(rows)} synthetic raw events; 5 retries, 1 merge, 1 bot included.')

if __name__ == '__main__':
    generate()
