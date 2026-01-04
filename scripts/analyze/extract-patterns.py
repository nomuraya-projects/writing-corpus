#!/usr/bin/env python3
"""
書き味パターン抽出: FC2記事から論理展開・感情表現・構造特徴を抽出

目的: AI学習用の特徴パターンを自動抽出し、writing_patternsテーブルに格納
使い方: python3 extract-patterns.py [--min-elo SCORE] [--limit N]
出力: writing-corpus.db の writing_patterns テーブル
"""

import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
import argparse


# パターン定義
LOGICAL_PATTERNS = {
    "反語型": [
        r"〜じゃないか[？?]",
        r"〜というのはおかしいんじゃないか[？?]",
        r"〜と思わないか[？?]",
        r"〜なんじゃないか[？?]",
        r"〜ではないだろうか[？?]"
    ],
    "極論前置き型": [
        r"はっきり言って",
        r"正直な話",
        r"端的に言えば",
        r"要するに",
        r"結論から言うと"
    ],
    "段階的展開": [
        r"まず[、,]",
        r"次に[、,]",
        r"最後に[、,]",
        r"第一に",
        r"第二に",
        r"そして[、,]"
    ],
    "対比型": [
        r"一方で[、,]",
        r"他方で[、,]",
        r"それに対して",
        r"逆に[、,]",
        r"反対に[、,]"
    ],
    "前提提示型": [
        r"前提として[、,]",
        r"そもそも[、,]",
        r"まず前提として",
        r"ここで重要なのは"
    ]
}

EMOTIONAL_PATTERNS = {
    "肯定表現": [
        r"〜でいいじゃない[!！]",
        r"素晴らしい",
        r"最高だ[!！]",
        r"これはいい[!！]",
        r"良いもの",
        r"気に入った"
    ],
    "否定表現": [
        r"〜はクソ",
        r"まぁ、〜だが",
        r"残念ながら",
        r"いまいち",
        r"微妙",
        r"ダメ"
    ],
    "驚き表現": [
        r"マジか[!！]",
        r"ちょ、",
        r"おいおい[、,]",
        r"びっくり",
        r"驚いた",
        r"まさか"
    ],
    "共感要請": [
        r"〜だよね[？?]",
        r"〜じゃん[!！]",
        r"〜でしょ[？?]",
        r"〜ですよね[？?]"
    ],
    "断定型": [
        r"〜である[。.]",
        r"〜だ[。.]",
        r"〜に違いない",
        r"間違いなく",
        r"確実に"
    ]
}

STRUCTURAL_PATTERNS = {
    "導入部": [
        r"^です、おはこんにちばんわ[!！]",
        r"^さて[、,]",
        r"^というわけで[、,]",
        r"^今回は",
        r"^本日は"
    ],
    "結論部": [
        r"まとめると",
        r"結論としては",
        r"つまり[、,]",
        r"ということで[、,]",
        r"以上[、,]"
    ],
    "補足部": [
        r"ちなみに[、,]",
        r"余談ですが[、,]",
        r"蛇足ながら",
        r"ついでに言うと",
        r"補足すると"
    ],
    "引用・参照": [
        r"〜によれば[、,]",
        r"〜の言葉を借りれば",
        r"参考：",
        r"引用：",
        r"出典："
    ],
    "列挙型": [
        r"[①②③④⑤⑥⑦⑧⑨⑩]",
        r"[1-9]\.",
        r"・",
        r"- ",
        r"\* "
    ]
}


