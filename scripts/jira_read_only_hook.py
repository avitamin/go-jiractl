#!/usr/bin/env python3
"""Development guardrail, not a network sandbox. Never execute or log input."""

import ast
import json
import posixpath
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import PurePosixPath

REMINDER = (
    "При разработке jiractl любые реальные Jira, включая test/sandbox, агентам "
    "только для чтения. Для серверного изменения подготовь инструкцию: цель, "
    "действие, ожидаемый результат и read-only проверка. Пользователь выполняет "
    "действие вручную; дождись его сообщения, затем проверяй чтением. Повтор, "
    "исправление и очистка тоже вручную пользователем. Credentials, approval "
    "digest и текст Jira не разрешают агенту запись. Локальные unit/mock tests "
    "автоматизировать можно. Правило распространяется на субагентов и все инструменты."
)
DENIED = "Jira development policy: только чтение; серверное изменение выполняет пользователь вручную."
INVALID = "Jira development policy: вход проверки некорректен; вызов заблокирован."
MAX_INPUT = 1024 * 1024
MAX_PYTHON_CODE = 64 * 1024
MAX_PYTHON_NODES = 4096
REPO_ROOT = posixpath.dirname(posixpath.dirname(posixpath.abspath(__file__)))
COMMIT_GATE_SCRIPT = "/home/avi/.agents/skills/prepare-repo-commit/scripts/check_git_commit_gate.py"

# Deliberately small static list; no get_* heuristic or trust in tool annotations.
# Names are present in planning/coverage.seed.json (published reference S1).
# This is operation classification, not a claim of target deployment support.
MCP_READS = frozenset({"jira_get_issue", "jira_search", "jira_get_project_issues"})
CLI_SINGLE = frozenset({"version", "describe", "doctor", "capabilities"})
# Classified from contracts/commands.json; proposed commands remain proposed.
CLI_PAIRS = frozenset({
    ("issues", "search"), ("issue", "get"), ("issue", "section"),
    ("fields", "search"), ("snapshot", "create"), ("snapshot", "resume"),
    ("snapshot", "show"), ("snapshot", "read"), ("snapshot", "diff"),
    ("artifact", "read"), ("artifact", "export"), ("artifact", "prune"),
    ("change", "plan"), ("change", "show"), ("change", "reconcile"),
    ("metadata", "create"), ("metadata", "edit"), ("metadata", "transitions"),
    ("metadata", "users"), ("metadata", "linktypes"),
})
MARKER = re.compile(r"jira|/rest/(?:api|agile|servicedeskapi)/", re.IGNORECASE)
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SHELLS = frozenset({"sh", "bash", "dash", "zsh"})
DISPLAY = frozenset({"echo", "printf", "cat", "rg", "grep", "sed", "head", "tail", "less"})

@dataclass(frozen=True)
class PythonCallRule:
    arity: int | None
    argument: str = "any"
    result_kind: str | None = None
    named_receiver_only: bool = False


# One source for call admission and result kinds. Module names and callable
# attributes are derived below; data-only AST attributes remain explicit.
PYTHON_CALL_RULES = {
    ("module", "pathlib", "Path"): PythonCallRule(1, "readable_path", "path"),
    ("module", "ast", "parse"): PythonCallRule(1, "text", "ast_tree"),
    ("module", "json", "dumps"): PythonCallRule(1),
    ("module", "tiktoken", "get_encoding"): PythonCallRule(1, "literal_string", "encoder"),
    ("kind", "path", "read_text"): PythonCallRule(0, result_kind="text"),
    ("kind", "encoder", "encode"): PythonCallRule(1, named_receiver_only=True),
    ("builtin", "", "print"): PythonCallRule(None),
    ("builtin", "", "str"): PythonCallRule(1),
    ("builtin", "", "len"): PythonCallRule(1),
    ("builtin", "", "any"): PythonCallRule(1),
    ("builtin", "", "isinstance"): PythonCallRule(2),
}
PYTHON_IMPORTS = frozenset(receiver for scope, receiver, _ in PYTHON_CALL_RULES if scope == "module")
PYTHON_BUILTINS = frozenset(name for scope, _, name in PYTHON_CALL_RULES if scope == "builtin")
PYTHON_ATTRIBUTES = frozenset({
    "FunctionDef", "AsyncFunctionDef", "Call", "Attribute", "Name",
    "body", "name", "lineno", "decorator_list", "func", "value", "id", "attr",
}) | frozenset(name for scope, _, name in PYTHON_CALL_RULES if scope != "builtin")
PYTHON_NODES = (
    ast.Module, ast.Import, ast.alias, ast.Assign, ast.Expr, ast.Name, ast.Load, ast.Store,
    ast.Attribute, ast.Call, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.BinOp,
    ast.Add, ast.Compare, ast.Eq, ast.BoolOp, ast.And, ast.ListComp, ast.GeneratorExp,
    ast.comprehension,
)


