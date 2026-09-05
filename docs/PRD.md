# PRD: jiractl

Статус: **Proposed**. Версия спецификации: 0.1. Дата: 2026-09-05.

## 1. Проблема и продукт

Агенту нужен интерфейс Jira, в котором подключение возможностей, массовое извлечение задач и служебные ответы не занимают большую часть контекста. Простая замена MCP-вызова на CLI, возвращающий тот же огромный JSON, не решает проблему.

**Продукт:** локальный CLI с компактным, версионированным JSON; explicit field selection; управляемой пагинацией; файловыми артефактами; детерминированным batch capture; небольшим Skill с загрузкой деталей по необходимости. LLM анализирует данные и принимает решения, но не исполняет сетевой цикл «получи следующую из 100 задач».

Подход CLI + Skill и progressive disclosure отражён в Playwright CLI и документации Codex, но конкретная экономия для Jira должна быть измерена, а не перенесена из чужого benchmark [S4, S7].

## 2. Пользователи и основные сценарии

Основной пользователь — разработчик/тимлид, запускающий Codex с доступом к внутренней Jira. Потребители CLI — главный агент и субагенты в отдельных сессиях; вторичный потребитель — CI/скрипты без LLM.

**U1. Найти и уточнить.** По JQL получить компактный список. Открыть 2–3 задачи. Отдельно прочитать описание, выбранные custom fields и нужные комментарии. Не получать пользователей, историю и вложения автоматически.

**U2. Собрать 100 задач для анализа.** Одной командой зафиксировать выбранные issue IDs и получить их данные в локальный snapshot. Вывести summary + ссылку. Агентам выдавать небольшие подмножества или конкретные секции. Анализ и план реализации являются внешней работой Codex, не встроенной функцией CLI.

**U3. Продолжить после сбоя.** Повторить capture из checkpoint без повторной загрузки подтверждённых завершённых единиц. Получить явный список ошибок и временные границы наблюдений. Не выдавать частичный результат за полный.

**U4. Сравнить.** Вычислить локальную разницу двух снимков по выбранным полям. Никаких Jira-запросов или LLM-вызовов во время diff.

**U5. Безопасно изменить, v0.2.** Подготовить изменение, разрешить все идентификаторы и обязательные поля, показать план. Применить только утверждённый план. При потере ответа после отправки не создавать дубликаты слепым retry.

## 3. Границы релизов

| Релиз | Включено | Не включено |
|---|---|---|
| v0.1 | PAT/config/TLS, doctor, capabilities, issue get, JQL search, описания/комментарии/links/attachment metadata, поля, snapshot capture/resume/read/diff, artifacts, Skill, eval |
| | | Любые изменения Jira; загрузка бинарных вложений; обещание полной истории изменений |
| v0.2 | Create/update/assign issue, add comment, transition, create issue link через plan/apply; metadata discovery; ledger и uncertain-outcome handling |
| | | Delete/move, bulk writes, rollback-транзакции, обещание exactly-once |
| v0.3+ | Выбранные Agile, worklog, versions/components, watchers, attachments; Jira Service Management и plugin APIs при подтверждённой потребности/совместимости |
| | | Автоматическая поддержка всех плагинов и всех Jira-версий |

Confluence, Jira Cloud, OAuth, MCP-server runtime, web UI, vector DB, LLM summarizer, автономный daemon и универсальный workflow engine — вне исходного scope.

`mcp-atlassian` — источник инвентаря и поведения. Полнота coverage означает, что **каждая обнаруженная Jira-возможность классифицирована**, а не что всё реализовано в первом релизе. Upstream содержит Cloud-only возможности; как минимум batch changelog и move issue явно исключаются из обязательного DC-parity [S2–S3].

## 4. Функциональные требования

**FR-01 — Явный deployment.** Профиль содержит `deployment=server_dc`, полный base URL с context path и ссылку на источник PAT. Не определять Cloud/DC только по имени хоста. `/serverInfo` и `/myself` используются для диагностики версии и principal; недоступность metadata фиксируется отдельно.

**FR-02 — Ограниченный вывод.** Все data-команды возвращают один JSON envelope. По умолчанию stdout не больше 8192 UTF-8 bytes. Большие результаты сохраняются целиком в artifact, а не обрезаются байтами. Полный результат доступен по ссылке и диапазонам. Прогресс и санитизированная диагностика — stderr.

**FR-03 — Избирательное чтение.** `brief` — id/key/summary/status/assignee/updated. `analysis` дополнительно включает описание, issue type, priority, labels, components, fixVersions и issue links. Custom fields включаются только явными IDs или утверждённым profile mapping. Комментарии и другие коллекции читаются отдельно. Jira позволяет задавать fields; defaults upstream API не должны определять defaults CLI [S9].

**FR-04 — Сохранение смыслов.** Отсутствующее поле, null, недоступное поле и незапрошенное поле различаются. Отсутствие видимого issue не доказывает его отсутствия в Jira. Полные текстовые значения сохраняются; preview не заменяет исходный текст.

**FR-05 — Snapshot.** Capture имеет явный верхний предел, записывает выбранные IDs, profile/principal, query hash, fields, время наблюдения, source.updated, полноту и ошибки. Для snapshots нет неявного общего «latest». Каждый результат получает новый immutable ID.

