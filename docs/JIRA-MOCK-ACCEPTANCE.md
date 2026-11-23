# Jira mock acceptance matrix

**Нормативный план проверок, не отчёт. Все новые results: `not_run`.** `disposition` отвечает на применимость, `result` — на выполнение. Допустимы dispositions `required`, `deferred`, `not_applicable`, `blocked`; results `passed`, `failed`, `blocked`, `not_run`. JM-A — traceability IDs, не число Go functions.

Каждый required CLI case использует настоящий subprocess по absolute executable path, separate stdout/stderr, exact exit, one JSON document + LF, byte budget, отсутствие `SYNTHETIC_PAT`, unexpected/forbidden HTTP и incomplete journal, сохранность null/absent и selected values, без automatic deletion test artifacts.

В колонке `JM-R` сокращение `Rnn` означает определение [JM-Rnn](JIRA-MOCK.md) в design-документе; оно не вводит второй контракт.

| ID | Scope | Disposition / основание | Stimulus → observable | JM-R | Owner | Result |
|---|---|---|---|---|---|---|
| JM-A01 | mock | required | deterministic corpus → same hashes/IDs, no production mapper | R04 | T04 | not_run |
| JM-A02 | mock | required | every route, key/ID, context path → exact Jira shape/prefix | R02,R03 | T04 | not_run |
| JM-A03 | mock | required | unexpected vs expected 404 → violation vs matched | R03,R05 | T04 | not_run |
| JM-A04 | mock | required | known/unknown/invalid JQL, reordered keys → strict catalog/400 | R03,R04 | T04 | not_run |
| JM-A05 | mock | required | fields/null/absent/nested/big int → exact types/projection | R04 | T04 | not_run |
| JM-A06 | mock | required | GET/POST, 100/25/cap7 → coherent 15-page traversal | R02,R04 | T04 | not_run |
| JM-A07 | mock | required | concurrent faults/instances/race → isolated state/sequence | R05,R06 | T04 | not_run |
| JM-A08 | mock | required | journal overflow/canary → incomplete/redacted evidence | R05,R06 | T04 | not_run |
| JM-A09 | mock | required | blocked handler/cancel → Wait, release, no hang/FailNow | R05,R06 | T04 | not_run |
| JM-A10 | mock | required | graph/build → no runtime mock/module/service dependency | R01 | T04 | not_run |
| JM-A11 | core_cli | required | trusted TLS issue subprocess → adapter/auth/envelope | R01,R06,R07 | T05 | not_run |
| JM-A12 | core_cli | required | missing credential, 401/403/404 → typed safe outcomes | R03,R06,R07 | T02 | not_run |
| JM-A13 | core_cli | required | trusted/untrusted/wrong-SAN → only valid trust succeeds | R06 | T02 | not_run |
| JM-A14 | core_cli | required | redirect origin → no follow/auth leak | R06 | T02 | not_run |
| JM-A15 | search | required | POST search read profile → POST allowed, no writes | R02,R03 | T02 | not_run |
| JM-A16 | core_cli | required | unsafe IDs/mutations → local denial, no dispatch | R03,R06 | T02 | not_run |
| JM-A17 | core_cli | required | 429/503 sequences → bounded actual retry policy | R05,R07 | T02 | not_run |
| JM-A18 | core_cli | required | Retry-After variants → bounded policy, no real long sleep | R07 | T02 | not_run |
| JM-A19 | core_cli | required | HTML/bad JSON/shape/body cutoff → typed bounded failure | R05,R07 | T02 | not_run |
| JM-A20 | core_cli | required | timeout/deadline → bounded termination | R05,R06,R07 | T02 | not_run |
| JM-A21 | core_cli | required | parallel env/profile/state/path → isolated local origin only | R06 | T05 | not_run |
| JM-A22 | core_cli | required | success/error/usage → contract envelope/exit/budget | R07 | T05 | not_run |
| JM-A23 | core_cli | required | auth/upstream canary → no output/state/evidence leak | R05,R06,R07 | T02 | not_run |
| JM-A24 | core_cli | blocked: no infrastructure proof of external-egress deny with loopback allow | offline boundary/proxy fallback → cannot prove firewall from env/journal | R06,R08 | T08 | not_run |
| JM-A25 | core_cli | required | issue projections → explicit selected values/no broad expand | R03,R04,R07 | T05 | not_run |
| JM-A26 | search | required | Unicode/quoted/long JQL → exact decoded catalog request | R03,R04 | T05 | not_run |
| JM-A27 | search | required | 100/25/cap7 → all IDs, no duplicates, 15 pages | R04,R07 | T05 | not_run |
| JM-A28 | search | required | empty/short/end → correct completion | R04,R07 | T05 | not_run |
| JM-A29 | search | required | no-progress/bad total → no loop or false complete | R04,R05,R07 | T05 | not_run |
| JM-A30 | core_cli | required | wire value variants → preserve identity/types | R04,R07 | T05 | not_run |
| JM-A31 | comments | required | 137/cap50 → complete requested comments, not embedded partial | R02,R04,R07 | T05 | not_run |
| JM-A32 | snapshots | required | comments user cap100 → explicit incomplete scope | R04,R07 | T06 | not_run |
| JM-A33 | fields | required | fields search/pages → agreed route/filter/continuation | R02,R03,R07 | T05 | not_run |
| JM-A34 | issue_sections | required | links/attachments → directions/metadata, no binary/follow | R02,R04,R06 | T05 | not_run |
| JM-A35 | artifacts | required | ≥64KiB description → lossless spill, bounded stdout | R04,R07 | T05 | not_run |
| JM-A36 | artifacts | required | oversized search/artifact/cursor → no page loss | R04,R07 | T05 | not_run |
| JM-A37 | artifacts | required | Unicode artifact chunks → exact reconstruction/progress | R04,R07 | T05 | not_run |
| JM-A38.1 | artifacts | required | `artifact read` with stopped mock/sentinel → works, 0 HTTP | R07 | T05 | not_run |
| JM-A38.2 | artifacts | deferred: local-write export | export overwrite/path policy separately | R07 | T03 | not_run |
| JM-A39 | core_cli | required | hostile literal text → data only, no execution/leak | R04,R06,R07 | T05 | not_run |
| JM-A40 | snapshots | required | capture 100/source500 → honest selection/capture completeness | R04,R07 | T06 | not_run |
| JM-A41 | snapshots | required | sufficient search projection → no unnecessary 100 gets | R04,R07 | T06 | not_run |
| JM-A42 | snapshots | required | graceful interrupt/resume → no reread persisted units | R05,R06,R07 | T06 | not_run |
| JM-A43 | snapshots | blocked: no exact HTTP-response→durable-commit seam | controlled crash → cannot claim exact window coverage | R06,R07 | T06 | not_run |
| JM-A44 | snapshots | required | matching 404 after freeze → partial/unavailable, not deletion | R03,R05,R07 | T06 | not_run |
| JM-A45 | snapshots | required | A→B/partial/incompatible → immutable A, honest diff | R05,R07 | T06 | not_run |
| JM-A46 | snapshots | required | local read/diff with stopped mock/sentinel → 0 HTTP | R06,R07 | T06 | not_run |
| JM-A47 | local_store | not_applicable: owned by T03 planned `internal/store/*_test.go` | quota/disk/publish faults → store contract, not mock E2E | R07 | T03 | not_run |
| JM-A48 | local_store | not_applicable: owned by T03 planned `internal/store/*_test.go` and `internal/cli/export_linux_test.go` | corrupt/cross-profile refs/export policy → store contract, not mock E2E | R07 | T03 | not_run |
| JM-A49 | local_cli | required | `describe` IDs/unknown → contract summary/error, 0 HTTP | R07 | T05 | not_run |
| JM-A50.1 | local_cli | required | offline `doctor` → validates config, 0 HTTP | R07 | T05 | not_run |
| JM-A50.2 | core_cli | required | `doctor --probe` → only serverInfo/myself/minimal search, output/journal | R02,R07 | T05 | not_run |
| JM-A51.1 | local_cli | required | `capabilities` no refresh → honest unknown, no unjustified HTTP | R07 | T05 | not_run |
| JM-A51.2 | core_cli | required | `capabilities --refresh` → only allowed probes/honest evidence | R02,R07 | T05 | not_run |
| JM-A52 | local_cli | required | `snapshot show` stopped mock/sentinel → 0 HTTP | R07 | T06 | not_run |
| JM-A53 | local_cli | required | preview `artifact prune` → preview, no state/manifests change | R07 | T05 | not_run |
| JM-A54 | local_cli | deferred: local-write retirement | `artifact prune --apply` separate acceptance | R07 | T03 | not_run |
| JM-A55 | child_race | deferred: separate child `go build -race` | instrumented executable evidence | R06 | T08 | not_run |

`JM-A47`/`JM-A48` не доказывают всю v0.1 acceptance без отдельной приёмки T03. `mock_ready` требует passed required `mock`, `go test -race` handler/recorder и no production import. `cli_offline_verified` дополнительно требует passed required subprocess cases и audit dispositions. `target_verified` требует отдельный allowed read-only target smoke; mock его не ставит.
