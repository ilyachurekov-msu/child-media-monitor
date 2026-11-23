"""Browser acceptance against synthetic-only running Compose; safe screenshots only."""
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path('artifacts/ui')
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto('http://localhost:8501')
    expect(page.get_by_text('Мониторинг информационного поля', exact=True)).to_be_visible(timeout=60000)
    labels = ['Обзор инфополя', 'Лента публикаций', 'Карта информационной активности', 'Проблемные темы', 'Аномалии', 'Поиск', 'Ежедневный дайджест', 'Источники и качество']
    for index, label in enumerate(labels):
        page.get_by_test_id('stSidebar').get_by_text(label, exact=True).click()
        expect(page.get_by_role('heading', name=label, exact=True)).to_be_visible(timeout=30000)
        expect(page.locator('[data-testid="stStatusWidget"]')).to_be_hidden(timeout=30000)
        expect(page.locator('[data-testid="stException"]')).to_have_count(0)
        if label == 'Лента публикаций':
            expect(page.get_by_text('В Москве открыли школу', exact=True)).to_be_visible(timeout=30000)
        if label == 'Поиск':
            page.get_by_role('textbox', name='Поиск публикаций').fill('школа')
            page.get_by_role('textbox', name='Поиск публикаций').press('Enter')
            expect(page.get_by_text('В Москве открыли школу', exact=True)).to_be_visible(timeout=30000)
        assert 'example@example.invalid' not in page.locator('body').inner_text()
        assert 'Тестов' not in page.locator('body').inner_text()
        page.screenshot(path=str(out / f'{index:02}.png'), full_page=True)
    page.get_by_test_id('stSidebar').get_by_text('Лента публикаций', exact=True).click()
    expect(page.get_by_role('heading', name='Лента публикаций', exact=True)).to_be_visible()
    page.get_by_role('combobox', name='Тема', exact=True).click()
    page.get_by_role('option', name='education', exact=True).click()
    expect(page.locator('[data-testid="stStatusWidget"]')).to_be_hidden(timeout=30000)
    page.get_by_role('combobox', name='Регион', exact=True).click()
    page.get_by_role('combobox', name='Регион', exact=True).fill('RU-77')
    page.get_by_role('option', name='RU-77', exact=True).click()
    expect(page.get_by_text('В Москве открыли школу', exact=True)).to_be_visible()
    expect(page.get_by_text('Социальная поддержка семей', exact=True)).to_have_count(0)
    page.get_by_text('Проверка аналитиком', exact=True).click()
    page.get_by_role('textbox', name='Идентификатор темы или региона').fill('education')
    page.get_by_role('textbox', name='Основание корректировки').fill('Синтетическая приемка интерфейса')
    page.get_by_role('button', name='Сохранить', exact=True).click()
    expect(page.get_by_text('Проверка сохранена', exact=True)).to_be_visible()
    page.screenshot(path=str(out / '08-review-filter.png'), full_page=True)
    page.get_by_test_id('stSidebar').get_by_text('Ежедневный дайджест', exact=True).click()
    expect(page.get_by_text('В Москве открыли школу', exact=True)).to_be_visible()
    browser.close()
