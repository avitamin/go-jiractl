# Deployment preflight

Проверка 2026-09-06: Linux amd64, Go 1.27.1, CGO enabled. Target version `8.20.13` user-reported; exact build, edition, URL/context path, principal, CA/proxy и read scope unknown. Реальные Jira-запросы не выполнялись, credentials не читались, `target_verified=false`. Для live probes нужен отдельный запрос пользователя; текущий путь приёмки — offline-only.

Pinned upstream `22369b76d6c1775a9730ba7d7cb37d49f7da671a` получен в `/tmp/reference-checkout.aahOG1`; SHA проверен через Git. Полный static/runtime inventory не подтверждён: AST extraction остановлен проектным hook; защита не менялась. Статус — [reference inventory](../planning/reference-inventory.json), [coverage](../planning/coverage.json). Upstream runtime не запускался.

Переданный результат локальной проверки: `GOCACHE=/tmp/race-cache.OXebML make check`, exit 0. Он включает hooks, gofmt check, `go vet`, unit/subprocess tests, race detector, `go mod tidy -diff` и build. Кэш оставлен для inspection. Результат относится к указанному на момент запуска дереву и не заменяет integration rerun после последующих изменений; он не доказывает совместимость Jira.

Текущий CLI реализует fixed read-only HTTP allowlist, PAT из `pat_env`, JSON/artifact output и snapshot workflow. Это implementation progress, а не target deployment validation. `capabilities` маркирует реализованные target operations как `unknown` до probe и не ведёт полный capability cache. `--format human` пока использует JSON rendering. `artifact prune` даёт preview, а `artifact prune --apply` реализует локальную retirement/cleanup операцию с transitive pin protection; tests используют fake unlink, поэтому агент не выполнял и не проверял cleanup в реальном пользовательском state store.

Модельный benchmark/agent eval пока не измерен. Runtime Skill не установлен в `.agents/skills`. Windows ACL для state/export paths не проверялись. Отсутствие live access допускает offline milestone, но отсутствие benchmark не закрывает T07. Полный v0.1 verdict требует выполнения остальных gates.
