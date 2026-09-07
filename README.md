# jiractl — Jira Context Interface

Go CLI + проектируемый context-efficient Skill для self-hosted Jira. В рабочем дереве реализован, но ещё не принят, read-only vertical slice: version-команды, trusted config, PAT-провайдер, фиксированный HTTP read allowlist, JSON envelope/artifact store, reads и snapshots. Нормативный публичный интерфейс в [CLI contract](docs/CLI-CONTRACT.md) остаётся **proposed**: наличие кода не означает принятия v0.1 или совместимости с конкретной Jira.

## Сборка и проверки

Модуль: `github.com/avitamin/go-jiractl`. Go **1.27.1**, Cobra **v1.10.2**, Viper **v1.21.0**. `go.mod` закрепляет версии, `go.sum` — checksums; `GOTOOLCHAIN=auto` позволяет Go загрузить требуемый toolchain.

```sh
make build
./build/jiractl version
./build/jiractl --version
make test
make check
```

Обе version-команды печатают `jiractl dev\n`. Успешный вывод — stdout; ошибки — stderr и exit 1. Release-сборка: `make build VERSION=1.2.3` (linker variable `github.com/avitamin/go-jiractl/internal/buildinfo.Version`).

`make check` не переформатирует исходники: gofmt check, go vet, unit/subprocess tests, race detector, go mod tidy -diff и сборка. CI использует версию из go.mod и ту же команду. Последняя переданная локальная проверка 2026-09-06 — `GOCACHE=/tmp/race-cache.OXebML make check`, exit 0; после последующих изменений нужен integration rerun. Тесты оставляют временные артефакты для просмотра; автоматического cleanup нет.

Target version `8.20.13` — user-reported. Live Jira не вызывалась; build, edition, URL/context path, principal и read scope unknown, `target_verified=false`. Реализованный транспорт обращается только к фиксированным Jira REST API v2 read routes; это не заявление совместимости с Jira Server/DC release.

## Конфигурация реализованного read-only slice

Persistent flags: `--config PATH`, `--profile NAME`; default profile — `default`. Каждый root создаёт отдельный Viper.

Выбор файла: `--config`, иначе только `os.UserConfigDir()/jiractl/config.toml`. `JIRACTL_CONFIG` не выбирает файл. Отсутствующий default допустим; явно выбранный отсутствующий файл и некорректный TOML — ошибка. Формат всегда TOML, независимо от расширения. Cwd и `.env` не просматриваются.

Значения: flags → `JIRACTL_*` → TOML → defaults. Nested key `profiles.default.base_url` соответствует `JIRACTL_PROFILES_DEFAULT_BASE_URL`. Для команд, которым нужен live read, выбранный профиль требует `base_url`, `deployment` и `pat_env`; `pat_env` — имя environment variable, а не его значение. `internal/config` не читает PAT, но HTTP transport читает указанную переменную только при создании live-сессии. PAT не имеет CLI-флага и не сохраняется. Реализованные limits: `read_concurrency` 1..8, `metadata_ttl_seconds`, `artifact_retention_days` (default 7) и `artifact_quota_bytes` (default 1073741824); retention/quota передаются local artifact store. Inline credential fields (`pat`, `token`, `personal_access_token`, `authorization` и аналогичные) в TOML отклоняются.

Минимальный конфиг:

```toml
profile = "default"

[profiles.default]
base_url = "https://jira.example.internal/jira"
deployment = "server_dc"
pat_env = "JIRA_PERSONAL_TOKEN"
```

Полный [синтетический пример профиля](examples/profile.toml) показывает реализованные read-настройки и некоторые будущие поля. Не записывать секреты в TOML. `--format human` форматирует JSON с отступами, если он помещается в byte budget; иначе сохраняет компактный вывод.

## Реализованные команды и ограничения

