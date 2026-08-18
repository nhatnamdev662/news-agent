"""Cau hinh + xac thuc cho AI Agent News Bot."""
import os
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()

# ---- Token ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# ---- AI provider (custom / OpenAI-compatible) ----
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "").strip()
CUSTOM_API_URL = os.getenv("CUSTOM_API_URL", "https://api.darkapi.dev/v1").strip()
CUSTOM_MODEL = os.getenv("CUSTOM_MODEL", "laguna-s-2.1-free").strip()
MAX_ARTICLES = int(os.getenv("MAX_ARTICLES", "6") or "6")

# ---- Schedule ----
SCAN_MINUTES = int(os.getenv("SCAN_MINUTES", "5") or "5")

# ---- DB ----
DB_PATH = os.getenv("DB_PATH", "data/news.db").strip()
REPO_DIR = os.path.dirname(os.path.abspath(__file__))

# ---- Nguon tin ----
CATEGORY_FEEDS = {
    "tat-ca": [
        "https://vnexpress.net/rss/tin-moi-nhat.rss",
        "https://dantri.com.vn/rss/tin-moi-nhat.rss",
        "https://znews.vn/rss/home.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi",
    ],
    "thoi-su": [
        "https://vnexpress.net/rss/thoi-su.rss",
        "https://dantri.com.vn/rss/xa-cong-dong.rss",
        "https://znews.vn/rss/xa-hoi.rss",
    ],
    "kinh-te": [
        "https://vnexpress.net/rss/kinh-doanh.rss",
        "https://dantri.com.vn/rss/kinh-doanh.rss",
        "https://znews.vn/rss/kinh-te.rss",
    ],
    "cong-nghe": [
        "https://vnexpress.net/rss/cong-nghe.rss",
        "https://dantri.com.vn/rss/cong-nghe-thong-tin.rss",
        "https://znews.vn/rss/cong-nghe.rss",
    ],
    "the-thao": [
        "https://vnexpress.net/rss/the-thao.rss",
        "https://dantri.com.vn/rss/the-thao.rss",
        "https://znews.vn/rss/the-thao.rss",
    ],
    "giai-tri": [
        "https://vnexpress.net/rss/giai-tri.rss",
        "https://dantri.com.vn/rss/giai-tri.rss",
        "https://znews.vn/rss/giai-tri.rss",
    ],
    "giao-duc": [
        "https://vnexpress.net/rss/giao-duc.rss",
        "https://dantri.com.vn/rss/giao-duc.rss",
        "https://znews.vn/rss/giao-duc.rss",
    ],
    "phap-luat": [
        "https://vnexpress.net/rss/phap-luat.rss",
        "https://dantri.com.vn/rss/phap-luat.rss",
        "https://znews.vn/rss/phap-luat.rss",
    ],
    "the-gioi": [
        "https://vnexpress.net/rss/the-gioi.rss",
        "https://dantri.com.vn/rss/the-gioi.rss",
        "https://znews.vn/rss/the-gioi.rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}

CATEGORY_LABELS = {
    "tat-ca": "📰 Tất cả",
    "thoi-su": "🗞️ Thời sự",
    "kinh-te": "💼 Kinh tế",
    "cong-nghe": "💻 Công nghệ",
    "the-thao": "⚽ Thể thao",
    "giai-tri": "🎬 Giải trí",
    "giao-duc": "📚 Giáo dục",
    "phap-luat": "⚖️ Pháp luật",
    "the-gioi": "🌍 Thế giới",
}
CATEGORY_KEYS = list(CATEGORY_LABELS.keys())


def all_feeds() -> List[str]:
    out = []
    for v in CATEGORY_FEEDS.values():
        out.extend(v)
    return out


def validate_config() -> Tuple[bool, List[str]]:
    errs = []
    if not BOT_TOKEN:
        errs.append("BOT_TOKEN (token bot Telegram)")
    if not CUSTOM_API_KEY:
        errs.append("CUSTOM_API_KEY (key API provider)")
    if not CUSTOM_API_URL:
        errs.append("CUSTOM_API_URL (base URL)")
    if not CUSTOM_MODEL:
        errs.append("CUSTOM_MODEL (chưa chọn model)")
    return (len(errs) == 0, errs)
