#!/usr/bin/env python3
"""AI Agent News Bot — unified bot: tin tức + thông báo tự động."""
import os
import re
import html
import asyncio
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler,
                          filters, CallbackQueryHandler)

import config
from sources import NewsSourceManager
from database import Database
from providers import get_provider, list_providers

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("bot")

# ---- Globals ----
sources = NewsSourceManager()
db = Database()
provider = None


def vescape(text: str) -> str:
    return html.escape(text, quote=False)


def is_admin(user_id) -> bool:
    return config.ADMIN_CHAT_ID and str(user_id) == config.ADMIN_CHAT_ID


# ---- Keyboard ----

def _kb(cats: list, current: str = "tat-ca", back: bool = True):
    rows, row = [], []
    for k in cats:
        label = config.CATEGORY_LABELS.get(k, k)
        row.append(InlineKeyboardButton(
            ("✅ " if k == current else "") + label, callback_data=f"cat:{k}"))
        if len(row) == 3:
            rows.append(row); row = []
    if row:
        rows.append(row)
    nav = []
    if back:
        nav.append(InlineKeyboardButton("🔍 Tìm kiếm", callback_data="do_search"))
    nav.append(InlineKeyboardButton("🔄 Làm mới", callback_data="refresh"))
    rows.append(nav)
    return InlineKeyboardMarkup(rows)


def card(a: dict) -> str:
    """Hiển thị bài viết đã viết lại với nguồn ở dưới."""
    src = html.escape(a.get("source", "?"), quote=False)
    link = a.get("link", "")
    rewritten = a.get("rewritten", "")
    if rewritten:
        return (
            f"{rewritten}\n\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📰 Nguồn: {src}"
            f"{' · <a href=\"' + link + "\">Đọc bài gốc</a>" if link else ""}"
        )
    title = html.escape(a.get("title", "")[:160], quote=False)
    pub = html.escape(a.get("published", ""), quote=False)
    sm = sources._clean_text(a.get("summary") or "", 160)
    body = f"<b>{title}</b>\n"
    if pub:
        body += f"🕒 {pub} · "
    body += f"📰 {src}\n"
    if link:
        body += f"🔗 <a href=\"{link}\">Đọc bài gốc</a>"
    if sm:
        body += f"\n\n{html.escape(sm, quote=False)}"
    return body


def card_kb(link: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Viết lại bài", callback_data=f"sum:{link}"),
         InlineKeyboardButton("🔗 Mở", url=link)],
    ])


# ---- Duplicate detection ----

RECENT = {}


def _is_duplicate_link(link: str, chat_id: int) -> bool:
    recent_links = RECENT.get(chat_id, [])
    return link in recent_links


def _mark_seen_link(link: str, chat_id: int):
    if chat_id not in RECENT:
        RECENT[chat_id] = []
    if link not in RECENT[chat_id]:
        RECENT[chat_id].append(link)
        if len(RECENT[chat_id]) > 20:
            RECENT[chat_id] = RECENT[chat_id][-20:]


def _filter_new_articles(articles: list, chat_id: int) -> list:
    """Lọc bỏ bài trùng: cả trong session RECENT + database."""
    seen = set()
    result = []
    for a in articles:
        link = a.get("link", "")
        if not link:
            continue
        key = link.split("?")[0]
        if key in seen:
            continue
        if _is_duplicate_link(link, chat_id):
            continue
        if db.is_seen(link):
            continue
        seen.add(key)
        result.append(a)
    return result


# ==================== HANDLERS ====================

async def start(update, ctx):
    u = update.effective_user
    db.upsert_user(u.id, u.username or "", u.first_name or "")
    admin_note = ""
    if is_admin(u.id):
        admin_note = (
            "\n\n<b>⚙️ Lệnh admin:</b>\n"
            "• /set_provider — chọn provider AI\n"
            "• /set_model — chọn model AI\n"
            "• /schedule HH:MM — lịch gửi tin tự động\n"
            "• /scan <phút> — quét tự động\n"
            "• /scan_now — quét ngay\n"
            "• /settings — xem cấu hình"
        )
    cats = list(CATEGORY_LABELS.keys())
    await update.message.reply_text(
        "<b>🤖 AI Agent News Bot</b>\n━━━━━━━━━━━━━━━━\n"
        "• /tin [thể_loại] — tin mới nhất\n"
        "• /tim từ_khóa — tìm kiếm tin tức\n"
        "• /the_loai — chọn thể loại yêu thích\n"
        "• /ai — hỏi tin tức mới nhất\n"
        "• /ho_tro — hướng dẫn sử dụng\n"
        f"\n👇 Chọn thể loại để xem tin:{admin_note}",
        parse_mode=ParseMode.HTML, reply_markup=_kb(cats))


