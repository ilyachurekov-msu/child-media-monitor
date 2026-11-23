from datetime import datetime, timedelta
from uuid import UUID
import secrets
import csv
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, Query, Header
from fastapi.responses import JSONResponse
from sqlalchemy import select, func, text, exists, update
from sqlalchemy.orm import Session as DB
from sqlalchemy.exc import SQLAlchemyError
from app.db import session
from app.models import *
from uuid import UUID
from app.schemas import PostOut, Page, Correction
from app.config import settings
from app.nlp.pipeline import embed
from app.privacy import VERSION, safe_link
from pydantic import BaseModel, Field

app = FastAPI(title='Мониторинг информационного поля', version='1.0.0')
PREFIX = '/api/v1/media'


def admin(authorization: str = Header(default='')):
    if not settings.admin_token or not secrets.compare_digest(authorization, 'Bearer ' + settings.admin_token):
        raise HTTPException(401, 'Нужен токен аналитика')


@app.exception_handler(SQLAlchemyError)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'detail': 'База данных временно недоступна'})


def row_dict(row):
    return {c.name: getattr(row, c.name) for c in row.__table__.columns}


def serialize(db, post):
    check = db.get(PrivacyCheck, post.post_id)
    if not check or check.status != 'allowed' or check.input_hash != post.text_hash or check.method_version != VERSION:
        raise HTTPException(404, 'Публикация недоступна')
    data = row_dict(post)
    data.update(title=check.safe_title, text=check.safe_text[:240], url=safe_link(post.url) or '')
    result = PostOut.model_validate(data)
    for field, model in [('topics', PostTopic), ('regions', PostRegion), ('sentiment', Sentiment)]:
        setattr(result, field, [row_dict(r) for r in db.scalars(select(model).where(model.post_id == post.post_id))])
    return result


def visible():
    return exists().where(PrivacyCheck.post_id == Post.post_id, PrivacyCheck.status == 'allowed',
                          PrivacyCheck.input_hash == Post.text_hash, PrivacyCheck.method_version == VERSION).correlate(Post)


@app.get('/health')
def health(db: DB = Depends(session)):
    db.execute(text('SELECT 1'))
    return {'status': 'ok', 'contract': '1.0.0'}


@app.get(PREFIX + '/posts', response_model=Page)
def posts(region_id: str | None = None, topic_id: str | None = None, source_id: UUID | None = None,
          since: datetime | None = None, until: datetime | None = None, sentiment: str | None = None,
          review_only: bool = False, limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0),
          sort: str = Query('desc', pattern='^(asc|desc)$'), db: DB = Depends(session)):
    q = select(Post).where(Post.is_deleted_at_source.is_(False), visible())
    if source_id: q = q.where(Post.source_id == source_id)
    if since: q = q.where(Post.published_at >= since)
    if until: q = q.where(Post.published_at < until)
    if topic_id: q = q.where(exists().where(PostTopic.post_id == Post.post_id, PostTopic.topic_id == topic_id))
    if region_id: q = q.where(exists().where(PostRegion.post_id == Post.post_id, PostRegion.region_id == region_id))
    if sentiment: q = q.where(exists().where(Sentiment.post_id == Post.post_id, Sentiment.label == sentiment))
    if review_only: q = q.where(exists().where(PostRegion.post_id == Post.post_id, PostRegion.review_status == 'pending'))
    count = db.scalar(select(func.count()).select_from(q.subquery()))
    ordering = Post.published_at.desc() if sort == 'desc' else Post.published_at.asc()
    items = db.scalars(q.order_by(ordering, Post.post_id).offset(offset).limit(limit)).all()
    return Page(items=[serialize(db, p) for p in items], total=count, offset=offset, limit=limit)


@app.get(PREFIX + '/posts/{post_id}', response_model=PostOut)
def post(post_id: UUID, db: DB = Depends(session)):
    p = db.get(Post, post_id)
    if not p: raise HTTPException(404, 'Публикация не найдена')
    return serialize(db, p)


@app.get(PREFIX + '/topics')
def topics(db: DB = Depends(session)) -> list[dict]:
    return [row_dict(r) for r in db.scalars(select(Topic))]


@app.get(PREFIX + '/regions')
def regions(db: DB = Depends(session)) -> list[dict]:
    canonical = [r['region_id'] for r in csv.DictReader(Path('shared-contracts/regions.csv').open(encoding='utf-8'))]
    return [row_dict(r) for r in db.scalars(select(Region).where(Region.region_id.in_(canonical)))]


@app.get(PREFIX + '/regions/{region_id}/summary')
def region_summary(region_id: str, db: DB = Depends(session)) -> dict:
    if not db.get(Region, region_id): raise HTTPException(404, 'Регион не найден')
    count = db.scalar(select(func.count()).select_from(PostRegion).join(Post).where(PostRegion.region_id == region_id, visible(), PostRegion.review_status != 'rejected'))
    return {'region_id': region_id, 'publications': count, 'interpretation': 'Упоминания, включая неподтвержденные привязки; не оценка положения детей'}


@app.get(PREFIX + '/trends')
def trends(days: int = Query(30, ge=1, le=366), db: DB = Depends(session)) -> list[dict]:
    rows = db.execute(select(func.date_trunc('day', Post.published_at).label('day'), func.count().label('count'))
                      .where(Post.published_at >= now() - timedelta(days=days), visible()).group_by('day').order_by('day'))
    return [dict(r._mapping) for r in rows]


@app.get(PREFIX + '/alerts')
def alerts(limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: DB = Depends(session)) -> list[dict]:
    return [row_dict(a) for a in db.scalars(select(Alert).order_by(Alert.detected_at.desc()).offset(offset).limit(limit))]


