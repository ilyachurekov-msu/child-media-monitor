from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from app.models import Post, PostTopic, Alert, now
from app.analytics.anomalies import detect


def update_alerts(db):
    """Evaluate the most recent complete UTC day, never an incomplete current day."""
    end = now().replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=29)
    totals = dict(db.execute(select(func.date(Post.published_at), func.count()).where(
        Post.published_at >= start, Post.published_at < end).group_by(func.date(Post.published_at))).all())
    target = (end - timedelta(days=1)).date()
    rows = db.execute(select(PostTopic.topic_id, func.date(Post.published_at), func.count(), func.count(func.distinct(Post.source_id)))
        .join(Post, Post.post_id == PostTopic.post_id).where(Post.published_at >= start, Post.published_at < end,
        PostTopic.review_status != 'rejected').group_by(PostTopic.topic_id, func.date(Post.published_at))).all()
    topics = {}
    for topic, day, count, sources in rows: topics.setdefault(topic, {})[day] = (count, sources)
    for topic, counts in topics.items():
        actual, sources = counts.get(target, (0, 0))
        history = [(counts.get(day, (0, 0))[0], total) for day, total in totals.items() if day < target]
        details = detect(actual, totals.get(target, 0), history, sources)
        if details:
            ids = db.scalars(select(Post.post_id).join(PostTopic).where(PostTopic.topic_id == topic,
                func.date(Post.published_at) == target, PostTopic.review_status != 'rejected')).all()
            details.update(post_ids=[str(pid) for pid in ids], unique_sources=sources)
            db.execute(insert(Alert).values(region_id='ALL', topic_id=topic, kind='topic_share_spike', period=target,
                actual=actual, baseline=details['baseline_share'] * totals[target], details=details).on_conflict_do_nothing())
