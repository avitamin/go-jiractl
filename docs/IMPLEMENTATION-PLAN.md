# План реализации для Codex: Sol + Terra + Luna

Статус: Proposed. План ориентирован на небольшие законченные slices, не на максимальное количество агентов. Источник machine-readable задач — `planning/tasks.json`. Это **не готовый scheduler**, а входной план для Sol и команды.

## 0. Выполненный scope bootstrap и отложенные инструменты

Bootstrap: version-команды, локальная конфигурация, Go-каркас, Makefile/CI и repo guides. T00–T08 остаются pending: bootstrap не означает принятие read-only v0.1.

**T-TOOLING (future, отдельная задача):** реализовать на Go полный validator schemas/registry/examples и инструмент pinned upstream inventory с тестами и явным разделением static/runtime evidence. Текущие checks не заменяют эти инструменты. Их реализация не входит в bootstrap.

Именованные роли: routine_worker — Luna/low; documentation_writer — Terra/medium; implementer — Sol/medium; reviewer — Sol/high; researcher и fixture_writer — Luna/low. В `.codex/config.toml` общий `default_subagent_model = "gpt-5.6-terra"` и medium effort сохранены; override именованных ролей явный.

## 1. Цель первого прохода

Получить проверяемый v0.1: `doctor → issue get/search → snapshot 100 → targeted reads → diff`, без write endpoint handlers. Первый рабочий вертикальный slice нужен раньше широкого покрытия. T00–T08 — обязательная первая итерация. T09–T12 — отдельная запись v0.2; E-серия — будущие возможности по подтверждённой потребности.

Критический путь: `T00 → T01 → (T02 ∥ T03 ∥ T04) → T05 → T06 → T07 → T08`. Dependency graph не означает одновременную работу над общими файлами. После каждого merge integrator перепроверяет целевой head.

## 2. Роли и настройки

| Роль | Модель / effort | Работа | Не поручать |
|---|---|---|---|
| Integrator, основной Codex | Sol / medium по умолчанию; high для contracts/security gates | Решения, contracts, декомпозиция, review расхождений, merge и release verdict | Рутинный обход всех endpoint files |
| Routine worker | Luna / low | Детерминированные проверки, краткие логи, точные механические правки, явно разрешённый commit | Архитектура, product contracts, неявный commit |
| Documentation writer | Terra / medium | README, guides, инструкции и проверенная документация | Продуктовый код и contracts |
| Implementer | Sol / medium | Законченный slice с тестами и ограниченными file ownership | Самовольное изменение контракта/рекурсивный spawn |
| Reviewer | Sol / high, read-only | Независимый correctness/security review, проверка evidence | Самостоятельное объявление релиза принятым |
| Researcher | Luna / low, read-only | Инвентарь, поиск source symbols, конкретные факты | Догадки о DC API, security decisions |
| Fixture writer | Luna / low | Синтетические fixtures и repetitive tests по frozen schema | Реализация auth/retry/write semantics |

Идентификаторы `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna` и current custom-agent format проверены в официальной документации [S5–S6]. Capability/availability проверить локально в T00. Не заменять модель молча, не снимать sandbox/approval policy ради прохождения теста.

**Лимит:** три активных субагента, без рекурсивных потомков. Обычно два implementers + один fixture/review worker, но reviewer запускается после появления содержательного slice, а не непрерывно. По умолчанию не Ultra: здесь нужен контролируемый task graph.

Каждому worker передают одну whole bounded task: цель, cwd, allowed paths, только необходимые sources и acceptance commands. Для named override создают fresh session. Каждый writer получает отдельный git worktree и явную рабочую директорию. Native subagents сами по себе не гарантируют разные worktrees/cwd. Если установленный клиент не позволяет надёжно задать изоляцию, использовать один writer для пересекающихся путей и параллельных read-only workers. Отдельные репозитории для ролей этой утилиты не нужны: сам инструмент — отдельный repo, который можно использовать в других repos.

## 3. Единый task protocol

