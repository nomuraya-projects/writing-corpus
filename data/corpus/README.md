# 学習用コーパス

書き味の学習・ファインチューニング用データ。

## ディレクトリ構成

```
corpus/
├── preference_pairs/    # AI版 vs ユーザー版のペアデータ
├── style_patterns/      # 書き味パターン定義
├── metadata.json        # FC2記事メタデータ
└── writing-corpus.db    # SQLiteデータベース
```

## preference_pairs/

RLHF/DPO用のpreference pairs形式。各行がJSONL。

### フィールド

| フィールド | 説明 |
|-----------|------|
| id | ペアの識別子 |
| instruction | タスク説明 |
| rejected | AI版（改善前） |
| chosen | ユーザー版（改善後） |
| patterns | 適用された書き味パターン |
| source | 元記事 |
| date | 作成日 |

### 使用例

```python
import json

with open("2026-01-05_github-repo-organization-transfer.jsonl") as f:
    for line in f:
        pair = json.loads(line)
        # DPO: rejected vs chosen で学習
        # instruction: プロンプト
        # patterns: どのパターンが適用されたか
```

### ファインチューニング形式変換

```python
# Alpaca形式へ変換
def to_alpaca(pair):
    return {
        "instruction": pair["instruction"],
        "input": "",
        "output": pair["chosen"]
    }

# ChatML形式へ変換
def to_chatml(pair):
    return {
        "messages": [
            {"role": "user", "content": pair["instruction"]},
            {"role": "assistant", "content": pair["chosen"]}
        ]
    }
```

## style_patterns/

書き味パターンの定義。JSONで構造化。

### カテゴリ

| カテゴリ | 説明 |
|---------|------|
| structure | 構造・フォーマット |
| tone | トーン・語調 |
| content | 内容・情報 |
| meta | メタ情報開示 |
| honesty | 正直さ・不確実性 |
| format | 記法・装飾 |

### 各パターンの構造

```json
{
  "pattern-name": {
    "description": "パターンの説明",
    "bad": "改善前の例",
    "good": "改善後の例",
    "reason": "なぜこのパターンが良いか"
  }
}
```

### プロンプトへの活用

```
以下の書き味パターンに従って文章を書き直してください：

- self-experience: 自分の経験として語る
- psychological-barrier: 心理的障壁を語る
- honest-result: 理想と現実のギャップを正直に

元の文章:
{rejected}

改善後:
```

## データの蓄積

新しい記事をレビューする度に:

1. AI版とユーザー版の差分を抽出
2. 適用されたパターンをタグ付け
3. preference_pairs/*.jsonl に追加
4. 必要に応じて patterns.json を更新

## 関連

- Issue #181: 書き味研究の元Issueの詳細
- AGENTS.md: 書き味の基準セクション
