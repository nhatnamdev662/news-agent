"""Nguồn tin: RSS đa thể loại, tìm kiếm, trích xuất ảnh, chống trùng lặp."""
import re
import html
import logging
import concurrent.futures
from urllib.parse import urlparse, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

from config import CATEGORY_FEEDS, CATEGORY_LABELS, MAX_ARTICLES

logger = logging.getLogger(__name__)

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")


class NewsSourceManager:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": UA})
        self._img_cache = {}

    # ---------- Helper ----------
    @staticmethod
    def _clean_text(text: str, limit: int = 250) -> str:
        text = html.unescape(re.sub(r"<[^>]+>", " ", text or ""))
        text = re.sub(r"\s+", " ", text).strip()
        return text[:limit] + ("..." if len(text) > limit else "")

    @staticmethod
    def _extract_image_from_summary(summary: str) -> str:
        m = re.search(r'<img[^>]+src="([^"]+)"', summary or "")
        if m:
            src = html.unescape(m.group(1))
            if src.startswith("//"):
                src = "https:" + src
            return src
        return ""

    @staticmethod
    def _feed_source(url: str) -> str:
        netloc = urlparse(url).netloc
        return netloc.replace("www.", "").split(".")[0].title()

    # ---------- Fetch RSS ----------
    def fetch_feed(self, url: str, category: str = "tat-ca", limit: int = 10) -> list:
        try:
            resp = self.session.get(url, timeout=12, allow_redirects=True)
            if resp.status_code != 200:
                logger.warning("Feed %s status %s", url, resp.status_code)
                return []
            feed = feedparser.parse(resp.content)
            if feed.bozo and not feed.entries:
                logger.warning("Feed %s parse error: %s", url, feed.bozo_exception)
                return []
            articles = []
            for entry in feed.entries[:limit]:
                link = getattr(entry, "link", "") or ""
                if not link:
                    continue
                summary_raw = getattr(entry, "summary", "") or ""
                image = self._extract_image_from_summary(summary_raw)
                if not image and entry.get("media_content"):
                    image = entry.media_content[0].get("url", "")
                if not image and entry.get("media_thumbnail"):
                    image = entry.media_thumbnail[0].get("url", "")
                for l in entry.get("links", []):
                    if "image" in (l.get("type") or ""):
                        image = l.get("href", "")
                        break
                articles.append({
                    "title": self._clean_text(getattr(entry, "title", ""), 160),
                    "link": link,
                    "summary": self._clean_text(summary_raw, 220),
                    "source": self._feed_source(url),
                    "category": category,
                    "image": image,
                    "published": getattr(entry, "published", ""),
                })
            return articles
        except Exception as exc:
            logger.warning("Feed %s error: %s", url, exc)
            return []

    def fetch_category(self, category: str = "tat-ca", limit: int = None) -> list:
        limit = limit or MAX_ARTICLES
        feeds = CATEGORY_FEEDS.get(category) or CATEGORY_FEEDS["tat-ca"]
        all_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(feeds)) as ex:
            futures = [ex.submit(self.fetch_feed, url, category, limit) for url in feeds]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    all_articles.extend(fut.result())
                except Exception:
                    pass
        return self._dedup_sorted(all_articles, limit)

    def search(self, query: str, limit: int = None) -> list:
        limit = limit or MAX_ARTICLES
        q = quote_plus(query)
        urls = [
            f"https://news.google.com/rss?hl=vi&gl=VN&ceid=VN:vi&q={q}",
            f"https://news.google.com/rss?hl=en&gl=US&ceid=US:en&q={q}",
        ]
        all_articles = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
            futures = [ex.submit(self.fetch_feed, url, "tim-kiem", limit) for url in urls]
            for fut in concurrent.futures.as_completed(futures):
                try:
                    all_articles.extend(fut.result())
                except Exception:
                    pass
        return self._dedup_sorted(all_articles, limit)

    def _dedup_sorted(self, articles: list, limit: int) -> list:
        seen = set()
        result = []
        for a in sorted(articles, key=lambda x: x.get("published", ""), reverse=True):
            key = a["link"].split("?")[0]
            if key in seen:
                continue
            seen.add(key)
            result.append(a)
            if len(result) >= limit:
                break
        return result

    # ---------- Ảnh fallback từ trang bài viết ----------
    def get_og_image(self, url: str, timeout: float = 6.0) -> str:
        if url in self._img_cache:
            return self._img_cache[url]
        image = ""
        try:
            resp = self.session.get(url, timeout=timeout)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                og = soup.find("meta", property="og:image")
                if og and og.get("content"):
                    image = og["content"]
        except Exception:
            pass
        self._img_cache[url] = image
        return image

    def attach_images(self, articles: list, max_threads: int = 4) -> list:
        """Điền ảnh còn thiếu bằng og:image từ trang bài viết."""
        missing = [a for a in articles if not a.get("image") and a.get("link")]
        if not missing:
            return articles

        def worker(a):
            img = self.get_og_image(a["link"])
            if img:
                a["image"] = img
            return a

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as ex:
            list(ex.map(worker, missing))
        return articles

    # ---------- Scrape nội dung bài viết (tóm tắt link) ----------
    def scrape_article(self, url: str) -> dict:
        try:
            resp = self.session.get(url, timeout=15)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.content, "html.parser")
            for elem in soup(["script", "style", "nav", "footer", "header", "aside"]):
                elem.decompose()
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            og = soup.find("meta", property="og:title")
            if og and og.get("content"):
                title = og["content"].strip()
            paragraphs = []
            for elem in soup.find_all(["p", "h2", "h3"]):
                text = elem.get_text(" ", strip=True)
                if len(text) > 60:
                    paragraphs.append(text)
            content = " ".join(paragraphs)[:4000]
            image = ""
            og_img = soup.find("meta", property="og:image")
            if og_img and og_img.get("content"):
                image = og_img["content"]
            return {"title": title, "content": content, "url": url, "image": image}
        except Exception as exc:
            logger.warning("Scrape %s error: %s", url, exc)
            return {"title": "", "content": "", "url": url, "image": ""}
