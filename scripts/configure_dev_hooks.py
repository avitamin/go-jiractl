"""Render project hook definitions with a pinned, shell-quoted handler path."""

import json
import shlex
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_COMMAND = "exit 2 # configure jiractl development hooks first"
EVENTS = ("SessionStart", "SubagentStart", "PreToolUse")


def render(config, handler):
    command = f"python3 -I {shlex.quote(str(handler.resolve(strict=True)))} || exit 2"
    for name in EVENTS:
        hooks = [
            (group, hook) for group in config["hooks"][name] for hook in group["hooks"]
            if hook.get("type") == "command" and hook.get("command") in (TEMPLATE_COMMAND, command)
        ]
        if len(hooks) != 1:
            raise ValueError(f"{name}: expected one project hook definition")
        group, hook = hooks[0]
        if group.get("matcher") not in (None, "", "*") or hook.get("async", False):
            raise ValueError(f"{name}: project hook must run synchronously for all matches")
        hook["command"] = command
    return config


if __name__ == "__main__":
    try:
        config = json.loads((ROOT / ".codex/hooks.json").read_text(encoding="utf-8"))
        result = render(config, ROOT / "scripts/jira_read_only_hook.py")
    except (KeyError, TypeError, ValueError, OSError) as error:
        sys.exit(f"Cannot render project hooks: {error}")
    print(json.dumps(result, ensure_ascii=False, indent=2))
