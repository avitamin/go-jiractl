"""Offline policy tests: inputs are data, no Jira command is ever executed."""

import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import jira_read_only_hook as hook

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/jira_read_only_hook.py"


class PolicyTest(unittest.TestCase):
    def decision(self, tool, payload):
        return hook.evaluate({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": payload})

    def blocked(self, result):
        return result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

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

    def test_registered_hook_commands_offline(self):
        config = json.loads((ROOT / ".codex/hooks.json").read_text())
        self.assertEqual({"SessionStart", "SubagentStart", "PreToolUse"}, set(config["hooks"]))
        for event_name, groups in config["hooks"].items():
            handler = groups[0]["hooks"][0]
            self.assertNotIn("matcher", groups[0])
            self.assertNotIn("async", handler)
            event = {"hook_event_name": event_name, "tool_name": "Bash", "tool_input": {"command": "jiractl change apply p_synthetic"}}
            # Execute only the registered checker, feeding a fictional tool event.
            result = subprocess.run(["sh", "-c", handler["command"]], input=json.dumps(event),
                                    text=True, capture_output=True, cwd="/tmp", check=False)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual("", result.stderr)
            output = json.loads(result.stdout)
            if event_name == "PreToolUse":
                self.assertTrue(self.blocked(output))
            else:
                self.assertIn("additionalContext", output["hookSpecificOutput"])


if __name__ == "__main__":
    unittest.main()
