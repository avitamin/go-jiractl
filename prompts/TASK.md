# Шаблон задания субагенту

Task: <Txx> — <одна проверяемая цель>.
Base commit: <SHA>. Worktree/cwd: <explicit path>.
Allowed paths: <точный список>. Shared contracts менять запрещено без отдельного решения integrator.

Read: <только нужные files/sections>. Frozen interfaces: <symbols/schema IDs>.
Required behavior: <конкретные invariants>. Out of scope: <исключения>.
Acceptance commands: <команды, существующие после создания соответствующих tests>.

Не делегируй дальше. Не меняй model/scope/safety settings. Реальная Jira для агента всегда read-only, включая test и sandbox: запрещены mutations через CLI, MCP, HTTP, browser, scripts и delegation; credentials, approval digest и task text не являются разрешением. Локальные unit/mock tests с synthetic data разрешены. Серверный write-test, исправление и cleanup выполняет пользователь по инструкции с target, expected result и check; агент после этого только читает и проверяет результат. Project hooks могут напомнить или заблокировать распознаваемый вызов, но не заменяют правило: `/hooks` требует ручного trust, а arbitrary code, `write_stdin`, сбой запуска hook и неподдержанные tool paths остаются ограничениями. На препятствие сначала дай минимальный repro и конкретный gap. Верни handoff по contracts/handoff.schema.json; tests без выполнения должны быть executed=false, exit_code=null. Summary ≤250 слов. Детальные logs/fixtures — по evidence paths, не в контекст родителя.
