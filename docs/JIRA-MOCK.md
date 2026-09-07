# Test-only Jira mock

**Status: Accepted design. Implementation and test evidence: not_run.**

## JM-R01. Назначение и границы

Это test-only Jira HTTP mock для `jiractl`: production HTTP adapter проверяется через настоящий loopback TCP/TLS listener, Jira wire JSON и реальный subprocess CLI. Мок не создаёт CLI envelope, artifacts, snapshots или checkpoints за приложение.

Не входят Jira Cloud API v3, Agile/JSM/plugin endpoints, Jira writes, binary attachments, JQL execution engine, proxy реальной Jira, recording production traffic, standalone service, runtime dependency, второй `go.mod`, Admin API/UI/Docker/JVM и изменение публичного CLI. Runtime packages не импортируют planned `internal/testjira`; API мока typed и finite, не JSON/YAML DSL.

## Repository bindings

| Binding | Значение |
|---|---|
| Module / Go | `github.com/avitamin/go-jiractl` / `1.27.1` |
| Entrypoint / executable | `cmd/jiractl` / `jiractl` |
| Contract / registry | `docs/CLI-CONTRACT.md` / `contracts/commands.json` |
| Production adapter | `internal/adapters/http` |
| Reads / snapshots | `internal/application/read.go`, `internal/application/sections.go` / `internal/application/snapshot.go` |
| Planned mock / E2E | `internal/testjira` / `tests/e2e` |
| Fixtures | normalized: `tests/fixtures`; wire: `internal/testjira/testdata` |
| Isolation | `--config PATH`, `XDG_STATE_HOME`, profile `pat_env`, synthetic `SYNTHETIC_PAT`, `ca_bundle` |
| Budgets | stdout `8192` (contract `1024..32768`); ordinary deadline `60s`; snapshot `300s` |

Один E2E package строит binary в уникальном сохранённом каталоге `/tmp`:

```bash
go build \
  -ldflags "-X github.com/avitamin/go-jiractl/internal/buildinfo.Version=e2e" \
  -o <unique-preserved-tmp-dir>/jiractl \
  ./cmd/jiractl
```

## JM-R02. Wire surface

Только текущий allowlist: `GET /rest/api/2/serverInfo`, `GET /rest/api/2/myself`, `GET /rest/api/2/field`, `GET /rest/api/2/issue/{keyOrId}`, `GET|POST /rest/api/2/search`, `GET /rest/api/2/issue/{keyOrId}/comment`. Base URL уже может содержать context path; обязательны пустой path и `/jira`. POST search остаётся read. Любой иной method/route — violation; новый endpoint требует CLI capability и источник wire shape. Fallback на real host запрещён.

## JM-R03. Exact matching

Method, context path и route сравниваются точно; query — после URL decoding. Порядок JSON object keys несущественен, но JQL literals/пробелы в literals не нормализуются. `fields` сравниваются как множество лишь при явном expectation. POST search проверяет `Content-Type`, типы `startAt`/`maxResults`, разрешённые свойства и один JSON document. Expected 400/401/403/404 не равен unexpected request. Последний записывается violation и получает малый `501`; harness проверяет violations независимо от exit CLI.

## JM-R04. Каталог, страницы и corpus

JQL parser не реализуется. Каталог хранит exact `project = SYN ORDER BY key ASC`, subset, empty, Unicode/quotes/`&`/spaces-in-literals, long POST и invalid JQL→400; known query заранее сортирует IDs. Основной corpus: 100 issues, CLI limit 25, server cap 7, 15 data-page responses; probes/retries отдельно. `SYN-42` имеет 137 comments и cap 50; source-limit corpus — 500.

`tests/fixtures` остаётся нормализованным application слоем. `internal/testjira/testdata` — независимые Jira REST wire responses: вручную reviewable малые JSON plus deterministic Go generator 100/500 без random и production normalizer. `SYN-1…SYN-100`; `SYN-1` содержит UTF-8 description ≥64 KiB, `SYN-42` — 137 comments, кириллицу/казахские символы/emoji, wiki и `{{...}}`, newlines, null/absent/empty/`0`/`false`, nested custom JSON, integer > safe JavaScript integer, equal display names, directed links и attachment metadata без binary. Manifest фиксирует revision, inputs, hashes, case IDs, basis и gaps; его wire basis — [Jira Server REST API 8.20.0](SOURCES.md), а не доказательство поведения user-reported target `8.20.13`.

## JM-R05. Typed API, state и journal

