import unittest
from unittest.mock import patch
from app.identity import normalize_url, source_id, post_id, text_hash
from app.collectors.rss import parse_feed, public_url
from app.nlp.pipeline import classify, geography, language
from app.analytics.anomalies import detect


class CoreTests(unittest.TestCase):
    def test_identity(self):
        a = source_id('rss', 'https://Example.org:443/rss?utm_source=x#x')
        b = source_id('rss', 'https://example.org/rss')
        self.assertEqual(a, b)
        self.assertEqual(post_id(a, '123'), post_id(b, '123'))
        self.assertNotEqual(post_id(a, '123'), post_id(a, '124'))

    def test_hash(self):
        self.assertEqual(text_hash(' Текст  новости\n'), text_hash('текст новости'))

    def test_query_preserved(self):
        self.assertEqual(normalize_url('https://a.org/?page=2&utm_medium=r'), 'https://a.org/?page=2')

    def test_rss(self):
        rss = b'<rss version="2.0"><channel><title>x</title><item><guid>1</guid><link>https://example.org/1</link><title>Title</title><description>&lt;b&gt;Text&lt;/b&gt;</description><pubDate>Mon, 23 Nov 2026 12:00:00 +0300</pubDate></item></channel></rss>'
        rows = parse_feed(rss)
        self.assertEqual(rows[0]['external_id'], '1')
        self.assertEqual(rows[0]['text'], 'Text')
        self.assertEqual(rows[0]['published_at'].hour, 9)
        self.assertEqual(rows, parse_feed(rss))

    def test_bad_feed(self):
        with self.assertRaises(ValueError): parse_feed(b'not xml')
        with self.assertRaises(ValueError): parse_feed(b'<!DOCTYPE rss>')

    def test_ssrf(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaises(ValueError): public_url('https://example.org/')

    def test_topics(self):
        self.assertIn('education', dict(classify('В школе выявлен буллинг')))
        self.assertEqual(classify('Биржа торгует нефтью'), [])

    def test_geo_no_source_inference(self):
        self.assertEqual(geography('Публикация без географии', {'RU-MOW': ['Москва']}), [])
        result = geography('В Москве открыли школу', {'RU-MOW': ['Москве']})
        self.assertEqual(result[0][2]['role'], 'mention')

    def test_language(self):
        self.assertEqual(language('Дети идут в школу'), 'ru')
        self.assertEqual(language('123'), 'und')

    def test_anomaly_guards(self):
        self.assertIsNone(detect(1, 100, [(1, 100)] * 30, 1))
        self.assertIsNone(detect(20, 100, [(1, 100)] * 3, 5))
        self.assertIsNotNone(detect(20, 100, [(1, 100)] * 30, 5))


if __name__ == '__main__': unittest.main()
