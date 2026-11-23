import json
from pathlib import Path
from app.nlp.pipeline import classify, geography
from app.privacy import assess, VERSION


def metrics(pairs):
    tp = sum(pred and gold for pred, gold in pairs)
    fp = sum(pred and not gold for pred, gold in pairs)
    fn = sum(not pred and gold for pred, gold in pairs)
    precision = tp / (tp + fp) if tp + fp else 0
    recall = tp / (tp + fn) if tp + fn else 0
    return {'tp': tp, 'fp': fp, 'fn': fn, 'precision': precision, 'recall': recall,
            'f1': 2 * precision * recall / (precision + recall) if precision + recall else 0}


def main():
    corpus = json.loads(Path('tests/fixtures/evaluation.json').read_text(encoding='utf-8'))
    aliases = json.loads(Path('contracts/region_aliases.json').read_text(encoding='utf-8'))
    topic_pairs, privacy_pairs, geo_pairs = [], [], []
    for item in corpus:
        predicted = set(dict(classify(item['text'])))
        for topic in set(predicted) | set(item['topics']): topic_pairs.append((topic in predicted, topic in item['topics']))
        privacy_pairs.append((bool(assess(item['text']).findings), item['pii']))
        geo_pairs.append((bool(geography(item['text'], aliases)), bool(item['region'])))
    report = {'samples': len(corpus), 'synthetic_only': True, 'topic_micro': metrics(topic_pairs),
              'pii_document_detection': metrics(privacy_pairs), 'geo_mention_detection': metrics(geo_pairs),
              'privacy_method': VERSION, 'e5_inference': 'not run: optional weights not installed',
              'sentiment_inference': 'not run: license and weights pending',
              'limitation': 'Tiny development corpus, not independent validation; no estimate of production reliability.'}
    Path('artifacts').mkdir(exist_ok=True)
    Path('artifacts/evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == '__main__': main()
