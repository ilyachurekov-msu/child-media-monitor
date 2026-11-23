# Changelog

## 0.1.0 — acceptance candidate, 2026-11-24

- Добавлен многоуровневый privacy-конвейер Natasha + regex/rules и отдельные безопасные производные.
- Публичные API/поиск/дайджест/статистика скрывают непроверенные и заблокированные публикации.
- Дополнительные миграции privacy и согласования региональных идентификаторов.
- PR CI: PostgreSQL16/pgvector, Docker health/restart, API/UI, фикстуры, secret/dependency/license checks.
- Shared contracts candidate и проверяемое сопоставление без изменения соседних модулей.
- Синтетический оценочный корпус; неопроверенные модели явно не считаются принятыми.
- Реальный CI: 27 тестов без пропусков, PostgreSQL16/pgvector, Docker и restart persistence, Playwright всех разделов/фильтров/коррекции/дайджеста.
- Исправлены найденные CI уязвимости: PyArrow23.0.1+ и setuptools84.1+; Gitleaks, pip-audit и проверка лицензий проходят.
