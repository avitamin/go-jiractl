# Coverage/reference strategy

## 1. Что входит в пакет

`contracts/reference.lock.json` фиксирует upstream commit. `planning/coverage.seed.json` перечисляет 63 Jira tools из опубликованной toolset reference [S1]. **Это seed, не доказанный полный inventory pinned checkout.** Полный checkout не был материализован при подготовке. Исходный read/write функционал CLI пока не реализован; у seed нет фиктивных PASS tests.

T00 пересоздаёт inventory из кода, добавляет все отсутствующие seed entries, сверяет runtime registration и отмечает deployment support. Нельзя вычислять «100% реализовано» из количества заполненных строк.

## 2. Как воспроизвести inventory

Go-инструмент upstream inventory ещё не реализован; его создание выделено в T-TOOLING. После реализации потребуется checkout ровно `22369b76d6c1775a9730ba7d7cb37d49f7da671a`, проверка clean tracked source и извлечение symbols/tags/parameters/source locations/hashes без исполнения upstream-кода.

Upstream реализован на Python [S2]; его исходники анализируются как reference. Static inventory не доказывает runtime exposure. Prefix `jira_` необходимо сверять с upstream composition. До появления инструмента seed остаётся неполным evidence; отсутствующая проверка не считается пройденной.

Runtime inventory получать отдельно в sandbox c pinned dependency lock и DC configuration; сравнить `tools/list` names/schemas. Не выдавать PAT write account широкому экспериментальному агенту. Учитывать toolset/read-only/deployment filtering: inventory всех возможностей и список разрешённых в конкретной сессии — разные сущности.

## 3. Матрица приёмки

Для каждого обнаруженного tool хранить: source symbol/line/SHA, arguments и nullable/required semantics; read/write; deployment/plugin requirements; CLI operation mapping; classification; differences; fixtures/tests; last target verification.

Обязательные классификации: planned-v0.1, planned-v0.2, deferred, excluded-cloud-only, excluded-product-scope, unsupported-target, unclassified. Последнее требует решения перед заявлением «inventory complete».

Отдельные метрики:

- **Inventory coverage:** доля обнаруженных tools с явным решением; не отражает реализацию.
- **Semantic implementation coverage:** принятые operation/argument cases, покрытые implementation + tests; denominator фиксируется scope релиза.
- **Target verification coverage:** возможности, проверенные на конкретном Jira deployment/build и permission profile.

## 4. Важные решения

`jira_batch_get_changelogs` и `jira_move_issue` явно помечены upstream как cloud_only [S2–S3]; не переносить Cloud endpoints в DC. Поздняя DC-композиция истории может быть отдельной capability с ограничениями, а не ложным batch parity.

`jira_get_project_issues` может покрываться JQL search, но только после проверки semantics. `jira_get_field_options` не считается полностью покрытым только потому, что create/edit metadata вернули часть allowed values. `get_issue` частичный набор fields/sections не равен всем upstream expand modes. Display-name resolution и default null semantics сравниваются отдельно.

JSM, ProForma, SLA и development info требуют отдельной проверки plugins/version/rights. HTTP 403 не доказывает отсутствие plugin. Unavailable `changelog` нельзя возвращать как пустую полную историю. Удаления и массовые записи сознательно исключены из первых релизов.

## 5. Reference equivalence tests

Сравнивать не byte-identical MCP JSON, а выбранные domain facts: issue IDs, texts, field values/null, pagination membership, link direction, transition metadata и error category. MCP presentation и extra fields не являются контрактом jiractl. Для мутаций сравнивать planned request и observable postconditions в sandbox, не дважды исполнять одну запись на production.

Если upstream поведение расходится с Jira docs/target: воспроизвести минимальный случай, сохранить evidence, принять intentional divergence через ADR. Не копировать bug лишь ради parity. Обновление pin — отдельный PR с inventory diff и targeted regression suite.
