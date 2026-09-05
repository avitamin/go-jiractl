# Работа со snapshots

Статус: Proposed; продуктовые команды ещё не реализованы.

Capture — синхронный детерминированный код. Сохранить query в файл, выбрать минимально нужные fields/sections и явный max-issues. `analysis` не захватывает comments автоматически.

Результат содержит run_ref и immutable snapshot_ref. `snapshot resume RUN_REF` продолжает неполный capture; предыдущий immutable partial snapshot не меняется. `snapshot read SNAPSHOT_REF --issue KEY --section description` читает локально без запросов Jira.

`selection_complete=false, limited_by=user, capture_complete=true` — полный capture намеренно ограниченного scope, не всех совпадений query. `capture_complete=false` обозначается как partial. Capture windows/source.updated — evidence, не гарантия транзакционного point-in-time среза.

Сравнение: `snapshot diff BEFORE AFTER --fields status,assignee`. Различия namespaces/projections и неполное membership ограничивают выводы. Отсутствующая задача в partial snapshot — unknown, не deleted.

Analyst subagents получают только выбранные issue refs/sections и конкретный вопрос. Их краткие выводы должны опираться на issue/field evidence. Чтение полного snapshot каждым агентом увеличивает расход контекста.
