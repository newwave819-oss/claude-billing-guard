#!/usr/bin/env python3
"""PostToolUse hook: Claude課金対象コマンドの実行後に使用量を台帳へ記録し、今回＋累計のサマリを表示する。

費用は実行出力に実際に含まれる数値だけを集計する（total_cost_usd、input/output_tokens）。
料金表からの推定はしない。費用情報が出力に無い実行は「計測不可」として回数のみ数える。
台帳: ~/.claude/billing-ledger.json
"""
import datetime
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

    resp_text = json.dumps(data.get("tool_response") or {}, ensure_ascii=False)

    cost = None
    m = re.search(r'\\?"total_cost_usd\\?"\s*:\s*([0-9][0-9.eE+-]*)', resp_text)
    if m:
        try:
            cost = float(m.group(1))
        except ValueError:
            cost = None

    def tok(name: str):
        mm = re.search(r'\\?"' + name + r'\\?"\s*:\s*(\d+)', resp_text)
        return int(mm.group(1)) if mm else None

    in_tok = tok("input_tokens")
    out_tok = tok("output_tokens")

    try:
        with open(LEDGER, encoding="utf-8") as f:
            entries = json.load(f)
        if not isinstance(entries, list):
            entries = []
    except Exception:
        entries = []

    entries.append({
        "ts": datetime.datetime.now().isoformat(timespec="seconds"),
        "command": cmd[:160],
        "kinds": hits,
        "cost_usd": cost,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
    })

    try:
        os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
        with open(LEDGER, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=1)
    except Exception:
        pass

    total_cost = sum(e.get("cost_usd") or 0 for e in entries)
    measured = sum(1 for e in entries if e.get("cost_usd") is not None)
    total_in = sum(e.get("input_tokens") or 0 for e in entries)
    total_out = sum(e.get("output_tokens") or 0 for e in entries)

    if cost is not None:
        now_line = f"今回: ${cost:.4f}"
    else:
        now_line = "今回: 計測不可（出力に費用情報なし）"
    if in_tok is not None or out_tok is not None:
        now_line += f" ｜ in {in_tok or 0} / out {out_tok or 0} tok"

    lines = [
        "💸 Claude従量課金サマリ",
        now_line,
        (
            f"累計: ${total_cost:.4f}（費用計測 {measured}/{len(entries)}回）"
            f" ｜ in {total_in} / out {total_out} tok"
        ),
        f"台帳: {LEDGER}",
    ]
    if cost is None and re.search(r"\bclaude\s+(-p\b|--print\b)", cmd):
        lines.append("ヒント: claude -p に --output-format json を付けると正確な費用を記録できます")

    print(json.dumps({"systemMessage": "\n".join(lines)}, ensure_ascii=False))
    sys.exit(0)


if __name__ == "__main__":
    main()
