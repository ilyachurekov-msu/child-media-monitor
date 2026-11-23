# Запуск и автоматическая приемка

## GitHub

Workflow .github/workflows/ci.yml запускается на PR и workflow_dispatch; только contents:read. Jobs независимы: test использует PostgreSQL16+pgvector, containers собирает образ и запускает Compose с отключенным реальным сбором. RSS — локальные синтетические файлы, не внешние сайты. Проверяются миграции, индексы, дубли, обновления, UUID, API, приватность, рестарт PostgreSQL, API/worker/Streamlit health и браузер. При CI без TEST_DATABASE_URL pytest падает, пропуски запрещены. Скриншоты только синтетического UI, срок артефактов 7 дней. Нет deployment, auto-merge и release.

## Без Docker

Python 3.11+, отдельный PostgreSQL16 с установленным vector. Создайте виртуальную среду, pip install -e '.[dev]'. Задайте DATABASE_URL и ADMIN_TOKEN, выполните alembic upgrade head и python -m scripts.seed. В отдельных процессах: uvicorn app.api.main:app --no-access-log; python -m app.workers.main; streamlit run app/ui/main.py. API_URL=http://localhost:8000. Для тестов используйте отдельную БД и TEST_DATABASE_URL равный DATABASE_URL. Не тестируйте на production.

## Будущий Docker-запуск

Владелец сейчас не обязан устанавливать Docker Desktop. При доступном Docker Engine: скопировать .env.example в .env, задать ADMIN_TOKEN/POSTGRES_PASSWORD, docker compose up --build -d. Адрес UI http://localhost:8501, API http://localhost:8000/docs. Все миграции/seed выполняет migrate до запуска сервисов. Прежде чем применять миграцию 0003 к объединенной БД, проверить region-mapping.csv и backup. Конфликтующие существующие региональные связи вызывают ошибку и rollback, а не потерю исправлений. Не запускайте down -v на рабочих данных.

Переменные: DATABASE_URL, API_URL, ADMIN_TOKEN, POSTGRES_PASSWORD; COLLECTION_ENABLED=false для полностью автономных фикстур; COLLECT_INTERVAL=900; RETENTION_DAYS=90; NLP_ENABLED=false; MODEL_PATH/MODEL_VERSION и SENTIMENT_PATH/SENTIMENT_VERSION — локальные snapshots. В Compose пути моделей /models/e5 и /models/sentiment; том только read-only. Основной образ без torch; для E5 установите extra [nlp] в отдельном локальном образе. Не включайте NLP_ENABLED без весов и конкретного SHA.

Мониторинг: /health проверяет БД, worker heartbeat — успешное завершение цикла, UI /_stcore/health. Сбой отдельного источника сохраняется в collection_runs. Ограничения моделей — docs/nlp.md; ограничения приемки — docs/mvp-readiness.md.
