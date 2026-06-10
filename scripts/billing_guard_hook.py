#!/usr/bin/env python3
"""PreToolUse hook: Claude従量課金（Agent SDKクレジット/API課金）に繋がるBashコマンドを検知して確認を求める。

これまでの累計（billing-ledger.json）があれば警告文に併記する。
"""
import json
import os
import re
import sys

LEDGER = os.path.expanduser("~/.claude/billing-ledger.json")

PATTERNS = [
    (r"\bclaude\s+(-p\b|--print\b)", "claude -p / --print（ヘッドレス実行）"),
    (r"api\.anthropic\.com", "Anthropic APIへの直接リクエスト"),
    (r"ANTHROPIC_API_KEY", "APIキーを使った実行"),
    (r"@anthropic-ai/claude-agent-sdk|claude_agent_sdk|claude-agent-sdk", "Claude Agent SDK"),
    (r"claude-code-action", "Claude Code GitHub Actions"),
    (r"(crontab|launchctl|systemctl)[^\n]*claude|claude[^\n]*(crontab|launchctl)", "claudeの定期実行・常駐登録"),
]


def ledger_summary() -> str:
    try:
        with open(LEDGER, encoding="utf-8") as f:
            entries = json.load(f)
    except Exception:
        return ""
    if not entries:
        return ""
    total = sum(e.get("cost_usd") or 0 for e in entries)
    measured = sum(1 for e in entries if e.get("cost_usd") is not None)
    return (
        f"｜参考: これまでの累計 ${total:.4f}"
        f"（費用計測 {measured}/{len(entries)}回）"
    )


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    cmd = (data.get("tool_input") or {}).get("command", "") or ""
    hits = [label for rx, label in PATTERNS if re.search(rx, cmd)]
    if not hits:
        sys.exit(0)

    reason = (
        "⚠️ Claude課金警告: このコマンドは「" + "、".join(hits) + "」を含みます。"
        "2026-06-15以降、Agent SDK月次クレジット（Pro/Max）または"
        "Anthropic API従量課金（APIキー認証）の対象になり得ます。"
        "1回限りか定期実行か、予算上限・max-turns・timeoutの設定有無を確認してから許可してください。"
        + ledger_summary()
    )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