@app.get(PREFIX + '/search', response_model=Page)
def search(q: str = Query(min_length=2, max_length=1000), mode: str = Query('fulltext', pattern='^(fulltext|semantic)$'),
           limit: int = Query(30, ge=1, le=100), offset: int = Query(0, ge=0), db: DB = Depends(session)):
    if mode == 'semantic':
        try: vector = embed(q, query=True)
        except Exception: raise HTTPException(503, 'Локальная модель поиска не настроена')
        query = select(Post).join(Embedding).where(Embedding.model == 'multilingual-e5-small', Embedding.model_version == settings.model_version)
        ordering = Embedding.vector.cosine_distance(vector)
    else:
        vector = func.to_tsvector('russian', PrivacyCheck.safe_title + ' ' + PrivacyCheck.safe_text)
        tsq = func.websearch_to_tsquery('russian', q)
        query = select(Post).join(PrivacyCheck).where(vector.op('@@')(tsq))
        ordering = func.ts_rank_cd(vector, tsq).desc()
    query = query.where(Post.is_deleted_at_source.is_(False), visible())
    count = db.scalar(select(func.count()).select_from(query.subquery()))
    return Page(items=[serialize(db, p) for p in db.scalars(query.order_by(ordering, Post.post_id).offset(offset).limit(limit))],
                total=count, limit=limit, offset=offset)


@app.get(PREFIX + '/sources/status')
def source_status(db: DB = Depends(session)) -> list[dict]:
    result = []
    for s in db.scalars(select(Source)):
        config = db.get(SourceConfig, s.source_id)
        run = db.scalar(select(Run).where(Run.source_id == s.source_id).order_by(Run.started_at.desc()).limit(1))
        last_run = row_dict(run) if run else None
        if last_run and last_run['errors']:
            last_run['errors'] = ['collection_error']  # Legacy messages may contain unsafe URLs.
        result.append({**row_dict(s), 'enabled': bool(config and config.enabled), 'last_run': last_run})
    return result


@app.get(PREFIX + '/digest', response_model=list[PostOut])
def digest(db: DB = Depends(session)):
    # Only analyst-confirmed labels; no automatically generated claims about children.
    q = select(Post).where(Post.published_at >= now() - timedelta(days=1), visible(), Post.is_deleted_at_source.is_(False),
        exists().where(PostTopic.post_id == Post.post_id, PostTopic.review_status == 'confirmed'))
    return [serialize(db, p) for p in db.scalars(q.order_by(Post.published_at.desc()).limit(20))]


@app.post(PREFIX + '/posts/{post_id}/reviews', dependencies=[Depends(admin)])
def review(post_id: UUID, correction: Correction, db: DB = Depends(session)) -> dict:
    if not db.get(Post, post_id): raise HTTPException(404, 'Публикация не найдена')
    cls, dictionary = (PostTopic, Topic) if correction.object_type == 'topic' else (PostRegion, Region)
    if not db.get(dictionary, correction.label): raise HTTPException(422, 'Неизвестная метка')
    row = db.get(cls, (post_id, correction.label))
    original = row_dict(row) if row else {}
    # Store JSON-safe audit snapshots.
    original = {k: str(v) if isinstance(v, (UUID, datetime)) else v for k, v in original.items()}
    if not row:
        args = dict(post_id=post_id, confidence=1.0)
        if cls == PostTopic: args.update(topic_id=correction.label, model_version='human-1.0.0')
        else: args.update(region_id=correction.label, detection_method='human-1.0.0', evidence={'role': 'event'})
        row = cls(**args)
        db.add(row)
    row.review_status = 'confirmed' if correction.accepted else 'rejected'
    db.add(Review(post_id=post_id, object_type=correction.object_type, original_label=original,
                  corrected_label=correction.model_dump(), reason=correction.reason))
    db.commit()
    return {'status': row.review_status}


@app.post(PREFIX + '/reprocess', dependencies=[Depends(admin)])
def reprocess(db: DB = Depends(session)) -> dict:
    count = db.execute(update(Post).values(processing_status='pending')).rowcount
    db.commit()
    return {'queued': count}


class PrivacyDecision(BaseModel):
    allow: bool
    reason: str = Field(min_length=5, max_length=1000)


@app.get(PREFIX + '/privacy/reviews', dependencies=[Depends(admin)])
def privacy_queue(db: DB = Depends(session)) -> list[dict]:
    return [{'post_id': str(c.post_id), 'safe_title': c.safe_title, 'safe_excerpt': c.safe_text[:240],
             'risk': c.risk, 'findings': c.findings, 'method_version': c.method_version}
            for c in db.scalars(select(PrivacyCheck).where(PrivacyCheck.status == 'held').limit(100))]


@app.post(PREFIX + '/privacy/{post_id}/review', dependencies=[Depends(admin)])
def privacy_review(post_id: UUID, decision: PrivacyDecision, db: DB = Depends(session)) -> dict:
    check = db.get(PrivacyCheck, post_id)
    if not check: raise HTTPException(404, 'Проверка не найдена')
    if check.method_version != VERSION: raise HTTPException(409, 'Требуется повторная автоматическая проверка')
    old = check.status
    check.status = 'allowed' if decision.allow else 'held'
    check.reviewed_at = now()
    # Do not retain untrusted free text in audit logs.
    db.add(Review(post_id=post_id, object_type='privacy', original_label={'status': old},
        corrected_label={'status': check.status}, reason='manual-privacy-decision'))
    db.commit()
    return {'status': check.status}
