import json
import csv
import logging
import time
import tempfile
from datetime import timedelta
from pathlib import Path
from sqlalchemy import select, delete, text, or_
from sqlalchemy.dialects.postgresql import insert
from app.db import Session, engine
from app.config import settings
from app.models import *
from app.identity import post_id, text_hash
from app.collectors.rss import fetch, allowed, parse_feed
from app.nlp.pipeline import classify, language, geography, embed, sentiment, RULE_VERSION, GEO_VERSION
from app.analytics.service import update_alerts
from app.privacy.service import check_post

log = logging.getLogger(__name__)


def collect(source_id):
    with Session() as db:
        source = db.get(Source, source_id)
        config = db.get(SourceConfig, source_id)
        run = Run(source_id=source_id)
        db.add(run)
        db.commit()
        try:
            if not allowed(source.url): raise ValueError('robots.txt disallows feed')
            headers = {}
            if config.etag: headers['If-None-Match'] = config.etag
            if config.last_modified: headers['If-Modified-Since'] = config.last_modified
            code, response_headers, body = fetch(source.url, headers)
            entries = [] if code == 304 else parse_feed(body)
            for item in entries:
                with db.begin_nested():
                    pid = post_id(source_id, item['external_id'])
                    digest = text_hash(item['title'] + '\n' + item['text'])
                    old = db.get(Post, pid)
                    if old:
                        if old.text_hash != digest:
                            for key, value in item.items(): setattr(old, key, value)
                            old.text_hash, old.processing_status = digest, 'pending'
                            db.execute(delete(Embedding).where(Embedding.post_id == pid))
                            check_post(db, old)
                    else:
                        db.execute(insert(Post).values(post_id=pid, source_id=source_id, source_type='rss',
                                   text_hash=digest, **item).on_conflict_do_nothing())
                        run.inserted += 1
                        check_post(db, db.get(Post, pid))
            config.etag = response_headers.get('etag', config.etag)
            config.last_modified = response_headers.get('last-modified', config.last_modified)
            config.failures = 0
            run.received, run.status = len(entries), 'success'
        except Exception as exc:
            db.rollback()
            run = db.get(Run, run.run_id)
            config = db.get(SourceConfig, source_id)
            config.failures += 1
            run.status, run.errors = 'failed', [type(exc).__name__]
            log.error('Collection failed for %s: %s', source_id, type(exc).__name__)
        config.next_attempt = now() + timedelta(seconds=min(86400, settings.collect_interval * 2 ** min(config.failures, 6)))
        run.finished_at = now()
        db.commit()


def process_batch():
    aliases = json.loads(Path('contracts/region_aliases.json').read_text(encoding='utf-8'))
    mapping = {r['old_region_id']: r['region_id'] for r in csv.DictReader(Path('shared-contracts/region-mapping.csv').open(encoding='utf-8'))}
    aliases = {mapping.get(k, k): v for k, v in aliases.items()}
    with Session() as db:
        ids = db.scalars(select(Post.post_id).where(Post.processing_status == 'pending').limit(100)).all()
    for pid in ids:
        try:
            with Session.begin() as db:
                post = db.get(Post, pid)
                check = check_post(db, post)
                if check.status != 'allowed':
                    db.execute(delete(Embedding).where(Embedding.post_id == pid))
                    post.processing_status = 'privacy_held'
                    continue
                content = (post.title or '') + '\n' + post.text
                post.language = language(content)
                for model in (PostTopic, PostRegion):
                    db.execute(delete(model).where(model.post_id == pid, model.review_status == 'pending'))
                confirmed_topics = set(db.scalars(select(PostTopic.topic_id).where(PostTopic.post_id == pid)))
                for topic, score in classify(content):
                    if topic not in confirmed_topics:
                        db.add(PostTopic(post_id=pid, topic_id=topic, confidence=score, model_version=RULE_VERSION))
                confirmed_regions = set(db.scalars(select(PostRegion.region_id).where(PostRegion.post_id == pid)))
                for region, score, evidence in geography(content, aliases):
                    if region not in confirmed_regions:
                        db.add(PostRegion(post_id=pid, region_id=region, confidence=score, evidence=evidence, detection_method=GEO_VERSION))
                if settings.nlp_enabled:
                    vector = embed(check.safe_title + '\n' + check.safe_text)
                    db.merge(Embedding(post_id=pid, model='multilingual-e5-small', model_version=settings.model_version, vector=vector))
                result = sentiment(content)
                if result:
                    db.execute(delete(Sentiment).where(Sentiment.post_id == pid, Sentiment.model_version == settings.sentiment_version))
                    db.add(Sentiment(post_id=pid, **result))
                post.processing_status = 'processed' if settings.nlp_enabled else 'baseline_only'
        except Exception as exc:
            with Session.begin() as db:
                db.get(Post, pid).processing_status = 'failed'
                db.add(ProcessingError(post_id=pid, stage='nlp', error=type(exc).__name__))
            log.error('Processing failed for %s: %s', pid, type(exc).__name__)


def tick():
    # A session advisory lock prevents overlapping workers; released even after process death.
    with engine.connect() as lock:
        if not lock.scalar(text('SELECT pg_try_advisory_lock(913041)')): return
        try:
            with Session() as db:
                sources = db.scalars(select(SourceConfig.source_id).where(SourceConfig.enabled.is_(True), SourceConfig.next_attempt <= now())).all()
            if settings.collection_enabled:
                for sid in sources: collect(sid)
            process_batch()
            with Session.begin() as db:
                update_alerts(db)
                db.execute(delete(Post).where(Post.collected_at < now() - timedelta(days=settings.retention_days)))
                db.execute(delete(Run).where(Run.started_at < now() - timedelta(days=settings.retention_days)))
                db.execute(delete(ProcessingError).where(ProcessingError.created_at < now() - timedelta(days=settings.retention_days)))
        finally:
            lock.execute(text('SELECT pg_advisory_unlock(913041)'))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            tick()
            Path(tempfile.gettempdir(), 'worker-heartbeat').touch()
        except Exception as exc: log.error('Worker tick failed: %s', type(exc).__name__)
        time.sleep(10)
