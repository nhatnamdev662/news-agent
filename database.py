"""SQLite: người dùng, sở thích, lịch gửi tin, bookmark, stats, chống trùng bài."""
import os
import sqlite3
import threading
from datetime import datetime, date
from config import DB_PATH


class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        with self._lock:
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY,
                    username TEXT DEFAULT '',
                    first_name TEXT DEFAULT '',
                    categories TEXT DEFAULT 'tat-ca',
                    schedule_time TEXT DEFAULT 'off',
                    last_digest TEXT DEFAULT '',
                    created_at TEXT DEFAULT ''
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS articles (
                    link TEXT PRIMARY KEY,
                    title TEXT DEFAULT '',
                    source TEXT DEFAULT '',
                    category TEXT DEFAULT '',
                    image TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    published TEXT DEFAULT '',
                    first_seen TEXT DEFAULT ''
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER NOT NULL,
                    link TEXT NOT NULL,
                    title TEXT DEFAULT '',
                    url TEXT DEFAULT '',
                    saved_at TEXT DEFAULT ''
                )
            """)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS user_stats (
                    chat_id INTEGER PRIMARY KEY,
                    category_clicks INTEGER DEFAULT 0,
                    searches INTEGER DEFAULT 0,
                    summaries INTEGER DEFAULT 0,
                    favorite_cat TEXT DEFAULT '',
                    last_category TEXT DEFAULT ''
                )
            """)
            self._conn.commit()

    # ---------- Users ----------
    def get_user(self, chat_id: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE chat_id = ?", (chat_id,)
            ).fetchone()
            return dict(row) if row else None

    def upsert_user(self, chat_id: int, username: str = "", first_name: str = ""):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute("""
                INSERT INTO users (chat_id, username, first_name, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(chat_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name
            """, (chat_id, username, first_name, now))
            self._conn.commit()

    def set_categories(self, chat_id: int, categories: str):
        with self._lock:
            self._conn.execute(
                "UPDATE users SET categories = ? WHERE chat_id = ?", (categories, chat_id)
            )
            self._conn.commit()

    def set_schedule(self, chat_id: int, schedule_time: str):
        with self._lock:
            self._conn.execute(
                "UPDATE users SET schedule_time = ? WHERE chat_id = ?", (schedule_time, chat_id)
            )
            self._conn.commit()

    def mark_digest_sent(self, chat_id: int, day: str = None):
        day = day or date.today().isoformat()
        with self._lock:
            self._conn.execute(
                "UPDATE users SET last_digest = ? WHERE chat_id = ?", (day, chat_id)
            )
            self._conn.commit()

    def get_scheduled_users(self, hour: int, minute: int) -> list:
        target = "{:02d}:{:02d}".format(hour, minute)
        today = date.today().isoformat()
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM users WHERE schedule_time = ? AND last_digest != ?",
                (target, today)
            ).fetchall()
            return [dict(r) for r in rows]

    # ---------- Bookmarks ----------
    def save_bookmark(self, chat_id: int, link: str, title: str, url: str):
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO saved_articles (chat_id, link, title, url, saved_at) VALUES (?, ?, ?, ?, ?)",
                (chat_id, link, title, url, now)
            )
            self._conn.commit()

    def list_bookmarks(self, chat_id: int) -> list:
        with self._lock:
            rows = self._conn.execute(
                "SELECT link, title, url, saved_at FROM saved_articles WHERE chat_id = ? ORDER BY saved_at DESC",
                (chat_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    def remove_bookmark(self, chat_id: int, link: str):
        with self._lock:
            self._conn.execute(
                "DELETE FROM saved_articles WHERE chat_id = ? AND link = ?", (chat_id, link)
            )
            self._conn.commit()

    def clear_bookmarks(self, chat_id: int):
        with self._lock:
            self._conn.execute("DELETE FROM saved_articles WHERE chat_id = ?", (chat_id,))
            self._conn.commit()

    # ---------- Stats ----------
    def inc_stat(self, chat_id: int, action: str):
        with self._lock:
            self._conn.execute(
                "INSERT OR IGNORE INTO user_stats (chat_id, category_clicks, searches, summaries) VALUES (?, 0, 0, 0)",
                (chat_id,)
            )
            self._conn.execute(
                "UPDATE user_stats SET "
                "category_clicks = category_clicks + ?, "
                "searches = searches + ?, "
                "summaries = summaries + ?",
                (1 if action == "cat" else 0, 1 if action == "search" else 0, 1 if action == "summary" else 0)
            )
            self._conn.commit()

    def record_category(self, chat_id: int, category: str):
        with self._lock:
            self._conn.execute(
                "INSERT INTO user_stats (chat_id, category_clicks, favorite_cat) VALUES (?, 0, ?) "
                "ON CONFLICT(chat_id) DO UPDATE SET category_clicks = category_clicks + 1, favorite_cat = ?",
                (chat_id, category, category)
            )
            self._conn.commit()

    def get_stats(self, chat_id: int) -> dict:
        with self._lock:
            row = self._conn.execute(
                "SELECT category_clicks, searches, summaries, favorite_cat FROM user_stats WHERE chat_id = ?",
                (chat_id,)
            ).fetchone()
            return dict(row) if row else {}

    # ---------- Articles ----------
    def is_seen(self, link: str) -> bool:
        with self._lock:
            row = self._conn.execute(
                "SELECT 1 FROM articles WHERE link = ?", (link,)
            ).fetchone()
            return row is not None

    def save_articles(self, articles: list):
        if not articles:
            return
        now = datetime.now().isoformat()
        with self._lock:
            self._conn.executemany("""
                INSERT OR IGNORE INTO articles
                (link, title, source, category, image, summary, published, first_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (a.get("link", ""), a.get("title", ""), a.get("source", ""),
                 a.get("category", ""), a.get("image", ""), a.get("summary", ""),
                 a.get("published", ""), now)
                for a in articles
            ])
            self._conn.commit()

    def prune_articles(self, keep_days: int = 7):
        with self._lock:
            self._conn.execute(
                "DELETE FROM articles WHERE first_seen < datetime('now', ?)",
                ("-{} days".format(keep_days),)
            )
            self._conn.commit()
