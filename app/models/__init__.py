from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import Text, Date, DateTime, Boolean, Float, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column as col
from pgvector.sqlalchemy import Vector


def now(): return datetime.now(timezone.utc)


class Base(DeclarativeBase): pass


class Region(Base):
    __tablename__ = 'regions'
    __table_args__ = {'schema': 'core'}
    region_id = col(Text, primary_key=True)
    name = col(Text, nullable=False)
    federal_district = col(Text, nullable=False)
    okato_code = col(Text)
    oktmo_code = col(Text)
    valid_from = col(Date, nullable=False)
    valid_to = col(Date)


class Topic(Base):
    __tablename__ = 'topics'
    __table_args__ = {'schema': 'core'}
    topic_id = col(Text, primary_key=True)
    name = col(Text, nullable=False)
    parent_topic_id = col(Text, ForeignKey('core.topics.topic_id'))


class Source(Base):
    __tablename__ = 'sources'
    __table_args__ = {'schema': 'core'}
    source_id = col(UUID(as_uuid=True), primary_key=True)
    source_type = col(Text, nullable=False)
    name = col(Text, nullable=False)
    url = col(Text)
    publisher = col(Text)
    created_at = col(DateTime(timezone=True), default=now, nullable=False)


class SourceConfig(Base):
    __tablename__ = 'source_config'
    __table_args__ = {'schema': 'media'}
    source_id = col(UUID(as_uuid=True), ForeignKey('core.sources.source_id'), primary_key=True)
    enabled = col(Boolean, default=True, nullable=False)
    etag = col(Text)
    last_modified = col(Text)
    next_attempt = col(DateTime(timezone=True), default=now)
    failures = col(Integer, default=0)


class Post(Base):
    __tablename__ = 'posts'
    __table_args__ = (UniqueConstraint('source_id', 'external_id'), Index('ix_posts_time', 'published_at'), Index('ix_posts_source', 'source_id'), Index('ix_posts_hash', 'text_hash'), {'schema': 'media'})
    post_id = col(UUID(as_uuid=True), primary_key=True)
    source_id = col(UUID(as_uuid=True), ForeignKey('core.sources.source_id'), nullable=False)
    external_id = col(Text, nullable=False)
    source_type = col(Text, nullable=False)
    url = col(Text, nullable=False)
    title = col(Text)
    text = col(Text, nullable=False)
    text_hash = col(Text, nullable=False)
    author_display = col(Text)
    published_at = col(DateTime(timezone=True), nullable=False)
    collected_at = col(DateTime(timezone=True), default=now, nullable=False)
    language = col(Text, default='und', nullable=False)
    raw_metadata = col(JSONB, default=dict, nullable=False)
    processing_status = col(Text, default='pending', nullable=False, index=True)
    is_deleted_at_source = col(Boolean, default=False, nullable=False)
    updated_at = col(DateTime(timezone=True), default=now, onupdate=now, nullable=False)


class PostTopic(Base):
    __tablename__ = 'post_topics'
    __table_args__ = (Index('ix_pt_topic', 'topic_id'), {'schema': 'media'})
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'), primary_key=True)
    topic_id = col(Text, ForeignKey('core.topics.topic_id'), primary_key=True)
    confidence = col(Float, nullable=False)
    model_version = col(Text, nullable=False)
    classified_at = col(DateTime(timezone=True), default=now)
    review_status = col(Text, default='pending')


class PostRegion(Base):
    __tablename__ = 'post_regions'
    __table_args__ = (Index('ix_pr_region', 'region_id'), {'schema': 'media'})
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'), primary_key=True)
    region_id = col(Text, ForeignKey('core.regions.region_id'), primary_key=True)
    confidence = col(Float, nullable=False)
    detection_method = col(Text, nullable=False)
    evidence = col(JSONB, nullable=False)
    review_status = col(Text, default='pending')


class Sentiment(Base):
    __tablename__ = 'post_sentiment'
    __table_args__ = {'schema': 'media'}
    analysis_id = col(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'), index=True)
    label = col(Text)
    score = col(Float)
    confidence = col(Float)
    model = col(Text)
    model_version = col(Text)
    analyzed_at = col(DateTime(timezone=True), default=now)


class Embedding(Base):
    __tablename__ = 'post_embeddings'
    __table_args__ = {'schema': 'media'}
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'), primary_key=True)
    model = col(Text, primary_key=True)
    model_version = col(Text, primary_key=True)
    vector = col(Vector(384), nullable=False)
    computed_at = col(DateTime(timezone=True), default=now)


class Run(Base):
    __tablename__ = 'collection_runs'
    __table_args__ = {'schema': 'media'}
    run_id = col(UUID(as_uuid=True), primary_key=True, default=uuid4)
    source_id = col(UUID(as_uuid=True), ForeignKey('core.sources.source_id'))
    started_at = col(DateTime(timezone=True), default=now)
    finished_at = col(DateTime(timezone=True))
    received = col(Integer, default=0)
    inserted = col(Integer, default=0)
    errors = col(JSONB, default=list)
    status = col(Text, default='running')


class Alert(Base):
    __tablename__ = 'alerts'
    __table_args__ = (UniqueConstraint('region_id', 'topic_id', 'period', 'kind'), {'schema': 'media'})
    alert_id = col(UUID(as_uuid=True), primary_key=True, default=uuid4)
    region_id = col(Text)
    topic_id = col(Text)
    kind = col(Text)
    period = col(Date)
    actual = col(Float)
    baseline = col(Float)
    status = col(Text, default='pending')
    detected_at = col(DateTime(timezone=True), default=now)
    details = col(JSONB, default=dict)


class Review(Base):
    __tablename__ = 'processing_reviews'
    __table_args__ = {'schema': 'media'}
    review_id = col(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'))
    object_type = col(Text)
    original_label = col(JSONB)
    corrected_label = col(JSONB)
    reviewed_at = col(DateTime(timezone=True), default=now)
    reason = col(Text)


class ProcessingError(Base):
    __tablename__ = 'processing_errors'
    __table_args__ = {'schema': 'media'}
    error_id = col(UUID(as_uuid=True), primary_key=True, default=uuid4)
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'))
    stage = col(Text)
    error = col(Text)
    created_at = col(DateTime(timezone=True), default=now)


class PrivacyCheck(Base):
    __tablename__ = 'privacy_checks'
    __table_args__ = {'schema': 'media'}
    post_id = col(UUID(as_uuid=True), ForeignKey('media.posts.post_id', ondelete='CASCADE'), primary_key=True)
    input_hash = col(Text, nullable=False)
    safe_title = col(Text, nullable=False)
    safe_text = col(Text, nullable=False)
    findings = col(JSONB, nullable=False)
    risk = col(Text, nullable=False)
    status = col(Text, nullable=False, index=True)
    method_version = col(Text, nullable=False)
    checked_at = col(DateTime(timezone=True), default=now, nullable=False)
    reviewed_at = col(DateTime(timezone=True))
