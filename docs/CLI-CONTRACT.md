# CLI contract: jiractl.v1

## Реализованный bootstrap

`jiractl version` и `jiractl --version` печатают `jiractl dev\n` (release version подменяется linker flag). Это текстовый служебный вывод, исключение из будущего JSON envelope. Ошибки bootstrap: stderr, exit 1; stdout ошибок пуст. Обе формы version проверяют конфигурацию перед выводом. `--help` показывает справку без загрузки конфигурации.

Persistent flags: `--config PATH`, `--profile NAME`. Отдельный Viper на экземпляр root; profile по умолчанию `default`. Файл выбирается только через `--config`, иначе `os.UserConfigDir()/jiractl/config.toml`; `JIRACTL_CONFIG` не выбирает файл. Отсутствующий default допустим, отсутствующий explicit или некорректный TOML — ошибка. Значения: flags → `JIRACTL_*` → TOML → defaults; nested key dots заменяются на underscores. Cwd и .env не используются; PAT provider и сохранение конфигурации отсутствуют. Inline credential fields в TOML отклоняются до загрузки в основной Viper.

**Остальные разделы ниже — proposed продуктовый контракт.** Jira-команды, JSON output, error taxonomy и transport ещё не реализованы.


**Нормативная спецификация, Proposed.** `MUST` — обязательное поведение; `SHOULD` — рекомендуемое с документированным исключением. Версия executable и версия wire/schema независимы. Примеры ниже иллюстрируют **будущий**, пока не реализованный CLI.

## 1. Общая форма и discovery

```text
jiractl [GLOBAL_OPTIONS] <resource> <operation> [ARGS] [OPTIONS]
```

Global options ставятся перед resource; command-specific options — после operation. Кодировки файлов и stdout — UTF-8. Default profile — `default`; для примеров настроен именно он. По умолчанию нет интерактивных вопросов, ANSI, прогресс-бара или попыток открыть браузер.

| Опция | Контракт |
|---|---|
| `--profile NAME` | Только имя существующего локального профиля; не URL |
| `--format json\|human` | По умолчанию `json`, независимо от TTY; human не является стабильным wire format |
| `--max-bytes N` | Весь stdout envelope, включая завершающий LF: default 8192; range 1024–32768 |
| `--deadline-seconds N` | Общий deadline invocation; default 60 для обычных команд, 300 для snapshot create/resume; range 1–1800 |
| `--debug` | Только санитизированная диагностика в stderr; не HTTP bodies и не Authorization |

`--help` и `--version` — явные text-mode исключения. Все остальные data-команды в json mode, включая ошибки CLI parsing, MUST вернуть один JSON object + LF. Не логировать в stdout. Abrupt SIGKILL/сбой ОС не может гарантировать envelope; caller учитывает ненулевой exit и отсутствие/невалидность JSON.

```sh
jiractl describe issues.search
jiractl describe change.apply
jiractl doctor --probe
jiractl capabilities
```

`describe COMMAND_ID` показывает только одну команду: аргументы, значения по умолчанию, result schema ID, exit codes и короткий пример. `--section summary|input|output|errors` ограничивает раздел; default summary. Большой schema result также идёт через artifact. Не печатать весь каталог инструментов в каждом ответе.

## 2. Configuration и PAT

Пользовательский config — вне репозитория, через platform-appropriate config directory. Проект не может незаметно изменить trusted base URL, secret source, CA или write policy. Не подхватывать произвольный `.env` из клонированного репозитория.

Пример `examples/profile.toml`:

```toml
[profiles.default]
base_url = "https://jira.example.internal/jira"
deployment = "server_dc"
pat_env = "JIRA_PERSONAL_TOKEN"
write_enabled = false
# ca_bundle = "/trusted/path/company-ca.pem"
read_concurrency = 4
metadata_ttl_seconds = 900
artifact_retention_days = 7
artifact_quota_bytes = 1073741824
```

Значение PAT читается из указанного environment variable; значения токена в TOML/argv не допускаются. Секретный file/keychain provider можно добавить позднее без изменения contract. PAT передаётся только `Authorization: Bearer …` [S8].

MUST сохранить context path при сборке URL. MUST отказать URL с userinfo, неподдержанным scheme, query/fragment. HTTPS обязателен в production profile. Custom CA — вместо `verify=false`. По умолчанию redirects не следовать; same-origin redirect может быть отдельно разрешён trusted config после проверки context path. Никогда не переносить PAT на другой origin.

