# Точечное чтение

Статус: Proposed; продуктовые команды ещё не реализованы.

Global flags предшествуют resource: `jiractl --profile corp issue get APP-421`.
`issue get` использует brief. `--preset analysis` добавляет description/type/priority/labels/components/versions/links. Для более узкой projection использовать `--fields` вместо явного preset. Custom fields требуют IDs из `fields search` или одобренного profile mapping.

`issue section KEY description|comments|links|attachments` читает одну секцию. Attachments в v0.1 — только metadata. Comments имеют pagination. Не считать вложенные comments или changelog полными автоматически.

Возвращается один JSON envelope. Exit 0 при пустом search допустим. Exit 9 — partial. Exit 3/4 требует восстановления authentication/permissions, а не повторения догадок. Exit 5 означает not found ИЛИ not visible; нельзя уверенно объявлять скрытые задачи несуществующими.

Большой результат: data=null, artifact.ref заполнен, delivery=artifact. Использовать `artifact read REF --pointer /items --offset 0 --limit 10`. Для длинного текста — `--char-offset` / `--char-limit` на точном pointer. Следовать continuation, не выводить всё содержимое. Server cursor продвигается за всю captured page, а не только показанные строки.

Для незнакомого синтаксиса вызывать `describe` одного dotted command ID. Help и recovery hints не дают разрешения на запись.
