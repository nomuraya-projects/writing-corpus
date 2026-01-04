# article-creation モード統合

**目的**: FC2記事をPrompt Cachingで参照し、AI非使用の書き味を学習

---

## 統合方法

### 1. 参照記事の抽出

**基準**:
- ELO 1550以上（高品質）
- リライトスコア50点以上（価値あり）
- 文字数800字以上（学習に十分な量）

**抽出クエリ**:

```bash
python3 scripts/sample/smart-sampler.py \
  --min-elo 1550 \
  --min-score 50 \
  --limit 20 \
  --order-by elo_rating \
  --format json \
  --output integration/article-creation/reference-articles.json
```

### 2. カテゴリ別サンプリング

**記事のテーマに応じてサンプリング**:

| 執筆テーマ | 参照カテゴリ | サンプル数 |
|----------|------------|----------|
| 技術記事・解説 | 考察、TRPG | 10件 |
| レビュー・批評 | レビュー、東方二次創作 | 10件 |
| エッセイ・体験記 | 徒然、報告 | 10件 |

**実装例**:

```python
# カテゴリ別サンプリング
tech_samples = sample_by_criteria(
    db_path,
    category="考察",
    min_elo=1520,
    limit=5
)

review_samples = sample_by_criteria(
    db_path,
    category="レビュー",
    min_elo=1520,
    limit=5
)
```

---

## Prompt Caching戦略

### 1. システムプロンプトへの追加

**現状**:
```
あなたはプロの記事ライターです。
読者に響く、わかりやすい記事を執筆してください。
```

**統合後**:
```
あなたはプロの記事ライターです。
以下は2008-2013年のAI非使用記事（書き味参照用）です。

<reference_articles>
[FC2記事10-20件の本文]
</reference_articles>

この書き味を参考に、読者に響く、わかりやすい記事を執筆してください。

【参考にすべき書き味の特徴】
- 論理展開: 反語型、極論前置き型
- 感情表現: 「〜じゃないか？」「〜でいいじゃない！」
- 構造: 起承転結、具体例の提示
```

### 2. Prompt Caching設定

**Claude APIのPrompt Caching**:
- 参照記事部分を`system`プロンプトに配置
- Cachingにより2回目以降のトークン消費を90%削減

**実装例**:

```python
import anthropic

client = anthropic.Anthropic()

# 参照記事を読み込み
with open('integration/article-creation/reference-articles.json') as f:
    references = json.load(f)

# システムプロンプト構築
system_prompt = [
    {
        "type": "text",
        "text": "あなたはプロの記事ライターです。"
    },
    {
        "type": "text",
        "text": f"以下は2008-2013年のAI非使用記事（書き味参照用）です。\n\n{format_references(references)}",
        "cache_control": {"type": "ephemeral"}  # Caching有効化
    }
]

response = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=2000,
    system=system_prompt,
    messages=[
        {"role": "user", "content": "技術記事を執筆してください"}
    ]
)
```

---

## 書き味パターンの抽出

### 1. 論理展開パターン

**抽出対象**:
- 反語型: 「〜じゃないか？」「〜というのはおかしいんじゃないか？」
- 極論前置き型: 「はっきり言って〜」「正直な話〜」
- 段階的展開: 「まず〜、次に〜、最後に〜」

**実装**: `scripts/analyze/extract-patterns.py`

### 2. 感情表現辞書

**抽出対象**:
- 肯定表現: 「〜でいいじゃない！」「素晴らしい」
- 否定表現: 「〜はクソ」「まぁ、〜だが」
- 驚き表現: 「マジか！」「ちょ、まずはこいつを見てくれ」

### 3. 構造特徴

**抽出対象**:
- 導入部: 「〜です、おはこんにちばんわ！」
- 結論部: 「まとめると〜」「結論としては〜」
- 補足部: 「ちなみに〜」「余談ですが〜」

---

## 統合の段階的実施

### Phase 1: 手動統合（テスト）

1. 高ELO記事10件を手動抽出
2. システムプロンプトに追加
3. 記事執筆テスト（3-5記事）
4. 書き味の違いを評価

### Phase 2: 自動サンプリング

1. `smart-sampler.py`で自動抽出
2. Prompt Cachingを有効化
3. 執筆テスト（10記事以上）

### Phase 3: カテゴリ別最適化

1. 執筆テーマ別にサンプリング戦略を調整
2. 書き味パターン抽出の自動化
3. 継続的な品質評価

---

## 評価指標

### 1. 書き味の近似度

**評価方法**: writing-evaluationモードでA/B比較
- A: FC2記事（参照元）
- B: 新規執筆記事（AI生成）

→ ELOが近ければ書き味が似ている

### 2. 表現の多様性

**評価方法**: 特徴語の出現頻度
- 反語表現の使用率
- 感情表現の使用率
- 極論表現の使用率

### 3. 読者反応

**評価方法**: note.com公開後の反応
- スキ数
- コメント数
- 読了率（Analytics）

---

## 期待される効果

### 1. AI臭の低減

AI生成記事特有の「優等生的な文章」から、生の書き味へ。

### 2. 個性の維持

2008-2013年の書き味を学習することで、個人の文体を維持。

### 3. エンタメ性の向上

FC2記事の「エンタメ性」（ユーモア、感情表現）をAI生成記事に反映。

---

## 次のステップ

1. `extract-patterns.py` 実装（書き味パターン抽出）
2. 高ELO記事10件の手動抽出
3. Prompt Cachingテスト
4. writing-evaluationモードでの評価
