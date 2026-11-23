from statistics import median


def detect(count, total, history, sources):
    """Compare daily shares; require 14 observed days and >=3 independent sources."""
    shares = [n / t for n, t in history if t > 0]
    if len(shares) < 14 or count < 5 or sources < 3 or total <= 0: return None
    base = median(shares)
    mad = median(abs(s - base) for s in shares)
    score = .6745 * (count / total - base) / max(mad, .005)
    if score <= 3.5: return None
    return {'score': score, 'baseline_share': base, 'actual_share': count / total,
            'method': 'robust-share-z-1.0.0', 'confidence': 'exploratory',
            'limitation': 'Интенсивность публикаций не измеряет распространенность проблем.'}
