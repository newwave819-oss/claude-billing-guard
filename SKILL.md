---
name: claude-billing-guard
description: Claude関連の従量課金（Agent SDKクレジット・Anthropic API課金）が発生しうる処理を提案・実行・コード生成する前に必ず警告するためのSkill。claude -p / --print、Claude Agent SDK、Claude Code GitHub Actions、api.anthropic.comへの直接リクエスト、ANTHROPIC_API_KEYを使うスクリプト、cron/launchd/CIへのclaude組み込み、ヘッドレス実行・自動化・定期実行の相談、Claudeのコスト・課金・クレジットの質問が出たら必ず使う。2026-06-15以降の課金体系変更に対応。
---

# Claude Billing Guard

## 目的

2026-06-15以降、Claude Pro/Max契約者のヘッドレス利用（Agent SDK・`claude -p`・Claude Code GitHub Actions）はAgent SDK月次クレジットの消費対象になり、APIキー認証の利用はAnthropic API従量課金（usage credits）の対象になる。気づかないうちに自動化へ組み込んで継続課金化するのが最大のリスクなので、**該当する処理を実行・提案する前に必ず警告し、ユーザーの明示的な了承を得る**。

## 課金が発生しうる経路（2026-06-15以降）

| 経路 | 課金先 |
|---|---|
| `claude -p` / `claude --print`（ヘッドレス実行） | Pro/Max: Agent SDKクレジット ／ APIキー認証: API従量課金 |
| Claude Agent SDK（Python/TS） | 同上 |
| Claude Code GitHub Actions | 同上（CI実行のたびに消費） |
| `api.anthropic.com` への直接リクエスト | API従量課金 |
| `ANTHROPIC_API_KEY` を使うスクリプト | API従量課金 |
| 上記を cron / launchd / CI に登録 | **継続課金化。最も危険** |

対話利用（通常の `claude`、Claude Desktop、IDE連携）はこの自動化枠とは別であり、警告対象外。

## 警告の出し方（必須）

該当する処理を実行・提案・コード生成する前に、必ず次のブロックをチャットに出し、了承を得てから進める。1回限りの小さな実行でも省略しない。定期実行・CI組み込みは特に必須。

```text
⚠️ 課金警告
- 処理内容:
- 課金経路: Agent SDKクレジット / API従量課金
- 実行頻度: 1回のみ / 定期（推定◯回/月）
- 概算規模: 入力サイズ・想定ターン数
- 代替案: （対話利用や手動実行で済むならその方法）
実行してよいですか？
```

## 自動化コードを書く場合のガードレール（生成するコードに必ず入れる）

- `ALLOW_CLAUDE_HEADLESS=1` のような明示フラグがないと実行されない構造にする。
- `--max-turns` を小さく、timeoutを短く設定する。
- Claude Platform側での月額上限・専用APIキー・専用プロジェクトの設定を案内する。
- GitHub Actionsは `workflow_dispatch` 優先、`concurrency` で同時実行1、対象ブランチ・パスで実行条件を絞る。
- 書き込み系ツールは最初から許可しない。
- 実行ログにモデル・入力サイズ・推定コスト・終了理由を残す。

## 常時警告のしくみ（hookとの併用）

Skillはモデルが必要と判断したときに読まれる仕組みのため、単体では「常に警告」を保証できない。実行時の強制警告と使用量記録は、同梱の2つのhookスクリプトをsettings.jsonに登録することで実現する（ハーネスが毎回必ず実行する）。

- `scripts/billing_guard_hook.py`（PreToolUse）: 課金対象コマンドの実行前に警告＋確認。これまでの累計も併記。
- `scripts/billing_usage_log_hook.py`（PostToolUse）: 実行後に「💸 今回＋累計」のサマリを表示し、台帳 `~/.claude/billing-ledger.json` に記録。

hookが確認を出した場合、**パターンに引っかからない形へのコマンド書き換えなどの回避は絶対にしない**。警告はユーザーの予算を守るための仕様であり、バグではない。

## 使用量の集計ルール

- 集計は**実行出力に実際に含まれる数値のみ**（`total_cost_usd`、`input_tokens` / `output_tokens`）。料金表からの推定はしない（料金改定で誤った金額を出さないため）。
- 費用情報が出力に無い実行は「計測不可」として回数のみ数える。`claude -p` は `--output-format json` を付けると正確な費用が記録される。
- ユーザーが「いくら使った？」と聞いたら台帳を読んで集計を答える。台帳が無ければ課金対象の実行はまだ無い。

## インストール

1. このフォルダを `~/.claude/skills/claude-billing-guard/` にコピーする。
2. hookスクリプト2つを任意の場所に置く（例: `~/.claude/hooks/`）。
3. `~/.claude/settings.json` に以下を追加する（既存の `hooks` がある場合はマージ）。パスは自分の環境に合わせること。

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/billing_guard_hook.py"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/billing_usage_log_hook.py"
          }
        ]
      }
    ]
  }
}
```

4. Claude Codeを再起動し、`echo test && claude -p "hi"` のようなコマンドを依頼すると確認ダイアログが出ることを確認する（許可しなければ実行されない）。許可して実行すると、完了後に💸サマリが表示され、台帳に記録される。

## 注意

- このSkillとhookは「警告と確認」を提供するもので、課金そのものを防ぐ技術的な上限ではない。予算上限はClaude Platform / Anthropic Console側で必ず設定すること。
- 課金体系は変わる可能性がある。最新は公式ドキュメント（Claude Code costs / Agent SDK with your Claude plan）を確認すること。