Integrator выдаёт task ID, цель, cwd, ссылки на **нужные разделы**, frozen interfaces, allowed paths, базовый commit и acceptance commands. Не передаёт всем агентам все docs и полный source reference. Большие fixtures/logs остаются файлами.

У task ровно один writer-owner. `contracts/`, shared domain DTO, dependency lock и public CLI registration принадлежат integrator после согласования. Workers меняют их только как отдельную согласованную contract patch. File ownership — организационное правило, не security sandbox: CI проверяет diff по allowed paths.

Planned product task с `Txx`/`Exx` и существующим base commit завершает handoff по `contracts/handoff.schema.json`: task/base/head, changed files, tests с exit code и evidence paths, known gaps, requested contract changes. Routine/docs/smoke task возвращает компактный отчёт ≤250 слов: changed files, команды/exit codes, evidence paths и gaps — без выдуманных task ID или SHA. Формулировка «вроде работает» не является evidence.

**State:** pending → in_progress → ready_for_review → accepted; blocked/rework отдельно. Worker не присваивает accepted. Только integrator после review и актуального evidence для integration head; tests запускаются повторно лишь после последующего изменения или при недостаточном evidence. Старый зелёный CI другого commit не считается.

Не более двух correction rounds на задачу. Сначала переиспользовать текущего worker с точным reproduction, а не создавать новую сессию. После двух циклов Sol исправляет границу задачи/contract или решает проблему сам. Не гонять бесконечный validator loop. Повторять checks только после изменения или при недостаточном evidence. Capacity failure не порождает параллельные дубликаты одного writer; явная остановка/разрешённая замена фиксируется.

## 4. Задачи v0.1

### T00 — Reference и deployment preflight

**Owner:** Sol; Luna researcher извлекает факты. **Depends:** нет.

Проверить installed Codex/model IDs, Go 1.27.1 и зависимости из go.mod и окружение. Сохранить evidence upstream pin из `reference.lock.json`. В trusted environment checkout именно pinned commit. Go inventory tool ещё не реализован (T-TOOLING). После его появления сравнить static names/tags с runtime registration, где это возможно. Дополнить seed новыми tools; отсутствие checkout не выдавать за полный inventory.

Определить target Jira version/build/base context path, current principal и права read. Первые probes можно выполнить малым диагностическим script, затем заменить `doctor` в T05; не развивать отдельный временный CLI. Не считывать PAT в вывод. Запросить только необходимые metadata, не production corpus.

**Результат:** `reference-inventory.json`, `coverage.json`, `deployment-profile.md`, `evidence/preflight.json`. Нет live доступа — сохранить конкретный gap и продолжить offline; target-supported release позже остаётся заблокирован, локальные slices — нет.

**Gate:** каждый обнаруженный tool классифицирован либо явно UNCLASSIFIED; UNCLASSIFIED блокирует заявление «coverage inventoried», не весь read prototyping. Cloud-only отмечены. Нет invented IDs. Pin не изменён автоматически на main.

### T01 — Freeze contract и минимальный каркас

**Owner:** Sol; Sol reviewer. **Depends:** T00.

Принять/исправить ADR, registry, schemas и examples. Использовать Go-bootstrap `cmd/jiractl`, `internal/{cli,config,buildinfo}`. Будущие `internal/{application,domain,adapters,output,store}` добавлять по slices. Зависимости фиксируют go.mod/go.sum, базовая CI запускает make check. Сформировать golden cases и feature gates. Проверить выбранные package versions; не полагаться на «latest» в CI.

**Gate:** schemas валидируются; accepted decisions и naming согласованы; tests для контрактных инвариантов initially failing ожидаемо/контролируемо. Production pipeline не должен объявлять успех через skip всех будущих tests. Repo ownership и allowed paths опубликованы.

### T02 — Trusted config, PAT, HTTP transport

**Owner:** Sol implementer A. **Depends:** T01. **Paths:** adapters/http, config, security, связанные unit tests.

