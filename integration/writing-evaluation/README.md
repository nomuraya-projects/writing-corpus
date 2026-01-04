# writing-evaluation モード統合

**目的**: FC2記事660件をELO評価プールに追加し、高品質記事を発掘

---

## 統合方法

### 1. ELOプール追加

**現状のwriting-evaluationモード**:
- プール: 2023年以降の記事
- ELO評価: article-comparisons.json

**統合後**:
- プール: 2023年以降の記事 + FC2記事660件
- ELO評価: writing-corpus.db（elo_comparisonsテーブル）

### 2. 統合スクリプト

**場所**: `integration/writing-evaluation/sync-elo-to-corpus.py`

**機能**:
1. `~/.llms/article-comparisons.json` から既存のELO評価を読み込み
2. FC2記事のIDに該当するものをwriting-corpus.dbに反映
3. `elo_comparisons`テーブルに比較履歴を記録
4. `articles`テーブルの`elo_rating`を更新

### 3. サンプリング戦略

**探索対象**（ELO未評価のFC2記事）:
- 比較回数3回未満
- リライトスコア50点以上（価値ある記事に絞る）

**活用対象**（ELO 1520以上の高品質記事）:
- AI学習用サンプリングの候補
- 「参照記事」として認定（ELO 1550以上 + 比較5回以上）

---

## 実装例

### sync-elo-to-corpus.py

```python
#!/usr/bin/env python3
import json
import sqlite3
from pathlib import Path

def sync_elo_ratings():
    # article-comparisons.json 読み込み
    comparisons_file = Path.home() / ".llms" / "article-comparisons.json"
    if not comparisons_file.exists():
        print("article-comparisons.json が見つかりません")
        return

    with comparisons_file.open('r') as f:
        data = json.load(f)

    # writing-corpus.db に接続
    db_path = Path(__file__).parent.parent.parent / "data" / "corpus" / "writing-corpus.db"
    conn = sqlite3.connect(db_path)

    # ELO評価を反映
    for article_id, rating_data in data.get('ratings', {}).items():
        if article_id.startswith('fc2_'):
            elo = rating_data.get('elo', 1500)
            comparison_count = rating_data.get('comparisonCount', 0)

            conn.execute("""
                UPDATE articles
                SET elo_rating = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (elo, article_id))

            print(f"更新: {article_id} → ELO {elo} (比較{comparison_count}回)")

    # 比較履歴を記録
    for comparison in data.get('comparisons', []):
        article_a = comparison.get('articleA')
        article_b = comparison.get('articleB')

        if article_a.startswith('fc2_') or article_b.startswith('fc2_'):
            conn.execute("""
                INSERT INTO elo_comparisons (article_a, article_b, winner, context, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                article_a,
                article_b,
                comparison.get('winner'),
                comparison.get('context'),
                comparison.get('confidence')
            ))

    conn.commit()
    conn.close()

    print("✅ ELO評価の同期完了")

if __name__ == "__main__":
    sync_elo_ratings()
```

---

## writing-evaluationモードでの利用

### モード内での統合

**場所**: `~/.claude-config/modes/writing-evaluation.md`

**修正箇所**:

```markdown
## プール定義

| プール | 条件 | 役割 |
|--------|------|------|
| 探索対象（2023年以降） | 比較3回未満 | 未評価発掘 |
| 探索対象（FC2記事） | 比較3回未満 + リライトスコア50点以上 | AI非使用の書き味発掘 |
| 活用対象 | ELO 1520以上 | 良いもの活用 |
| 参照記事 | ELO 1550以上 + 比較5回以上 | 書き味の手本 |
```

### A/B比較の対戦カード選出

**改善案**:
- A: 活用対象（ELO 1520以上の2023年以降記事）
- B: 探索対象（ELO未評価のFC2記事、リライトスコア50点以上）

→ 新旧記事を比較することで、AI使用前後の書き味の違いを評価

---

## 参照記事の活用

### article-creationモードでの利用

**高ELO FC2記事を参照**:
- ELO 1550以上のFC2記事を「書き味の手本」として抽出
- Prompt Cachingで10-20件をコンテキストに追加
- 特に「論理展開パターン」「感情表現」を学習

**サンプリングクエリ**:

```bash
python3 scripts/sample/smart-sampler.py \
  --min-elo 1550 \
  --min-score 50 \
  --limit 20 \
  --order-by elo_rating \
  --format json \
  --output integration/article-creation/reference-articles.json
```

---

## 統合のメリット

### 1. 書き味の多様性

2023年以降のAI使用記事だけでなく、2008-2013年のAI非使用記事も評価対象に。

→ AI使用前後の書き味の違いを定量的に評価可能

### 2. 高品質記事の発掘

ELO評価により、FC2記事660件から高品質記事を自動発掘。

→ リライト候補の優先順位付けに活用

### 3. 参照記事プールの拡大

ELO 1550以上の記事が増えることで、AI学習用サンプルが充実。

→ article-creationモードの品質向上

---

## 次のステップ

1. `sync-elo-to-corpus.py` 実装
2. writing-evaluationモードの修正
3. article-creationモードへの統合
4. 定期的なELO同期（週次バッチ等）
