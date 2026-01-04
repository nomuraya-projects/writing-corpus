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
- [ ] Phase 1: データ収集・整備
  - [ ] FC2記事660件をdata/raw/にコピー
  - [ ] metadata.json生成
- [ ] Phase 2: 書き味分析
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

### 価値B: AI学習用コーパス
- 場所: `writing-corpus/data/raw/fc2_extracted/`
- 性質: **永久保存・変更禁止**（Read-only）

両者は `data/corpus/metadata.json` で状態管理され、同期スクリプトで連携。

## 🔗 関連リポジトリ

- [nomuraya-articles/note](https://github.com/nomuraya-articles/note) - note.com記事管理（リライト作業場所）
- [nomuraya-articles/Zenn](https://github.com/nomuraya-articles/Zenn) - Zenn記事管理（article-creation統合先）

## 📝 ライセンス

MIT License
