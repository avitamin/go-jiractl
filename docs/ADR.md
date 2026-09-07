# Architecture Decision Records

Standalone status **Accepted** имеют только ADR-002 и ADR-011 по утверждённому handoff пользователя. Остальные ADR сохраняют standalone status **Proposed**.

T01, 2026-09-06: для read-only v0.1 приняты только указанные границы ADR-001, ADR-003–006, read-only части ADR-007 и ADR-008/010; это scoped acceptance, не смена standalone status этих ADR. Нормативные уточнения помечены T01 в CLI contract. Write-решения, включая write-часть ADR-007, остаются proposed. Shared DTO находятся в `internal/domain`; JSON Schema examples проверяются Go tests пакета `contracts` с закреплённым `github.com/google/jsonschema-go v0.3.0`. Это focused contract tests, а не полный validator/inventory из T-TOOLING. Primary владеет contracts/domain/dependency lock/CLI integration; T02 — config/transport/security; T03 — output/store; T04 — synthetic fixtures/bench.

## ADR-001. CLI + Skill вместо обязательного MCP runtime

**Контекст.** Цель — уменьшить model-visible overhead, а не заменить протокол ради замены. Progressive disclosure и короткие команды подходят coding-agent workflow [S4, S7].

**Решение.** `jiractl` вызывается из shell. Skill содержит выбор сценария и safety rules. Подробные схемы доступны через `describe` и файлы. В обычной сессии нет подключения mcp-atlassian.

**Альтернативы.** Настроить ENABLED_TOOLS/TOOLSETS и read-only MCP; сделать CLI-прокси к MCP; fork MCP. Настроенный MCP обязательно входит в baseline: upstream уже умеет ограничивать инструменты [S1].

**Последствия.** Появляется собственный контракт и тесты. Экономия не гарантирована протоколом. MCP wrapper может быть добавлен позднее над тем же application layer, без изменения семантики.

**Пересмотр.** Если настроенный MCP даёт сопоставимую стоимость/надёжность, а сопровождение CLI не окупается.

## ADR-002. Go, Cobra, Viper и собственный HTTP adapter

**Статус: Accepted, 2026-09-05.** Пользователь выбрал Go и утвердил bootstrap.

**Контекст.** Go знаком владельцу проекта. Upstream mcp-atlassian реализован на Python [S2], но остаётся behavioral reference без runtime-зависимости.

**Решение.** Модуль `github.com/avitamin/go-jiractl`; Go 1.27.1, Cobra v1.10.2, Viper v1.21.0. Версии закрепляются в `go.mod`, checksums — в `go.sum`. Entrypoint — `cmd/jiractl`; `internal/cli`, `internal/config`, `internal/buildinfo` реализуют bootstrap. Каждый root получает собственный Viper. Слой `cli → application → domain ports → Jira DC HTTP adapter` использует Go structs, `encoding/json`, `net/http` и `httptest`; fixed read transport существует в рабочем дереве, но reusable Jira mock ещё отсутствует.

**Альтернативы.** TypeScript и CLI-прокси к MCP. Выбран Go с учётом опыта владельца, компиляции в бинарник и стандартной библиотеки. Импорт upstream internals связывал бы runtime с чужими внутренними API.

**Последствия.** Bootstrap включает version, TOML/env/flag configuration, unit-тесты, Makefile и CI. JSON Schema сохраняются как продуктовые контракты; runtime validation, HTTP adapter и store требуют отдельных slices. Go-инструменты для полного pack validation и upstream inventory отложены в T-TOOLING.

**Пересмотр.** Если подтверждённая стоимость сопровождения adapters превысит выгоду контроля. Публичный CLI/JSON контракт не зависит от языка.

## ADR-003. Pinned behavioral reference, не one-command-per-tool

**Решение.** Зафиксировать `22369b76d6c1775a9730ba7d7cb37d49f7da671a` как начальную точку reference [S3]. Сначала извлечь inventory, затем классифицировать DC support и продуктовый приоритет. Общая операция поиска может покрывать несколько upstream tools. Разделять `observed`, `planned`, `implemented`, `tested`, `verified_on_target`.

