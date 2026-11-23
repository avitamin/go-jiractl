# Deployment preflight

Пользователь указал целевую версию Jira 8.20.13. Build, edition, context path, principal, CA/proxy и доступный scope чтения требуют отдельной проверки. Статус `target_verified=false`.

Для T00 зафиксированы [reference pin](../contracts/reference.lock.json) и [начальный каталог операций](../planning/coverage.seed.json). Полный inventory и результаты запросов к целевой Jira остаются открытыми.

Текущий bootstrap позволяет проверить сборку, version-команды и локальную конфигурацию. Для проверки совместимости понадобятся реализованный транспорт, пройденные offline cases и отдельно разрешённый read-only smoke.
