# writing-corpus ロードマップ

## 現状と課題

### 価値A: note.comリライト素材（課題）
**現状**: FC2記事660件が `note/drafts/wordpress/fc2_extracted/` に配置されているが、選別基準が不明確

**課題**:
1. どの記事をリライトするか？
2. どの記事を削除するか？
3. 判断基準の策定

**リスク**: 手当たり次第にリライト → 陳腐化した記事を公開してしまう

---

### 価値B: AI学習用コーパス（課題）
**現状**: FC2記事660件が `data/raw/fc2_extracted/` にファイルとして保存されているが、参照しにくい

**課題**:
1. ファイルベース → データベース化
2. メタデータ不足（カテゴリ、書き味特徴等）
3. 検索・抽出が困難

**リスク**: AI学習時に全660件を毎回読み込む → トークン浪費、非効率

---

## Phase別ロードマップ

### Phase 1: データ収集・整備（現在地）

#### Phase 1.1: メタデータ生成 ✅
- [x] FC2記事660件をコピー
- [x] Read-only化
- [ ] metadata.json生成（次タスク）

#### Phase 1.2: 選別基準策定（価値A対応）
**目的**: リライト vs 削除の判断基準を明確化

**アプローチ**:
1. カテゴリ別に価値評価
2. サンプリング記事（各カテゴリ3-5件）を実際に読む
3. 判断基準フレームワーク策定

**成果物**:
- `docs/rewrite-criteria.md` - リライト判断基準
- `data/processed/rewrite-candidates.json` - リライト候補リスト
- `data/processed/deletion-candidates.json` - 削除候補リスト

**判断軸（案）**:
| 軸 | 評価基準 | 重み |
|----|---------|------|
| 時代性 | 2026年に読んでも価値があるか | 30% |
| 普遍性 | 個人的すぎないか | 25% |
| エンタメ性 | 読み物として面白いか | 20% |
| リライト工数 | 修正量が多すぎないか | 15% |
| リスク | 炎上リスク、センシティブ情報 | 10% |

**スコアリング**:
- 70点以上: リライト確定
- 50-69点: 保留（ユーザー判断）
- 49点以下: 削除候補

---

### Phase 2: データベース化（価値B対応）

#### Phase 2.1: データベース選定
**候補**:

| DB | メリット | デメリット | 推奨度 |
|----|---------|----------|--------|
| **SQLite** | 軽量、ファイルベース、SQL使える | 同時書き込み弱い | ⭐⭐⭐⭐⭐ |
| **Supabase** | PostgreSQL、既存運用と統合可 | 外部依存 | ⭐⭐⭐⭐ |
| **JSON** | シンプル、Git管理可 | 検索遅い、大規模不向き | ⭐⭐⭐ |

**推奨**: **SQLite** （ローカル完結、検索高速、Git管理可能）

#### Phase 2.2: スキーマ設計

```sql
-- articles テーブル
CREATE TABLE articles (
  id TEXT PRIMARY KEY,           -- fc2_2010-05-09_001
  title TEXT NOT NULL,
  date DATE NOT NULL,
  year INTEGER NOT NULL,
  category TEXT,                 -- 【徒然】等
  word_count INTEGER,
  file_path TEXT NOT NULL,       -- data/raw/fc2_extracted/...
  content TEXT,                  -- 本文（全文検索用）

  -- AI学習用メタデータ
  quality_score REAL,            -- 0.0-1.0
  elo_rating INTEGER DEFAULT 1500,
  sampled BOOLEAN DEFAULT 0,
  reference_article BOOLEAN DEFAULT 0,

  -- note.comリライト用メタデータ
  rewrite_status TEXT DEFAULT 'pending',  -- pending/in_progress/completed/deleted/archived
  rewrite_score REAL,            -- リライト価値スコア（0-100）
  note_article_path TEXT,
  rewrite_date DATE,
  rewrite_type TEXT,             -- タイムカプセル型/文化史抽出型/哲学昇華型
  deletion_reason TEXT,

  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- tags テーブル（多対多）
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL      -- 論理展開、感情表現強、等
);

CREATE TABLE article_tags (
  article_id TEXT,
  tag_id INTEGER,
  FOREIGN KEY (article_id) REFERENCES articles(id),
  FOREIGN KEY (tag_id) REFERENCES tags(id),
  PRIMARY KEY (article_id, tag_id)
);

-- writing_patterns テーブル
CREATE TABLE writing_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pattern_type TEXT NOT NULL,    -- 論理展開/感情表現/構造特徴
  pattern_name TEXT NOT NULL,    -- 反語型、極論前置き型、等
  pattern TEXT,                  -- 正規表現 or 説明
  examples TEXT                  -- JSON配列: ["fc2_2010-05-09_001", ...]
);

-- elo_comparisons テーブル
CREATE TABLE elo_comparisons (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_a TEXT NOT NULL,
  article_b TEXT NOT NULL,
  winner TEXT,                   -- A/B/draw
  context TEXT,                  -- 体験の具体性、等
  confidence TEXT,               -- high/medium/low
  compared_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (article_a) REFERENCES articles(id),
  FOREIGN KEY (article_b) REFERENCES articles(id)
);
```

