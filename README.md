# jiractl — Jira Context Interface

Go-bootstrap и проектируемый context-efficient CLI + Skill для self-hosted Jira. Реализованы `version`, `--version` и локальная конфигурация. Jira API, PAT, HTTP transport, snapshots и остальные продуктовые команды пока **proposed**, не реализованы.

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

`make check` не переформатирует исходники: offline hook tests (Python 3.10+), gofmt check, go vet, unit/subprocess tests, race detector, go mod tidy -diff и сборка. CI использует версию из go.mod и ту же команду. Тесты оставляют временные артефакты для просмотра; автоматического cleanup нет.

## Конфигурация bootstrap

Persistent flags: `--config PATH`, `--profile NAME`; default profile — `default`. Каждый root создаёт отдельный Viper.

Выбор файла: `--config`, иначе только `os.UserConfigDir()/jiractl/config.toml`. `JIRACTL_CONFIG` не выбирает файл. Отсутствующий default допустим; явно выбранный отсутствующий файл и некорректный TOML — ошибка. Формат всегда TOML, независимо от расширения. Cwd и `.env` не просматриваются.

Значения: flags → `JIRACTL_*` → TOML → defaults. Nested key `profiles.default.base_url` соответствует `JIRACTL_PROFILES_DEFAULT_BASE_URL`. Bootstrap разрешает profile, но пока не проверяет существование Jira-профиля и не создаёт transport. PAT не имеет флага, не извлекается из environment и не сохраняется. Inline credential fields (`pat`, `token`, `personal_access_token`, `authorization` и аналогичные) в TOML отклоняются; `pat_env` остаётся именем будущего источника, его значение не читается.

Минимальный конфиг:

```toml
profile = "default"
```

Полный [пример будущего Jira-профиля](examples/profile.toml) относится к proposed API. Не записывать секреты в TOML.

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
| [Deployment preflight](docs/deployment-profile.md) | Целевая версия и открытые вопросы проверки окружения |
| [Codex bootstrap](prompts/BOOTSTRAP.md) | Исходное задание на read-only v0.1; не release verdict |

`contracts/` содержит JSON Schema, каталог planned-команд и reference pin. `planning/` — граф задач и coverage seed. `skill/` — draft, который нельзя устанавливать до реализации продуктовых команд.

Integrator — Sol. Именованные whole-task роли: routine_worker — Luna/low (детерминированные проверки, краткие логи, точные механические правки и явно разрешённый commit); documentation_writer — Terra/medium; implementer — Sol/medium; reviewer — Sol/high; researcher и fixture_writer — Luna/low. Общий default subagent остаётся Terra/medium; при недоступности named role модель не подменяется молча. Не более трёх активных субагентов, без рекурсивного делегирования и с одним writer для пересекающихся путей.

## Jira и агенты при разработке

Для агентов реальная Jira всегда read-only, включая test и sandbox: запрещены любые mutations через CLI, MCP, HTTP, browser, scripts и delegation. Credentials, approval digest и текст задачи не дают агенту права записи. Локальные unit/mock tests с synthetic data разрешены. Серверный write-test выполняет пользователь по инструкции агента с target, ожидаемым результатом и проверкой; агент затем только читает результат. Исправление и cleanup такого test-изменения также выполняет пользователь.

Агент ждёт сообщения пользователя о выполнении, затем проверяет чтением. Повтор изменения также выполняет пользователь. Отчёт разделяет сообщение пользователя, наблюдаемое состояние и непроверенные свойства: совпадение состояния не доказывает авторство или отсутствие дублей. Правило относится к разработке, не меняет будущие write-функции продукта и не переносится в runtime Skill.