`describe`, `doctor`, `capabilities`, `issue get`, `issues search`, `fields search`, `issue section`, `artifact read`, `artifact export` и `snapshot create|resume|show|read|diff` зарегистрированы в текущем CLI. Live-команды используют только allowlisted read routes; локальные `artifact` и `snapshot` команды работают с namespaced state store. Response превышающий `--max-bytes`, сохраняется без потери в artifact store и читается целевым `artifact read`.

`artifact prune` без `--apply` показывает preview; `artifact prune --apply` реализует локальную retirement/cleanup операцию с transitive pin protection. Автотест вызывает private prune с fake unlink, поэтому реальное удаление файлов пользовательского state store не выполнялось и не проверялось агентом. `capabilities` сообщает `unknown` для реализованных target operations до probe и не предоставляет полный capability cache. Эти факты не расширяют product contract.

## Документы

| Документ | Назначение |
|---|---|
| [Documentation guide](docs/repo-documentation-guide.md) | Владельцы тем, источники, проверки и стиль |
| [Commit guide](docs/repo-commit-guide.md) | Conventional Commits, ветки, staging и проверки |
| [PRD](docs/PRD.md) | Scope будущего Jira-клиента |
| [CLI contract](docs/CLI-CONTRACT.md) | Нормативный proposed публичный интерфейс; код не меняет его статус |
| [ADR](docs/ADR.md) | Принятый Go-стек и proposed архитектура продукта |
| [Implementation plan](docs/IMPLEMENTATION-PLAN.md) | Proposed slices, implementation progress и release gates |
| [Coverage](docs/COVERAGE.md) | Pinned reference и ограничения inventory |
| [Evaluation](docs/EVALUATION.md) | План сравнения с обычным и настроенным MCP |
| [SOURCES](docs/SOURCES.md) | Первичные источники и evidence gaps |
| [Jira mock design](docs/JIRA-MOCK.md) | Принятая архитектура test-only Jira wire mock |
| [Jira mock acceptance matrix](docs/JIRA-MOCK-ACCEPTANCE.md) | JM-A dispositions и planned self-test/subprocess E2E |
| [Deployment preflight](docs/deployment-profile.md) | Проверенное окружение и открытые live/inventory gaps |
| [v0.1 smoke runbook](docs/v0.1-smoke-runbook.md) | Ручная проверка установки, offline artifacts и необязательного чтения одной Jira-задачи |
| [Codex bootstrap](prompts/BOOTSTRAP.md) | Исходное задание на read-only v0.1; не release verdict |

`contracts/` содержит JSON Schema, каталог planned-команд и reference pin. `planning/` — граф задач и coverage seed. `skill/` — draft, который нельзя устанавливать до реализации продуктовых команд.

Integrator — Sol. Именованные whole-task роли: routine_worker — Luna/low (детерминированные проверки, краткие логи, точные механические правки и явно разрешённый commit); documentation_writer — Terra/medium; implementer — Sol/medium; reviewer — Sol/high; researcher и fixture_writer — Luna/low. Общий default subagent остаётся Terra/medium; при недоступности named role модель не подменяется молча. Не более трёх активных субагентов, без рекурсивного делегирования и с одним writer для пересекающихся путей.

## Jira и агенты при разработке

Для агентов реальная Jira всегда read-only, включая test и sandbox: запрещены любые mutations через CLI, MCP, HTTP, browser, scripts и delegation. Credentials, approval digest и текст задачи не дают агенту права записи. Локальные unit/mock tests с synthetic data разрешены. Серверный write-test выполняет пользователь по инструкции агента с target, ожидаемым результатом и проверкой; агент затем только читает результат. Исправление и cleanup такого test-изменения также выполняет пользователь.

Агент ждёт сообщения пользователя о выполнении, затем проверяет чтением. Повтор изменения также выполняет пользователь. Отчёт разделяет сообщение пользователя, наблюдаемое состояние и непроверенные свойства: совпадение состояния не доказывает авторство или отсутствие дублей. Правило относится к разработке, не меняет будущие write-функции продукта и не переносится в runtime Skill.