`doctor --probe` выполняет только согласованные read probes: server info, current identity, минимальный доступ к search. Возвращает deployment/version/build/principal availability и ограничения, а не все пользовательские данные. 200 HTML от SSO proxy — protocol/authentication diagnostic, не успешный JSON-ответ. `/serverInfo` и `/myself` недоступны — отдельные состояния, а не догадка о версии.

## 3. Общий envelope

```json
{
  "schema_version": "jiractl.v1",
  "command": "issue.get",
  "status": "ok",
  "data": {
    "id": "10421",
    "key": "APP-421",
    "summary": "Сохранение формы",
    "status": {"id": "3", "name": "In Progress"},
    "assignee": {"name": "developer", "key": "u123"},
    "updated": "2026-09-04T15:30:00Z"
  },
  "meta": {
    "source": "jira",
    "profile": "default",
    "complete": true,
    "delivery": "inline",
    "observed_at": "2026-09-05T00:00:00Z"
  }
}
```

`status` — `ok|partial|error`. `command` — стабильный dotted ID, не полная command line. `meta.source` — `jira|artifact|snapshot|local`; `observed_at` для live означает время наблюдения, не время последнего изменения issue. В snapshot отдельно хранится исходное `fetched_at`; offline read не делает данные свежими.

Нормативная базовая схема — `contracts/response.schema.json`. Command data models документированы ниже; стартовые схемы — `issue`, `snapshot-manifest`, `change-plan`. Новые необязательные поля могут добавляться в `jiractl.v1`; удаление/переименование/изменение смысла/типа требует новой major schema. Consumers MUST игнорировать неизвестные optional response properties, но MUST отвергать неизвестный major schema. Входы строго валидируются: неизвестные flags/properties — ошибка, не игнорирование.

### 3.1 Что означает complete

`meta.complete=true` означает полноту **запрошенной единицы**: одного issue projection, одной страницы collection или заданного capture scope. Это не «вся Jira», не отсутствие скрытых permission-filtered issues и не автоматически весь JQL result set. Для collection обязательно отдельное pagination. Для snapshot обязательно selection/capture completeness.

Поле, которое не запрашивали, не добавляется. Поле, которое Jira вернула как null, сохраняется как null. Requested field, отсутствующее в ответе, сопровождается `meta.field_states[field]="unknown"` или конкретным доказанным состоянием. Нельзя объявлять `not_authorized` без такого свидетельства. Нельзя подменять неизвестное значение пустой строкой/массивом.

### 3.2 Переполнение вывода

Если полный command result не помещается в budget, MUST сначала атомарно записать **весь выбранный нормализованный результат** в artifact и вернуть:

```json
{
  "schema_version": "jiractl.v1",
  "command": "issues.search",
  "status": "ok",
  "data": null,
  "artifact": {"ref": "a_0123456789abcdef0123456789abcdef", "kind": "json", "bytes": 47210},
  "meta": {
    "source": "jira", "profile": "default", "complete": true,
    "delivery": "artifact", "item_count": 25,
    "pagination": {"returned": 25, "total": 100, "next_cursor": "c_0123456789abcdef0123456789abcdef"}
  }
}
```

Spill — **не data truncation**, поэтому status остаётся ok, если source complete. Вывод не содержит часть JSON или незаметно потерянные строки. Нет автоматически урезанного description под видом полного. Artifact содержит выбранные поля, а не все существующие поля Jira; исходные тексты этих полей сохраняются без semantic summarization.

Если source endpoint возвращает неполную запрошенную секцию, это partial/complete=false независимо от размещения. Если artifact нельзя безопасно сохранить, вернуть storage error; не выбрасывать данные в stdout вне budget. Envelope ошибки всегда небольшой. До записи в Jira проверить способность создать local journal/receipt; операция не должна зависеть от последующего вывода огромного payload.

## 4. Read-команды v0.1

