#!/usr/bin/env python3
"""
metadata.jsonからSQLiteデータベースへ移行する

目的: ファイルベースの管理から高速検索可能なDB化
使い方: python3 migrate-to-sqlite.py
出力: data/corpus/writing-corpus.db
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime


def create_schema(conn: sqlite3.Connection):
    """データベーススキーマを作成"""

    # articlesテーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            date DATE NOT NULL,
            year INTEGER NOT NULL,
            category TEXT,
            word_count INTEGER,
            file_path TEXT NOT NULL,
            content TEXT,

            -- AI学習用メタデータ
            quality_score REAL,
            elo_rating INTEGER DEFAULT 1500,
            sampled BOOLEAN DEFAULT 0,
            reference_article BOOLEAN DEFAULT 0,

            -- note.comリライト用メタデータ
            rewrite_status TEXT DEFAULT 'pending',
            rewrite_score REAL,
            rewrite_type TEXT,
            note_article_path TEXT,
            rewrite_date DATE,
            deletion_reason TEXT,
            archived_reason TEXT,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # tagsテーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # article_tagsテーブル（多対多）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS article_tags (
            article_id TEXT,
            tag_id INTEGER,
            FOREIGN KEY (article_id) REFERENCES articles(id),
            FOREIGN KEY (tag_id) REFERENCES tags(id),
            PRIMARY KEY (article_id, tag_id)
        )
    """)

    # writing_patternsテーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS writing_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type TEXT NOT NULL,
            pattern_name TEXT NOT NULL,
            pattern TEXT,
            examples TEXT
        )
    """)

    # elo_comparisonsテーブル
    conn.execute("""
        CREATE TABLE IF NOT EXISTS elo_comparisons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_a TEXT NOT NULL,
            article_b TEXT NOT NULL,
            winner TEXT,
            context TEXT,
            confidence TEXT,
            compared_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (article_a) REFERENCES articles(id),
            FOREIGN KEY (article_b) REFERENCES articles(id)
        )
    """)

    # 全文検索用FTS5テーブル
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
            title,
            category,
            content,
            content='articles',
            content_rowid='rowid'
        )
    """)

    # インデックス作成
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_year ON articles(year)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_rewrite_status ON articles(rewrite_status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_articles_rewrite_score ON articles(rewrite_score)")

    conn.commit()
    print("✅ スキーマ作成完了")


def load_article_content(file_path: Path) -> str:
    """記事ファイルから本文を読み込む"""
    try:
        content = file_path.read_text(encoding='utf-8')
        # frontmatterを除去
        import re
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        return content.strip()
    except Exception as e:
        print(f"⚠️ 読み込みエラー: {file_path} - {e}")
        return ""


def migrate_articles(conn: sqlite3.Connection, metadata: dict, base_dir: Path):
    """articlesテーブルにデータを移行"""

    articles = metadata['articles']
    print(f"\n記事データ移行開始: {len(articles)}件")

    for i, article in enumerate(articles, 1):
        # ファイルパスから本文を読み込む
        file_path = base_dir / article['corpus_metadata']['source_path']
        content = load_article_content(file_path) if file_path.exists() else ""

        # corpus_metadata
        corpus_meta = article['corpus_metadata']

        # rewrite_status
        rewrite_status = article['rewrite_status']

        conn.execute("""
            INSERT OR REPLACE INTO articles (
                id, title, date, year, category, word_count, file_path, content,
                quality_score, elo_rating, sampled, reference_article,
                rewrite_status, rewrite_score, rewrite_type, note_article_path,
                rewrite_date, deletion_reason, archived_reason
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            article['id'],
            article['title'],
            article['date'],
            article['year'],
            article.get('category'),
            article['word_count'],
            corpus_meta['source_path'],
            content,
            corpus_meta.get('quality_score'),
            corpus_meta.get('elo_rating', 1500),
            1 if corpus_meta.get('sampled') else 0,
            1 if corpus_meta.get('reference_article') else 0,
            rewrite_status['status'],
            rewrite_status.get('rewrite_score'),
            rewrite_status.get('rewrite_type'),
            rewrite_status.get('note_article_path'),
            rewrite_status.get('rewrite_date'),
            rewrite_status.get('deletion_reason'),
            rewrite_status.get('archived_reason')
        ))

        # 全文検索テーブルにも挿入
        conn.execute("""
            INSERT INTO articles_fts(rowid, title, category, content)
            SELECT rowid, title, category, content FROM articles WHERE id = ?
        """, (article['id'],))

        if i % 100 == 0:
            print(f"  処理中... {i}/{len(articles)}")
            conn.commit()

    conn.commit()
    print(f"✅ 記事データ移行完了: {len(articles)}件")


def create_statistics_view(conn: sqlite3.Connection):
    """統計情報用のビューを作成"""

    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_statistics AS
        SELECT
            COUNT(*) as total,
            COUNT(CASE WHEN rewrite_status = 'pending' THEN 1 END) as pending,
            COUNT(CASE WHEN rewrite_status = 'in_progress' THEN 1 END) as in_progress,
            COUNT(CASE WHEN rewrite_status = 'completed' THEN 1 END) as completed,
            COUNT(CASE WHEN rewrite_status = 'deleted' THEN 1 END) as deleted,
            COUNT(CASE WHEN rewrite_status = 'archived' THEN 1 END) as archived,
            COUNT(CASE WHEN rewrite_score >= 70 THEN 1 END) as rewrite_candidates,
            COUNT(CASE WHEN rewrite_score >= 50 AND rewrite_score < 70 THEN 1 END) as review_candidates,
            COUNT(CASE WHEN rewrite_score >= 30 AND rewrite_score < 50 THEN 1 END) as archive_candidates,
            COUNT(CASE WHEN rewrite_score < 30 THEN 1 END) as deletion_candidates,
            AVG(elo_rating) as avg_elo,
            COUNT(CASE WHEN sampled = 1 THEN 1 END) as sampled_count,
            COUNT(CASE WHEN reference_article = 1 THEN 1 END) as reference_count
        FROM articles
    """)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_category_stats AS
        SELECT
            COALESCE(category, '未分類') as category,
            COUNT(*) as count,
            AVG(rewrite_score) as avg_rewrite_score,
            AVG(word_count) as avg_word_count
        FROM articles
        GROUP BY category
        ORDER BY count DESC
    """)

    conn.execute("""
        CREATE VIEW IF NOT EXISTS v_year_stats AS
        SELECT
            year,
            COUNT(*) as count,
            AVG(rewrite_score) as avg_rewrite_score
        FROM articles
        GROUP BY year
        ORDER BY year
    """)

    conn.commit()
    print("✅ 統計ビュー作成完了")


def main():
    """メイン処理"""
    project_root = Path(__file__).parent.parent.parent
    metadata_file = project_root / "data" / "corpus" / "metadata.json"
    db_file = project_root / "data" / "corpus" / "writing-corpus.db"

    # 既存DBを削除（クリーンな状態から開始）
    if db_file.exists():
        db_file.unlink()
        print(f"既存DBを削除: {db_file}")

    # metadata.json読み込み
    print(f"\nmetadata.json読み込み: {metadata_file}")
    with metadata_file.open('r', encoding='utf-8') as f:
        metadata = json.load(f)

    # データベース作成
    print(f"\nSQLiteデータベース作成: {db_file}")
    conn = sqlite3.connect(db_file)

    try:
        # スキーマ作成
        create_schema(conn)

        # データ移行
        migrate_articles(conn, metadata, project_root)

        # 統計ビュー作成
        create_statistics_view(conn)

        # 統計情報表示
        print("\n📊 移行後の統計情報:")
        cursor = conn.execute("SELECT * FROM v_statistics")
        stats = cursor.fetchone()

        if stats:
            print(f"  総記事数: {stats[0]}件")
            print(f"  未処理: {stats[1]}件")
            print(f"  作業中: {stats[2]}件")
            print(f"  完了: {stats[3]}件")
            print(f"  削除: {stats[4]}件")
            print(f"  アーカイブ: {stats[5]}件")
            print(f"\n  リライト確定: {stats[6]}件")
            print(f"  保留: {stats[7]}件")
            print(f"  アーカイブ候補: {stats[8]}件")
            print(f"  削除候補: {stats[9]}件")
            print(f"\n  平均ELO: {stats[10]:.1f}")
            print(f"  サンプリング済み: {stats[11]}件")
            print(f"  参照記事: {stats[12]}件")

        print(f"\n✅ 移行完了: {db_file}")
        print(f"データベースサイズ: {db_file.stat().st_size / 1024 / 1024:.2f} MB")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
