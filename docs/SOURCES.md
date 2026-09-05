# Первичные источники и provenance

Проверено 2026-09-05. Ссылки на API-конструкции служат reference, а не обещанием совместимости с неизвестной версией вашей Jira. Ни production Jira, ни пользовательские credentials не использовались.

| ID | Источник | Что подтверждает |
|---|---|---|
| S1 | [mcp-atlassian tools reference](https://mcp-atlassian.soomiles.com/docs/tools-reference) | Toolsets, ENABLED_TOOLS и read-only mode; исходный coverage seed |
| S2 | [Pinned Jira tool definitions](https://raw.githubusercontent.com/sooperset/mcp-atlassian/22369b76d6c1775a9730ba7d7cb37d49f7da671a/src/mcp_atlassian/servers/jira.py) | Python implementation, tools/tags, контекст DC/Cloud; нужна полная локальная AST-проверка |
| S3 | [Pinned commit](https://github.com/sooperset/mcp-atlassian/commit/22369b76d6c1775a9730ba7d7cb37d49f7da671a) и [Cloud-only filtering change](https://github.com/sooperset/mcp-atlassian/commit/a213816e88347645a7cb6242a3492caa15d7aeaa) | Зафиксированная reference точка; batch_get_changelogs/move_issue исключены для DC |
| S4 | [Microsoft Playwright CLI](https://github.com/microsoft/playwright-cli) | Мотивация CLI + Skill для coding-agent workflows; не Jira benchmark |
| S5 | [OpenAI Codex models](https://developers.openai.com/codex/models) | Sol/Terra/Luna model identifiers; выбрать реально доступные модели/efforts |
| S6 | [OpenAI Codex subagents](https://developers.openai.com/codex/subagents) | `.codex/agents/*.toml`, required fields, explicit model/effort и max_concurrent_threads_per_session |
| S7 | [OpenAI skills](https://developers.openai.com/codex/skills) | Progressive disclosure и `.agents/skills` |
| S8 | [Atlassian: personal access tokens](https://confluence.atlassian.com/enterprise/using-personal-access-tokens-1026032365.html) | PAT как Bearer authentication в Jira/Confluence Server/DC |
| S9 | [Jira 9.12 REST reference](https://docs.atlassian.com/software/jira/docs/api/REST/9.12.0/) | `fields`, POST search, startAt/maxResults, editmeta, transitions.fields; выбран как конкретный versioned reference, не как установленная у пользователя версия |

## Уровни доказательности

**Подтверждено первичными публичными источниками:** reference SHA существует; перечисленные mechanisms/flags/model configuration опубликованы; cloud-only tools помечены в upstream.

**Принято пользователем:** имя jiractl, Go 1.27.1, Cobra v1.10.2, Viper v1.21.0, Sol implementer/medium и Sol reviewer/high. **Proposed:** продуктовые команды/JSON schemas, byte/retention/concurrency defaults, task graph и target benchmark thresholds.

**Требует выполнения T00 и дальнейших gates:** complete pinned inventory/runtime parity, live deployment compatibility, exact endpoints optional plugins, метрики экономии, производительность и фактическая безопасность реализации.

Полный checkout upstream не удалось материализовать в контейнер подготовки. `coverage.seed.json` создан по опубликованному toolset reference и не называется полным инвентарём pinned source. Go replacement для inventory и полного pack validator отложен в T-TOOLING; этот gap остаётся открытым.

## Источники Go-bootstrap

- [Go toolchains](https://go.dev/doc/toolchain): директива `go` и выбор toolchain; версия закреплена handoff пользователя.
- [Cobra v1.10.2](https://github.com/spf13/cobra/tree/v1.10.2): дерево CLI и flags.
- [Viper v1.21.0](https://github.com/spf13/viper/tree/v1.21.0): `viper.New`, TOML, приоритет flags/env/file/defaults и nested environment keys.

Фактическая проверка bootstrap — `make check` на локальном Go toolchain. Она не является проверкой Jira, полного pack validator или upstream inventory.