| Command ID / CLI | Вход | Data |
|---|---|---|
| `describe` / `jiractl describe ID` | ID, optional section | Описание одной команды |
| `doctor` / `jiractl doctor --probe` | probe=false по умолчанию; без probe только local config validation | Диагностика и version/capability evidence |
| `capabilities` / `jiractl capabilities [--refresh]` | optional refresh; только ограниченные read probes | operation → state/evidence/checked_at |
| `issues.search` / `jiractl issues search` | `--jql-file PATH` или `--jql TEXT`, взаимоисключающие; либо только `--cursor REF` | `{items:[Issue], page:{returned,total,next_cursor}}` |
| `issue.get` / `jiractl issue get KEY_OR_ID` | `--preset brief|analysis` или `--fields CSV` | Issue |
| `issue.section` / `jiractl issue section KEY_OR_ID SECTION` | section: description, comments, links, attachments; limit/cursor для коллекций | `SectionResult` |
| `fields.search` / `jiractl fields search --query TEXT` | optional query, `--limit 25`, cursor | Field metadata collection |
| `snapshot.create` / `jiractl snapshot create` | query file или issue-keys file, max-issues, preset/fields | SnapshotManifest |
| `snapshot.resume` / `jiractl snapshot resume RUN_REF` | ранее созданный run | Новый final snapshot manifest после продолжения |
| `snapshot.show` / `jiractl snapshot show SNAPSHOT_REF` | immutable ID | SnapshotManifest |
| `snapshot.read` / `jiractl snapshot read SNAPSHOT_REF` | `--issue KEY_OR_ID`, optional `--section SECTION` или `--fields CSV` | Issue или SectionResult из snapshot |
| `snapshot.diff` / `jiractl snapshot diff BEFORE AFTER` | `--fields CSV`, default summary,status,assignee,updated | Added/removed/changed/unknown records |
| `artifact.read` / `jiractl artifact read REF` | pointer и диапазон | Selected value/chunk + continuation |
| `artifact.export` / `jiractl artifact export REF --out PATH` | новый output path | Receipt с path/bytes/hash; payload только в файле |
| `artifact.prune` / `jiractl artifact prune` | default preview; `--apply` для удаления expired/unpinned local blobs | Counts/bytes; Jira не меняется |

Root global flags разрешены для всех. Неописанная команда — validation error. Команды v0.2 до их реализации MUST отсутствовать в capability `supported`; `describe` может показывать `availability=planned`, но Skill MVP их не рекламирует как рабочие.

### 4.1 Issues и поля

Issue ID хранится строкой. Issue key не преобразуется в URL и не интерпретируется shell. Identifier MUST быть одним безопасным path segment; запретить slash/backslash, control characters, traversal и encoded separators. Не навязывать всем DC project keys Cloud regex. Допустимые бизнес-форматы keys определяются profile/target, URL safety — отдельно.

`brief`: id, key, summary, status{id,name}, assignee{name,key}|null, updated. `analysis`: brief + description{format,text}|null, issue_type, priority, labels, components, fix_versions, links. Source field IDs отображаются явно в normalized fields. `--fields` и явно указанный `--preset` взаимоисключающие. Identity id/key всегда сохраняется. Custom fields доступны как `custom_fields.customfield_N` с оригинальными JSON values и schema metadata при необходимости.

`description.format` — `jira-wiki|plain|unknown`; не отправлять DC-текст в ADF-конвертер по умолчанию. Не удалять разметку/таблицы в lossless record. HTML renderedFields не включать автоматически.

`SectionResult` содержит `issue_id`, `issue_key`, `section`, `value` (для description) либо `items` (для коллекции), и section completeness/page metadata. Comments читаются отдельным paginated endpoint, а не считаются полными по встроенному полю issue. Attachments v0.1 — только metadata, не bytes/base64. Links — нормализованные входящие/исходящие связи с IDs и направлением.

### 4.2 Pagination

`issues search --limit N`: default 25, range 1–100; это максимум записей **одного invocation**, не общий лимит всего JQL. Server-side maxResults может быть меньше. Default fields — brief. `total` — integer или null, а не придуманное число. `next_cursor=null` только когда конец достоверно известен; неопределённый конец выражается предупреждением/partial.

Cursor — opaque локальный ref на query/fields/order/profile/principal/next offset. Он не содержит PAT и не принимается как URL. `issues search --cursor C` не допускает новых JQL/fields/limit; изменённый запрос начинает новый traversal. Expired/corrupt/cross-profile cursor — typed error.

При spill artifact содержит **всю уже полученную страницу**, а cursor переходит к следующей серверной странице. Для анализа всех данных caller сначала читает текущий artifact, затем следует next_cursor. Не использовать CLI output budget как server page size.

