"""Bounded public HTTP reader. Redirect targets are validated before each request."""
import ipaddress
import socket
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import feedparser
import httpx
from bs4 import BeautifulSoup
from app.identity import normalize_url

AGENT = 'ChildMediaMonitor/1.0'
MAX_BYTES = 5_000_000


def public_url(url):
    normalized = normalize_url(url)
    u = urlsplit(normalized)
    if u.port not in (None, 80, 443): raise ValueError('Nonstandard port')
    addresses = socket.getaddrinfo(u.hostname, u.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Nonpublic address blocked')
    return normalized


def fetch(url, headers=None):
    with httpx.Client(timeout=25, follow_redirects=False, trust_env=False) as client:
        for _ in range(5):
            url = public_url(url)
            with client.stream('GET', url, headers={'User-Agent': AGENT, **(headers or {})}) as r:
                if r.is_redirect:
                    url = urljoin(url, r.headers['location'])
                    continue
                if r.status_code == 304: return r.status_code, dict(r.headers), b''
                r.raise_for_status()
                chunks, size = [], 0
                for chunk in r.iter_bytes():
                    size += len(chunk)
                    if size > MAX_BYTES: raise ValueError('Response too large')
                    chunks.append(chunk)
                return r.status_code, dict(r.headers), b''.join(chunks)
    raise ValueError('Too many redirects')


def allowed(url):
    u = urlsplit(public_url(url))
    robots = f'{u.scheme}://{u.netloc}/robots.txt'
    try:
        _, _, body = fetch(robots)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404: return True
        raise
    parser = RobotFileParser()
    parser.parse(body.decode('utf-8', errors='replace').splitlines())
    return parser.can_fetch(AGENT, url)


def clean(value):
    return BeautifulSoup(value or '', 'html.parser').get_text(' ', strip=True)


def parse_feed(body):
    if b'<!ENTITY' in body.upper() or b'<!DOCTYPE' in body.upper():
        raise ValueError('DTD/entities prohibited')
    feed = feedparser.parse(body)
    if feed.bozo and not feed.entries: raise ValueError('Invalid RSS/Atom')
    result = []
    for entry in feed.entries[:1000]:
        link = entry.get('link', '')
        if not link: continue
        try: normalize_url(link)
        except ValueError: continue
        date = entry.get('published_parsed') or entry.get('updated_parsed')
        import calendar
        published = datetime.fromtimestamp(calendar.timegm(date), timezone.utc) if date else datetime.now(timezone.utc)
        text = clean(entry.get('content', [{}])[0].get('value') or entry.get('summary', ''))
        title = clean(entry.get('title', ''))
        result.append(dict(external_id=str(entry.get('id') or normalize_url(link)), url=link,
                           title=title[:2000], text=text[:100000], published_at=published,
                           author_display=None, raw_metadata={'date_inferred': not bool(date)}))
    return result
