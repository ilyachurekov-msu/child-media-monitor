"""Adopt sibling numeric region IDs, retaining legacy dictionary rows for traceability."""
import csv
from pathlib import Path
from datetime import date
import sqlalchemy as sa
from alembic import op

revision = '0003'
down_revision = '0002'


def upgrade():
    db = op.get_bind()
    rows = list(csv.DictReader(Path('contracts/regions.csv').open(encoding='utf-8')))
    rows += list(csv.DictReader(Path('shared-contracts/regions.csv').open(encoding='utf-8')))
    for row in rows:
        values = {k: v or None for k, v in row.items()}
        values['valid_from'] = date.fromisoformat(values['valid_from'])
        values['valid_to'] = date.fromisoformat(values['valid_to']) if values['valid_to'] else None
        values['federal_district'] = values['federal_district'] or ''
        db.execute(sa.text('INSERT INTO core.regions (region_id,name,federal_district,okato_code,oktmo_code,valid_from,valid_to) VALUES (:region_id,:name,:federal_district,:okato_code,:oktmo_code,:valid_from,:valid_to) ON CONFLICT (region_id) DO NOTHING'), values)
    for row in csv.DictReader(Path('shared-contracts/region-mapping.csv').open(encoding='utf-8')):
        # Existing numeric rows are not overwritten. Preserve old evidence/reviews.
        db.execute(sa.text('UPDATE media.post_regions SET region_id=:region_id WHERE region_id=:old_region_id'), row)


def downgrade():
    db = op.get_bind()
    for row in csv.DictReader(Path('shared-contracts/region-mapping.csv').open(encoding='utf-8')):
        db.execute(sa.text('UPDATE media.post_regions SET region_id=:old_region_id WHERE region_id=:region_id'), row)
    # Retain shared rows to avoid deleting another module's dictionary.
