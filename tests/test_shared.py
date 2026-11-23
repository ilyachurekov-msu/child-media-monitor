import csv
import runpy
from pathlib import Path
from app.identity import source_id


def test_mapping_and_shared_identity():
    old = list(csv.DictReader(Path('contracts/regions.csv').open(encoding='utf-8')))
    canonical = list(csv.DictReader(Path('shared-contracts/regions.csv').open(encoding='utf-8')))
    mapping = list(csv.DictReader(Path('shared-contracts/region-mapping.csv').open(encoding='utf-8')))
    assert {r['old_region_id'] for r in mapping} == {r['region_id'] for r in old}
    assert len({r['region_id'] for r in mapping}) == len(mapping)
    assert {r['region_id'] for r in mapping} <= {r['region_id'] for r in canonical}
    shared = runpy.run_path('shared-contracts/identity.py')
    assert shared['source_id']('rss', 'https://example.org/feed') == source_id('rss', 'https://example.org/feed')
