#!/usr/bin/env python3
"""
スマートサンプリング: 条件指定でコーパスを抽出

目的: AI学習用に最適な記事をサンプリング
使い方: python3 smart-sampler.py --category 徒然 --min-score 60 --limit 10
出力: 標準出力またはJSONファイル
"""

import sqlite3
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional


def sample_by_criteria(
    db_path: Path,
    category: Optional[str] = None,
    min_rewrite_score: Optional[float] = None,
    min_quality_score: Optional[float] = None,
    min_elo: Optional[int] = None,
    rewrite_type: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    limit: int = 50,
    order_by: str = "rewrite_score"
) -> List[Dict]:
    """
    条件指定でサンプリング

    Args:
        db_path: データベースファイルパス
        category: カテゴリ
        min_rewrite_score: リライトスコア最小値
        min_quality_score: 品質スコア最小値
        min_elo: ELO最小値
        rewrite_type: リライトタイプ
        year_from: 開始年
        year_to: 終了年
        limit: 取得件数上限
        order_by: ソート順（rewrite_score, elo_rating, word_count等）

    Returns:
        記事リスト
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM articles WHERE 1=1"
    params = []

    if category:
        query += " AND category = ?"
        params.append(category)

    if min_rewrite_score is not None:
        query += " AND rewrite_score >= ?"
        params.append(min_rewrite_score)

    if min_quality_score is not None:
        query += " AND quality_score >= ?"
        params.append(min_quality_score)

    if min_elo is not None:
        query += " AND elo_rating >= ?"
        params.append(min_elo)

    if rewrite_type:
        query += " AND rewrite_type = ?"
        params.append(rewrite_type)

    if year_from:
        query += " AND year >= ?"
        params.append(year_from)

    if year_to:
        query += " AND year <= ?"
        params.append(year_to)

    # ソート
    valid_order_by = ["rewrite_score", "elo_rating", "word_count", "date", "year"]
    if order_by in valid_order_by:
        query += f" ORDER BY {order_by} DESC"
    else:
        query += " ORDER BY rewrite_score DESC"

    query += " LIMIT ?"
    params.append(limit)

    cursor = conn.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return results


def search_full_text(db_path: Path, keyword: str, limit: int = 50) -> List[Dict]:
    """
    全文検索

    Args:
        db_path: データベースファイルパス
        keyword: 検索キーワード
        limit: 取得件数上限

    Returns:
        記事リスト
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT articles.*, rank
        FROM articles_fts
        JOIN articles ON articles.rowid = articles_fts.rowid
        WHERE articles_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """

    cursor = conn.execute(query, (keyword, limit))
    results = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return results


def get_top_articles_by_category(db_path: Path, limit_per_category: int = 5) -> Dict[str, List[Dict]]:
    """
    カテゴリ別のトップ記事を取得

    Args:
        db_path: データベースファイルパス
        limit_per_category: カテゴリごとの取得件数

    Returns:
        カテゴリ別記事辞書
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # カテゴリ一覧取得
    cursor = conn.execute("SELECT DISTINCT category FROM articles ORDER BY category")
    categories = [row[0] for row in cursor.fetchall()]

    results = {}

    for category in categories:
        query = """
            SELECT * FROM articles
            WHERE category = ?
            ORDER BY rewrite_score DESC
            LIMIT ?
        """
        cursor = conn.execute(query, (category, limit_per_category))
        results[category or "未分類"] = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return results