async def help_cmd(update, ctx):
    admin_section = ""
    if is_admin(update.effective_user.id):
        admin_section = (
            "\n\n<b>⚙️ Lệnh admin:</b>\n"
            "• /set_provider — chọn provider AI\n"
            "• /set_model — chọn model AI\n"
            "• /schedule 07:30 — đặt lịch gửi tin mỗi ngày\n"
            "• /schedule off — tắt lịch gửi tin\n"
            "• /scan 5 — quét tự động mỗi 5 phút\n"
            "• /scan_now — quét ngay\n"
            "• /settings — xem cấu hình"
        )
    await _reply(update, None,
        "<b>📖 Hướng dẫn sử dụng</b>\n━━━━━━━━━━━━━━━━\n"
        "• /tin [thể_loại] — vd /tin the-thao\n"
        "• /tim <từ khóa> — tìm tin tức\n"
        "• /the_loai — chọn thể loại yêu thích\n"
        "• /ai — tin tức mới nhất (AI trả lời)\n"
        "• Gửi link → AI viết lại bài\n\n"
        "<b>Thể loại:</b>\n"
        "tat-ca · thoi-su · kinh-te · cong-nghe\n"
        "the-thao · giai-tri · giao-duc · phap-luat\n"
        "the-gioi · quoc-te"
        f"{admin_section}",
        with_kb=False)


async def ping(update, ctx):
    await update.message.reply_text(
        f"🏓 Pong — vẫn sống khỏe ✅ ({datetime.now().strftime('%H:%M:%S')})",
        parse_mode=ParseMode.HTML)


async def news_cmd(update, ctx):
    key = (ctx.args[0].lower().replace("_", "-") if ctx.args else "tat-ca")
    cat = key if key in config.CATEGORY_KEYS else next(
        (k for k in config.CATEGORY_KEYS if k in key), "tat-ca")
    db.record_category(update.effective_user.id, cat)
    await _load_send(update.effective_chat.id, cat, update=update)


async def search_cmd(update, ctx):
    kw = " ".join(ctx.args).strip()
    if not kw:
        await _reply(update, None, "🔍 Cú pháp: /tim từ khóa\nVí dụ: /tim trí tuệ nhân tạo")
        return
    await update.message.reply_text(
        f"🔍 Đang tìm: <b>{html.escape(kw, quote=False)}</b>...",
        parse_mode=ParseMode.HTML)
    db.upsert_user(update.effective_user.id,
                   update.effective_user.username or "",
                   update.effective_user.first_name or "")
    articles = sources.search(kw, limit=config.MAX_ARTICLES)
    new_articles = _filter_new_articles(articles, update.effective_chat.id)
    db.save_articles(new_articles)
    await send_articles(update, None, new_articles, f"Kết quả: {html.escape(kw, quote=False)}")


async def _load_send(chat_id, cat, update=None, query=None, search_kw=None):
    if search_kw:
        articles = sources.search(search_kw, limit=config.MAX_ARTICLES)
    else:
        articles = sources.fetch_category(cat, limit=config.MAX_ARTICLES)
    new_articles = _filter_new_articles(articles, chat_id)
    for a in new_articles:
        _mark_seen_link(a.get("link", ""), chat_id)
    db.save_articles(new_articles)
    label = f"{config.CATEGORY_LABELS.get(cat, '')} · Mới nhất" if not search_kw else f"Kết quả: {search_kw}"
    await send_articles(update, query, new_articles, label)


async def refresh(update, ctx):
    cat = (db.get_user(update.effective_user.id) or {}).get("categories", "tat-ca")
    cid = (cat or "tat-ca").split(",")[0].strip()
    await _load_send(update.effective_chat.id, cid, update=update)


async def handle_msg(update, ctx):
    txt = (update.message.text or "").strip()
    if not txt:
        return
    db.upsert_user(update.effective_user.id, update.effective_user.username or "", update.effective_user.first_name or "")
    await update.message.chat.send_action("typing")
    if txt.startswith(("http://", "https://")):
        await _rewrite_link(update, txt)
    else:
        await _ask_ai(update, txt)


