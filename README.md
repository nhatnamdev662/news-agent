# 🤖 AI Agent News Bot

Bot Telegram tin tức thông minh — chạy trên **Termux (Android)** hoặc Linux, dùng **AI provider tùy chỉnh** (OpenAI-compatible, ví dụ DarkAPI `laguna-s-2.1-free`).

## ✨ Tính năng

- 📰 Tin mới nhất theo **9 thể loại** (Thời sự, Kinh tế, Công nghệ, Thể thao, Giải trí, Giáo dục, Pháp luật, Thế giới, Tất cả)
- 🖼️ Gửi tin **kèm ảnh** + bố cục đẹp, nút bấm chọn thể loại ngay trong Telegram
- 🔍 Tìm kiếm tin tức theo từ khóa
- 🧠 Tóm tắt bài viết/link bằng AI provider tùy chỉnh
- ⏰ **Lịch tự gửi tin** mỗi ngày theo giờ bạn chọn
- 🏷️ Ghi nhớ sở thích thể loại từng người dùng (hỗ trợ nhiều người)
- 🚀 Gõ `nhatnam` trong Termux là chạy tất cả: kiểm tra cấu hình, hỏi nhập nếu thiếu, tự restart khi lỗi, tắt bằng `Ctrl+C`
- 🔁 Watchdog tự khởi động lại bot khi lỗi
- 📴 Tự chạy khi bật máy (Termux:Boot / crontab @reboot)

## 🚀 Cài đặt (1 lệnh)

```bash
curl -sL https://raw.githubusercontent.com/nhatnamdev662/news-agent/main/install.sh | bash
```

> 💡 Chạy được ngay trên **Termux mới**: script tự cài `git` + `python` (`pkg`), clone mã nguồn, cài thư viện, tạo lệnh `nhatnam` và script boot.

Hoặc thủ công:

```bash
git clone https://github.com/nhatnamdev662/news-agent.git
cd news-agent
bash install.sh
```

## ⚙️ Cấu hình (trong Termux)

```bash
nhatnam config
```

Nó sẽ hỏi lần lượt:

| Thông tin | Mô tả |
|-----------|-------|
| `TELEGRAM_BOT_TOKEN` | Token bot từ [@BotFather](https://t.me/BotFather) |
| `CUSTOM_API_KEY` | Key provider AI (vd DarkAPI) |
| `CUSTOM_API_URL` | URL API, vd `https://api.darkapi.dev/v1` |
| `CUSTOM_MODEL` | Model, vd `laguna-s-2.1-free` |

Hoặc sửa trực tiếp file `.env`.

## ▶️ Chạy bot

```bash
nhatnam            # chạy bot: kiểm tra cấu hình -> hỏi nhập nếu thiếu -> tự restart khi lỗi
nhatnam config     # nhập lại cấu hình
```

Tắt bot: bấm **Ctrl+C** — bot sẽ tự dọn sạch tiến trình python.

## 📋 Lệnh trong bot Telegram

| Lệnh | Mô tả |
|------|-------|
| `/start` | Menu chính + nút chọn thể loại |
| `/news` | Tin mới nhất (tất cả thể loại) |
| `/news the-thao` | Tin theo thể loại cụ thể |
| `/search AI` | Tìm kiếm tin tức |
| `/cat` | Chọn thể loại yêu thích |
| `/schedule 07:30` | Gửi tin tự động mỗi ngày (dùng `off` để tắt) |
| `/settings` | Xem cấu hình của bạn |
| Gửi link | Tóm tắt bài viết bằng AI |
| Gửi đoạn văn | Tóm tắt bằng AI |

Thể loại: `tat-ca`, `thoi-su`, `kinh-te`, `cong-nghe`, `the-thao`, `giai-tri`, `giao-duc`, `phap-luat`, `the-gioi`

## 🗂️ Cấu trúc

```
news-agent/
├── bot.py           # Bot Telegram chính
├── config.py        # Cấu hình + nguồn tin theo thể loại
├── database.py      # SQLite: người dùng, sở thích, chống trùng tin
├── sources.py       # RSS, tìm kiếm, ảnh, scrape bài viết
├── providers/       # Custom AI provider
├── nhatnam          # Lệnh chạy bot trong Termux (tất cả trong 1)
├── run.sh           # Watchdog tự restart (foreground/nền)
├── install.sh       # Cài đặt 1 lệnh
└── .env             # Cấu hình
```

## 🔌 Tùy chỉnh nguồn tin

Sửa `RSS_FEEDS` trong `.env` theo định dạng:

```
thoi-su=https://url1.rss,https://url2.rss|kinh-te=https://url3.rss
```

## 🧪 Test nhanh trên máy

```bash
python3 -c "from sources import NewsSourceManager; s=NewsSourceManager(); print(len(s.fetch_category('tat-ca')), 'tin')"
```

## ⚠️ Ghi chú Termux

- Cài thêm app **Termux:Boot** (từ F-Droid) để bot tự chạy khi mở máy.
- Script boot được tạo sẵn tại `~/.termux/boot/news-agent.sh`.