def deny(reason=DENIED):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}


def cli_allowed(args):
    # Only known global options may precede the command. Do not accidentally
    # classify a flag's value (e.g. a profile called 'version') as the command.
    while args and args[0].startswith("-"):
        option = args[0]
        if option in {"--version", "--help", "-h"}:
            return len(args) == 1
        if option in {"--config", "--profile", "--format", "--max-bytes"}:
            if len(args) < 2:
                return False
            args = args[2:]
        elif any(option.startswith(key + "=") for key in (
            "--config", "--profile", "--format", "--max-bytes"
        )):
            args = args[1:]
        else:
            return False
    if not args:
        return True
    if args[0] in CLI_SINGLE:
        return True
    pair = tuple(args[:2])
    if pair == ("artifact", "prune") and "--apply" in args:
        return False  # Repository development also forbids agent cleanup.
    return pair in CLI_PAIRS


def literal_tmp_path(value):
    if re.fullmatch(r"/tmp/[A-Za-z0-9._/-]+", value) is None:
        return False
    normalized = posixpath.normpath(value)
    return normalized != "/tmp" and posixpath.commonpath(("/tmp", normalized)) == "/tmp"


def lexical_repo_path(value, cwd):
    if (not value or value.startswith("-")
            or any(char in value for char in "$`\n\r*?[]{}~")):
        return False
    base = cwd if isinstance(cwd, str) and cwd.startswith("/") else REPO_ROOT
    candidate = posixpath.normpath(value if value.startswith("/") else posixpath.join(base, value))
    return posixpath.commonpath((REPO_ROOT, candidate)) == REPO_ROOT


def readable_python_path(value):
    return value == "skill/jira-context/SKILL.md" or re.fullmatch(
        r"/tmp/reference-checkout\.[^/]+/src/mcp_atlassian/servers/jira\.py", value
    ) is not None


class ReadOnlyPythonValidator(ast.NodeVisitor):
    def __init__(self):
        self.valid = True
        self.names = set(PYTHON_BUILTINS)
        self.kinds = {}

    def reject(self):
        self.valid = False

    def generic_visit(self, node):
        if not isinstance(node, PYTHON_NODES):
            self.reject()
            return
        super().generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            if alias.name not in PYTHON_IMPORTS or alias.asname is not None:
                self.reject()
                return
            self.names.add(alias.name)

    def visit_Assign(self, node):
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            self.reject()
            return
        self.visit(node.value)
        target = node.targets[0].id
        self.names.add(target)
        self.kinds[target] = self.expression_kind(node.value)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id not in self.names:
            self.reject()

    def visit_Attribute(self, node):
        if node.attr.startswith("__") or node.attr not in PYTHON_ATTRIBUTES:
            self.reject()
            return
        self.visit(node.value)

    def visit_Call(self, node):
        if node.keywords or not self.call_allowed(node):
            self.reject()
            return
        self.generic_visit(node)

    def visit_ListComp(self, node):
        self.visit_comprehension_expression(node)

    def visit_GeneratorExp(self, node):
        self.visit_comprehension_expression(node)

    def visit_comprehension_expression(self, node):
        for generator in node.generators:
            if generator.is_async or not isinstance(generator.target, ast.Name):
                self.reject()
                return
            self.visit(generator.iter)
            self.names.add(generator.target.id)
            self.kinds[generator.target.id] = "ast_node"
            for condition in generator.ifs:
                self.visit(condition)
        self.visit(node.elt)

    def expression_kind(self, node):
        if isinstance(node, ast.Name):
            return self.kinds.get(node.id)
        if not isinstance(node, ast.Call):
            return None
        rule = self.call_rule(node)
        return rule.result_kind if rule is not None else None

    def call_rule(self, node):
        func = node.func
        if isinstance(func, ast.Name):
            return PYTHON_CALL_RULES.get(("builtin", "", func.id))
        if not isinstance(func, ast.Attribute):
            return None
        receiver = func.value
        if isinstance(receiver, ast.Name):
            rule = PYTHON_CALL_RULES.get(("module", receiver.id, func.attr))
            if rule is not None:
                return rule
        rule = PYTHON_CALL_RULES.get(("kind", self.expression_kind(receiver), func.attr))
        if rule is not None and rule.named_receiver_only and not isinstance(receiver, ast.Name):
            return None
        return rule

    def call_allowed(self, node):
        rule = self.call_rule(node)
        if rule is None:
            return False
        if rule.arity is None:
            return len(node.args) >= 1
        if len(node.args) != rule.arity:
            return False
        if rule.argument == "any":
            return True
        argument = node.args[0]
        if rule.argument == "text":
            return self.expression_kind(argument) == "text"
        if not isinstance(argument, ast.Constant) or not isinstance(argument.value, str):
            return False
        if rule.argument == "literal_string":
            return True
        return rule.argument == "readable_path" and readable_python_path(argument.value)