async def _ask_ai(update, txt):
    """Lệnh /ai - AI trả lời VỀ TIN TỨC CHỈ."""
    if not config.BOT_TOKEN:
        await update.message.reply_text("❌ Bot chưa đủ cấu hình.")
        return
    lower_txt = txt.lower().strip()
    news_keywords = ["tin", "tin tức", "tin mới", "tin hôm nay", "tin buổi này",
                     "thể thao", "kinh tế", "công nghệ", "thời sự", "giáo dục"]
    is_news_question = any(keyword in lower_txt for keyword in news_keywords) or len(lower_txt) < 50
    if not is_news_question:
        await update.message.reply_text(
            "⚠️ AI chỉ được trả lời về tin tức mới nhất.\n"
            "Ví dụ: <code>/ai hôm nay có tin gì</code>",
            parse_mode=ParseMode.HTML)
        return
    try:
        articles = sources.fetch_category("tat-ca", limit=5)
        if not articles:
            await update.message.reply_text("⚠️ Hiện không có tin tức.")
            return
        news_summary = "📰 <b>TIN TỨC MỚI NHẤT</b>\n━━━━━━━━━━━━━━━━\n\n"
        for i, a in enumerate(articles, 1):
            title = html.escape(a.get("title", ""), quote=False)[:100]
            src = html.escape(a.get("source", ""), quote=False)
            link = a.get("link", "")
            link_part = f' — <a href="{link}">đọc</a>' if link else ""
            news_summary += f"{i}. <b>{title}</b>\n   📰 {src}{link_part}\n\n"
        news_summary += "━━━━━━━━━━━━━━━━\n💬 Hỏi thêm: <code>/ai [câu hỏi]</code>"
        await update.message.reply_text(news_summary, parse_mode=ParseMode.HTML)
    except Exception as exc:
        logger.error("AI news: %s", exc)
        await update.message.reply_text("❌ AI lỗi — kiểm tra key/provider .env")