PAT provider; context-path-safe URL builder; CA/proxy configuration; no cross-origin auth redirects; timeout/deadline; semantic read retry allowlist; safe logging/error mapping. `/search` POST разрешён как read, arbitrary write routes недоступны.

**Gate:** мок-тесты 401/403/404/429/5xx/HTML login page/invalid JSON; Retry-After numeric/date/negative/absurd; secret canary; path injection; request URL фиксируется целевым instance. Никаких production mutations.

### T03 — Output codec, refs и local store

**Owner:** Sol implementer B. **Depends:** T01. **Paths:** output, store, соответствующие tests.

JSON envelope/errors; byte budget; lossless spill; range reads; immutable publication/checksum; SQLite manifests/checkpoints interface; namespace; retention/quota. `artifact prune` по умолчанию только preview. Сохранение text Unicode без разрыва JSON.

**Gate:** oversized single description, multibyte boundaries, full disk, partial write, symlink/traversal, corrupt/cross-profile ref, concurrent processes. Проверки сохранности всех selected values и ≤budget stdout, а не snapshot строкового усечения.

### T04 — Fixture corpus и baseline harness

**Owner:** Luna fixture writer для механических данных; Sol принимает harness. **Depends:** T01. **Paths:** tests/fixtures, tests/golden, bench.

Synthetic Jira DC responses: обычные и длинные issues, custom fields/null, paginated comments, hidden issue, weird keys, API caps, partial capture. Положить сценарии оценки, recorder stdout/stderr/request counts. Настроенный и default MCP baseline выполняются отдельно от runtime CLI, с тем же corpus/permissions.

**Gate:** fixtures не содержат production data/secrets; expected values объяснимы; smoke fixture generator детерминирован; benchmark сохраняет config/tokenizer/model IDs. Luna не проектирует критерии fairness самостоятельно.

### T05 — Первый vertical read slice

**Owner:** Sol implementer; Sol интегрирует. **Depends:** T02,T03,T04. **Paths:** application/read, adapters/jira_dc/read, cli/read, integration tests.

`doctor`, `capabilities`, `describe`, `issue get`, `issues search`, `fields search`, `issue section` для description/comments/links/attachment metadata. Brief/analysis DTO, strict field selection, safe identities, live vs local provenance. Сначала один `issue get` end-to-end, затем search и секции.

**Gate:** реальные invocation subprocess tests проверяют stderr/stdout/exit codes, не только service methods. Ни `*all`, ни comments/changelog без запроса. Server page cap и continuation корректны. Read-only suite доказывает отсутствие write dispatch. Начальный target smoke при наличии разрешённого окружения.

### T06 — Snapshot, resume, targeted read, diff

**Owner:** Sol implementer. **Depends:** T05. **Paths:** application/snapshot, store/checkpoint integration, cli/snapshot, tests/snapshot.

Детерминированная membership/hydration, bounded concurrency, explicit max, progress checkpoint, immutable manifests, snapshots refs, local section reads, structural diff. Capture использует уже доступные fields, не fetch-ит каждый issue второй раз без причины.

**Gate:** corpus 100 issues; cancellation + resume; duplicate IDs; issue removed/permission changed; changing updated/order; cap comments; one item failure → partial9; snapshot comparison при неполных scopes не выдаёт false deletions. Ни одного model call внутри capture/diff. После resume завершённые units не запрашиваются повторно.

### T07 — Skill и agent evaluation

**Owner:** Terra documentation_writer + Sol eval; Sol принимает UX. **Depends:** T06.

Установить `skill/jira-context` в `.agents/skills/jira-context` только когда CLI работает. documentation_writer актуализирует docs по проверенным sources; Skill ≤900 benchmark tokens, references загружаются по необходимости. Проверить discovery без чтения всего CLI manual. Сделать fixed agent runs для locate→read, 100 capture→targeted analysis, snapshot diff, recovery.

**Gate:** отчёт с cold/warm MCP and CLI, tuned baseline, success/completeness/token totals. Если цель экономии не достигнута, сначала исправлять projection/disclosure/лишние вызовы, а не добавлять endpoints. Сокращение токенов ценой потерянных требований — fail.