**FR-06 — Resume.** Checkpoint принадлежит run, связан с fingerprint запроса и namespace credentials. Изменение query/fields/profile требует нового run. Повторное продолжение не переисполняет завершённые capture units, но не обещает, что Jira не изменилась между ними.

**FR-07 — Capabilities.** Различать `supported`, `unsupported`, `forbidden`, `unknown`. Capability-проверка не запускает записи и не перебирает всё API. Отсутствие плагина/прав/endpoint не маскируется одной ошибкой.

**FR-08 — Reference coverage.** Пин upstream; статический inventory + проверка runtime регистрации; явные gaps; тест на каждую поддержанную семантику. Upstream update — отдельный change request с diff, не автоматическое изменение scope.

**FR-09 — Запись.** В v0.2 все операции проходят через change plan. Никаких generic `api METHOD URL`, произвольных shell hooks и скрытой записи в read-командах. Учесть, что POST `/search` семантически read-only: запрещать не HTTP-метод, а неподдержанную операцию.

**FR-10 — Удобство агента.** Маленький Skill; `describe` только одной команды; понятные recovery hints; единые exit codes; отсутствие interactive prompts. Обнаруживаемость ошибок важнее экономии нескольких токенов в названии поля.

## 5. Нефункциональные требования

**Безопасность.** PAT передаётся Bearer-header [S8]; никогда не печатается. TLS verification включён. Поддерживается доверенный CA bundle. Запрещены cross-origin redirects с credentials, URL userinfo и произвольные URL из issue content. Локальные данные защищены правами ОС, исключены из Git и логов. Markdown, Jira wiki, комментарии и attachment names — недоверенные данные, не инструкции.

**Надёжность.** Таймауты и retries ограничены. Retry определяется семантикой операции. Local state updates атомарны. Конкурентные CLI-процессы не повреждают ledger/checkpoints. Вся важная полнота выражена машинными полями.

**Переносимость.** Первый проверяемый профиль запуска — Linux/WSL2 + Go 1.27.1 (бинарник jiractl). Пакетирование не должно мешать будущему Windows native. До проверки ACL, locking и console encoding Windows native не объявляется поддержанным. Корпоративный proxy/CA проверяется на реальной среде в T00/T08.

**Ограничение нагрузки.** Read concurrency по умолчанию 4, настраиваемое 1–8. Server page cap уважается. Ответы 429 и Retry-After обрабатываются ограниченно. Локальный state имеет quota/retention и предсказуемое поведение при disk full.

**Стоимость сопровождения.** В runtime нет MCP, orchestration framework или LLM SDK. Референсный MCP запускается только в отдельных benchmark/compatibility окружениях.

## 6. Метрики и критерии приёмки

Все числа ниже — **целевые критерии**, не результаты измерений.

| Область | Gate |
|---|---|
| Contract | 100% data-команд соблюдают response schema, exit mapping и byte limit |
| Skill | Активированный SKILL.md ≤900 токенов выбранного и зафиксированного benchmark tokenizer; metadata считается отдельно |
| Read workflow | Медиана model-visible interface tokens ≤50% от настроенного MCP на согласованном наборе read-сценариев при не меньшем task success |
| Capture 100 | Нет per-issue LLM orchestration; один вызов CLI собирает данные; stdout summary обычно ≤2 KiB |
| Correctness | 100% обязательных фактов fixtures доступны; ни один усечённый источник не помечен complete |
| Recovery | Инъекции network/disk/process ошибок дают проверяемый результат и безопасный resume |
| Secret handling | 0 утечек test secrets в stdout/stderr/artifacts/tracebacks; проверяется canary suite |
| Writes v0.2 | 0 blind retries после неопределённого результата; stale plan/неутверждённый digest отвергаются |
| Live acceptance | Проверен конкретный deployment/build Jira; точные capabilities и ограничения записаны |

Токены считать не только в stdout, но и в инструкциях, tool schemas, help/describe, вызовах, recovery и handoff. Большой snapshot, целиком прочитанный агентом, всё равно занимает контекст: перенос на диск сам по себе не делает семантический анализ бесплатным.

## 7. Неизвестные параметры и способ закрытия

Версия/build Jira, context path, корпоративные CA/proxy, доступный test project, issue types, workflow transitions, custom fields, объём комментариев и наличие JSM/plugin APIs выясняются в T00. Не угадывать IDs и не принимать Cloud schemas за DC schemas. Невозможность live probe отмечается как конкретный deployment-validation gap; offline работа продолжается.

Обязательный вход для live acceptance — согласованный test project и PAT с минимальными необходимыми правами. Для read MVP предпочтительнее учётная запись, которой на стороне Jira не разрешена запись. Это надёжнее, чем полагаться только на описание Skill.

## 8. Определение готовности

v0.1 готов после T00–T08: установка воспроизводима; contracts/fixtures проходят; 100-issue capture и resume проверены; сравнительный benchmark опубликован; ограничения deployment честно указаны; Skill не рекламирует отсутствующие команды. v0.2 готов только после отдельного review записей и sandbox Jira E2E. Пустой список известных багов не заменяет evidence от тестов.
