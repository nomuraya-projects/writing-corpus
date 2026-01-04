#!/usr/bin/env python3
"""
ELO評価の同期: writing-evaluationモードからwriting-corpusへ

目的: ~/.llms/article-comparisons.json のELO評価をwriting-corpus.dbに反映
使い方: python3 sync-elo-to-corpus.py [--dry-run]
出力: writing-corpus.db の articles.elo_rating と elo_comparisons テーブルを更新
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import argparse


def load_article_comparisons(comparisons_file: Path) -> dict:
    """
    article-comparisons.json を読み込み

    Args:
        comparisons_file: JSONファイルパス

    Returns:
        比較データ辞書
    """
    if not comparisons_file.exists():
        print(f"❌ article-comparisons.json が見つかりません: {comparisons_file}")
        print("   writing-evaluationモードを一度実行してください")
        return None

    with comparisons_file.open('r', encoding='utf-8') as f:
        data = json.load(f)

    return data


def sync_elo_ratings(db_path: Path, comparisons_data: dict, dry_run: bool = False):
    """
    ELO評価をデータベースに同期

    Args:
        db_path: データベースパス
        comparisons_data: 比較データ
        dry_run: True の場合は実際の更新を行わない
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # FC2記事のELO評価を抽出
    ratings = comparisons_data.get('ratings', {})
    fc2_ratings = {aid: data for aid, data in ratings.items() if aid.startswith('fc2_')}

    print(f"\n📊 同期対象: {len(fc2_ratings)}件のFC2記事")

    # ELO評価を更新
    updated_count = 0
    for article_id, rating_data in fc2_ratings.items():
        elo = rating_data.get('elo', 1500)
        comparison_count = rating_data.get('comparisonCount', 0)

        # 記事が存在するか確認
        cursor = conn.execute("SELECT id, elo_rating FROM articles WHERE id = ?", (article_id,))
        article = cursor.fetchone()

        if article:
            old_elo = article['elo_rating']

            if not dry_run:
                conn.execute("""
                    UPDATE articles
                    SET elo_rating = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (elo, article_id))

            print(f"  {article_id}: ELO {old_elo} → {elo} (比較{comparison_count}回)")
            updated_count += 1
        else:
            print(f"  ⚠️ 記事が見つかりません: {article_id}")

    # 比較履歴を記録
    comparisons = comparisons_data.get('comparisons', [])
    fc2_comparisons = [
        c for c in comparisons
        if c.get('articleA', '').startswith('fc2_') or c.get('articleB', '').startswith('fc2_')
    ]

    print(f"\n📝 比較履歴: {len(fc2_comparisons)}件")

    inserted_count = 0
    for comparison in fc2_comparisons:
        article_a = comparison.get('articleA')
        article_b = comparison.get('articleB')
        winner = comparison.get('winner')
        context = comparison.get('context', '')
        confidence = comparison.get('confidence', 'medium')

        # 既存の比較履歴をチェック
        cursor = conn.execute("""
            SELECT id FROM elo_comparisons
            WHERE article_a = ? AND article_b = ?
        """, (article_a, article_b))

        existing = cursor.fetchone()

        if not existing and not dry_run:
            conn.execute("""
                INSERT INTO elo_comparisons (article_a, article_b, winner, context, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (article_a, article_b, winner, context, confidence))

            inserted_count += 1

    if not dry_run:
        conn.commit()
        print(f"\n✅ 同期完了:")
        print(f"  - ELO評価更新: {updated_count}件")
        print(f"  - 比較履歴追加: {inserted_count}件")
    else:
        print(f"\n🔍 Dry-run モード:")
        print(f"  - ELO評価更新予定: {updated_count}件")
        print(f"  - 比較履歴追加予定: {inserted_count}件")
        print("   実際の更新は行いません（--dry-run が指定されています）")

    conn.close()


def show_statistics(db_path: Path):
    """同期後の統計情報を表示"""

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ELO分布
    cursor = conn.execute("""
        SELECT
            COUNT(*) as total,
            AVG(elo_rating) as avg_elo,
            MIN(elo_rating) as min_elo,
            MAX(elo_rating) as max_elo,
            COUNT(CASE WHEN elo_rating >= 1550 THEN 1 END) as high_elo,
            COUNT(CASE WHEN elo_rating >= 1520 AND elo_rating < 1550 THEN 1 END) as medium_elo,
            COUNT(CASE WHEN elo_rating < 1520 THEN 1 END) as low_elo
        FROM articles
    """)

    stats = cursor.fetchone()

    print("\n📈 ELO分布:")
    print(f"  - 総記事数: {stats['total']}件")
    print(f"  - 平均ELO: {stats['avg_elo']:.1f}")
    print(f"  - 最小ELO: {stats['min_elo']}")
    print(f"  - 最大ELO: {stats['max_elo']}")
    print(f"\n  - 高ELO (1550+): {stats['high_elo']}件 → 参照記事候補")
    print(f"  - 中ELO (1520-1549): {stats['medium_elo']}件 → 活用対象")
    print(f"  - 低ELO (<1520): {stats['low_elo']}件 → 探索対象")

    # 比較履歴統計
    cursor = conn.execute("SELECT COUNT(*) as count FROM elo_comparisons")
    comparison_count = cursor.fetchone()['count']

    print(f"\n📊 比較履歴: {comparison_count}件")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="ELO評価の同期")

    parser.add_argument("--dry-run", action="store_true", help="実際の更新を行わず、変更内容のみ表示")
    parser.add_argument("--comparisons-file", help="article-comparisons.json のパス（デフォルト: ~/.llms/article-comparisons.json）")

    args = parser.parse_args()

    # パス設定
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "corpus" / "writing-corpus.db"

    if args.comparisons_file:
        comparisons_file = Path(args.comparisons_file)
    else:
        comparisons_file = Path.home() / ".llms" / "article-comparisons.json"

    # データベース存在確認
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        print("   先に migrate-to-sqlite.py を実行してください")
        return

    # 比較データ読み込み
    comparisons_data = load_article_comparisons(comparisons_file)

    if not comparisons_data:
        return

    # ELO同期
    print("ELO評価の同期を開始します...")
    sync_elo_ratings(db_path, comparisons_data, dry_run=args.dry_run)

    # 統計表示
    if not args.dry_run:
        show_statistics(db_path)


if __name__ == "__main__":
    main()
