
CREATE TABLE core.regions (
	region_id TEXT NOT NULL, 
	name TEXT NOT NULL, 
	federal_district TEXT NOT NULL, 
	okato_code TEXT, 
	oktmo_code TEXT, 
	valid_from DATE NOT NULL, 
	valid_to DATE, 
	PRIMARY KEY (region_id)
)

;

CREATE TABLE core.sources (
	source_id UUID NOT NULL, 
	source_type TEXT NOT NULL, 
	name TEXT NOT NULL, 
	url TEXT, 
	publisher TEXT, 
	created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (source_id)
)

;

CREATE TABLE core.topics (
	topic_id TEXT NOT NULL, 
	name TEXT NOT NULL, 
	parent_topic_id TEXT, 
	PRIMARY KEY (topic_id), 
	FOREIGN KEY(parent_topic_id) REFERENCES core.topics (topic_id)
)

;

CREATE TABLE media.alerts (
	alert_id UUID NOT NULL, 
	region_id TEXT, 
	topic_id TEXT, 
	kind TEXT, 
	period DATE, 
	actual FLOAT, 
	baseline FLOAT, 
	status TEXT, 
	detected_at TIMESTAMP WITH TIME ZONE, 
	details JSONB, 
	PRIMARY KEY (alert_id), 
	UNIQUE (region_id, topic_id, period, kind)
)

;

CREATE TABLE media.collection_runs (
	run_id UUID NOT NULL, 
	source_id UUID, 
	started_at TIMESTAMP WITH TIME ZONE, 
	finished_at TIMESTAMP WITH TIME ZONE, 
	received INTEGER, 
	inserted INTEGER, 
	errors JSONB, 
	status TEXT, 
	PRIMARY KEY (run_id), 
	FOREIGN KEY(source_id) REFERENCES core.sources (source_id)
)

;

CREATE TABLE media.posts (
	post_id UUID NOT NULL, 
	source_id UUID NOT NULL, 
	external_id TEXT NOT NULL, 
	source_type TEXT NOT NULL, 
	url TEXT NOT NULL, 
	title TEXT, 
	text TEXT NOT NULL, 
	text_hash TEXT NOT NULL, 
	author_display TEXT, 
	published_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	collected_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	language TEXT NOT NULL, 
	raw_metadata JSONB NOT NULL, 
	processing_status TEXT NOT NULL, 
	is_deleted_at_source BOOLEAN NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (post_id), 
	UNIQUE (source_id, external_id), 
	FOREIGN KEY(source_id) REFERENCES core.sources (source_id)
)

;
CREATE INDEX ix_media_posts_processing_status ON media.posts (processing_status);
CREATE INDEX ix_posts_source ON media.posts (source_id);
CREATE INDEX ix_posts_hash ON media.posts (text_hash);
CREATE INDEX ix_posts_time ON media.posts (published_at);

CREATE TABLE media.source_config (
	source_id UUID NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	etag TEXT, 
	last_modified TEXT, 
	next_attempt TIMESTAMP WITH TIME ZONE, 
	failures INTEGER, 
	PRIMARY KEY (source_id), 
	FOREIGN KEY(source_id) REFERENCES core.sources (source_id)
)

;

CREATE TABLE media.post_embeddings (
	post_id UUID NOT NULL, 
	model TEXT NOT NULL, 
	model_version TEXT NOT NULL, 
	vector VECTOR(384) NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (post_id, model, model_version), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE
)

;

CREATE TABLE media.post_regions (
	post_id UUID NOT NULL, 
	region_id TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	detection_method TEXT NOT NULL, 
	evidence JSONB NOT NULL, 
	review_status TEXT, 
	PRIMARY KEY (post_id, region_id), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE, 
	FOREIGN KEY(region_id) REFERENCES core.regions (region_id)
)

;
CREATE INDEX ix_pr_region ON media.post_regions (region_id);

CREATE TABLE media.post_sentiment (
	analysis_id UUID NOT NULL, 
	post_id UUID, 
	label TEXT, 
	score FLOAT, 
	confidence FLOAT, 
	model TEXT, 
	model_version TEXT, 
	analyzed_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (analysis_id), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE
)

;
CREATE INDEX ix_media_post_sentiment_post_id ON media.post_sentiment (post_id);

CREATE TABLE media.post_topics (
	post_id UUID NOT NULL, 
	topic_id TEXT NOT NULL, 
	confidence FLOAT NOT NULL, 
	model_version TEXT NOT NULL, 
	classified_at TIMESTAMP WITH TIME ZONE, 
	review_status TEXT, 
	PRIMARY KEY (post_id, topic_id), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE, 
	FOREIGN KEY(topic_id) REFERENCES core.topics (topic_id)
)

;
CREATE INDEX ix_pt_topic ON media.post_topics (topic_id);

CREATE TABLE media.processing_errors (
	error_id UUID NOT NULL, 
	post_id UUID, 
	stage TEXT, 
	error TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (error_id), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE
)

;

CREATE TABLE media.processing_reviews (
	review_id UUID NOT NULL, 
	post_id UUID, 
	object_type TEXT, 
	original_label JSONB, 
	corrected_label JSONB, 
	reviewed_at TIMESTAMP WITH TIME ZONE, 
	reason TEXT, 
	PRIMARY KEY (review_id), 
	FOREIGN KEY(post_id) REFERENCES media.posts (post_id) ON DELETE CASCADE
)

;