Планируемые компоненты: `Server` (TLS, URL, CA, lifecycle), `Scenario` (corpus/principals/expectations/faults), `Expectation`, `FaultStep` (status/body/header/delay/gate/malformed/body cutoff/redirect sink), `Journal`, `Record` и `Violation`. Mutable state защищён mutex; outward maps/slices/journal — copies. Fault sequence привязана к canonical request identity; probe/другая issue её не расходует. Mutex не удерживается при sleep/gate/write; handler не вызывает `t.Fatal`, `Fatalf`, `FailNow`. Для journal/recorder scenario задаёт ограниченные record/byte budgets: при overflow новые записи не принимаются, case получает failed/incomplete evidence даже при успешном exit CLI, а уже захваченные redacted records и артефакты сохраняются. Authorization/token/cookies не сохраняются raw.

## JM-R06. TLS и process isolation

Только HTTPS: test CA через `ca_bundle`, cases trusted/untrusted/wrong-SAN; `InsecureSkipVerify` и изменение system trust запрещены. Synthetic PAT передаётся Bearer, но не argv/URL/repository/evidence. Redirect sink — второй local origin, credentials туда не переходят; canary ищется в stdout/stderr/artifacts/snapshots/evidence.

E2E: создать corpus/scenario/listener, записать CA/config в сохранённый directory, сформировать minimal `exec.Cmd.Env` без `JIRA_*`, production PAT и proxy variables, вызвать absolute binary через `os/exec` без shell, отдельно bounded stdout/stderr, затем проверить output и journal даже при nonzero exit. Overflow stdout/stderr — failed/incomplete evidence: прекратить capture, cancel context и перейти к termination child; сохранить уже захваченные redacted fragments и пути артефактов. Закрыть bodies/gates/child/listener, но не удалять files/directories.

Официальные API: [net/http/httptest](https://pkg.go.dev/net/http/httptest), [os/exec](https://pkg.go.dev/os/exec), [testing](https://pkg.go.dev/testing), [race detector](https://go.dev/doc/articles/race_detector), [net/http](https://pkg.go.dev/net/http), [encoding/json](https://pkg.go.dev/encoding/json), [crypto/x509](https://pkg.go.dev/crypto/x509).

## JM-R07. Journal и evidence

Assertions выполняются также при nonzero CLI exit. Self-test доказывает, что intentional unexpected request обнаруживается. Journal не доказывает отсутствие запросов на другой origin; это отдельный инфраструктурный gap JM-A24.

## JM-R08. Contract assertions

Мок не владеет CLI schema: применяется `CLI-CONTRACT.md`. Проверяются один JSON object + LF, byte budget, separate stderr, lossless spill/continuation, null≠absent, partial≠complete, immutability A после B, incomplete absence≠deletion, no reread persisted resume units. Raw HTTP response не checkpoint.

## JM-R09. Lifecycle

Gate реагирует release, request cancellation и test context cancellation; `Wait` обязателен. При hung child или истечении case deadline harness сначала cancel context, затем запрашивает termination child и обязательно ждёт `Wait`; невозврат/ошибка `Wait` до внешнего bounded test deadline означает failed/incomplete evidence с сохранёнными артефактами. Listener закрывается после child и in-flight handlers. Deadline cancellation, graceful interrupt и abrupt crash различны; `CommandContext` kill не graceful. Не заявляется гарантия остановки process tree/descendants: harness управляет только известным child без process-group обходов. `go test -race` проверяет test-binary state; child из `go build -race` — deferred.

## JM-R10. CLI output

Проверки результата не создают второй CLI contract: stdout/stderr/exit и schema берутся из `CLI-CONTRACT.md`; mock лишь наблюдает wire exchange и доказательства.

## JM-R11. Snapshots и local work

Snapshot/resume проверяют immutable manifests, честную completeness, отсутствие reread persisted units и local `show`/`read`/`diff` без network dispatch. Local-store failure semantics принадлежат T03, не mock E2E.

## JM-R12. Scope и уровни готовности

`docs_adapted` — документы приняты. `mock_ready` — required mock cases и race handler/recorder прошли, production graph не зависит от mock. `cli_offline_verified` — также прошли required subprocess E2E с явными disposition остальных. `target_verified` требует отдельный разрешённый read-only smoke, который наблюдает version/build/principal/scope; offline mock его не даёт. Сейчас все уровни кроме `docs_adapted` — `not_run`; target `8.20.13` user-reported, `target_verified=false`.
