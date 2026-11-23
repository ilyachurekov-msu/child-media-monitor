"""Offline, fail-closed privacy assessment. Findings never store matched strings."""
from dataclasses import dataclass
from functools import lru_cache
import re
from urllib.parse import urlsplit, urlunsplit

VERSION = 'privacy-1.0.0+natasha-1.6.0'
PATTERNS = {
    'email': r'[\w.+-]+\s*@\s*[\w.-]+\.[A-Za-zА-Яа-я]{2,}',
    'phone': r'(?<!\d)(?:\+7|8)[\s(.-]*\d{3}[\s).\-]*\d{3}[\s.\-]*\d{2}[\s.\-]*\d{2}(?!\d)',
    'passport': r'(?<!\d)\d{2}\s?\d{2}\s+\d{6}(?!\d)',
    'snils': r'(?<!\d)\d{3}-\d{3}-\d{3}\s?\d{2}(?!\d)',
    'identifier': r'\b(?:ИНН|полис|паспорт|свидетельство о рождении)\s*[:№]?\s*[А-ЯA-Z0-9\- ]{6,25}',
    'home_address': r'(?:ул(?:ица)?\.?|проспект|переулок)\s+[А-ЯЁа-яё0-9 .-]{2,60}?[, ]+(?:д(?:ом)?\.?\s*\d+[А-Яа-я]?(?:[, ]+кв(?:артира)?\.?\s*\d+)?)',
    'person_rule': r'\b[А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?\b',
}
CHILD = re.compile(r'дет[ьи]|реб[её]н|несовершеннолет|школьни|учени[кц]|\b\d{1,2}[- ]летн', re.I)
SENSITIVE = re.compile(r'диагноз|насили|инвалид|сирот|погиб|пострад|заболев|пропал|опек|адрес|телефон', re.I)


@lru_cache
def ner():
    from natasha import Segmenter, NewsEmbedding, NewsNERTagger
    return Segmenter(), NewsNERTagger(NewsEmbedding())


def persons(text):
    from natasha import Doc
    segmenter, tagger = ner()
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(tagger)
    return [(s.start, s.stop, 'person') for s in doc.spans if s.type == 'PER']


@dataclass
class Assessment:
    safe_text: str
    findings: list[dict]
    risk: str
    status: str
    method_version: str = VERSION


def assess(text):
    spans = [(m.start(), m.end(), kind) for kind, pattern in PATTERNS.items()
             for m in re.finditer(pattern, text, re.I if kind != 'person_rule' else 0)]
    available = True
    try: spans += persons(text)
    except Exception: available = False
    child = bool(CHILD.search(text))
    # Named people are entities, not automatically a privacy violation.
    # Still redact for public derivatives. Child + identifying context is held.
    identifying = bool(spans) or bool(re.search(r'\b\d{1,2}[- ]летн', text, re.I))
    held = not available or (child and (identifying or SENSITIVE.search(text)))
    safe = text
    merged = []
    for start, end, kind in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else: merged.append((start, end))
    for start, end in reversed(merged): safe = safe[:start] + '[СКРЫТО]' + safe[end:]
    findings = [{'kind': kind, 'start': start, 'end': end} for start, end, kind in spans]
    return Assessment(safe, findings, 'high' if held else ('moderate' if spans else 'low'),
                      'held' if held else 'allowed')


def safe_link(url):
    """No query/fragment, mailto, credentials, email, phone or person slugs."""
    u = urlsplit(url)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username: return None
    from urllib.parse import unquote
    path = unquote(u.path)
    if re.search(r'@|\d{10,}|[А-Яа-яЁё]', path): path = '/'
    # Keep origin attribution; article path only when a numeric ID or simple numeric route.
    if not re.fullmatch(r'/[a-zA-Z_/-]*\d+(?:\.html)?/?', path): path = '/'
    return urlunsplit((u.scheme, u.netloc, path, '', ''))
