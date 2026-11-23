"""One-time packaging from the existing sibling contract, never changes that project."""
import csv
import json
from pathlib import Path
from app.identity import source_id
from scripts.seed import TOPICS

target = Path('shared-contracts')
target.mkdir(exist_ok=True)
old = list(csv.DictReader(Path('contracts/regions.csv').open(encoding='utf-8')))
canonical = list(csv.DictReader(Path('../contracts/regions.csv').open(encoding='utf-8')))
(target / 'regions.csv').write_text(Path('../contracts/regions.csv').read_text(encoding='utf-8'), encoding='utf-8')
def normalize(name):
    import re
    return re.sub(r'[^а-яё]', '', name.lower()).replace('республика', '').replace('кузбасс', '').replace('алания', '').replace('югра', '').replace('якутия', '')
lookup = {normalize(r['name']): r['region_id'] for r in canonical}
mapping = []
for row in old:
    key = normalize(row['name'])
    code = lookup.get(key)
    if not code: raise ValueError('No explicit mapping: ' + row['name'])
    mapping.append({'old_region_id': row['region_id'], 'region_id': code, 'name': row['name']})
with (target / 'region-mapping.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['old_region_id', 'region_id', 'name']); w.writeheader(); w.writerows(mapping)
with (target / 'topics.csv').open('w', encoding='utf-8', newline='') as f:
    w = csv.writer(f); w.writerow(['topic_id','name','parent_topic_id'])
    for tid, name in TOPICS.items(): w.writerow([tid,name,''])
(target / 'identity.py').write_text(Path('app/identity.py').read_text(encoding='utf-8'), encoding='utf-8')
(target / 'VERSION').write_text('1.0.0\n', encoding='utf-8')
for entity, fields in {
    'region': {'region_id':'string','name':'string','federal_district':['string','null'],'okato_code':['string','null'],'oktmo_code':['string','null'],'valid_from':'string','valid_to':['string','null']},
    'topic': {'topic_id':'string','name':'string','parent_topic_id':['string','null']},
    'source': {'source_id':'string','source_type':'string','name':'string','url':['string','null'],'publisher':['string','null'],'created_at':'string'},
}.items():
    schema = {'$schema':'https://json-schema.org/draft/2020-12/schema', 'title':entity,'type':'object','additionalProperties':False,
              'required':list(fields), 'properties':{k:{'type':v} for k,v in fields.items()}}
    (target / (entity + '.schema.json')).write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding='utf-8')
