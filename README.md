# writing-corpus

AI以前（2008-2013年）の生の書き味データを体系化し、記事執筆AIの品質向上に活用するプロジェクト。

## 🎯 目的

- **FC2ブログ記事660件**からAI非使用の書き味パターンを抽出
- 記事執筆モード（article-creation）の参照コーパスとして提供
- A/B評価（writing-evaluation）で高品質記事を発掘
- note.comリライト作業との両立運用

## 📊 ステータス

🚧 **開発中**（nomuraya-projects）

完成後は **nomuraya-operation** へ移行予定

📈 [ダッシュボード](docs/dashboard.md) - 最新の統計情報と進捗

## 📦 構成

```
writing-corpus/
├── data/
│   ├── raw/              # FC2記事660件（永久保存・Read-only）
│   ├── processed/        # 処理済みデータ
│   └── corpus/           # 学習用コーパス
├── scripts/
│   ├── extract/          # メタデータ抽出
│   ├── analyze/          # 書き味分析
│   ├── sample/           # サンプリング
│   ├── sync/             # note リポジトリとの状態同期
│   └── report/           # レポート生成
└── integration/          # 既存モードとの統合設定
```

## 🚀 Phase

- [x] Phase 0: リポジトリ作成・初期セットアップ
- [x] **Phase 1: データ収集・整備（完了）**
  - [x] FC2記事660件をdata/raw/にコピー
  - [x] metadata.json生成（Phase 1.1完了）
  - [x] リライト判断基準策定（Phase 1.2完了）
    - ✅ リライト確定: 39件
    - ⏸️ 保留: 94件
    - 📦 アーカイブ: 470件
    - 🗑️ 削除候補: 57件
- [x] **Phase 2: データベース化（完了）**
  - [x] SQLiteデータベース構築（5.49MB）
  - [x] 全文検索（FTS5）実装
  - [x] スマートサンプリング実装
  - [ ] 論理展開パターン抽出
  - [ ] 感情表現辞書化
  - [ ] 構造特徴分析
- [ ] Phase 3: サンプリング
  - [ ] 代表50-100件選定
  - [ ] ELO評価システム統合
- [ ] Phase 4: 統合テスト
  - [ ] article-creation モード統合
  - [ ] writing-evaluation モード統合
  - [ ] article-review モード統合

## 💎 FC2記事の2つの価値

### 価値A: note.comリライト素材
- 場所: `nomuraya-articles/note/drafts/wordpress/fc2_extracted/`
- 性質: リライト・削除OK（作業用）
- **進捗**: Phase 1.2完了（スコアリング済み）

### 価値B: AI学習用コーパス
- 場所: `writing-corpus/data/raw/fc2_extracted/`
- 性質: **永久保存・変更禁止**（Read-only）
- **進捗**: Phase 2完了（SQLite化済み）
- **データベース**: writing-corpus.db（5.49MB、FTS5全文検索対応）

両者は `data/corpus/metadata.json` で状態管理され、同期スクリプトで連携。

詳細: [docs/rewrite-criteria.md](docs/rewrite-criteria.md)

## 🔗 関連リポジトリ

- [nomuraya-articles/note](https://github.com/nomuraya-articles/note) - note.com記事管理（リライト作業場所）
- [nomuraya-articles/Zenn](https://github.com/nomuraya-articles/Zenn) - Zenn記事管理（article-creation統合先）

## 📝 ライセンス

MIT License
