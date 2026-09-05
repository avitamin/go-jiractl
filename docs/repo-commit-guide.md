# Правила коммитов jiractl

## Source Priority

Явные требования пользователя → `AGENTS.md` → этот guide → проверенное состояние Git. Не выводить правила из чужого репозитория.

## Commit Message Format

Conventional Commits: `type(scope): description`, scope необязателен. Примеры:

```text
chore: bootstrap Go CLI
feat(cli): add doctor command
```

## Issue Key Rules

Jira key не обязателен без явного требования пользователя или задачи. Не придумывать ключи.

## Branch Policy

Initial bootstrap разрешён в `main`. После initial commit работать через рабочие ветки. Публикация и merge требуют соответствующего запроса.

## Staging Policy

`routine_worker` (Luna/low) выполняет целый ограниченный commit workflow через `prepare-repo-commit`: детерминированные проверки, краткие логи, точные механические правки и только явно разрешённый commit. Уже данное пользователем разрешение на commit не требует повторного подтверждения; запрос только сообщения коммита не разрешает staging или commit.

Stage только просмотренных файлов, относящихся к задаче, и только после явного запроса пользователя на staging/commit. Исключить `.idea`, secrets, private evidence и legacy pack artifacts. Перед коммитом просмотреть `git diff --cached` и выполнить `git diff --cached --check`. Если применённый commit workflow требует gate-файл, его отсутствие блокирует staging и commit; не обходить gate или hooks. Выполнять Git index и commit последовательно, после завершения всех writers.

## Validation Policy

Для Go-кода выполнить `make check`. Для документации следовать [documentation guide](repo-documentation-guide.md). Проверить `git status --short`, состав staged diff и отсутствие секретов. Сообщать команды и фактические результаты; непрошедшие проверки не выдавать за успешные. Не обходить hooks.

## Git Commit Gate

Перед разрешённым commit проверить формат branch и subject конфигурацией [`.agents/git-commit-gate.json`](../.agents/git-commit-gate.json). В текущей bootstrap-политике именованная группа `issue_key` намеренно захватывает пустую строку: у репозитория нет обязательного Jira key. Поэтому без явного требования Jira key запускать checker без `--issue-key`, например:

```bash
python3 /home/avi/.agents/skills/prepare-repo-commit/scripts/check_git_commit_gate.py \
  --repo-root /home/avi/GolandProjects/jiractl \
  --commit-subject 'chore: bootstrap Go CLI'
```

Gate проверяет только соответствие subject и branch заданным regex. Он не подтверждает валидность Git ref или историю ветки: отдельно выполнить `git check-ref-format --branch <branch>` и убедиться, что `main` используется только для unborn initial commit. После initial commit работать в рабочей ветке.

Этот gate не установлен как Git hook; checker является внешним helper из skill `prepare-repo-commit`, а не project runtime. Если для конкретной работы явно нужен Jira key, согласовать или адаптировать policy и конфигурацию до commit; не передавать выдуманный key и не игнорировать требование.

## Missing Facts And Defaults

Если история отсутствует, использовать описанный initial bootstrap workflow. Не угадывать issue key, branch naming или release policy. Блокирующие продуктовые решения уточнять, обычные локальные изменения выполнять в согласованном scope. Не запускать удаление файлов; точные пути передавать пользователю.