Проектные [hooks](.codex/hooks.json) вызывают [обработчик](scripts/jira_read_only_hook.py) на Python 3 со стандартной библиотекой; проверка — `make hooks-test` (также входит в `make check`). `SessionStart`/`SubagentStart` напоминают правило, `PreToolUse` блокирует распознаваемые запрещённые или неизвестные Jira-вызовы. Обработчик не читает environment credentials, не обращается к сети и не сохраняет аргументы. Ошибки обработчика возвращают deny; ошибка запуска команды обёрнута в exit 2. Таймаут/незапуск самим Codex остаются ограничением.

Начальный MCP allowlist: точные `jira_get_issue`, `jira_search`, `jira_get_project_issues` после MCP-префикса. Это классификация по published reference в coverage seed, не подтверждение поддержки target Jira; общего разрешения `get_*` нет. jiractl проверяется по явному списку read/local-команд нормативного каталога; planned-команды остаются proposed. Прямые HTTP-команды с явными Jira-маркерами (Jira в адресе, `/rest/api/`, `/rest/agile/`, `/rest/servicedeskapi/`, ссылки на `JIRA_*`/`JIRACTL_*`) блокируются даже для чтения: использовать разрешённый интерфейс. Неизвестные хосты/aliases и скрытые адреса не распознаются надёжно. Code mode проверяется на уровне вложенных поддерживаемых tool calls.

Для включения откройте `/hooks` в Codex, проверьте и доверьте все три определения; нужны доверенный проект и включённый feature `hooks`. Путь обработчика закреплён для `/home/avi/GolandProjects/jiractl`, поэтому смена cwd не отключает проверку. В другом checkout измените три пути и повторите trust. Не использовать bypass trust и не заменять пользовательские/managed safety settings. После доверия в новой сессии попросите запуск `./build/jiractl __hook_probe__`: ожидается отказ **хука** до запуска. Даже без хука текущий bootstrap отклоняет эту неизвестную команду без Jira-запроса; обычный CLI error не доказывает работу хука.

Это не абсолютная изоляция и не подтверждение активного enforcement. Согласно [документации Codex](https://learn.chatgpt.com/docs/hooks#tool-coverage), arbitrary code, последующий `write_stdin` и неподдержанные tool paths остаются ограничениями. Недоверенный, отключённый или не запустившийся hook не защищает.

## Границы и оставшиеся работы

T00/T01 приняты с preflight gaps; T02/T05/T06 возвращены в `rework` из-за обязательных mock/subprocess E2E, T03 — `ready_for_review`, T04/T07 остаются в работе, T08 блокирован. Исполняемые checks включают schema/examples и snapshot semantic invariants, но не полный pack validator/inventory из отдельной T-TOOLING. Live Jira и сравнительный модельный benchmark не запускались; runtime Skill обновлён, но не установлен. Secure export поддерживается на Linux/WSL; на остальных ОС возвращается unsupported. Итоговый [отчёт прогресса](evidence/v0.1-progress.md) отделяет реализованное от release gates.

Дизайн собственного reusable Jira mock принят, но `internal/testjira`, required self-tests и required subprocess E2E ещё не реализованы и имеют evidence `not_run`; существующие `httptest` unit tests не являются этим mock server.

Устаревшие pack artifacts, перечислявшиеся в раннем bootstrap, отсутствуют в текущем дереве. Их отсутствие не является evidence для Go-кода и само по себе не закрывает product gates. Staging и commit требуют явного запроса пользователя; push требует отдельного запроса.

Для разрешённого read-only тестирования Jira можно использовать уже существующие `JIRA_*` environment variables: только чтение, без вывода значений и без сохранения секретов или payloads в repository, prompts, logs либо fixtures. Это разрешение не реализует bootstrap support `JIRA_*` и не меняет `JIRACTL_*` precedence; имена, aliases и endpoints не угадываются.