`fields.search`, comments и остальные collections имеют собственные cursors с теми же принципами. Разные API endpoint pagination не притворяются одинаковыми HTTP-протоколами: adapter переводит их в общий CLI контракт.

Live pagination — best effort. Concurrent edits могут изменять membership/order. Дедупликация наблюдавшихся IDs не доказывает отсутствие пропусков. Caller может передать JQL с устойчивым ORDER BY; CLI не переписывает произвольный JQL наивной строковой конкатенацией.

## 5. Snapshots и массовый сценарий

```sh
jiractl snapshot create --jql-file queries/backlog.jql --max-issues 100 --preset analysis
jiractl snapshot show s_0123456789abcdef0123456789abcdef
jiractl snapshot read s_0123456789abcdef0123456789abcdef --issue APP-421 --section description
jiractl snapshot diff s_0123456789abcdef0123456789abcdef s_abcdef0123456789abcdef0123456789ab --fields status,assignee
```

`--jql-file PATH` и `--keys-file PATH` взаимоисключающие. Keys file — UTF-8, один key/ID на строку; blank lines игнорируются, comments не интерпретируются. `--max-issues` обязателен для JQL, range 1–10000; для keys file default — число уникальных inputs, максимум 10000. `--sections comments,links,attachments` явно добавляет коллекции; description принадлежит analysis preset. Для comments `--max-comments-per-issue` default 1000, range 1–10000: достижение cap при наличии ещё данных делает capture partial. Полная история changelog не входит в v0.1.

Алгоритм MUST быть обычным кодом: persist run → enumerate IDs с de-dup → freeze membership → hydrate units → persist/checkpoint → finalize immutable manifest. Уже полученные достаточные fields SHOULD переиспользоваться вместо дублирующего get issue. Запросы limited-concurrency; LLM не вызывается. Cancellation оставляет проверяемый run для resume.

`run_ref=r_…` — mutable progress record, `snapshot_ref=s_…` — immutable manifest и ссылки на captured payloads. Resume создаёт новый final snapshot, не переписывает ранее опубликованный partial snapshot. Unit минимум issue+projection+section page; completed unit повторно не fetch-ится. Crash между HTTP response и persisted unit допускает повтор безопасного read.

Manifest MUST включать:

- instance/profile/principal namespace; schema/CLI version; query hash и reference на query input; selected immutable issue IDs;
- started_at/finished_at; first/last observation; consistency=`best_effort`;
- requested fields/sections; selected/captured/failed counts; field/section completeness;
- `selection_complete`: исчерпан ли весь источник; `limited_by`: `user|source|none`; `capture_complete`: все ли данные выбранного scope получены;
- per-issue fetched_at/source.updated/hash, unavailable records и типизированные errors;
- refs/checksums payloads и resume run_ref для незавершённой работы.

`--max-issues 100` при 500 совпадениях — успешный ограниченный capture: selected=100, selection_complete=false, limited_by=user, capture_complete=true. Ошибка получения хотя бы одного выбранного issue или обязательной секции — status partial, exit 9, capture_complete=false. Никогда не превращать partial в ok флагом «разрешить ошибки».

Snapshot НЕ атомарный point-in-time dump Jira. Временные окна и source versions сохраняются честно. Diff между разными instances/principals/проекциями MUST отклоняться, если сопоставимость не подтверждена. Отсутствующее в одном partial snapshot issue отмечать `unknown`, а не `deleted`. Для сравнения брать пересечение запрошенных полей или явно ошибаться; не объявлять незапрошенное поле удалённым.

## 6. Artifact store

Refs имеют вид `a_`/`c_`/`s_`/`r_`/`p_` + 32 lowercase hex; являются непрозрачными handles, не security tokens. Default output не содержит absolute state paths. Store — user-private, не shared global `/tmp` и не Git repo. Default retention 7 дней, quota 1 GiB. Active run/plan dependencies защищены от prune; удаление зависимых data требует явной политики.

Каждый blob записывается atomic temp+rename, с checksum и правами пользователя. SQLite manifests и blob publication согласуются recovery-процедурой; orphan cleanup не удаляет referenced blobs. Проверять symlinks/path traversal, collisions, permissions и concurrent writers. POSIX 0700/0600; Windows — эквивалентные ACL после отдельной проверки.

