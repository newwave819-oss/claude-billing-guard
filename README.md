# claude-billing-guard

Claude Codeの従量課金につながる操作を、**実行前に警告し、実行後に費用を記録・表示する**ためのSkill＋hookセットです。

2026-06-15以降、Claude Pro/Maxのヘッドレス利用（`claude -p`・Agent SDK・Claude Code GitHub Actions）はAgent SDK月次クレジットの消費対象になり、APIキー認証の利用はAnthropic API従量課金の対象になります。気づかないうちに自動化へ組み込んで継続課金化するのを防ぐのが目的です。

## 含まれるもの

| ファイル | 役割 |
|---|---|
| `SKILL.md` | billing guard Skill本体（警告テンプレート・ガードレール設計ルール） |
| `scripts/billing_guard_hook.py` | PreToolUse hook：課金対象コマンドの**実行前に警告＋確認**（累計も併記） |
| `scripts/billing_usage_log_hook.py` | PostToolUse hook：**実行後に今回＋累計のサマリを表示**し、台帳に記録 |
| `examples/settings.example.json` | settings.json 登録例 |
| `README.md` | インストール手順・動作確認手順（このファイル） |

## 動作イメージ

実行前（許可しない限り実行されません）：

```text
⚠️ Claude課金警告: このコマンドは「claude -p / --print（ヘッドレス実行）」を含みます。
2026-06-15以降、Agent SDK月次クレジット（Pro/Max）または
Anthropic API従量課金（APIキー認証）の対象になり得ます。
1回限りか定期実行か、予算上限・max-turns・timeoutの設定有無を確認してから許可してください。
｜参考: これまでの累計 $0.0234（費用計測 1/2回）
```

実行後：

```text
💸 Claude従量課金サマリ
今回: $0.0234 ｜ in 120 / out 456 tok
累計: $0.0234（費用計測 1/2回） ｜ in 120 / out 456 tok
台帳: ~/.claude/billing-ledger.json
```

## 検知パターン

| パターン | 内容 |
|---|---|
| `claude -p` / `claude --print` | ヘッドレス実行 |
| `api.anthropic.com` | APIへの直接リクエスト |
| `ANTHROPIC_API_KEY` | APIキーを使った実行 |
| `@anthropic-ai/claude-agent-sdk` 等 | Claude Agent SDK |
| `claude-code-action` | Claude Code GitHub Actions |
| `crontab` / `launchctl` / `systemctl` × `claude` | 定期実行・常駐登録（継続課金化のリスクが最大） |

通常の対話利用（`claude`、Claude Desktop、IDE連携）は警告対象外です。

## 必要環境

- Claude Code（hooks対応バージョン）
- `python3`（macOS / Linuxは標準的に利用可能。動作確認はmacOSで実施）

## インストール

1. このリポジトリの内容を `~/.claude/skills/claude-billing-guard/` にコピーする。
2. hookスクリプト2つを `~/.claude/hooks/` にコピーする。

   ```bash
   mkdir -p ~/.claude/hooks
   cp scripts/billing_guard_hook.py scripts/billing_usage_log_hook.py ~/.claude/hooks/
   ```

3. `~/.claude/settings.json` に `examples/settings.example.json` の内容を追加する（既存の `hooks` がある場合はマージ。ファイルが無ければそのままコピーでOK）。
4. Claude Codeを再起動する。

## 動作確認手順

1. Claude Codeで `echo test && claude -p "hi" と実行して` のように依頼する。
2. 実行前に「⚠️ Claude課金警告」の確認ダイアログが出ればPreToolUse hookは動作しています（**許可しなければ実行されず、課金も発生しません**）。
3. 許可して実行した場合、完了後に「💸 Claude従量課金サマリ」が表示され、`~/.claude/billing-ledger.json` に記録されれば PostToolUse hookも動作しています。
4. 警告が出ない場合：`/hooks` を一度開いて設定を再読込するか、Claude Codeを再起動してください。スクリプト単体の動作は次で確認できます。

   ```bash
   echo '{"tool_name":"Bash","tool_input":{"command":"claude -p \"hi\""}}' | python3 ~/.claude/hooks/billing_guard_hook.py
   ```

## 集計ルール（重要）

- **料金表からの推定はしません。** 実行出力に実際に含まれる数値（`total_cost_usd`、`input_tokens` / `output_tokens`）だけを記録します。料金改定時に誤った金額を表示しないためです。
- 費用情報が出力に無い実行は「計測不可」として回数のみ記録します。
- `claude -p` は `--output-format json` を付けると `total_cost_usd` が出力されるため、正確に記録できます。

## 台帳

`~/.claude/billing-ledger.json` に1実行1エントリで追記されます。

```json
[
 {
  "ts": "2026-06-15T10:00:00",
  "command": "claude -p \"hi\" --output-format json",
  "kinds": ["claude -p / --print（ヘッドレス実行）"],
  "cost_usd": 0.0234,
  "input_tokens": 120,
  "output_tokens": 456
 }
]
```

累計をリセットしたい場合は、このファイルを削除してください。

## アンインストール

`~/.claude/settings.json` から該当の `hooks` エントリを削除し、`~/.claude/hooks/` と `~/.claude/skills/claude-billing-guard/` の各ファイルを削除してください。

## 注意

- このhookは「警告・確認・記録」の仕組みであり、**課金の技術的な上限ではありません**。正確な総額の確認と予算上限の設定は、Anthropic Console / Claude側のusage画面で必ず行ってください。
- 課金体系は変わる可能性があります。最新は公式ドキュメントを確認してください。
  - [Use Claude Agent SDK with your Claude plan](https://support.anthropic.com/en/articles/12111930-use-claude-agent-sdk-with-your-claude-plan)
  - [Claude Code costs](https://docs.anthropic.com/en/docs/claude-code/costs)

## ライセンス

MIT License（`LICENSE` を参照）