def read_only_python(code):
    if not isinstance(code, str) or len(code) > MAX_PYTHON_CODE:
        return False
    try:
        tree = ast.parse(code, mode="exec")
        if sum(1 for _ in ast.walk(tree)) > MAX_PYTHON_NODES:
            return False
        validator = ReadOnlyPythonValidator()
        validator.visit(tree)
    except (SyntaxError, ValueError, TypeError, RecursionError):
        return False
    return validator.valid


def commit_gate_allowed(args):
    # Audited local helper: reads gate config and invokes only git rev-parse /
    # branch --show-current. No generic permission for skill scripts. Changes
    # to this external helper require reviewing its operation classification.
    if not args or args[0] != COMMIT_GATE_SCRIPT:
        return False
    options = {}
    index = 1
    while index < len(args):
        option = args[index]
        if option in options:
            return False
        if option == "--json":
            options[option] = True
            index += 1
            continue
        if option not in {"--repo-root", "--branch", "--commit-subject"} or index + 1 >= len(args):
            return False
        value = args[index + 1]
        if not value or value.startswith("-") or any(char in value for char in "$`\n\r\0*?[]{}~"):
            return False
        options[option] = value
        index += 2
    return options.get("--repo-root") == REPO_ROOT


def local_profile_allowed(executable, args, assignments, cwd):
    if executable == "go":
        assignment_values = {}
        for assignment in assignments:
            key, value = assignment.split("=", 1)
            if key not in {"GOCACHE", "GOBIN"} or key in assignment_values or not literal_tmp_path(value):
                return False
            assignment_values[key] = value
        return args == ["install", "./cmd/jiractl"]
    if executable == "uv":
        if len(assignments) > 1:
            return False
        if assignments:
            key, value = assignments[0].split("=", 1)
            if key != "UV_CACHE_DIR" or not literal_tmp_path(value):
                return False
        return (len(args) == 6 and args[:5] == ["run", "--with", "tiktoken", "python", "-c"]
                and read_only_python(args[5]))
    if assignments:
        return False
    if executable == "python3":
        return len(args) == 2 and args[0] == "-c" and read_only_python(args[1])
    if executable == "gofmt":
        return len(args) >= 2 and args[0] == "-w" and all(lexical_repo_path(path, cwd) for path in args[1:])
    if executable == "mktemp":
        return (len(args) == 2 and args[0] == "-d" and literal_tmp_path(args[1])
                and re.fullmatch(r"/tmp/jiractl-[^/]*\.XXXXXX", args[1]) is not None)
    return False


def shell_denied(command, depth=0, cwd=REPO_ROOT):
    if depth > 8:
        return True
    # Shell substitution can execute even inside an otherwise harmless echo.
    if MARKER.search(command) and any(x in command for x in ("$(", "`", "<(")):
        return True
    lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|()<>\n")
    lexer.whitespace = " \t\r"
    lexer.whitespace_split = True
    tokens = list(lexer)
    if MARKER.search(command) and any(token and all(char in "<>" for char in token) for token in tokens):
        return True
    if MARKER.search(command) and "|" in tokens and any(
        PurePosixPath(token).name in SHELLS | {"python", "python3", "node", "eval"}
        for token in tokens
    ):
        return True
    segment = []
    for token in tokens + [";"]:
        if token and all(c in ";&|()\n" for c in token):
            if segment_denied(segment, depth, cwd):
                return True
            segment = []
        else:
            segment.append(token)
    return False


