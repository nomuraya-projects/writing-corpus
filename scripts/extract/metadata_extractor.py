#!/usr/bin/env python3
"""
FC2記事からメタデータを抽出してmetadata.jsonを生成する

目的: 660件のFC2記事から以下を抽出
- 基本情報（id, title, date, category, word_count）
- コーパス用メタデータ（quality_score, elo_rating等）
- リライト状態（status, score等）

使い方: python3 metadata_extractor.py
出力: data/corpus/metadata.json
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional


def extract_frontmatter(content: str) -> Dict[str, any]:
    """
    Markdownファイルのfrontmatterを抽出

    Args:
        content: ファイル全体の内容

    Returns:
        frontmatter辞書（title, date, original_id）
    """
    frontmatter_match = re.match(r'^---\n(.*?)\n---\n', content, re.DOTALL)
    if not frontmatter_match:
        return {}

    frontmatter_text = frontmatter_match.group(1)
    frontmatter = {}

    for line in frontmatter_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip().strip('"\'')

            if key == 'date':
                frontmatter[key] = value
            elif key == 'original_id':
                frontmatter[key] = int(value) if value.isdigit() else value
            else:
                frontmatter[key] = value

    return frontmatter


def extract_category(title: str) -> Optional[str]:
    """
    タイトルから【カテゴリ】を抽出

    Args:
        title: 記事タイトル

    Returns:
        カテゴリ名（【】なしの文字列）、なければNone
    """
    category_match = re.search(r'【(.+?)】', title)
    return category_match.group(1) if category_match else None


def count_words(content: str) -> int:
    """
    本文の文字数をカウント（frontmatterを除く）

    Args:
        content: ファイル全体の内容

    Returns:
        文字数
    """
    # frontmatterを除去
    body = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)

    # 空白・改行を除いた文字数
    body_cleaned = re.sub(r'\s+', '', body)

    return len(body_cleaned)


def generate_article_id(date_str: str, original_id: any) -> str:
    """
    記事IDを生成（fc2_YYYY-MM-DD_NNN形式）

    Args:
        date_str: 日付文字列（YYYY-MM-DD）
        original_id: FC2のオリジナルID

    Returns:
        記事ID
    """
    # original_idを3桁ゼロパディング
    id_num = str(original_id).zfill(3)
    return f"fc2_{date_str}_{id_num}"


def extract_article_metadata(file_path: Path, base_dir: Path) -> Dict:
    """
    1つのFC2記事からメタデータを抽出

    Args:
        file_path: 記事ファイルのパス
        base_dir: data/raw/fc2_extracted/のパス

    Returns:
        記事メタデータ辞書
    """
    content = file_path.read_text(encoding='utf-8')
    frontmatter = extract_frontmatter(content)

    title = frontmatter.get('title', file_path.stem)
    date_str = str(frontmatter.get('date', ''))
    original_id = frontmatter.get('original_id', 0)

    # 相対パス取得
    try:
        relative_path = file_path.relative_to(base_dir)
    except ValueError:
        relative_path = file_path

    article_id = generate_article_id(date_str, original_id)
    category = extract_category(title)
    word_count = count_words(content)

    # 年を抽出
    year = int(date_str.split('-')[0]) if date_str and '-' in date_str else None

    return {
        "id": article_id,
        "title": title,
        "date": date_str,
        "category": category,
        "word_count": word_count,
        "year": year,
        "original_id": original_id,

        "corpus_metadata": {
            "source_path": f"data/raw/fc2_extracted/{relative_path}",
            "tags": [],  # 将来的に分析で追加
            "quality_score": None,  # 将来的にELO評価で設定
            "elo_rating": 1500,  # 初期値
            "sampled": False,
            "reference_article": False
        },

        "rewrite_status": {
            "status": "pending",  # pending/in_progress/completed/deleted/archived
            "rewrite_score": None,  # 0-100点
            "note_article_path": None,
            "rewrite_date": None,
            "rewrite_type": None,  # タイムカプセル型/文化史抽出型/哲学昇華型
            "deletion_reason": None,
            "archived_reason": None
        }
    }


def generate_statistics(articles: List[Dict]) -> Dict:
    """
    統計情報を生成

    Args:
        articles: 記事リスト

    Returns:
        統計情報辞書
    """
    total = len(articles)

    # 状態別カウント
    status_counts = {}
    for article in articles:
        status = article["rewrite_status"]["status"]
        status_counts[status] = status_counts.get(status, 0) + 1

    # 年別カウント
    year_counts = {}
    for article in articles:
        year = article.get("year")
        if year:
            year_counts[year] = year_counts.get(year, 0) + 1

    # カテゴリ別カウント
    category_counts = {}
    for article in articles:
        category = article.get("category", "未分類")
        category_counts[category] = category_counts.get(category, 0) + 1

    return {
        "total": total,
        "by_status": status_counts,
        "by_year": dict(sorted(year_counts.items())),
        "by_category": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
    }


def main():
    """メイン処理"""
    # パス設定
    project_root = Path(__file__).parent.parent.parent
    fc2_dir = project_root / "data" / "raw" / "fc2_extracted"
    output_dir = project_root / "data" / "corpus"
    output_file = output_dir / "metadata.json"

    # 出力ディレクトリ作成
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"FC2記事ディレクトリ: {fc2_dir}")
    print(f"出力先: {output_file}")

    # FC2記事をすべて収集
    md_files = sorted(fc2_dir.glob("**/*.md"))
    print(f"\n検出したFC2記事: {len(md_files)}件")

    # メタデータ抽出
    articles = []
    errors = []

    for i, md_file in enumerate(md_files, 1):
        try:
            article = extract_article_metadata(md_file, fc2_dir)
            articles.append(article)

            if i % 100 == 0:
                print(f"処理中... {i}/{len(md_files)}")
        except Exception as e:
            errors.append({"file": str(md_file), "error": str(e)})
            print(f"エラー: {md_file} - {e}")

    print(f"\n抽出完了: {len(articles)}件")

    if errors:
        print(f"エラー件数: {len(errors)}件")

    # 統計情報生成
    statistics = generate_statistics(articles)

    # メタデータJSON生成
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "version": "1.0",
        "articles": articles,
        "statistics": statistics,
        "errors": errors
    }

    # 出力
    with output_file.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ metadata.json を生成しました: {output_file}")
    print(f"\n📊 統計情報:")
    print(f"  総記事数: {statistics['total']}件")
    print(f"  年別:")
    for year, count in statistics['by_year'].items():
        print(f"    {year}: {count}件")
    print(f"\n  カテゴリ別（上位5件）:")
    for category, count in list(statistics['by_category'].items())[:5]:
        print(f"    {category}: {count}件")


if __name__ == "__main__":
    main()