def extract_patterns_from_article(content: str, pattern_dict: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    1つの記事から特定パターンを抽出

    Args:
        content: 記事本文
        pattern_dict: パターン定義辞書

    Returns:
        パターン別の出現例リスト
    """
    results = {}

    for pattern_name, pattern_regexes in pattern_dict.items():
        examples = []

        for regex in pattern_regexes:
            matches = re.finditer(regex, content, re.MULTILINE)
            for match in matches:
                # マッチした部分の前後20文字を含めて抽出
                start = max(0, match.start() - 20)
                end = min(len(content), match.end() + 20)
                context = content[start:end].strip()
                examples.append(context)

        if examples:
            results[pattern_name] = examples[:5]  # 各パターン最大5例

    return results


def analyze_corpus(db_path: Path, min_elo: int = 1500, limit: int = 100) -> Dict[str, Dict[str, Counter]]:
    """
    コーパス全体からパターンを抽出・集計

    Args:
        db_path: データベースパス
        min_elo: 最小ELOレーティング
        limit: 分析対象記事数上限

    Returns:
        パターン種別ごとの集計結果
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    query = """
        SELECT id, title, content
        FROM articles
        WHERE elo_rating >= ? AND content IS NOT NULL AND content != ''
        ORDER BY elo_rating DESC
        LIMIT ?
    """

    cursor = conn.execute(query, (min_elo, limit))
    articles = cursor.fetchall()

    print(f"分析対象: {len(articles)}件の記事（ELO >= {min_elo}）")

    # パターン別の集計
    logical_counter = Counter()
    emotional_counter = Counter()
    structural_counter = Counter()

    # 例文の収集
    logical_examples = {}
    emotional_examples = {}
    structural_examples = {}

    for i, article in enumerate(articles, 1):
        content = article['content']

        # 論理展開パターン
        logical_matches = extract_patterns_from_article(content, LOGICAL_PATTERNS)
        for pattern_name, examples in logical_matches.items():
            logical_counter[pattern_name] += len(examples)
            if pattern_name not in logical_examples:
                logical_examples[pattern_name] = []
            logical_examples[pattern_name].extend(examples)

        # 感情表現パターン
        emotional_matches = extract_patterns_from_article(content, EMOTIONAL_PATTERNS)
        for pattern_name, examples in emotional_matches.items():
            emotional_counter[pattern_name] += len(examples)
            if pattern_name not in emotional_examples:
                emotional_examples[pattern_name] = []
            emotional_examples[pattern_name].extend(examples)

        # 構造特徴パターン
        structural_matches = extract_patterns_from_article(content, STRUCTURAL_PATTERNS)
        for pattern_name, examples in structural_matches.items():
            structural_counter[pattern_name] += len(examples)
            if pattern_name not in structural_examples:
                structural_examples[pattern_name] = []
            structural_examples[pattern_name].extend(examples)

        if i % 20 == 0:
            print(f"  処理中... {i}/{len(articles)}")

    conn.close()

    return {
        "論理展開": {"counter": logical_counter, "examples": logical_examples},
        "感情表現": {"counter": emotional_counter, "examples": emotional_examples},
        "構造特徴": {"counter": structural_counter, "examples": structural_examples}
    }


def save_patterns_to_db(db_path: Path, analysis_results: Dict[str, Dict[str, Counter]]):
    """
    抽出したパターンをデータベースに保存

    Args:
        db_path: データベースパス
        analysis_results: 分析結果
    """
    conn = sqlite3.connect(db_path)

    # 既存データをクリア
    conn.execute("DELETE FROM writing_patterns")

    for pattern_type, data in analysis_results.items():
        counter = data['counter']
        examples = data['examples']

        for pattern_name, count in counter.items():
            # 例文をJSON形式で保存（最大10例）
            example_list = list(set(examples.get(pattern_name, [])))[:10]
            examples_json = '\n---\n'.join(example_list)

            # パターンの正規表現を取得
            if pattern_type == "論理展開":
                pattern_regex = '|'.join(LOGICAL_PATTERNS.get(pattern_name, []))
            elif pattern_type == "感情表現":
                pattern_regex = '|'.join(EMOTIONAL_PATTERNS.get(pattern_name, []))
            else:
                pattern_regex = '|'.join(STRUCTURAL_PATTERNS.get(pattern_name, []))

            conn.execute("""
                INSERT INTO writing_patterns (pattern_type, pattern_name, pattern, examples)
                VALUES (?, ?, ?, ?)
            """, (pattern_type, pattern_name, pattern_regex, examples_json))

            print(f"  保存: {pattern_type} > {pattern_name} ({count}回出現)")

    conn.commit()
    conn.close()

    print(f"\n✅ パターンをデータベースに保存しました")


def print_summary(analysis_results: Dict[str, Dict[str, Counter]]):
    """分析結果のサマリーを表示"""

    print("\n📊 抽出パターンサマリー\n")

    for pattern_type, data in analysis_results.items():
        counter = data['counter']

        print(f"## {pattern_type}")

        if counter:
            for pattern_name, count in counter.most_common(10):
                print(f"  - {pattern_name}: {count}回")
        else:
            print("  （該当パターンなし）")

        print()


def main():
    parser = argparse.ArgumentParser(description="書き味パターン抽出")

    parser.add_argument("--min-elo", type=int, default=1500, help="最小ELOレーティング（デフォルト: 1500）")
    parser.add_argument("--limit", type=int, default=100, help="分析対象記事数上限（デフォルト: 100）")
    parser.add_argument("--summary-only", action="store_true", help="サマリーのみ表示（DBに保存しない）")

    args = parser.parse_args()

    # データベースパス
    project_root = Path(__file__).parent.parent.parent
    db_path = project_root / "data" / "corpus" / "writing-corpus.db"

    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        print("   先に migrate-to-sqlite.py を実行してください")
        return

    print("書き味パターン抽出を開始します...\n")

    # コーパス分析
    analysis_results = analyze_corpus(db_path, min_elo=args.min_elo, limit=args.limit)

    # サマリー表示
    print_summary(analysis_results)

    # データベースに保存
    if not args.summary_only:
        save_patterns_to_db(db_path, analysis_results)
    else:
        print("（--summary-only が指定されたため、データベースには保存しません）")


if __name__ == "__main__":
    main()