```sh
jiractl artifact read a_0123456789abcdef0123456789abcdef --pointer /items --offset 0 --limit 10
jiractl artifact read a_0123456789abcdef0123456789abcdef --pointer /items/0/description/text --char-offset 0 --char-limit 2000
jiractl artifact export a_0123456789abcdef0123456789abcdef --out ./export/issues.json
```

Pointer — RFC 6901 JSON Pointer, не исполняемое выражение. Для array: offset/limit; для string: char-offset/char-limit по Unicode code points. Нельзя смешивать. Если один array element слишком велик, вернуть его artifact/pointer, не бесконечно повторять ту же страницу. String chunk уменьшается до безопасного budget и сообщает `next_char_offset`; JSON остаётся валидным. Pointer/offset находятся в `meta.continuation`.

`artifact.export` не перезаписывает существующий файл; `--overwrite` требует отдельного явного флага. Запрещены symlink destinations и выход за разрешённые caller paths. Export receipt может показывать явно заданный пользователем path. Automatic log upload/telemetry отсутствует. Cache revoke не удаляет уже экспортированные копии: этот предел указан в документации.

## 7. Контролируемая запись v0.2

```sh
jiractl change plan --operation issue.update --input changes/update.json
jiractl change show p_0123456789abcdef0123456789abcdef
jiractl change apply p_0123456789abcdef0123456789abcdef --approve SHA256_FROM_PLAN
jiractl change reconcile p_0123456789abcdef0123456789abcdef
```

`change plan` делает read-only validation/discovery, сохраняет immutable plan и возвращает change summary, preconditions, risk и digest. Supported operation set v0.2: `issue.create`, `issue.update`, `issue.assign`, `issue.transition`, `comment.add`, `link.create`. Каждая — одна серверная write-operation. `delete`, `move`, `bulk` не поддерживаются.

Payload передаётся только JSON file или `--input -` со stdin. Строгая schema, max input 1 MiB. Ни credentials, ни arbitrary URL/HTTP method в payload нет. IDs должны быть разрешены metadata; display name с несколькими совпадениями вызывает `AMBIGUOUS_IDENTIFIER`.

Пример update input:

```json
{"issue":"APP-421","fields":{"summary":"Исправить сохранение формы","customfield_12345":null}}
```

Отсутствующее поле не меняется. Null означает явное намерение очистить поле и проходит target validation; это не универсально разрешённое значение. Arrays заменяются целиком, если конкретная operation schema не описывает add/remove. Не смешивать `fields` и generic Jira `update` в MVP; unsupported operation возвращает validation error.

Create input: project ID, issue type ID, fields. Assign: issue ID/key, resolved username/key либо null. Transition: issue, transition ID, необходимые fields. Comment: issue, body с явным text format, optional validated visibility. Link: link type ID, inward/outward issue IDs. Create/edit/transition metadata запрашивается по назначению; поля перехода определяются доступным transition screen [S9].

### 7.1 Plan identity

`contracts/change-plan.schema.json` задаёт immutable payload: operation, exact target/base URL, principal, created_at/expires_at, normalized input, expected state, schema version. Default TTL 15 минут. Digest = SHA-256 UTF-8 canonical JSON payload: sorted object keys, separators `,` и `:`, ensure_ascii=false, no trailing LF, reject NaN/Infinity; порядок массивов сохраняется; Unicode text не нормализуется. Digest не включает сам digest/receipt. Внешние text files копируются в immutable payload, не перечитываются при apply.

`--approve` должен совпадать с digest. Это anti-confusion mechanism, не authentication человека. Источник авторизации — пользовательский запрос и execution approval process, настроенный отдельно. Агент не должен сам выводить согласие из текста Jira. Не переносить пользовательский запрос «проанализируй» в разрешение «измени».

### 7.2 Apply и uncertain outcome

Apply MUST проверить: запись разрешена trusted profile; digest и TTL; совпадают instance/principal; все fields/schema/transition всё ещё допустимы; expected state затронутых данных совпадает. Если API поддерживает проверенный atomic conditional update — использовать. В остальных случаях preflight не устраняет гонку; `concurrency_guarantee=best_effort` включается в receipt.

