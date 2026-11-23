# Приемка MVP v0.1.0

Дата: 24 ноября 2026. Статус: **проверки выполняются, готовность пока не подтверждена**.

Новый публичный репозиторий: https://github.com/ilyachurekov-msu/child-media-monitor . Существующие репозитории не изменялись. PR: ожидает предоставления GitHub App доступа на запись к новому репозиторию; создание ветки получило 403 Resource not accessible by integration.

| Проверка | Фактическое состояние |
|---|---|
| Ранее существовавшие unit/API-contract | 13 проходили до этапа приемки |
| Новые privacy/Natasha/UI/shared | 23 теста прошли локально; 3 PostgreSQL-теста пропущены без БД. Все 8 разделов прошли Streamlit AppTest. Реальный Natasha NER прошел тест |
| PostgreSQL16/pgvector / миграции / реальный API | Тесты и CI подготовлены; результата запуска пока нет |
| Docker build / restart / persistence | Workflow подготовлен; результата GitHub Actions пока нет |
| RSS→DB→API→UI | Синтетические фикстуры и сквозные проверки подготовлены, не считать пройденными до CI |
| E5 / тональность | Веса не установлены, inference не проверен; baseline сохранен |
| PII | Natasha+regex+правила+ручная очередь, fail-closed; не абсолютная анонимизация |
| Общие контракты | Пакет-кандидат из existing regional snapshot, сопоставление 83 кодов; согласование отсутствует |
| Secrets / vulnerabilities / licenses | Лицензии runtime/dev прошли локальную проверку; pip-audit не обнаружил известных уязвимостей. Полный Gitleaks и повторный скан в CI еще не выполнялись |

Метрики scripts.evaluate: 12 синтетических примеров. Темы: TP=8, FP=0, FN=0, micro precision/recall/F1=1.0. PII на уровне документа: TP=6, FP=0, FN=0, precision/recall/F1=1.0. Геоупоминания: TP=1, FP=0, FN=0; precision/recall/F1=1.0. Это маленький development-набор, на котором разрабатывались правила, **не независимая оценка качества** и не основание заявлять 100% надежность. E5 и sentiment inference не выполнены. Их конкретные commit SHA получены с Hugging Face и закреплены в contracts/models.lock.json.

Синтаксис (compileall) и линтер Ruff прошли локально. Обнаруженная несовместимость PyArrow26/NumPy1 исправлена диапазоном PyArrow18–19 и проверена повторным AppTest.

Итог: нельзя объявить весь этап завершенным до успешного обязательного CI. Docker Desktop владельцу не требуется; принять PostgreSQL, контейнеры и браузер можно в GitHub Actions. Ни auto-merge, ни release, ни production deployment не выполняются.
