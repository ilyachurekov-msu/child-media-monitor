"""Live diagnostics, no DB writes. Does not bypass robots or access failures."""
import json
from pathlib import Path
from scripts.seed import SOURCES
from app.collectors.rss import allowed, fetch, parse_feed

result = []
for name, url in SOURCES:
    try:
        if not allowed(url): raise ValueError('robots.txt disallows access')
        code, _, body = fetch(url)
        rows = parse_feed(body)
        result.append(dict(name=name, url=url, status=code, entries=len(rows), success=bool(rows)))
    except Exception as exc:
        result.append(dict(name=name, url=url, success=False, error=str(exc)[:300]))
Path('docs/source-check.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=True, indent=2))
