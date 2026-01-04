#!/usr/bin/env python3
"""
FC2記事をリライト判断基準に基づいてスコアリングする

目的: metadata.jsonの全記事にrewrite_scoreを付与
使い方: python3 score-articles.py
出力: metadata.jsonを更新、候補リストJSONを生成
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List


# カテゴリ別基準スコア（経験則ベース）
CATEGORY_BASE_SCORES = {
    "徒然": {"時代性": 12, "普遍性": 8, "エンタメ性": 10, "リライト工数": 10, "リスク": 8},
    "レビュー": {"時代性": 18, "普遍性": 12, "エンタメ性": 14, "リライト工数": 8, "リスク": 6},
    "報告": {"時代性": 8, "普遍性": 6, "エンタメ性": 8, "リライト工数": 12, "リスク": 8},
    "東方二次創作": {"時代性": 22, "普遍性": 18, "エンタメ性": 16, "リライト工数": 12, "リスク": 9},
    "考察": {"時代性": 20, "普遍性": 15, "エンタメ性": 12, "リライト工数": 10, "リスク": 9},
    "告知": {"時代性": 2, "普遍性": 3, "エンタメ性": 4, "リライト工数": 6, "リスク": 8},
    "速報": {"時代性": 4, "普遍性": 4, "エンタメ性": 6, "リライト工数": 8, "リスク": 7},
    "生存報告": {"時代性": 5, "普遍性": 4, "エンタメ性": 6, "リライト工数": 10, "リスク": 8},
    "TRPG": {"時代性": 18, "普遍性": 14, "エンタメ性": 12, "リライト工数": 10, "リスク": 9},
    "ＴＲＰＧ": {"時代性": 18, "普遍性": 14, "エンタメ性": 12, "リライト工数": 10, "リスク": 9},
    "東方二次創作ゲームレビュー": {"時代性": 22, "普遍性": 18, "エンタメ性": 16, "リライト工数": 12, "リスク": 9},
    "募集": {"時代性": 2, "普遍性": 3, "エンタメ性": 4, "リライト工数": 5, "リスク": 8},
    "通知": {"時代性": 2, "普遍性": 3, "エンタメ性": 4, "リライト工数": 6, "リスク": 8},
    "連絡": {"時代性": 2, "普遍性": 3, "エンタメ性": 4, "リライト工数": 6, "リスク": 8},
    None: {"時代性": 10, "普遍性": 8, "エンタメ性": 8, "リライト工数": 8, "リスク": 7}
}


def calculate_base_score(article: Dict) -> Dict[str, int]:
    """
    カテゴリベースの基準スコアを取得

    Args:
        article: 記事メタデータ

    Returns:
        各軸のスコア辞書
    """
    category = article.get("category")
    return CATEGORY_BASE_SCORES.get(category, CATEGORY_BASE_SCORES[None]).copy()


def adjust_score_by_word_count(scores: Dict[str, int], word_count: int) -> Dict[str, int]:
    """
    文字数によるスコア調整

    Args:
        scores: 基準スコア
        word_count: 文字数

    Returns:
        調整後スコア
    """
    if word_count < 300:
        # 短すぎる記事はエンタメ性とリライト工数を減点
        scores["エンタメ性"] = max(0, scores["エンタメ性"] - 4)
        scores["リライト工数"] = max(0, scores["リライト工数"] - 3)
    elif word_count > 2000:
        # 長い記事はエンタメ性とリライト工数を加点
        scores["エンタメ性"] = min(20, scores["エンタメ性"] + 2)
        scores["リライト工数"] = max(0, scores["リライト工数"] - 2)  # 工数増

    return scores


def adjust_score_by_year(scores: Dict[str, int], year: int) -> Dict[str, int]:
    """
    年代によるスコア調整

    Args:
        scores: 基準スコア
        year: 記事の年

    Returns:
        調整後スコア
    """
    if year == 2023:
        # 2023年の記事は異常値として扱う
        scores["時代性"] = 0
        scores["普遍性"] = 0
        scores["エンタメ性"] = 0
    elif year <= 2009:
        # 古い記事はタイムカプセル価値が高い
        scores["時代性"] = min(30, scores["時代性"] + 3)

    return scores


def detect_risk_patterns(article: Dict, content: str = None) -> int:
    """
    リスクパターンを検出（簡易版）

    Args:
        article: 記事メタデータ
        content: 記事本文（オプション）

    Returns:
        リスクスコア（0-10点、高いほど安全）
    """
    title = article.get("title", "")

    # タイトルベースの簡易判定
    risk_keywords = ["政治", "速報", "通知", "募集", "告知"]

    for keyword in risk_keywords:
        if keyword in title:
            return 6  # 若干リスク減点

    # 2023年のHello world!は明確な削除対象
    if article.get("year") == 2023 and "Hello world" in title:
        return 10  # リスクはないが価値もない

    return 8  # デフォルト


def calculate_total_score(scores: Dict[str, int]) -> int:
    """
    各軸のスコアから総合スコアを算出

    Args:
        scores: 各軸のスコア辞書

    Returns:
        総合スコア（0-100点）
    """
    return sum(scores.values())


def determine_rewrite_type(article: Dict, total_score: int) -> str:
    """
    リライトタイプを判定

    Args:
        article: 記事メタデータ
        total_score: 総合スコア

    Returns:
        リライトタイプ
    """
    if total_score < 70:
        return None

    category = article.get("category")
    year = article.get("year", 2010)

    # カテゴリベースの判定
    if category in ["考察", "TRPG", "ＴＲＰＧ"]:
        return "哲学昇華型"
    elif category in ["東方二次創作", "東方二次創作ゲームレビュー", "レビュー"]:
        return "文化史抽出型"
    elif category in ["徒然", "報告"]:
        return "タイムカプセル型"
    else:
        # 年代で判定
        if year <= 2010:
            return "タイムカプセル型"
        else:
            return "文化史抽出型"


def score_article(article: Dict) -> Dict:
    """
    1つの記事をスコアリング

    Args:
        article: 記事メタデータ

    Returns:
        スコア情報を含む辞書
    """
    # 基準スコア取得
    scores = calculate_base_score(article)

    # 調整
    scores = adjust_score_by_word_count(scores, article.get("word_count", 0))
    scores = adjust_score_by_year(scores, article.get("year", 2010))

    # リスク判定
    scores["リスク"] = detect_risk_patterns(article)

    # 総合スコア
    total_score = calculate_total_score(scores)

    # リライトタイプ判定
    rewrite_type = determine_rewrite_type(article, total_score)

    return {
        "total_score": total_score,
        "detail_scores": scores,
        "rewrite_type": rewrite_type
    }


def classify_articles(articles: List[Dict]) -> Dict[str, List[str]]:
    """
    記事をスコア別に分類

    Args:
        articles: 全記事リスト

    Returns:
        分類結果辞書
    """
    rewrite_candidates = []
    review_candidates = []
    archive_candidates = []
    deletion_candidates = []

    for article in articles:
        score = article["rewrite_status"].get("rewrite_score")
        if score is None:
            continue

        article_id = article["id"]

        if score >= 70:
            rewrite_candidates.append(article_id)
        elif score >= 50:
            review_candidates.append(article_id)
        elif score >= 30:
            archive_candidates.append(article_id)
        else:
            deletion_candidates.append(article_id)

    return {
        "rewrite": rewrite_candidates,
        "review": review_candidates,
        "archive": archive_candidates,
        "deletion": deletion_candidates
    }


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent.parent
    metadata_file = project_root / "data" / "corpus" / "metadata.json"
    processed_dir = project_root / "data" / "processed"

    # 出力ディレクトリ作成
    processed_dir.mkdir(parents=True, exist_ok=True)

    # metadata.json読み込み
    with metadata_file.open('r', encoding='utf-8') as f:
        metadata = json.load(f)

    articles = metadata["articles"]

    print(f"スコアリング開始: {len(articles)}件")

    # 全記事をスコアリング
    for i, article in enumerate(articles, 1):
        score_info = score_article(article)

        # metadata更新
        article["rewrite_status"]["rewrite_score"] = score_info["total_score"]
        article["rewrite_status"]["rewrite_type"] = score_info["rewrite_type"]
        article["rewrite_status"]["detail_scores"] = score_info["detail_scores"]

        if i % 100 == 0:
            print(f"処理中... {i}/{len(articles)}")

    print(f"\nスコアリング完了: {len(articles)}件")

    # 分類
    classification = classify_articles(articles)

    print(f"\n📊 分類結果:")
    print(f"  ✅ リライト確定: {len(classification['rewrite'])}件")
    print(f"  ⏸️  保留: {len(classification['review'])}件")
    print(f"  📦 アーカイブ: {len(classification['archive'])}件")
    print(f"  🗑️  削除候補: {len(classification['deletion'])}件")

    # metadata.json保存
    metadata["generated_at"] = datetime.now().isoformat()
    with metadata_file.open('w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print(f"\n✅ metadata.json を更新しました")

    # 候補リスト保存
    candidates_files = {
        "rewrite-candidates.json": classification["rewrite"],
        "review-candidates.json": classification["review"],
        "archive-candidates.json": classification["archive"],
        "deletion-candidates.json": classification["deletion"]
    }

    for filename, article_ids in candidates_files.items():
        output_file = processed_dir / filename
        with output_file.open('w', encoding='utf-8') as f:
            json.dump(article_ids, f, ensure_ascii=False, indent=2)
        print(f"  - {filename}: {len(article_ids)}件")


if __name__ == "__main__":
    main()