### T08 — Независимая приёмка v0.1

**Owner:** Sol reviewer, Sol final gate. **Depends:** T07.

Проверить security и trust boundary; публичный CLI/help против registry; full tests на integration head; сборку и запуск Go-бинарника в clean environment; read-only deployment smoke и ограниченный 100-issue test в разрешённом scope. Не выкладывать внутренние snapshots в CI artifacts публичного repo.

**Gate:** все v0.1 criteria выполнены; documented target matrix; benchmark actual numbers; реальные evidence paths/SHAs. Без live validation можно принять offline milestone, но не заявлять verified support вашей Jira. На этом остановить первый проход.

## 5. Задачи v0.2 — только после отдельного разрешения scope

**T09 — Write metadata.** Sol: project issue types, create/edit fields, allowed values, users, transition fields, link types. Отдельные DC adapters. Зависит от T08. Gate: нет Cloud ID assumptions, ambiguity/null/unsupported field tests, read-only discovery.

**T10 — Change plan/ledger.** Sol + Sol security review: immutable payload/digest/TTL/principal, profile write policy, atomic ledger, expected state, bounded reconcile. Зависит от T09. Gate: wrong digest/profile/stale state reject; concurrent apply; crash before/after send; outcome_unknown never retries. Документирован residual TOCTOU, не обещан exactly-once.

**T11 — Шесть write operations.** Sol: create, update, assign, transition, comment.add, link.create поверх T10. Handler registry не имеет generic bypass. До live tests только mocks. Gate: planned payload = applied payload, permissions/screens/required fields, explicit null, partial/ambiguous responses. В sandbox Jira разрешение даётся на конкретные тестовые изменения.

**T12 — Write acceptance.** Независимый Sol reviewer + Sol. Sandbox E2E, receipts, side effects, retries disabled, evidence after simulated response loss. Документировать отсутствие bulk/rollback и пределы approval digest. Только после gate поддержка записи становится accepted.

## 6. Расширение reference coverage

E01 Agile reads/writes; E02 worklogs/watchers/comment editing; E03 versions/components/epic relations; E04 binary attachments; E05 JSM; E06 Forms/SLA/development info; E07 project hierarchy/dependency aggregation. Одна family на итерацию, со своей deployment evidence и benchmark regression test. Plugin-dependent features не обязательны без наличия соответствующего plugin.

Перед каждой E-family: обновить exact operation contracts, назначить allowed paths и критерии ошибок, затем реализация. Не отправлять Sol задание «реализуй всё остальное из 60 tools». Cloud-only move/bulk-changelog не портировать в DC под видом parity; альтернативную DC-композицию описывать как отличающуюся capability.

## 7. CI и доказательства

Текущая bootstrap CI: `make check` (gofmt, go vet, unit/subprocess tests, race, tidy -diff, build). После T01 расширить её: schema/golden cases, security-canary, deterministic fault-injection, чистая сборка/запуск. Эти продуктовые gates ещё не реализованы. Интеграционные live Jira тесты opt-in и protected; PR от forks не получает PAT. Модельные eval — отдельный protected job с фиксированными budgets; routine unit CI не зависит от LLM.

Тестовый отчёт указывает commit, tool/package versions, command, start/end, exit code и artifact hash. Ручной Markdown «PASS» не substitute. Integrator сравнивает actual git diff с ownership и пересоздаёт aggregate status после merge. Одна bounded reconciliation round исправляет stale handoffs; не начинать с нуля весь workflow.

## 8. Что намеренно не делать

Не тянуть full mcp-atlassian в runtime. Не писать свой orchestrator/queue. Не поручать LLM HTTP pagination, checksums, validation или copy-loop. Не выдавать все инструменты в SKILL.md. Не путать static tool inventory с tested coverage. Не параллелить контрактные изменения. Не исправлять quota/capacity снятием safety ограничений. Не позволять красивому PRD заменять проверенный vertical slice.