#### Phase 2.3: データ移行

```python
# scripts/export/migrate-to-sqlite.py
import sqlite3
import json
from pathlib import Path

def migrate():
    conn = sqlite3.connect('data/corpus/writing-corpus.db')

    # metadata.json を読み込み
    metadata = json.load(open('data/corpus/metadata.json'))

    for article in metadata['articles']:
        # articles テーブルに挿入
        conn.execute("""
            INSERT INTO articles (id, title, date, ...)
            VALUES (?, ?, ?, ...)
        """, (...))

    conn.commit()
```

---

### Phase 3: 検索・抽出システム

#### Phase 3.1: 全文検索

```sql
-- SQLite FTS5（全文検索）
CREATE VIRTUAL TABLE articles_fts USING fts5(
  title, category, content,
  content='articles',
  content_rowid='rowid'
);

-- 検索例
SELECT * FROM articles_fts
WHERE articles_fts MATCH '論理展開 AND 政治'
ORDER BY rank;
```

#### Phase 3.2: スマートサンプリング

```python
# scripts/sample/smart-sampler.py
import sqlite3

def sample_by_criteria(
    category: str = None,
    min_quality_score: float = 0.7,
    limit: int = 50
) -> list:
    """条件指定でサンプリング"""
    conn = sqlite3.connect('data/corpus/writing-corpus.db')

    query = """
        SELECT * FROM articles
        WHERE quality_score >= ?
    """
    params = [min_quality_score]

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY quality_score DESC LIMIT ?"
    params.append(limit)

    return conn.execute(query, params).fetchall()
```

#### Phase 3.3: 類似記事検索（将来）

**技術**: 埋め込みベクトル（OpenAI Embeddings等）

```python
# 記事の埋め込みベクトルを生成
embeddings = openai.Embedding.create(
    input=article['content'],
    model="text-embedding-ada-002"
)

# ベクトル類似度で類似記事検索
similar_articles = search_similar(embeddings, top_k=10)
```

---

## Phase 4: 統合・運用

### Phase 4.1: article-creation モード統合

**統合方法**: Prompt Caching + データベースクエリ

```python
# article-creation モード内で実行
import sqlite3

# 1. カテゴリ別サンプリング
samples = sample_by_criteria(
    category="ゲーム製作論",
    min_quality_score=0.8,
    limit=10
)

# 2. Prompt Caching でコンテキストに追加
system_prompt = f"""
以下は2008-2013年のAI非使用記事（書き味参照用）:

{format_samples(samples)}

この書き味を参考に記事を生成してください。
"""
```

### Phase 4.2: note.comリライトワークフロー

```bash
# 1. リライト候補を抽出
python scripts/sample/extract-rewrite-candidates.py \
  --min-score 70 \
  --output data/processed/rewrite-queue.json

# 2. 記事をリライト
# （note リポジトリで作業）

# 3. 状態同期
python scripts/sync/sync-rewrite-status.py

# 4. データベース更新
python scripts/export/update-db-from-metadata.py
```

---

## マイルストーン

### M1: Phase 1完了（1-2週間）
- [ ] metadata.json生成
- [ ] リライト判断基準策定
- [ ] サンプル記事評価（各カテゴリ3-5件）

### M2: Phase 2完了（2-3週間）
- [ ] SQLiteデータベース構築
- [ ] データ移行完了
- [ ] 全文検索実装

### M3: Phase 3完了（1-2週間）
- [ ] スマートサンプリング実装
- [ ] 書き味パターン抽出

### M4: Phase 4完了（2週間）
- [ ] article-creation統合
- [ ] writing-evaluation統合
- [ ] article-review統合

### M5: operation移行（1週間）
- [ ] ドキュメント最終化
- [ ] nomuraya-operation/writing-corpus へ移行

**総期間**: 6-10週間

---

## 優先度

| Phase | 優先度 | 理由 |
|-------|--------|------|
| Phase 1.1 (metadata.json) | 🔥 最高 | すべての基盤 |
| Phase 1.2 (選別基準) | 🔥 最高 | note.comリライト作業に必須 |
| Phase 2 (DB化) | ⭐ 高 | 効率化・スケーラビリティ |
| Phase 3 (検索) | ⭐ 高 | AI学習用に必須 |
| Phase 4 (統合) | 中 | Phase 1-3完了後 |

---

## 次のアクション（今週）

1. **metadata_extractor.py 実装**
2. **metadata.json 生成**
3. **リライト判断基準ドラフト作成**
4. **サンプル記事評価（10件程度）**
