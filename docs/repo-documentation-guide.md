# Правила документации jiractl

## Source Priority

Явные требования пользователя → `AGENTS.md` → этот guide → нормативный `docs/CLI-CONTRACT.md` и PRD → ADR → планы. Код и результаты проверок подтверждают реализованное поведение, но не подменяют продуктовые требования. Расхождения фиксируются явно.

## Document Ownership

| Документ | Владелец темы |
|---|---|
| [README](../README.md) | Entrypoint, сборка и индекс |
| [PRD](PRD.md) | Продуктовый scope и критерии приёмки |
| [CLI contract](CLI-CONTRACT.md) | Нормативный публичный интерфейс |
| [ADR](ADR.md) | Решения и причины |
| [Implementation plan](IMPLEMENTATION-PLAN.md), [task graph](../planning/tasks.json) | Порядок будущей реализации |
| [SOURCES](SOURCES.md) | Provenance и evidence |

## Verification Matrix

| Изменение | Проверка |
|---|---|
| Реализованные CLI/config | Код, unit-тесты, `make check` |
| Proposed API | PRD, CLI contract, schemas и examples; без заявления runtime-совместимости |
| Стек и сборка | `go.mod`, Makefile, CI |
| Роли и делегирование | `.codex/config.toml`, `.codex/agents/*.toml`, `AGENTS.md` |
| Ссылки и структурированные данные | Существование локальных Markdown-ссылок, синтаксис JSON/TOML |
| Provenance | Первичные источники и явные evidence gaps |

## Indexing Policy

README содержит ссылки на основные документы и оба repo guide. Новая тема сначала направляется в существующий документ-владелец. `AGENTS.md` направляет workflows к guides. Пути будущего кода указываются как planned, не как существующие ссылки.

## Маршрутизация документации

`documentation_writer` (Terra/medium) выполняет одну ограниченную документационную задачу через `project-docs` и только в назначенном documentation scope. Он сверяет источники этого guide, обновляет владельца темы и индекс при необходимости, фиксирует принятые решения. Новое архитектурное решение, конфликт источников или выход за scope передаёт integrator для эскалации; продуктовый код и contracts самостоятельно не меняет.

## Стиль и Completion Criteria

Писать по-русски; команды, пути, идентификаторы и точные цитаты сохранять в исходном виде. Разделять implemented и proposed. Не объявлять тесты, Jira-совместимость или coverage подтверждёнными без выполненных проверок. Перед завершением сверить владельцев тем, индекс, локальные ссылки, JSON/TOML и `git diff --check`; перечислить реально выполненные проверки и незакрытые ограничения. Отсутствие старых pack artifacts не является evidence для Go-bootstrap. Для описания read-only Jira tests сверять `AGENTS.md`: существующие `JIRA_*` могут применяться только без раскрытия значений и без заявления bootstrap support.