async def _rewrite_link(update, url):
    """Xử lý khi user gửi link: Scrape + AI viết lại."""
    global provider
    await update.message.reply_text("✍️ Đang đọc và viết lại bài...", parse_mode=ParseMode.HTML)
    art = sources.scrape_article(url)
    if not art.get("content"):
        await update.message.reply_text("⚠️ Không đọc được nội dung bài viết.", parse_mode=ParseMode.HTML)
        return
    try:
        src = url.split("/")[2] if "/" in url else url
        rewritten = await provider.rewrite_article(art["title"], art["content"], src)
        result = f"{rewritten}\n\n━━━━━━━━━━━━━━━━\n📰 Nguồn: <a href=\"{url}\">{src}</a>"
        await update.message.reply_text(result, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
    except Exception as exc:
        logger.error("rewrite link: %s", exc)
        await update.message.reply_text("❌ AI lỗi — kiểm tra key/provider .env", parse_mode=ParseMode.HTML)


# ==================== CALLBACK QUERY HANDLER (btn) ====================

async def btn(update, ctx):
    """Xử lý tất cả callback query từ inline keyboard."""
    global provider
    query = update.callback_query
    data = query.data or ""
    chat_id = query.message.chat_id if query.message else 0
    user_id = query.from_user.id

    await query.answer()

    # --- Chọn thể loại ---
    if data.startswith("cat:"):
        cat = data.split(":", 1)[1]
        db.record_category(user_id, cat)
        await _load_send(chat_id, cat, query=query)

    # --- Viết lại bài ---
    elif data.startswith("sum:"):
        link = data.split(":", 1)[1]
        if not provider:
            await query.edit_message_text("⚠️ Provider AI chưa cấu hình.")
            return
        await query.edit_message_text("✍️ Đang viết lại bài bằng AI...")
        try:
            art = sources.scrape_article(link)
            if not art.get("content"):
                await query.edit_message_text("⚠️ Không đọc được nội dung bài viết.")
                return
            src = link.split("/")[2] if "/" in link else link
            rewritten = await provider.rewrite_article(art["title"], art["content"], src)
            result = f"{rewritten}\n\n━━━━━━━━━━━━━━━━\n📰 Nguồn: <a href=\"{link}\">{src}</a>"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Mở bài gốc", url=link)]
            ])
            await query.edit_message_text(result, parse_mode=ParseMode.HTML,
                                          disable_web_page_preview=True, reply_markup=kb)
        except Exception as exc:
            logger.error("rewrite btn: %s", exc)
            await query.edit_message_text("❌ AI lỗi — không viết lại được bài.")

    # --- Tìm kiếm ---
    elif data == "do_search":
        await query.edit_message_text(
            "🔍 Nhập từ khóa tìm kiếm:\n"
            "Ví dụ: <code>/tim trí tuệ nhân tạo</code>",
            parse_mode=ParseMode.HTML)

    # --- Làm mới ---
    elif data == "refresh":
        cat = (db.get_user(user_id) or {}).get("categories", "tat-ca")
        cid = (cat or "tat-ca").split(",")[0].strip()
        await _load_send(chat_id, cid, query=query)

    # --- Chọn provider ---
    elif data.startswith("pick_provider:"):
        if not is_admin(user_id):
            await query.edit_message_text("⚠️ Chỉ admin mới được đổi provider.")
            return
        prov_name = data.split(":", 1)[1]
        if prov_name not in list_providers():
            await query.edit_message_text("⚠️ Provider không hợp lệ.")
            return
        _save_env("AI_PROVIDER", prov_name)
        # provider changed via config
        provider = get_provider(prov_name)
        cur_model = config.CUSTOM_MODEL if prov_name == "opencode" else config.CUSTOM_MODEL
        await query.edit_message_text(
            f"✅ Đã chuyển sang provider: <b>{prov_name}</b>\n"
            f"Model hiện tại: <b>{cur_model or 'chưa chọn'}</b>\n"
            f"Dùng /set_model để đổi model.",
            parse_mode=ParseMode.HTML)

    # --- Chọn model ---
    elif data.startswith("pick_model:"):
        if not is_admin(user_id):
            await query.edit_message_text("⚠️ Chỉ admin mới được đổi model.")
            return
        model_name = data.split(":", 1)[1]
        env_key = "OPENCODE_MODEL" if config.AI_PROVIDER == "opencode" else "CUSTOM_MODEL"
        _save_env(env_key, model_name)
        if config.AI_PROVIDER == "opencode":
            config.CUSTOM_MODEL = model_name
        else:
            config.CUSTOM_MODEL = model_name
        provider = get_provider(config.AI_PROVIDER)
        await query.edit_message_text(
            f"✅ Đã chọn model: <b>{model_name}</b>\n"
            f"Provider: {config.AI_PROVIDER}",
            parse_mode=ParseMode.HTML)

    # --- Unknown ---
    else:
        await query.edit_message_text("⚠️ Không nhận diện được thao tác.")


# ==================== ARTICLES DISPLAY ====================

async def send_articles(update, query, articles: list, title: str):
    if not articles:
        await _reply(update, query, "⚠️ Không có tin mới.", with_kb=False)
        return

    # Viết lại tất cả bài bằng AI
    rewritten = await _rewrite_all(articles)

    for i, a in enumerate(rewritten, 1):
        if a.get("rewritten"):
            lines = [card(a)]
            await _reply(update, query if i == 1 else None, "\n".join(lines))
        else:
            kb = card_kb(a["link"]) if a.get("link") else None
            sources.attach_images([a])
            if a.get("image"):
                try:
                    chat = (query.message if query else update.message).chat
                    await chat.send_photo(
                        photo=a["image"], caption=card(a),
                        parse_mode=ParseMode.HTML, reply_markup=kb)
                except Exception:
                    lines = [f"<b>📰 {html.escape(title, quote=False)}</b>",
                             "━━━━━━━━━━━━━━━━", card(a)]
                    await _reply(update, query if i == 1 else None, "\n".join(lines))
            else:
                lines = [f"<b>📰 {html.escape(title, quote=False)}</b>" if i == 1 else "",
                         "━━━━━━━━━━━━━━━━", card(a)]
                await _reply(update, query if i == 1 else None, "\n".join(lines))