def get_random_sample(db_path: Path, limit: int = 10, seed: Optional[int] = None) -> List[Dict]:
    """
    ランダムサンプリング

    Args:
        db_path: データベースファイルパス
        limit: 取得件数
        seed: 乱数シード（再現性のため）

    Returns:
        記事リスト
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    if seed is not None:
        # SQLiteのRANDOMはシード固定できないので、Pythonで実装
        import random
        random.seed(seed)

        cursor = conn.execute("SELECT id FROM articles")
        all_ids = [row[0] for row in cursor.fetchall()]

        sampled_ids = random.sample(all_ids, min(limit, len(all_ids)))

        placeholders = ','.join('?' * len(sampled_ids))
        query = f"SELECT * FROM articles WHERE id IN ({placeholders})"
        cursor = conn.execute(query, sampled_ids)
    else:
        query = "SELECT * FROM articles ORDER BY RANDOM() LIMIT ?"
        cursor = conn.execute(query, (limit,))

    results = [dict(row) for row in cursor.fetchall()]

    conn.close()

    return results


def format_output(articles: List[Dict], format_type: str = "json") -> str:
    """
    出力フォーマット

    Args:
        articles: 記事リスト
        format_type: 出力形式（json, simple, markdown）

    Returns:
        フォーマット済み文字列
    """
    if format_type == "json":
        return json.dumps(articles, ensure_ascii=False, indent=2)

    elif format_type == "simple":
        lines = []
        for article in articles:
            lines.append(f"{article['id']}: {article['title']} ({article.get('rewrite_score', 'N/A')}点)")
        return '\n'.join(lines)

    elif format_type == "markdown":
        lines = ["| ID | タイトル | カテゴリ | スコア | タイプ |", "|---|---------|---------|--------|--------|"]
        for article in articles:
            lines.append(
                f"| {article['id']} | {article['title']} | {article.get('category', '未分類')} | "
                f"{article.get('rewrite_score', 'N/A')} | {article.get('rewrite_type', 'N/A')} |"
            )
        return '\n'.join(lines)

    else:
        return str(articles)


def main():
    parser = argparse.ArgumentParser(description="スマートサンプリング: 条件指定でコーパスを抽出")

    # 検索条件
    parser.add_argument("--category", help="カテゴリ")
    parser.add_argument("--min-score", type=float, help="リライトスコア最小値")
    parser.add_argument("--min-quality", type=float, help="品質スコア最小値")
    parser.add_argument("--min-elo", type=int, help="ELO最小値")
    parser.add_argument("--type", help="リライトタイプ（タイムカプセル型/文化史抽出型/哲学昇華型）")
    parser.add_argument("--year-from", type=int, help="開始年")
    parser.add_argument("--year-to", type=int, help="終了年")

    # 検索モード
    parser.add_argument("--search", help="全文検索キーワード")
    parser.add_argument("--random", action="store_true", help="ランダムサンプリング")
    parser.add_argument("--top-by-category", action="store_true", help="カテゴリ別トップ記事")

    # オプション
    parser.add_argument("--limit", type=int, default=50, help="取得件数上限（デフォルト: 50）")
    parser.add_argument("--order-by", default="rewrite_score", help="ソート順（デフォルト: rewrite_score）")
    parser.add_argument("--format", choices=["json", "simple", "markdown"], default="simple", help="出力形式")
    parser.add_argument("--output", help="出力ファイルパス（指定しない場合は標準出力）")

    args = parser.parse_args()

    # データベースパス
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "corpus" / "writing-corpus.db"

    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        print("   先に migrate-to-sqlite.py を実行してください")
        return

    # サンプリング実行
    if args.search:
        articles = search_full_text(db_path, args.search, args.limit)
        print(f"全文検索: '{args.search}' → {len(articles)}件")

    elif args.random:
        articles = get_random_sample(db_path, args.limit)
        print(f"ランダムサンプリング: {len(articles)}件")

    elif args.top_by_category:
        category_articles = get_top_articles_by_category(db_path, args.limit)
        # フラット化
        articles = []
        for category, arts in category_articles.items():
            articles.extend(arts)
        print(f"カテゴリ別トップ記事: {len(articles)}件")

    else:
        articles = sample_by_criteria(
            db_path,
            category=args.category,
            min_rewrite_score=args.min_score,
            min_quality_score=args.min_quality,
            min_elo=args.min_elo,
            rewrite_type=args.type,
            year_from=args.year_from,
            year_to=args.year_to,
            limit=args.limit,
            order_by=args.order_by
        )
        print(f"条件検索: {len(articles)}件")

    # 出力
    output_text = format_output(articles, args.format)

    if args.output:
        output_file = Path(args.output)
        output_file.write_text(output_text, encoding='utf-8')
        print(f"✅ 出力完了: {output_file}")
    else:
        print("\n" + output_text)


if __name__ == "__main__":
    main()
