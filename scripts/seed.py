import csv
from datetime import date
from pathlib import Path
from sqlalchemy.dialects.postgresql import insert
from app.db import Session
from app.models import Region, Topic, Source, SourceConfig
from app.identity import source_id

TOPICS = dict(demography='Демография', family='Семья', education='Образование', healthcare='Здравоохранение',
              social_support='Социальная поддержка', orphanhood='Сиротство', safety='Безопасность', infrastructure='Инфраструктура')
SOURCES = [('ТАСС', 'https://tass.ru/rss/v2.xml'), ('Российская газета', 'https://rg.ru/xml/index.xml'),
           ('РИА Новости', 'https://ria.ru/export/rss2/archive/index.xml')]


def main():
    with Session.begin() as db:
        for row in csv.DictReader(Path('shared-contracts/regions.csv').open(encoding='utf-8')):
            row = {k: v or None for k, v in row.items()}
            row['federal_district'] = row['federal_district'] or ''
            row['valid_from'] = date.fromisoformat(row['valid_from'])
            row['valid_to'] = date.fromisoformat(row['valid_to']) if row['valid_to'] else None
            db.execute(insert(Region).values(**row).on_conflict_do_nothing())
        for tid, name in TOPICS.items():
            db.execute(insert(Topic).values(topic_id=tid, name=name).on_conflict_do_nothing())
        for name, url in SOURCES:
            sid = source_id('rss', url)
            db.execute(insert(Source).values(source_id=sid, source_type='rss', name=name, url=url, publisher=name).on_conflict_do_nothing())
            db.execute(insert(SourceConfig).values(source_id=sid).on_conflict_do_nothing())


if __name__ == '__main__': main()
