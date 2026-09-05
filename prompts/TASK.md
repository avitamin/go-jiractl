# Шаблон задания субагенту

Task: <Txx> — <одна проверяемая цель>.
Base commit: <SHA>. Worktree/cwd: <explicit path>.
Allowed paths: <точный список>. Shared contracts менять запрещено без отдельного решения integrator.

Read: <только нужные files/sections>. Frozen interfaces: <symbols/schema IDs>.
Required behavior: <конкретные invariants>. Out of scope: <исключения>.
Acceptance commands: <команды, существующие после создания соответствующих tests>.

Не делегируй дальше. Не меняй model/scope/safety settings. На препятствие сначала дай минимальный repro и конкретный gap. Верни handoff по contracts/handoff.schema.json; tests без выполнения должны быть executed=false, exit_code=null. Summary ≤250 слов. Детальные logs/fixtures — по evidence paths, не в контекст родителя.
