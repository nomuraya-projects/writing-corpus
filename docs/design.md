# writing-corpus システム設計書

## 概要

FC2ブログ記事660件（2008-2013年）を体系化し、AI記事執筆の品質向上に活用するシステム。

## アーキテクチャ

### データフロー

```
FC2記事660件（元データ）
    ↓ コピー
data/raw/fc2_extracted/ （永久保存・Read-only）
    ↓ メタデータ抽出
data/corpus/metadata.json （状態管理）
    ↓ 分析・サンプリング
data/corpus/{writing-patterns,expression-dict}.json
    ↓ 統合
article-creation/writing-evaluation/article-review モード
```

### 状態管理

FC2記事は2つの場所で管理される：

1. **writing-corpus/data/raw/** - AI学習用（永久保存）
2. **note/drafts/wordpress/fc2_extracted/** - note.comリライト用（作業用）

`metadata.json` が両者の状態を一元管理。

## データスキーマ

### metadata.json

```json
{
  "articles": [
    {
      "id": "fc2_2010-05-09_001",
      "title": "【政治意見】義務教育の意味を疑う",
      "date": "2010-05-09",
      "category": "政治意見",
      "word_count": 1234,
      "year": 2010,

      "corpus_metadata": {
        "source_path": "data/raw/fc2_extracted/2010/05/...",
        "tags": ["論理展開", "感情表現強"],
        "quality_score": 0.85,
        "elo_rating": 1520,
        "sampled": true,
        "reference_article": false
      },

      "rewrite_status": {
        "status": "pending",
        "note_article_path": null,
        "rewrite_date": null,
        "rewrite_type": null,
        "deletion_reason": null,
        "archived_reason": null
      }
    }
  ],

  "statistics": {
    "total": 660,
    "by_status": {
      "pending": 620,
      "in_progress": 5,
      "completed": 30,
      "deleted": 3,
      "archived": 2
    }
  }
}
```

### rewrite_status 値

| status | 説明 |
|--------|------|
| `pending` | 未処理 |
| `in_progress` | リライト作業中 |
| `completed` | リライト完了（note/articles/に移動済み） |
| `deleted` | 削除済み |
| `archived` | アーカイブ（削除せず保存） |

## スクリプト仕様

### metadata_extractor.py

**目的**: FC2記事からメタデータを抽出

**入力**: `data/raw/fc2_extracted/`
**出力**: `data/corpus/metadata.json`

**処理内容**:
1. Markdown frontmatter解析（title, date, original_id）
2. 本文から文字数カウント
3. タイトルからカテゴリ抽出（【徒然】等）
4. 初期状態を `pending` で設定

### sync-rewrite-status.py

**目的**: note リポジトリの変更を metadata.json に反映

**入力**:
- `~/workspace-ai/nomuraya-blogs/note/drafts/wordpress/fc2_extracted/`
- `data/corpus/metadata.json`

**出力**: 更新された `metadata.json`

**処理内容**:
1. FC2記事ファイルの存在チェック
2. 削除検出 → status を `deleted` に
3. note/articles/ への移動検出 → status を `completed` に
4. ファイル更新検出 → status を `in_progress` に
5. 統計情報更新

### generate-dashboard.py

**目的**: 運用ダッシュボード生成

**入力**: `data/corpus/metadata.json`
**出力**: `docs/dashboard.md`

**処理内容**:
1. 全体統計（状態別件数）
2. AI学習用コーパス統計（サンプリング数、ELO等）
3. note.comリライト進捗（カテゴリ別）
4. 最近の変更履歴

## 統合設計

### article-creation.md 統合

**参照方法**:
- Prompt Caching でFC2記事サンプル10-20件を参照
- 特に「書き味の温度」「論理展開パターン」を学習

**実装場所**: `integration/article-creation/`

### writing-evaluation.md 統合

**ELOプール追加**:
- FC2記事50件をA/B比較対象に追加
- 高ELO記事を「参照記事」として認定

**実装場所**: `integration/writing-evaluation/`

### article-review.md 統合

**許容表現リスト**:
- FC2記事から頻出表現を抽出
- 過剰な禁止ルールを緩和

**実装場所**: `integration/article-review/`

## 運用フロー

### Phase 1: データ収集・整備

```bash
# 1. FC2記事をコピー
cd ~/workspace-ai/writing-corpus
cp -r ~/workspace-ai/nomuraya-blogs/note/drafts/wordpress/fc2_extracted \
      data/raw/

# 2. Read-only化
chmod -R a-w data/raw/fc2_extracted/

# 3. メタデータ生成
python scripts/extract/metadata_extractor.py

# 4. コミット
git add data/
git commit -m "feat: FC2記事660件とメタデータを追加"
git push
```

### Phase 2以降

詳細は各Phaseのマイルストーンを参照。

## nomuraya-operation への移行条件

1. ✅ Phase 1-4完了
2. ✅ 統合テスト成功率90%以上
3. ✅ ドキュメント整備完了
4. ✅ ユーザー承認

移行後は `nomuraya-operation/writing-corpus` で運用。
