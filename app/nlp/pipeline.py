"""Explicit baseline; no remote AI calls or silent model substitution."""
import re
import json
from pathlib import Path
from functools import lru_cache
from app.config import settings

RULE_VERSION = 'keywords-1.0.0'
GEO_VERSION = 'dictionary-1.0.0'
RULES = {
    'demography': ['рождаем', 'многодет', 'рождени'],
    'family': ['семь', 'семейн', 'родител'],
    'education': ['школ', 'ученик', 'образован', 'буллинг', 'детсад'],
    'healthcare': ['медицин', 'лекарств', 'больниц', 'вакцин'],
    'social_support': ['пособи', 'социальн', 'выплат', 'поддержк'],
    'orphanhood': ['сирот', 'усынов', 'опек', 'приемн'],
    'safety': ['безопас', 'погиб', 'травм', 'насили', 'пропал'],
    'infrastructure': ['строительств', 'ремонт', 'инфраструктур'],
}


def language(text):
    letters = re.findall(r'[^\W\d_]', text.lower())
    if not letters: return 'und'
    return 'ru' if sum('а' <= c <= 'я' or c == 'ё' for c in letters) / len(letters) > .5 else 'other'


def classify(text):
    text = text.casefold()
    return [(topic, min(.85, .45 + .15 * sum(k in text for k in keys)))
            for topic, keys in RULES.items() if any(k in text for k in keys)]


def geography(text, aliases):
    results = []
    for region, names in aliases.items():
        hits = [n for n in names if re.search(r'(?<!\w)' + re.escape(n) + r'(?!\w)', text, re.I)]
        if hits:
            results.append((region, .6, {'matches': hits, 'role': 'mention', 'version': GEO_VERSION,
                                        'limitation': 'Место события требует проверки; источник не используется.'}))
    return results


@lru_cache
def encoder():
    if not settings.nlp_enabled or settings.model_version == 'uninstalled':
        raise RuntimeError('Local embedding model not installed/configured')
    from sentence_transformers import SentenceTransformer
    lock = json.loads(Path('contracts/models.lock.json').read_text())['intfloat/multilingual-e5-small']['revision']
    provenance = json.loads(Path(settings.model_path, 'PROVENANCE.json').read_text())
    if settings.model_version != lock or provenance['revision'] != lock:
        raise RuntimeError('Embedding revision does not match approved lock')
    model = SentenceTransformer(settings.model_path, local_files_only=True, trust_remote_code=False)
    if model.get_sentence_embedding_dimension() != 384: raise ValueError('Expected 384 dimensions')
    return model


def embed(text, query=False):
    return encoder().encode(('query: ' if query else 'passage: ') + text,
                            normalize_embeddings=True).tolist()


@lru_cache
def sentiment_model():
    lock = json.loads(Path('contracts/models.lock.json').read_text())['cointegrated/rubert-tiny-sentiment-balanced']['revision']
    provenance = json.loads(Path(settings.sentiment_path, 'PROVENANCE.json').read_text())
    if settings.sentiment_version != lock or provenance['revision'] != lock:
        raise RuntimeError('Sentiment revision does not match approved lock')
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    tokenizer = AutoTokenizer.from_pretrained(settings.sentiment_path, local_files_only=True, trust_remote_code=False)
    model = AutoModelForSequenceClassification.from_pretrained(settings.sentiment_path, local_files_only=True, trust_remote_code=False)
    model.eval()
    return tokenizer, model


def sentiment(text):
    if settings.sentiment_version == 'uninstalled': return None
    import torch
    tokenizer, model = sentiment_model()
    with torch.inference_mode():
        tokens = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
        probabilities = torch.sigmoid(model(**tokens).logits)[0].tolist()
    # cointegrated/rubert-tiny-sentiment-balanced: independent sigmoid outputs.
    labels = [model.config.id2label[i].lower() for i in range(len(probabilities))]
    winner = max(range(len(labels)), key=probabilities.__getitem__)
    score = sum(p * {'negative': -1, 'neutral': 0, 'positive': 1}[l] for p, l in zip(probabilities, labels))
    return {'label': labels[winner], 'score': score, 'confidence': probabilities[winner],
            'model': 'cointegrated/rubert-tiny-sentiment-balanced', 'model_version': settings.sentiment_version}