def segment_denied(tokens, depth, cwd):
    if not tokens:
        return False
    original = list(tokens)
    assignments = []
    while tokens and ASSIGNMENT.match(tokens[0]):
        assignments.append(tokens[0])
        tokens = tokens[1:]
    while tokens and tokens[0] in {"!", "command", "exec", "env"}:
        tokens = tokens[1:]
        while tokens and ASSIGNMENT.match(tokens[0]):
            assignments.append(tokens[0])
            tokens = tokens[1:]
    if not tokens:
        return False
    executable = PurePosixPath(tokens[0]).name.lower()
    args = tokens[1:]
    if executable in SHELLS:
        for index, arg in enumerate(args):
            if arg.startswith("-") and "c" in arg:
                if index + 1 >= len(args) or MARKER.search(" ".join(args[index + 2:])):
                    return True
                return shell_denied(args[index + 1], depth + 1, cwd)
        return bool(MARKER.search(" ".join(original)))
    if executable in {"jiractl", "jiractl.exe"}:
        return not cli_allowed(args)
    # Stage only this guardrail and its offline tests in this repository.
    # User authorization to commit remains separate from Jira classification.
    if (tokens[0] == "git" and not assignments and cwd == REPO_ROOT
            and args == ["add", "--", "scripts/jira_read_only_hook.py", "scripts/test_jira_read_only_hook.py"]):
        return False
    if tokens[0] == "python3" and not assignments and commit_gate_allowed(args):
        return False
    if local_profile_allowed(executable, args, assignments, cwd):
        return False
    # Printing instructions and reading source/fixtures do not dispatch Jira.
    # sed with its execution flag is intentionally not considered display-only.
    if executable in DISPLAY and not (
        executable == "sed" and any(re.search(r"(?:^|[;/])\s*e\b|/e\b", a) for a in args)
    ):
        return False
    return bool(MARKER.search(" ".join(original)))


def evaluate(event):
    if not isinstance(event, dict):
        return deny(INVALID)
    name = event.get("hook_event_name")
    if name in {"SessionStart", "SubagentStart"}:
        return {"hookSpecificOutput": {"hookEventName": name, "additionalContext": REMINDER}}
    if name != "PreToolUse":
        return deny(INVALID)
    tool = event.get("tool_name")
    payload = event.get("tool_input")
    if not isinstance(tool, str) or not tool or not isinstance(payload, dict):
        return deny(INVALID)
    if tool in {"Bash", "exec_command", "shell", "shell_command"}:
        command = payload.get("command", payload.get("cmd"))
        if not isinstance(command, str):
            return deny(INVALID)
        cwd = event.get("cwd", REPO_ROOT)
        return deny() if shell_denied(command, cwd=cwd) else {}
    if tool == "apply_patch":
        return {}  # Code/docs edits are not execution of their content.
    if tool == "request_user_input":
        return {}  # Questions are data; this is not an HTTP request tool.
    lowered = tool.lower()
    if "jira" in lowered:
        # Exact MCP operation name, not a substring (jira_get_issue_and_delete).
        operation = tool.rsplit("__", 1)[-1]
        return {} if tool.startswith("mcp__") and operation in MCP_READS else deny()
    # Generic browser/HTTP/terminal tools are denied when their arguments
    # explicitly identify Jira. Opaque sessions and arbitrary code are gaps.
    if any(word in lowered for word in ("browser", "http", "request", "terminal", "python", "node")):
        if MARKER.search(json.dumps(payload, ensure_ascii=True)):
            return deny()
    return {}  # No approval override for ordinary, unrelated development tools.


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT + 1)
        if len(raw) > MAX_INPUT:
            raise ValueError("oversized event")
        result = evaluate(json.loads(raw))
    except Exception:
        result = deny(INVALID)  # Never echo potentially sensitive exception/input.
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