**Альтернативы.** Скопировать все команды MCP и объявить parity; следить за main автоматически. Оба варианта создают нестабильный scope и могут принести Cloud-only операции.

**Последствия.** Coverage — матрица возможностей/параметров/ограничений, а не процент названий. Upstream считается reference, но не абсолютной истиной: Jira docs и целевой deployment имеют приоритет при расхождении. Каждое намеренное отличие документируется.

## ADR-004. Ограниченный JSON, lossless artifacts, отсутствие LLM внутри

**Решение.** Default brief projection, один JSON envelope, byte budget. Когда результат не помещается, сохранить полную запрошенную нормализованную выдачу и вернуть artifact reference. `artifact read` позволяет локально читать диапазоны. LLM summarization, embeddings и opaque TOON-подобная компрессия не входят в v0.1.

**Причина.** Семантическая компрессия может терять важные требования, а слишком короткие неочевидные ключи ухудшают использование. JSON понятен агентам и CI. Реальная экономия достигается выбором нужных данных и исключением повторений.

**Последствия.** Артефакты могут содержать чувствительные данные. Нужны quota, retention, permissions, provenance и явная полнота. Не обещать токеновую экономию при чтении полного большого корпуса.

## ADR-005. Stateless process, небольшой локальный state

**Решение.** Каждый CLI invocation завершается сам; нет daemon. Сетевые reads по умолчанию live. Immutable artifacts/snapshots лежат в user state directory, вне репозитория. Checkpoint metadata и mutation ledger — локальная SQLite с транзакциями и locking; blobs — отдельные immutable файлы. SQLite — не очередь фоновых работ и не workflow engine.

**Namespace.** Полный canonical base URL, profile, подтверждённый principal, format version. Секрет не используется как имя директории. Смена credentials требует проверки identity до сетевого reuse metadata. Offline snapshot read использует recorded identity, ничего не обещает о текущих правах Jira.

**Freshness.** Metadata cache TTL по умолчанию 15 минут. Issue reads не имеют неявного persistent response cache в v0.1. Snapshot — сознательно исторические данные. Immutable refs читаются без сети.

**Последствия.** Работа возможна после перезапуска агента. Cached данные могут пережить отзыв доступа — локальное удаление/retention регулируется отдельно. При требовании мгновенного server-side revocation нельзя обещать его локальному snapshot.

## ADR-006. Batch — обычный код; snapshot не транзакция Jira

**Решение.** `snapshot create` фиксирует membership, затем детерминированно гидратирует capture units с bounded concurrency. `resume` продолжает pending units. Внутри нет LLM, subagents и универсального DAG scheduler.

**Ограничение.** JQL pagination и несколько REST reads не образуют атомарный срез Jira. Стабильный ORDER BY уменьшает дрейф, но не исключает пропуски при изменениях. Сохранять capture window, IDs, source.updated и consistency=`best_effort`. Exact point-in-time snapshot требует отдельного server-side механизма и не обещается.

**Последствия.** Для массового анализа агент тратит решения на смысл, а не сетевой цикл. Обнаруженная неполнота видна в manifest. Resume не переписывает уже завершённые units; свежий полный срез создаётся новым capture.

## ADR-007. Read-first, затем plan/apply и осторожные retries

**Решение.** v0.1 не реализует мутаций. v0.2: plan → inspect/authorization → apply → receipt. Профиль должен разрешать запись; apply требует digest конкретного плана. В начальной версии план содержит одну серверную write-operation. Многооперационных транзакций/rollback нет.

**Проверки.** План привязан к principal/base URL, payload, TTL и expected state. Перед apply заново проверить metadata, состояние затрагиваемых полей и transition availability. Read-after-write используется для подтверждения где применимо. Generic API escape hatch отсутствует.

**Принципиальное ограничение.** Client-side preflight не атомарный compare-and-swap. Без проверенного server-side условного обновления остаётся TOCTOU. Для write timeout после отправки outcome=`unknown`, auto retry запрещён. Локальный ledger не превращает Jira в exactly-once API.

