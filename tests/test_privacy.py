from unittest.mock import patch
from app.privacy import assess, safe_link


def test_direct_identifiers_masked():
    result = assess('Контакт example@example.invalid, +7 (000) 000-00-00, паспорт 00 00 000000, СНИЛС 000-000-000 00.')
    assert 'example@' not in result.safe_text
    assert '000000' not in result.safe_text
    assert {'email', 'phone', 'passport', 'snils'} <= {r['kind'] for r in result.findings}
    assert all('value' not in item for item in result.findings)


def test_child_conservative_hold():
    result = assess('Школьник Тестов Пример Образцович, диагноз, улица Учебная, дом 999, квартира 99.')
    assert result.status == 'held'
    assert 'Тестов' not in result.safe_text
    assert 'Учебная' not in result.safe_text


def test_ner_actual_inference():
    from app.privacy import persons
    assert persons('Иван Иванов выступил с докладом.')


def test_fail_closed():
    with patch('app.privacy.persons', side_effect=RuntimeError('synthetic')):
        assert assess('Открыта школа').status == 'held'


def test_name_is_entity_not_automatic_violation():
    with patch('app.privacy.persons', return_value=[(0, 11, 'person')]):
        result = assess('Иван Иванов выступил с докладом о бюджете.')
    assert result.status == 'allowed'
    assert result.risk == 'moderate'


def test_link_no_identifier_query():
    assert safe_link('https://example.org/news/100?email=example@example.invalid#person') == 'https://example.org/news/100'
    assert safe_link('mailto:example@example.invalid') is None
