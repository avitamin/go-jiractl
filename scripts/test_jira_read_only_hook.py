"""Offline policy tests: inputs are data, no Jira command is ever executed."""

import json
import shlex
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import configure_dev_hooks
import jira_read_only_hook as hook

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/jira_read_only_hook.py"


class PolicyTest(unittest.TestCase):
    def decision(self, tool, payload):
        return hook.evaluate({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": payload})

    def blocked(self, result):
        return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    def test_marker_bearing_local_commands_pass(self):
        commands = [
            "GOCACHE=/tmp/race-cache.OXebML GOBIN=/tmp/install-smoke.v1zeDx go install ./cmd/jiractl",
            "gofmt -w internal/cli cmd/jiractl/main_test.go",
            "mktemp -d /tmp/jiractl-race-cache.XXXXXX",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual({}, self.decision("exec_command", {"cmd": command}))

    @patch.object(hook, "REPO_ROOT", "/synthetic/jiractl")
    @patch.object(hook, "COMMIT_GATE_SCRIPT", "/synthetic/commit-gate.py")
    def test_commit_gate_is_a_scoped_local_check(self):
        helper = hook.COMMIT_GATE_SCRIPT
        base = f"python3 {helper} --repo-root {hook.REPO_ROOT}"
        for suffix in (
            "", " --json", " --branch chore/read-only-development-hooks --json",
            " --commit-subject 'fix(hooks): classify Jira path arguments' --json",
        ):
            with self.subTest(suffix=suffix):
                self.assertEqual({}, self.decision("exec_command", {"cmd": base + suffix}))

    def test_staging_hook_files_is_local_and_exact(self):
        base = "git add -- scripts/jira_read_only_hook.py scripts/test_jira_read_only_hook.py"
        self.assertEqual({}, self.decision("exec_command", {"cmd": base}))
        for command in (
            base + " README.md", base.replace("add --", "add -A --"),
            base.replace("git add", "git -c alias.add=anything add"),
            "GIT_DIR=/tmp/synthetic " + base,
            base + " && jiractl change apply p_synthetic",
            base + " $(jiractl change apply p_synthetic)",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.blocked(self.decision("exec_command", {"cmd": command})))
        self.assertTrue(self.blocked(hook.evaluate({
            "cwd": "/tmp", "hook_event_name": "PreToolUse", "tool_name": "exec_command",
            "tool_input": {"cmd": base},
        })))

    @patch.object(hook, "REPO_ROOT", "/synthetic/jiractl")
    @patch.object(hook, "COMMIT_GATE_SCRIPT", "/synthetic/commit-gate.py")
    def test_commit_gate_profile_rejects_other_execution_and_composition(self):
        helper = hook.COMMIT_GATE_SCRIPT
        base = f"python3 {helper} --repo-root {hook.REPO_ROOT}"
        mutation = "jiractl change apply p_synthetic"
        commands = [
            base.replace(helper, "/tmp/check_git_commit_gate.py"),
            base.replace(hook.REPO_ROOT, hook.REPO_ROOT + "-other"),
            base.replace("python3", "uv run python3", 1),
            base.replace("python3", "/tmp/python3", 1),
            "PYTHONPATH=/tmp/synthetic " + base,
            "env JIRA_TOKEN=SYNTHETIC-CANARY " + base,
            base + " --config alternate.json", base + " --commit-msg-file /tmp/message",
            base + " --repo-root /tmp", base + " --json --json",
            base + " --branch", base + " --unknown", base + " extra.py",
            base + " --commit-subject '$(" + mutation + ")'",
            base + " --commit-subject '`" + mutation + "`'",
            base + " > /tmp/gate-output",
        ]
        for operator in ("&&", "||", ";", "|", "\n"):
            commands.append(base + " " + operator + " " + mutation)
        for wrapper in ("env", "command", "exec", "bash -c"):
            wrapped = wrapper + " " + (shlex.quote(mutation) if wrapper == "bash -c" else mutation)
            commands.append(base + " && " + wrapped)
        for command in commands:
            with self.subTest(command=command):
                result = self.decision("exec_command", {"cmd": command})
                self.assertTrue(self.blocked(result))
                self.assertNotIn("SYNTHETIC-CANARY", json.dumps(result))

    def test_read_only_python_profiles_pass(self):
        tokenizer = (
            "uv run --with tiktoken python -c 'import pathlib,tiktoken; "
            "data=pathlib.Path(\"skill/jira-context/SKILL.md\").read_text(); "
            "enc=tiktoken.get_encoding(\"o200k_base\"); "
            "print(\"o200k_base_proxy_tokens=\"+str(len(enc.encode(data))))'"
        )
        inventory = (
            "python3 -c 'import ast,json,pathlib; "
            "p=pathlib.Path(\"/tmp/reference-checkout.aahOG1/src/mcp_atlassian/servers/jira.py\"); "
            "tree=ast.parse(p.read_text()); "
            "rows=[{\"symbol\":n.name,\"line\":n.lineno,\"classification\":\"UNCLASSIFIED\"} "
            "for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and "
            "any(isinstance(d,ast.Call) and isinstance(d.func,ast.Attribute) and "
            "isinstance(d.func.value,ast.Name) and d.func.value.id==\"jira_mcp\" and "
            "d.func.attr==\"tool\" for d in n.decorator_list)]; "
            "print(json.dumps({\"schema_version\":\"jiractl.reference-inventory.v1\","
            "\"source_file\":\"src/mcp_atlassian/servers/jira.py\",\"rows\":rows}))'"
        )
        for command in (tokenizer, inventory):
            with self.subTest(command=command):
                self.assertEqual({}, self.decision("exec_command", {"cmd": command}))
        with_cache = "UV_CACHE_DIR=/tmp/jiractl-uv-cache.AbC123 " + tokenizer
        self.assertEqual({}, self.decision("exec_command", {"cmd": with_cache}))

    def test_request_user_input_question_is_data(self):
        payload = {
            "questions": [{
                "header": "Приёмка",
                "id": "acceptance_mode",
                "question": "Проводим Jira-приёмку read-only или полностью offline?",
                "options": [
                    {"label": "Read-only", "description": "Только чтение Jira."},
                    {"label": "Offline", "description": "Без Jira-запросов."},
                ],
            }],
        }
        self.assertEqual({}, self.decision("request_user_input", payload))

    def test_python_call_rules_preserve_argument_and_receiver_boundaries(self):
        prefix = 'import ast,json,pathlib,tiktoken; p=pathlib.Path("skill/jira-context/SKILL.md"); '
        cases = [
            ('data=p.read_text(); tree=ast.parse(data); print(json.dumps(tree.body))', True),
            ('print(p.read_text())', True),
            ('enc=tiktoken.get_encoding("o200k_base"); print(enc.encode("jira"))', True),
            ('print(pathlib.Path("/tmp/jira-secret").read_text())', False),
            ('print(p.read_text("utf-8"))', False),
            ('print(p.read_text(encoding="utf-8"))', False),
            ('print(ast.parse("jira"))', False),
            ('print(json.dumps())', False),
            ('print(tiktoken.get_encoding(42))', False),
            ('print(tiktoken.get_encoding("o200k_base").encode("jira"))', False),
            ('print(p.encode("jira"))', False),
            ('print(pathlib.parse(p.read_text()))', False),
            ('print(len())', False),
            ('print(isinstance(p))', False),
        ]
        for code, allowed in cases:
            with self.subTest(code=code):
                result = self.decision("exec_command", {"cmd": "python3 -c " + shlex.quote(prefix + code)})
                self.assertEqual(not allowed, self.blocked(result))

    def test_local_allow_profiles_do_not_extend_to_jira_mutations(self):
        safe_commands = [
            "GOCACHE=/tmp/race-cache.OXebML GOBIN=/tmp/install-smoke.v1zeDx go install ./cmd/jiractl",
            "gofmt -w internal/cli cmd/jiractl/main_test.go",
            "mktemp -d /tmp/jiractl-race-cache.XXXXXX",
            (
                "uv run --with tiktoken python -c 'import pathlib,tiktoken; "
                "data=pathlib.Path(\"skill/jira-context/SKILL.md\").read_text(); "
                "enc=tiktoken.get_encoding(\"o200k_base\"); print(str(len(enc.encode(data))))'"
            ),
            (
                "python3 -c 'import ast,pathlib; "
                "p=pathlib.Path(\"/tmp/reference-checkout.aahOG1/src/mcp_atlassian/servers/jira.py\"); "
                "print(len(ast.parse(p.read_text()).body))'"
            ),
        ]
        mutation = "jiractl change apply p_synthetic"
        for safe in safe_commands:
            for operator in ("&&", "||", ";", "|", "\n"):
                command = safe + (operator if operator == "\n" else " " + operator + " ") + mutation
                with self.subTest(safe=safe, operator=operator):
                    self.assertTrue(self.blocked(self.decision("exec_command", {"cmd": command})))

    def test_substitutions_wrappers_and_unsafe_python_block(self):
        commands = [
            "echo $(jiractl change apply p_synthetic)",
            "printf '%s' `jiractl change apply p_synthetic`",
            "env jiractl change apply p_synthetic",
            "command jiractl change apply p_synthetic",
            "exec jiractl change apply p_synthetic",
            "bash -c 'jiractl change apply p_synthetic'",
            "bash -c 'eval \"$1\"' _ 'jiractl change apply p_synthetic'",
            "gofmt -w cmd/jiractl/main_test.go > /tmp/formatted.go",
            (
                "uv run --with tiktoken python -c 'import subprocess; "
                "subprocess.run([\"jiractl\",\"change\",\"apply\",\"p_synthetic\"])'"
            ),
            (
                "uv run --with tiktoken python -c 'import urllib.request; "
                "urllib.request.urlopen(\"https://jira.invalid/rest/api/2/myself\")'"
            ),
            "python3 -c 'import os; os.system(\"jiractl change apply p_synthetic\")'",
            (
                "python3 -c 'import pathlib; "
                "pathlib.Path(\"skill/jira-context/SKILL.md\").write_text(\"jira\")'"
            ),
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.blocked(self.decision("exec_command", {"cmd": command})))

    def test_local_profiles_are_exact(self):
        commands = [
            "FOO=/tmp/x go install ./cmd/jiractl",
            "GOCACHE=relative go install ./cmd/jiractl",
            "go install -race ./cmd/jiractl",
            "go install ./cmd/jiractl ./cmd/other",
            "gofmt -w ../jiractl-copy/main.go",
            "gofmt -d cmd/jiractl/main_test.go",
            "mktemp -d /tmp/jiractl-race-cache.XXXXXX extra",
            "mktemp -d /tmp/jiractl-race-cache.XXXXX",
            "uv run --with requests python -c 'print(\"jira\")'",
            "uv run --with tiktoken python3 -c 'print(\"jira\")'",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.blocked(self.decision("exec_command", {"cmd": command})))

    def test_outer_exec_is_data_but_nested_tool_call_is_classified(self):
        outer = self.decision("exec", {
            "code": "await tools.exec_command({cmd: 'jiractl change apply p_synthetic'})",
        })
        nested = self.decision("exec_command", {"cmd": "jiractl change apply p_synthetic"})
        self.assertEqual({}, outer)
        self.assertTrue(self.blocked(nested))

    def test_server_writes_and_unknown_operations_block(self):
        for operation in (
            "create_issue", "update_issue", "delete_issue", "assign_issue",
            "transition_issue", "add_comment", "create_issue_link",
            "add_attachment", "batch_create_issues", "future_operation",
            "get_issue_and_delete", "get_unclassified",
        ):
            with self.subTest(operation=operation):
                self.assertTrue(self.blocked(self.decision("mcp__atlassian__jira_" + operation, {})))

    def test_exact_mcp_reads_do_not_override_approval(self):
        for operation in hook.MCP_READS:
            with self.subTest(operation=operation):
                self.assertEqual({}, self.decision("mcp__atlassian__" + operation, {}))
        self.assertTrue(self.blocked(self.decision("jira_get_issue", {})))

    def test_shell_blocks(self):
        commands = [
            "jiractl change apply p_synthetic", "./build/jiractl issue delete DEMO-1",
            "jiractl future read", "jiractl --profile version change apply p_synthetic",
            "jiractl --profile=default change apply p_synthetic",
            "env JIRACTL_PROFILE=default ./build/jiractl change apply p_synthetic",
            "command jiractl change apply p_synthetic",
            "echo ready && jiractl change apply p_synthetic",
            "echo ready\njiractl change apply p_synthetic",
            "bash -lc 'jiractl change apply p_synthetic'",
            "bash -c 'echo ok; sh -c \"jiractl change apply p_synthetic\"'",
            "echo $(jiractl change apply p_synthetic)",
            "printf '%s' `jiractl change apply p_synthetic`",
            "printf '%s' 'jiractl change apply p_synthetic' | bash",
            "curl -X DELETE https://jira.invalid/rest/api/2/issue/DEMO-1",
            'curl -X POST "$JIRA_URL/rest/api/2/search"',
            "curl https://jira.invalid/rest/api/2/myself",
            "wget https://tracker.invalid/rest/api/2/issue/DEMO-1",
            "python3 -c 'import requests; requests.delete(\"https://jira.invalid/x\")'",
            "sudo curl -X DELETE https://jira.invalid/x",
            "jiractl artifact prune --apply",
            "jiractl artifact prune --apply=true",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertTrue(self.blocked(self.decision("Bash", {"command": command})))

    def test_development_reads_and_manual_instructions_pass(self):
        commands = [
            "git status --short", "make test", "make hooks-test", "go test ./...",
            "jiractl version", "./build/jiractl --version",
            "jiractl --profile default issue get DEMO-1",
            "jiractl --config '/tmp/a file.toml' snapshot create --keys-file keys.txt",
            "jiractl --profile=default change plan --input change.json",
            "jiractl change reconcile p_synthetic", "jiractl artifact export a_synthetic --out out.json",
            "jiractl describe change.apply", "jiractl metadata edit DEMO-1",
            "jiractl issues search --jql 'summary ~ \"delete\"'",
            "echo 'jiractl change apply p_synthetic'",
            "printf '%s\\n' 'curl -X DELETE https://jira.invalid/x'",
            "rg 'jira_delete_issue|change apply' docs scripts",
            "cat docs/CLI-CONTRACT.md",
            "sed -n '1,30p' scripts/jira_read_only_hook.py",
            "bash -lc 'jiractl issue get DEMO-1'",
        ]
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual({}, self.decision("Bash", {"command": command}))

    def test_editing_code_or_documentation_is_not_execution(self):
        self.assertEqual({}, self.decision("apply_patch", {"command": "+curl -X DELETE https://jira.invalid/x"}))
        self.assertEqual({}, self.decision("exec", {"code": "await tools.apply_patch('jira_delete_issue');"}))

    def test_explicit_jira_generic_tools_block(self):
        for tool in ("mcp__ide__execute_terminal_command", "browser_click", "http_request"):
            self.assertTrue(self.blocked(self.decision(tool, {"url": "https://jira.invalid"})))

    def test_denial_does_not_echo_secrets(self):
        secret = "SYNTHETIC-CANARY-NOT-A-REAL-TOKEN"
        result = self.decision("mcp__atlassian__jira_delete_issue", {"token": secret})
        self.assertTrue(self.blocked(result))
        self.assertNotIn(secret, json.dumps(result))

    def test_start_reminders(self):
        for name in ("SessionStart", "SubagentStart"):
            for source in ("startup", "resume", "compact", "clear"):
                with self.subTest(name=name, source=source):
                    result = hook.evaluate({"hook_event_name": name, "source": source})
                    self.assertEqual(name, result["hookSpecificOutput"]["hookEventName"])
                    self.assertIn("вручную", result["hookSpecificOutput"]["additionalContext"])

    def test_cwd_does_not_disable_policy(self):
        for cwd in (str(ROOT), str(ROOT / "internal"), "/tmp"):
            self.assertTrue(self.blocked(hook.evaluate({
                "cwd": cwd, "hook_event_name": "PreToolUse",
                "tool_name": "Bash", "tool_input": {"command": "jiractl change apply p_synthetic"},
            })))

    def test_invalid_events_block(self):
        for event in (None, [], {}, {"hook_event_name": "Unexpected"},
                      {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": []},
                      {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {}}):
            self.assertTrue(self.blocked(hook.evaluate(event)))

    def test_shell_parse_errors_and_internal_errors_are_denied(self):
        with patch.object(hook.sys, "stdin") as stream, patch("builtins.print") as output:
            stream.buffer.read.return_value = json.dumps({
                "hook_event_name": "PreToolUse", "tool_name": "Bash",
                "tool_input": {"command": "'unterminated"},
            }).encode()
            hook.main()
            self.assertTrue(self.blocked(json.loads(output.call_args.args[0])))
        with patch.object(hook.sys, "stdin") as stream, patch("builtins.print") as output:
            stream.buffer.read.return_value = b"{}"
            with patch.object(hook, "evaluate", side_effect=RuntimeError("SECRET-CANARY")):
                hook.main()
            self.assertTrue(self.blocked(json.loads(output.call_args.args[0])))
            self.assertNotIn("SECRET-CANARY", output.call_args.args[0])

    def test_subprocess_wire_format_and_bounds(self):
        for raw in (b"not-json", b"[]", b"{" + b"x" * hook.MAX_INPUT):
            result = subprocess.run([sys.executable, "-B", str(SCRIPT)], input=raw, capture_output=True, check=False)
            self.assertEqual(0, result.returncode)
            self.assertEqual(b"", result.stderr)
            self.assertTrue(self.blocked(json.loads(result.stdout)))
            self.assertLess(len(result.stdout), 1024)

    def test_contract_global_flags_preserve_command_classification(self):
        for args in (["--debug", "version"], ["--deadline-seconds=60", "issue", "get"],
                     ["--deadline-seconds", "60", "snapshot", "show"]):
            self.assertTrue(hook.cli_allowed(args))
        self.assertFalse(hook.cli_allowed(["--debug", "change", "apply"]))
        self.assertFalse(hook.cli_allowed(["--deadline-seconds"]))

    def test_registered_hook_commands_offline(self):
        config = json.loads((ROOT / ".codex/hooks.json").read_text())
        # Additional user hooks stay intact and are never executed by this test.
        extra = {"matcher": "^OtherTool$", "hooks": [{"type": "command", "command": "user-hook"}]}
        config["hooks"].setdefault("Stop", []).append(extra)
        config["hooks"]["PreToolUse"].insert(0, extra)
        configure_dev_hooks.render(config, SCRIPT)
        self.assertEqual(extra, config["hooks"]["PreToolUse"][0])
        self.assertIn(extra, config["hooks"]["Stop"])
        expected_command = f"python3 -I {shlex.quote(str(SCRIPT))} || exit 2"
        for event_name in configure_dev_hooks.EVENTS:
            registered = [hook["command"] for group in config["hooks"][event_name]
                          for hook in group["hooks"] if hook.get("command") == expected_command]
            self.assertEqual([expected_command], registered)
            event = {"hook_event_name": event_name, "tool_name": "Bash", "tool_input": {"command": "jiractl change apply p_synthetic"}}
            result = subprocess.run(["sh", "-c", expected_command], input=json.dumps(event),
                                    text=True, capture_output=True, cwd="/tmp", timeout=5, check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("", result.stderr)
            output = json.loads(result.stdout)
            if event_name == "PreToolUse":
                self.assertTrue(self.blocked(output))
            else:
                self.assertIn("additionalContext", output["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