**Граница безопасности.** Digest — защита от случайного применения другого плана, **не доказательство человеческого одобрения**. Если тот же агент имеет PAT и произвольный shell, он технически может обойти CLI. Сильное separation of duties требует отдельного execution boundary/credential broker или прав Jira. В scope v0.2 — защитный workflow, а не sandbox для враждебного агента.

## ADR-008. Deployment-aware metadata и строгая типизация входов

**Решение.** Не hardcode transition IDs, custom field IDs, названия Epic и Cloud accountId. Использовать IDs от target metadata; mapping profile — только явный. Ambiguous display name — ошибка. `null` означает очистить поле, отсутствующее свойство — не менять. Create/edit/transition metadata различаются и не взаимозаменяемы [S9].

**Последствия.** Больше discovery reads, но меньше опасных догадок. Тип текста Jira DC сохраняется явно; ADF Cloud не используется по умолчанию. Unsupported field shape возвращает actionable error, не silent drop.

## ADR-009. Явные роли для whole-task делегирования

**Решение о моделях принято пользователем.** Sol — contract owner/integrator, именованный implementer (medium) и независимый reviewer (high). Luna — researcher, fixture_writer и routine_worker (low); последний выполняет только детерминированные проверки, краткие логи, точные механические правки и явно разрешённые commits. Terra — documentation_writer (medium). Модель/effort заданы явно в custom agent files [S5–S6]. Общий default subagent остаётся Terra/medium; именованные роли используют override. Если named role недоступна, модель не подменяется молча. Остальной процесс ниже — proposed для продуктовых slices.

**Процесс.** Максимум три активных субагента; без рекурсивного делегирования. Каждый получает одну ограниченную законченную задачу: цель, cwd, allowed paths, релевантные sources и acceptance commands — без полного контекста проекта. Для named override создаётся fresh session. Один writer владеет пересекающимися путями. Planned product task с `Txx`/`Exx` и существующим base commit передаёт schema-handoff; routine/docs/smoke передают компактный evidence-отчёт без выдуманных task ID или SHA. Два correction rounds, затем эскалация. Повторять checks и исполнять tests на integration head только после изменения либо при недостаточном evidence; статус DONE назначает integrator.

**Альтернативы.** 100 новых сессий; рекурсивная оркестрация; отдельный агент на каждую мелкую функцию; универсальный workflow engine до появления продукта. Отвергнуты как лишние накладные расходы.

**Пересмотр.** Durable execution между машинами/днями и большим числом независимых запусков станет реальным требованием. Тогда orchestration добавляется вне CLI adapter.

## ADR-010. Security and efficiency — исполняемые gates

**Решение.** Unit + contract + property + fault-injection + integration + agent eval. Baseline включает полный MCP и tuned MCP с одинаковой семантикой. Сравниваются success, completeness, tokens, requests, latency и recovery, а не только длина одного stdout.

**Последствия.** Дополнительные eval-затраты ограничены фиксированным corpus. Важные регрессии видны до расширения покрытия. Benchmark не должен использовать production issue text без разрешения.

## ADR-011. Собственный Jira HTTP mock на Go

**Статус: Accepted, 2026-09-07.**

**Решение.** Прежняя внешняя mock-инфраструктура не входит в целевую документацию. `net/http/httptest` реализует test-only helper `internal/testjira`; E2E запускают настоящий `jiractl` из `tests/e2e`. API typed и finite, wire fixtures независимы от production normalizer. Runtime imports, CLI flags/env/headers для scenario и публичные CLI изменения запрещены.

**Причина.** Нужны строгие проверяемые Jira REST exchanges, TLS и subprocess без отдельного service/runtime dependency. Мок не является Jira emulator, daemon, Admin API, DSL или JQL parser.

**Последствия.** T02/T04/T05/T06/T08 получают work из `JIRA-MOCK-ACCEPTANCE.md`; требуются handler, corpus, recorder, self-tests и subprocess E2E. В текущем checkout это Accepted design, но implementation/evidence остаются `not_run`.
