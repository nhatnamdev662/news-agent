"""Cau hinh + xac thuc cho AI Agent News Bot."""
import os
from typing import List, Tuple
from dotenv import load_dotenv

load_dotenv()

# ---- Token ----
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()

# ---- AI provider ----
AI_PROVIDER = os.getenv("AI_PROVIDER", "opencode").strip()
CUSTOM_API_KEY = os.getenv("CUSTOM_API_KEY", "").strip()
CUSTOM_API_URL = os.getenv("CUSTOM_API_URL", "").strip()
CUSTOM_MODEL = os.getenv("CUSTOM_MODEL", "").strip()
OPENCODE_API_URL = os.getenv("OPENCODE_API_URL", "").strip()
OPENCODE_MODEL = os.getenv("OPENCODE_MODEL", "").strip()
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
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=th%E1%BB%9Di%20s%E1%BB%B1",
    ],
    "kinh-te": [
        "https://vnexpress.net/rss/kinh-doanh.rss",
        "https://dantri.com.vn/rss/kinh-doanh.rss",
        "https://znews.vn/rss/kinh-te.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=kinh%20t%E1%BA%BF",
    ],
    "cong-nghe": [
        "https://vnexpress.net/rss/cong-nghe.rss",
        "https://dantri.com.vn/rss/cong-nghe-thong-tin.rss",
        "https://znews.vn/rss/cong-nghe.rss",
        "https://news.google.com/rss?hl=en&gl=US&ceid=US:en&q=technology",
    ],
    "the-thao": [
        "https://vnexpress.net/rss/the-thao.rss",
        "https://dantri.com.vn/rss/the-thao.rss",
        "https://znews.vn/rss/the-thao.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=th%E1%BB%83%20thao",
    ],
    "giai-tri": [
        "https://vnexpress.net/rss/giai-tri.rss",
        "https://dantri.com.vn/rss/giai-tri.rss",
        "https://znews.vn/rss/giai-tri.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=gi%E1%BA%A3i%20tr%C3%AD",
    ],
    "giao-duc": [
        "https://vnexpress.net/rss/giao-duc.rss",
        "https://dantri.com.vn/rss/giao-duc.rss",
        "https://znews.vn/rss/giao-duc.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=gi%C3%A1o%20d%E1%BB%A5c",
    ],
    "phap-luat": [
        "https://vnexpress.net/rss/phap-luat.rss",
        "https://dantri.com.vn/rss/phap-luat.rss",
        "https://znews.vn/rss/phap-luat.rss",
        "https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q=ph%C3%A1p%20lu%E1%BA%ADt",
    ],
    "the-gioi": [
        "https://vnexpress.net/rss/the-gioi.rss",
        "https://dantri.com.vn/rss/the-gioi.rss",
        "https://znews.vn/rss/the-gioi.rss",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
    ],
}

INTERNATIONAL_FEEDS = {
    "quoc-te": [
        "https://feeds.bbci.co.uk/news/rss.xml",
        "https://feeds.reuters.com/reuters/topNews",
        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "https://techcrunch.com/feed/",
        "https://news.ycombinator.com/rss",
        "https://www.theguardian.com/international/rss",
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
    "quoc-te": "🌐 Quốc tế",
}
CATEGORY_KEYS = list(CATEGORY_LABELS.keys())

PROVIDER_CHOICES = ["opencode", "custom"]


def all_feeds() -> List[str]:
    out = []
    for k, v in {**CATEGORY_FEEDS, **INTERNATIONAL_FEEDS}.items():
        out.extend(v)
    return out


def validate_config() -> Tuple[bool, List[str]]:
    """Kiem tra cau hinh bat buoc. Tra ve (du_khong, danh_sach_loi)."""
    errs = []
    if not BOT_TOKEN:
        errs.append("BOT_TOKEN (token bot Telegram)")
    if AI_PROVIDER == "custom":
        if not CUSTOM_API_KEY:
            errs.append("CUSTOM_API_KEY (key API)")
        if not CUSTOM_API_URL:
            errs.append("CUSTOM_API_URL (base URL)")
        if not CUSTOM_MODEL:
            errs.append("CUSTOM_MODEL (chua chon model)")
    elif AI_PROVIDER == "opencode":
        if not OPENCODE_MODEL:
            errs.append("OPENCODE_MODEL (chua chon model)")
    return (len(errs) == 0, errs)