Ledger states: `planned → applying → applied|failed|outcome_unknown`. До отправки `applying` durable persisted. Повтор для applied возвращает тот же receipt, не выполняет запрос. Crash после `applying`, response timeout, connection reset после возможной отправки — outcome_unknown, exit 10. Повторный apply неизвестного результата не отправляет write повторно.

`change reconcile` выполняет только read checks. Оно возвращает evidence и confidence/result, но не повторяет write. State-based совпадение не всегда доказывает авторство операции; comment/create могут остаться unknown. Проверяемый unique operation marker допустим только при проверенной поддержке endpoint, без выдуманной idempotency header. Разрешение ambiguous outcome требует внешнего решения; generic `--force-retry` отсутствует в v0.2.

Read retries: allowlist семантически безопасных read operations, включая POST search; max 3 attempts, exponential backoff с jitter, sane clamp Retry-After, общий deadline. 401/403/validation не retry. Write retries автоматом отсутствуют в v0.2, даже если ошибка выглядит временной, кроме доказанной до отправки ошибки локальной валидации, при которой запроса вообще не было.

## 8. Ошибки и exit codes

Error object: `{code,message,retryable,details?,recovery?}`. `message` не содержит секретов и полного upstream body. `recovery` — typed hint/описание, не исполняемый shell из ответа сервера. Retriable означает допустимость retry по контракту, не обязанность бесконечно повторять.

| Exit | Категория / примеры |
|---|---|
| 0 | Успех; help/version; empty successful search |
| 2 | Usage/schema/JQL validation, AMBIGUOUS_IDENTIFIER |
| 3 | AUTHENTICATION_FAILED |
| 4 | FORBIDDEN, если Jira явно вернула отказ |
| 5 | NOT_FOUND_OR_NOT_VISIBLE; не утверждать существование/отсутствие скрытого issue |
| 6 | UNSUPPORTED_CAPABILITY / отсутствующий подтверждённый endpoint |
| 7 | PRECONDITION_FAILED / PLAN_EXPIRED / конфликт |
| 8 | TRANSPORT_FAILED / DEADLINE_EXCEEDED после bounded retry безопасного read |
| 9 | PARTIAL_RESULT: часть запрошенного scope не получена |
| 10 | WRITE_OUTCOME_UNKNOWN; auto retry запрещён |
| 11 | INVALID_REFERENCE / STORAGE_ERROR / quota/checksum/cursor mismatch |
| 12 | POLICY_DENIED: запись disabled, approval mismatch, unsafe target |
| 70 | INTERNAL_ERROR, санитизированный trace ID |
| 130 | Обработанный interrupt; checkpoint сохранён по возможности |

Если retryable read исчерпал лимит, retryable может быть true с backoff hint. Для outcome_unknown всегда false. Не преобразовывать любую upstream exception в пустой successful list.

## 9. Обязательные invariants для тестов

JSON stdout валиден и не превышает budget; Unicode и oversized single fields не ломают chunking. Spill сохраняет всё запрошенное; pagination и artifact continuation не теряют строки. Нет PAT в logs/fixtures/tracebacks и cross-origin requests. Null отличается от absent. Refs проверяются по namespace и checksum. Snapshot partial не превращается в ok; diff не выводит недоказанные удаления. Mutations не reachable в v0.1. Повтор apply не дублирует подтверждённую запись; ambiguous write не retry. Все перечисленные checks входят в release gates, а не только в текст Skill.
## 10. Metadata discovery v0.2

`jiractl metadata create --project ID_OR_KEY [--issue-type ID]`: без issue type возвращает доступные issue types и нужные для выбора IDs; с issue type — create fields/required/allowed values. `jiractl metadata edit KEY_OR_ID` возвращает только edit metadata конкретной задачи. `jiractl metadata transitions KEY_OR_ID` возвращает доступные transition IDs, target statuses и transition fields. `jiractl metadata users --issue KEY_OR_ID --query TEXT` или `--project ID_OR_KEY` возвращает candidates без автоматического выбора; два scope flags взаимоисключающие. `jiractl metadata linktypes` возвращает ID и направленные labels link types.

Все metadata результаты ограничены общим output budget, пагинация/continuation сохраняется при необходимости. Metadata cache хранит instance/principal/context/checked_at/TTL; apply обновляет критичные данные независимо от обычного cache TTL. Для полного project discovery дополнительных commands v0.2 не обещает: пользователь/профиль задаёт project key, а doctor проверяет его scope только при явном задании.