async def _rewrite_all(articles: list) -> list:
    """Viết lại tất cả bài viết bằng thread để nhanh hơn."""
    def rewrite_one(a):
        link = a.get("link", "")
        if not link or not provider:
            a["rewritten"] = ""
            return a
        try:
            art = sources.scrape_article(link)
            if not art.get("content"):
                a["rewritten"] = ""
                return a
            src = a.get("source", "")
            title = art.get("title") or a.get("title", "")
            loop = asyncio.new_event_loop()
            try:
                rewritten = loop.run_until_complete(
                    provider.rewrite_article(title, art["content"], src))
            finally:
                loop.close()
            a["rewritten"] = rewritten
            if art.get("image") and not a.get("image"):
                a["image"] = art["image"]
        except Exception as exc:
            logger.warning("rewrite %s: %s", link, exc)
            a["rewritten"] = ""
        return a

    with ThreadPoolExecutor(max_workers=min(len(articles) or 1, 3)) as ex:
        results = list(ex.map(rewrite_one, articles))
    return results


async def _reply(update, query, text: str, with_kb: bool = True, category: str = "tat-ca"):
    kb = _kb(list(config.CATEGORY_FEEDS.keys()), category) if with_kb else None
    target = getattr(query, "message", None) or getattr(update, "message", None)
    if query is not None:
        try:
            await query.edit_message_text(text, parse_mode=ParseMode.HTML,
                                          disable_web_page_preview=True, reply_markup=kb)
            return
        except Exception:
            pass
    await target.reply_text(text, parse_mode=ParseMode.HTML,
                            disable_web_page_preview=True, reply_markup=kb)


# ==================== ADMIN: PROVIDER / MODEL ====================