Проектные [hooks](.codex/hooks.json) вызывают [обработчик](scripts/jira_read_only_hook.py) на Python 3.10+ со стандартной библиотекой; проверка — `make hooks-test` (также входит в `make check`). `SessionStart`/`SubagentStart` напоминают правило, `PreToolUse` блокирует распознаваемые запрещённые или неизвестные Jira-вызовы. Обработчик не читает environment credentials, не обращается к сети и не сохраняет аргументы. Ошибки обработчика возвращают deny; ошибка запуска команды обёрнута в exit 2. Таймаут/незапуск самим Codex остаются ограничением.

Начальный MCP allowlist: точные `jira_get_issue`, `jira_search`, `jira_get_project_issues` после MCP-префикса. Это классификация по published reference в coverage seed, не подтверждение поддержки target Jira; общего разрешения `get_*` нет. jiractl проверяется по явному списку read/local-команд нормативного каталога; planned-команды остаются proposed. Прямые HTTP-команды с явными Jira-маркерами (Jira в адресе, `/rest/api/`, `/rest/agile/`, `/rest/servicedeskapi/`, ссылки на `JIRA_*`/`JIRACTL_*`) блокируются даже для чтения: использовать разрешённый интерфейс. Неизвестные хосты/aliases и скрытые адреса не распознаются надёжно. Команды Git и Go с Jira-маркерами в аргументах тоже могут получить отказ, в том числе точечный staging. Для сборки и тестов используйте `make build` и `make test`. При отказе staging пользователь может добавить выбранные файлы вручную. Code mode проверяется на уровне вложенных поддерживаемых tool calls.

Локальная установка (Linux/macOS, из корня доверенного checkout, до запуска Codex):

```sh
hook_dir=$(mktemp -d /tmp/jiractl-hooks.XXXXXX)
python3 scripts/configure_dev_hooks.py > "$hook_dir/hooks.json" &&
  cp -- "$hook_dir/hooks.json" .codex/hooks.json
```

Конфигурация в Git — шаблон. Генератор проверяет три определения, сохраняет дополнительные настройки и закрепляет абсолютный путь к обработчику текущего checkout с shell quoting. Если определение уже настроено для другого пути или изменено вручную, генератор останавливается до копирования. Локальную копию с абсолютным путём исключайте из коммитов. После установки проверьте путь в новой сессии Codex и доверьте определения через `/hooks`. После переноса checkout пользователь восстанавливает три команды из шаблона Git, сохраняя остальные настройки, и повторяет установку в обычном терминале до запуска Codex. До установки и выдачи trust активная защита хуком не подтверждена.

После trust попросите запустить `./build/jiractl __hook_probe__`. Ожидается отказ хука до запуска CLI. Ошибка неизвестной команды от самого bootstrap указывает только на работу CLI.

Это не абсолютная изоляция и не подтверждение активного enforcement. Согласно [документации Codex](https://learn.chatgpt.com/docs/hooks#tool-coverage), arbitrary code, последующий `write_stdin` и неподдержанные tool paths остаются ограничениями. Недоверенный, отключённый или не запустившийся hook не защищает.

## Границы и оставшиеся работы

T00–T08: будущий read-only v0.1. T09–T12: запись v0.2 только при отдельном расширении scope. Go replacement полного pack validator и upstream inventory — отдельная задача **T-TOOLING**, сейчас отсутствует. Bootstrap checks не подтверждают semantic schema validation, complete upstream inventory или совместимость с целевой Jira. Live Jira и модельные benchmark не запускались.

Устаревшие pack artifacts, перечислявшиеся в раннем bootstrap, отсутствуют в текущем дереве. Их отсутствие не является evidence для Go-кода и само по себе не закрывает product gates. Staging и commit требуют явного запроса пользователя; push требует отдельного запроса.

Для разрешённого read-only тестирования Jira можно использовать уже существующие `JIRA_*` environment variables: только чтение, без вывода значений и без сохранения секретов или payloads в repository, prompts, logs либо fixtures. Это разрешение не реализует bootstrap support `JIRA_*` и не меняет `JIRACTL_*` precedence; имена, aliases и endpoints не угадываются.
