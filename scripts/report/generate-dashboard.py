#!/usr/bin/env python3
"""
運用ダッシュボードを生成する

目的: metadata.jsonから統計情報を抽出し、docs/dashboard.mdを生成
使い方: python3 generate-dashboard.py
出力: docs/dashboard.md
"""

import json
from pathlib import Path
from datetime import datetime


def format_statistics(metadata: dict) -> str:
    """統計情報をMarkdown形式でフォーマット"""
    stats = metadata['statistics']

    md = "## 全体統計\n\n"
    md += f"- **総記事数**: {stats['total']}件\n"
    md += f"- **最終更新**: {metadata['generated_at'][:10]}\n\n"

    # 年別統計
    md += "### 年別分布\n\n"
    md += "| 年 | 件数 |\n"
    md += "|---|------|\n"
    for year, count in stats['by_year'].items():
        md += f"| {year} | {count}件 |\n"
    md += "\n"

    # カテゴリ別統計（上位10件）
    md += "### カテゴリ別分布（上位10件）\n\n"
    md += "| カテゴリ | 件数 |\n"
    md += "|---------|------|\n"
    for category, count in list(stats['by_category'].items())[:10]:
        category_name = category if category != "null" else "未分類"
        md += f"| {category_name} | {count}件 |\n"
    md += "\n"

    # リライト状態別統計
    md += "### リライト状態別\n\n"
    md += "| 状態 | 件数 |\n"
    md += "|------|------|\n"
    for status, count in stats['by_status'].items():
        status_ja = {
            "pending": "未処理",
            "in_progress": "作業中",
            "completed": "完了",
            "deleted": "削除済み",
            "archived": "アーカイブ"
        }.get(status, status)
        md += f"| {status_ja} | {count}件 |\n"
    md += "\n"

    return md


def format_corpus_stats(articles: list) -> str:
    """AI学習用コーパス統計をフォーマット"""
    md = "## AI学習用コーパス統計\n\n"

    # サンプリング済み記事数
    sampled_count = sum(1 for a in articles if a['corpus_metadata']['sampled'])
    reference_count = sum(1 for a in articles if a['corpus_metadata']['reference_article'])

    md += f"- **サンプリング済み**: {sampled_count}件\n"
    md += f"- **参照記事**: {reference_count}件\n"
    md += f"- **平均ELO**: 1500（初期値）\n\n"

    md += "### 品質スコア分布\n\n"
    md += "（まだ評価未実施）\n\n"

    return md


def format_rewrite_progress(articles: list, stats: dict) -> str:
    """note.comリライト進捗をフォーマット"""
    md = "## note.comリライト進捗\n\n"

    # 状態別集計
    by_status = stats['by_status']
    total = stats['total']
    pending = by_status.get('pending', 0)
    in_progress = by_status.get('in_progress', 0)
    completed = by_status.get('completed', 0)

    progress_rate = (completed / total * 100) if total > 0 else 0

    md += f"- **進捗率**: {progress_rate:.1f}% ({completed}/{total}件)\n"
    md += f"- **未処理**: {pending}件\n"
    md += f"- **作業中**: {in_progress}件\n\n"

    # カテゴリ別進捗（予定）
    md += "### カテゴリ別進捗\n\n"
    md += "（Phase 1.2完了後に表示）\n\n"

    return md


def format_recent_changes(metadata: dict) -> str:
    """最近の変更履歴をフォーマット"""
    md = "## 最近の変更履歴\n\n"

    # エラーがあれば表示
    if metadata.get('errors'):
        md += f"⚠️ **エラー**: {len(metadata['errors'])}件\n\n"
        for error in metadata['errors'][:5]:
            md += f"- {error['file']}: {error['error']}\n"
        md += "\n"

    md += "### 最新コミット\n\n"
    md += "- Phase 1.1完了: metadata.json生成\n"
    md += "- 660件のFC2記事をメタデータ化\n\n"

    return md


def generate_dashboard(metadata_path: Path, output_path: Path):
    """ダッシュボードを生成"""
    with metadata_path.open('r', encoding='utf-8') as f:
        metadata = json.load(f)

    articles = metadata['articles']
    stats = metadata['statistics']

    # Markdownコンテンツ生成
    md = "# writing-corpus ダッシュボード\n\n"
    md += f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    md += "---\n\n"

    md += format_statistics(metadata)
    md += format_corpus_stats(articles)
    md += format_rewrite_progress(articles, stats)
    md += format_recent_changes(metadata)

    md += "---\n\n"
    md += "## 次のアクション\n\n"
    md += "- [ ] Phase 1.2: リライト判断基準策定\n"
    md += "- [ ] サンプル記事評価（10-20件）\n"
    md += "- [ ] 2023年「Hello world!」記事の削除\n\n"

    # 出力
    with output_path.open('w', encoding='utf-8') as f:
        f.write(md)

    print(f"✅ ダッシュボードを生成しました: {output_path}")


def main():
    project_root = Path(__file__).parent.parent.parent
    metadata_path = project_root / "data" / "corpus" / "metadata.json"
    output_path = project_root / "docs" / "dashboard.md"

    if not metadata_path.exists():
        print(f"❌ metadata.jsonが見つかりません: {metadata_path}")
        return

    generate_dashboard(metadata_path, output_path)


if __name__ == "__main__":
    main()