async def set_provider(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    providers = list_providers()
    rows = []
    for p in providers:
        mark = "✅ " if p == config.AI_PROVIDER else ""
        rows.append([InlineKeyboardButton(f"{mark}{p}", callback_data=f"pick_provider:{p}")])
    kb = InlineKeyboardMarkup(rows)
    await update.message.reply_text(
        "<b>⚙️ Chọn provider AI</b>\n━━━━━━━━━━━━━━━━\n"
        "• <b>opencode</b> — miễn phí, không cần API key\n"
        "• <b>custom</b> — cần API key + base URL",
        parse_mode=ParseMode.HTML, reply_markup=kb)


async def set_model(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text("⏳ Đang quét danh sách model...", parse_mode=ParseMode.HTML)

    prov = get_provider(config.AI_PROVIDER)
    models = await prov.fetch_models()

    if not models:
        await update.message.reply_text(
            "⚠️ Không quét được model. Dùng <code>nhatnam config</code> để đổi.",
            parse_mode=ParseMode.HTML)
        return

    rows = []
    current = config.OPENCODE_MODEL if config.AI_PROVIDER == "opencode" else config.CUSTOM_MODEL
    for m in models[:20]:
        mark = "✅ " if m == current else ""
        rows.append([InlineKeyboardButton(f"{mark}{m}", callback_data=f"pick_model:{m}")])
    kb = InlineKeyboardMarkup(rows)
    await update.message.reply_text(
        f"<b>⚙️ Chọn model ({config.AI_PROVIDER})</b>\n"
        f"Tổng: {len(models)} model — hiển thị 20 đầu:",
        parse_mode=ParseMode.HTML, reply_markup=kb)


async def schedule_cmd(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    arg = " ".join(ctx.args).strip()
    if not arg:
        user = db.get_user(update.effective_user.id)
        cur = (user or {}).get("schedule_time", "off")
        await update.message.reply_text(
            f"⏰ Lịch hiện tại: <b>{cur}</b>\n"
            "Dùng: <code>/schedule 07:30</code> hoặc <code>/schedule off</code>",
            parse_mode=ParseMode.HTML)
        return
    if arg.lower() == "off":
        db.set_schedule(update.effective_user.id, "off")
        await update.message.reply_text("✅ Đã tắt lịch gửi tin tự động.", parse_mode=ParseMode.HTML)
        return
    parts = arg.split(":")
    if len(parts) != 2:
        await update.message.reply_text("❌ Sai định dạng. Dùng: <code>/schedule 07:30</code>", parse_mode=ParseMode.HTML)
        return
    try:
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Giờ không hợp lệ. Dùng: <code>/schedule 07:30</code>", parse_mode=ParseMode.HTML)
        return
    db.set_schedule(update.effective_user.id, f"{h:02d}:{m:02d}")
    await update.message.reply_text(
        f"✅ Đã đặt lịch gửi tin lúc <b>{h:02d}:{m:02d}</b> mỗi ngày.",
        parse_mode=ParseMode.HTML)


async def scan_cmd(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    arg = " ".join(ctx.args).strip()
    if not arg:
        await update.message.reply_text(
            f"⏰ Đang quét mỗi <b>{config.SCAN_MINUTES}</b> phút.\nDùng: <code>/scan 5</code>",
            parse_mode=ParseMode.HTML)
        return
    try:
        mins = int(arg)
    except ValueError:
        await update.message.reply_text("❌ Sai định dạng. Dùng số phút: /scan 5", parse_mode=ParseMode.HTML)
        return
    if mins < 1:
        await update.message.reply_text("❌ Tối thiểu 1 phút.", parse_mode=ParseMode.HTML)
        return
    _set_scan_minutes(mins)
    await update.message.reply_text(f"✅ Đã đặt quét mỗi <b>{mins}</b> phút.", parse_mode=ParseMode.HTML)


def _set_scan_minutes(mins: int):
    _save_env("SCAN_MINUTES", str(mins))
    config.SCAN_MINUTES = mins


async def scan_now(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    await update.message.reply_text("⏳ Đang quét tin mới...", parse_mode=ParseMode.HTML)
    await _send_digest_to(ctx, update.effective_user.id)


async def settings_cmd(update, ctx):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⚠️ Lệnh này chỉ dành cho admin.", parse_mode=ParseMode.HTML)
        return
    user = db.get_user(update.effective_user.id)
    sched = (user or {}).get("schedule_time", "off")
    config.CUSTOM_MODEL
    config.CUSTOM_API_URL
    await update.message.reply_text(
        "<b>⚙️ Cấu hình hiện tại</b>\n━━━━━━━━━━━━━━━━\n"
        f"• BOT_TOKEN: {'✅' if config.BOT_TOKEN else '❌'}\n"
        f"• Provider: <b>{config.AI_PROVIDER}</b>\n"
        f"• Model: <b>{cur_model or '❌ chưa chọn'}</b>\n"
        f"• API URL: <code>{cur_url or 'mặc định'}</code>\n"
        f"• Admin Chat ID: <code>{config.ADMIN_CHAT_ID or 'không đặt'}</code>\n"
        f"• Quét mỗi: {config.SCAN_MINUTES} phút\n"
        f"• Lịch gửi tin: <b>{sched}</b>",
        parse_mode=ParseMode.HTML)


# ==================== SCHEDULED DIGEST ====================

async def send_scheduled_digest(context):
    """Kiểm tra và gửi tin cho user có lịch."""
    now = datetime.now()
    hour, minute = now.hour, now.minute
    users = db.get_scheduled_users(hour, minute)
    for u in users:
        chat_id = u["chat_id"]
        try:
            articles = sources.fetch_category("tat-ca", limit=config.MAX_ARTICLES)
            new_articles = _filter_new_articles(articles, chat_id)
            if not new_articles:
                continue
            db.save_articles(new_articles)
            db.mark_digest_sent(chat_id)
            await _send_digest_to_user(context, chat_id, new_articles)
        except Exception as exc:
            logger.error("digest %s: %s", chat_id, exc)


async def _send_digest_to(ctx, chat_id):
    """Gửi tin mới nhất (cho /scan_now) — VIẾT LẠI TẤT CẢ BÀI."""
    articles = sources.fetch_category("tat-ca", limit=config.MAX_ARTICLES)
    new_articles = _filter_new_articles(articles, chat_id)
    if not new_articles:
        await ctx.bot.send_message(chat_id, "⚠️ Không lấy được tin mới nào (hoặc đã đọc hết).",
                                   parse_mode=ParseMode.HTML)
        return
    db.save_articles(new_articles)
    for a in new_articles:
        _mark_seen_link(a.get("link", ""), chat_id)
    await _send_digest_to_user(ctx, chat_id, new_articles)


async def _send_digest_to_user(context, chat_id, articles):
    """Gửi tin — viết lại TẤT CẢ bài bằng AI."""
    rewritten = await _rewrite_all(articles)

    for i, a in enumerate(rewritten):
        sources.attach_images([a])
        if a.get("rewritten"):
            # Bài đã viết lại — gửi đầy đủ
            if a.get("image"):
                try:
                    await context.bot.send_photo(
                        chat_id=chat_id, photo=a["image"],
                        caption=card(a), parse_mode=ParseMode.HTML)
                except Exception:
                    await context.bot.send_message(
                        chat_id=chat_id, text=card(a),
                        parse_mode=ParseMode.HTML, disable_web_page_preview=True)
            else:
                await context.bot.send_message(
                    chat_id=chat_id, text=card(a),
                    parse_mode=ParseMode.HTML, disable_web_page_preview=True)
        else:
            # Không viết lại được — gửi tóm tắt + link
            kb = card_kb(a["link"]) if a.get("link") else None
            await context.bot.send_message(
                chat_id=chat_id, text=card(a),
                parse_mode=ParseMode.HTML, reply_markup=kb,
                disable_web_page_preview=True)


def _rewrite_one_v2(a: dict) -> dict:
    """Đọc và viết lại 1 bài (sync fallback)."""
    link = a.get("link", "")
    if not link or not provider:
        return a
    try:
        art = sources.scrape_article(link)
        if not art.get("content"):
            return a
        src = a.get("source", "")
        title = art.get("title") or a.get("title", "")
        loop = asyncio.new_event_loop()
        try:
            rewritten = loop.run_until_complete(
                provider.rewrite_article(title, art["content"], src))
        finally:
            loop.close()
        a["rewritten"] = rewritten
        if art.get("image") and not a.get("image"):
            a["image"] = art["image"]
    except Exception:
        pass
    return a


# ==================== ENV HELPER ====================

def _save_env(name, value):
    env_path = os.path.join(config.REPO_DIR, ".env")
    try:
        if os.path.exists(env_path):
            with open(env_path, "r") as f:
                lines = f.readlines()
            found = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{name}="):
                    lines[i] = f"{name}={value}\n"
                    found = True
                    break
            if found:
                with open(env_path, "w") as f:
                    f.writelines(lines)
            else:
                with open(env_path, "a") as f:
                    f.write(f"{name}={value}\n")
        else:
            with open(env_path, "w") as f:
                f.write(f"{name}={value}\n")
    except Exception as exc:
        logger.error("save env %s: %s", name, exc)


# ==================== STARTUP ====================

async def on_startup(app):
    await app.bot.set_my_commands([
        BotCommand("start", "Khởi động"),
        BotCommand("tin", "Tin mới nhất"),
        BotCommand("tim", "Tìm kiếm tin tức"),
        BotCommand("the_loai", "Chọn thể loại"),
        BotCommand("ho_tro", "Hướng dẫn sử dụng"),
        BotCommand("ping", "Kiểm tra bot"),
        BotCommand("set_provider", "Chọn provider AI (admin)"),
        BotCommand("set_model", "Chọn model AI (admin)"),
        BotCommand("schedule", "Đặt lịch gửi tin (admin)"),
        BotCommand("scan", "Quét tự động (admin)"),
        BotCommand("scan_now", "Quét ngay (admin)"),
        BotCommand("settings", "Xem cấu hình (admin)"),
        BotCommand("ai", "Tin tức mới nhất — AI trả lời"),
    ])


async def post_init(app):
    await on_startup(app)
    app.job_queue.run_repeating(
        send_scheduled_digest,
        interval=60,
        first=10
    )


def main():
    global provider
    ok, errs = config.validate_config()
    if not ok:
        print("❌ Cấu hình chưa đầy đủ:")
        for e in errs:
            print("  -", e)
        print("Hãy sửa .env hoặc dùng: nhatnam config")
        return
    provider = get_provider(config.AI_PROVIDER)
    config.CUSTOM_MODEL
    print(f"🚀 AI Agent News Bot — provider: {config.AI_PROVIDER} | model: {cur_model}")

    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler(["help", "ho_tro"], help_cmd))
    app.add_handler(CommandHandler(["ping", "song"], ping))
    app.add_handler(CommandHandler(["news", "tin"], news_cmd))
    app.add_handler(CommandHandler(["search", "tim"], search_cmd))
    app.add_handler(CommandHandler("the_loai", news_cmd))
    app.add_handler(CommandHandler("set_provider", set_provider))
    app.add_handler(CommandHandler("set_model", set_model))
    app.add_handler(CommandHandler("schedule", schedule_cmd))
    app.add_handler(CommandHandler("scan", scan_cmd))
    app.add_handler(CommandHandler("scan_now", scan_now))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("ai", _ask_ai))
    app.add_handler(CallbackQueryHandler(btn))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))

    app.run_polling(allowed_updates=__import__("telegram").Update.ALL_TYPES)


if __name__ == "__main__":
    main()
