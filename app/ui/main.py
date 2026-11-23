import os
from datetime import datetime, time, timezone, timedelta
import httpx
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Навигатор детства · Инфополе', page_icon='◉', layout='wide')
API = os.getenv('API_URL', 'http://localhost:8000') + '/api/v1/media'


def get(path, **params):
    try:
        r = httpx.get(API + path, params={k: v for k, v in params.items() if v is not None}, timeout=30)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPError as exc:
        st.error('Не удалось получить данные API. Проверьте состояние сервисов. ' + str(exc))
        st.stop()


def cards(items):
    for p in items:
        with st.container(border=True):
            st.subheader(p['title'] or 'Без заголовка')
            st.caption(f"{p['published_at']} · {p['processing_status']}")
            st.write(p['text'][:1500])
            if p['url']: st.link_button('Открыть первоисточник', p['url'])
            st.caption('Темы: ' + ', '.join(f"{t['topic_id']} ({t['confidence']:.2f}; {t['model_version']}; {t['review_status']})" for t in p['topics']))
            st.caption('Регионы: ' + ', '.join(f"{t['region_id']} ({t['review_status']})" for t in p['regions']))
            with st.expander('Проверка аналитиком'):
                with st.form('review-' + p['post_id']):
                    kind = st.selectbox('Объект', ['topic', 'region'])
                    label = st.text_input('Идентификатор темы или региона')
                    accepted = st.checkbox('Подтвердить', value=True)
                    reason = st.text_input('Основание корректировки')
                    if st.form_submit_button('Сохранить'):
                        r = httpx.post(API + f"/posts/{p['post_id']}/reviews", json={'object_type': kind, 'label': label, 'accepted': accepted, 'reason': reason}, headers={'Authorization': 'Bearer ' + os.getenv('ADMIN_TOKEN', '')})
                        if r.is_success: st.success('Проверка сохранена')
                        else: st.error(r.text)


st.title('Мониторинг информационного поля')
st.caption('Навигатор детства · публичные публикации')
st.info('Информационная активность отражает публикации источников и не измеряет распространенность социальных проблем.')
pages = ['Обзор инфополя', 'Лента публикаций', 'Карта информационной активности', 'Проблемные темы', 'Аномалии', 'Поиск', 'Ежедневный дайджест', 'Источники и качество']
page = st.sidebar.radio('Раздел', pages)
st.header(page)
if page == pages[0]:
    data = get('/posts', limit=1)
    st.metric('Собрано публикаций', data['total'])
    frame = pd.DataFrame(get('/trends'))
    if not frame.empty: st.line_chart(frame.set_index('day')['count'])
    else: st.write('Пока нет данных. Worker выполнит первый сбор автоматически.')
elif page == pages[1]:
    topics = get('/topics'); regions = get('/regions'); sources = get('/sources/status')
    t = st.sidebar.selectbox('Тема', [''] + [x['topic_id'] for x in topics])
    r = st.sidebar.selectbox('Регион', [''] + [x['region_id'] for x in regions])
    s = st.sidebar.selectbox('Источник', [''] + [x['source_id'] for x in sources])
    dates = st.sidebar.date_input('Период', (datetime.now().date() - timedelta(days=30), datetime.now().date()))
    review_only = st.sidebar.checkbox('Требуется проверка географии')
    offset = st.sidebar.number_input('Пропустить публикаций', min_value=0, step=30)
    params = {}
    if len(dates) == 2:
        params = {'since': datetime.combine(dates[0], time(), timezone.utc).isoformat(), 'until': datetime.combine(dates[1] + timedelta(days=1), time(), timezone.utc).isoformat()}
    result = get('/posts', topic_id=t or None, region_id=r or None, source_id=s or None, review_only=review_only, offset=offset, **params)
    st.caption(f"Найдено: {result['total']}"); cards(result['items'])
elif page == pages[2]:
    st.warning('Географические привязки включают упоминания. Карта с границами субъектов требует согласованного GeoJSON; пока доступна таблица.')
    regions = get('/regions')
    st.dataframe([{'Регион': r['name'], **get('/regions/' + r['region_id'] + '/summary')} for r in regions])
elif page == pages[3]:
    st.dataframe(get('/topics'))
    st.write('Динамика общего потока')
    frame = pd.DataFrame(get('/trends'))
    if not frame.empty: st.bar_chart(frame.set_index('day')['count'])
elif page == pages[4]:
    st.write('Сигналы требуют проверки аналитиком.')
    st.dataframe(get('/alerts'))
elif page == pages[5]:
    q = st.text_input('Поиск публикаций')
    mode = st.radio('Метод', ['fulltext', 'semantic'], format_func=lambda x: {'fulltext': 'Полнотекстовый', 'semantic': 'Семантический (локальная модель)'}[x])
    if len(q) >= 2: cards(get('/search', q=q, mode=mode)['items'])
elif page == pages[6]:
    st.caption('Материалы за 24 часа с подтвержденной аналитиком тематикой, до 20 публикаций.')
    cards(get('/digest'))
else:
    st.json(get('/sources/status'))

with st.sidebar.expander('Приватность · очередь аналитика'):
    if st.button('Получить очередь проверки'):
        response = httpx.get(API + '/privacy/reviews', headers={'Authorization': 'Bearer ' + os.getenv('ADMIN_TOKEN', '')})
        if response.is_success: st.session_state['privacy_queue'] = response.json()
        else: st.error('Доступ к очереди требует токен аналитика')
    for check in st.session_state.get('privacy_queue', []):
        st.caption(check['safe_title'])
        st.write(check['safe_excerpt'])
        with st.form('privacy-' + check['post_id']):
            allow = st.checkbox('Разрешить безопасное представление')
            reason = st.text_input('Основание ручной проверки')
            if st.form_submit_button('Принять решение'):
                response = httpx.post(API + '/privacy/' + check['post_id'] + '/review', json={'allow': allow, 'reason': reason}, headers={'Authorization': 'Bearer ' + os.getenv('ADMIN_TOKEN', '')})
                if response.is_success: st.success('Решение сохранено')
                else: st.error('Проверьте токен и основание решения')
