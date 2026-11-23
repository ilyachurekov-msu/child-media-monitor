import hashlib
import re
import unicodedata
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from uuid import UUID, uuid5

NAMESPACE = UUID('72c4db98-6752-5fe0-a56d-af600628f13b')


def normalize_url(url: str) -> str:
    u = urlsplit(url.strip())
    if u.scheme.lower() not in ('http', 'https') or not u.hostname or u.username:
        raise ValueError('Only public HTTP(S) URLs are supported')
    host = u.hostname.encode('idna').decode().lower()
    port = u.port
    if port and not ((u.scheme == 'https' and port == 443) or (u.scheme == 'http' and port == 80)):
        host += f':{port}'
    query = sorted((k, v) for k, v in parse_qsl(u.query, keep_blank_values=True)
                   if not k.lower().startswith('utm_') and k.lower() not in ('yclid', 'fbclid'))
    return urlunsplit((u.scheme.lower(), host, u.path or '/', urlencode(query), ''))


def source_id(kind: str, url: str):
    return uuid5(NAMESPACE, f'source:{kind.strip().lower()}:{normalize_url(url)}')


def post_id(source, external_id: str):
    return uuid5(UUID(str(source)), unicodedata.normalize('NFC', external_id.strip()))


def text_hash(text: str):
    return hashlib.sha256(re.sub(r'\s+', ' ', unicodedata.normalize('NFKC', text)).strip().casefold().encode()).hexdigest()
