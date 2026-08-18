"""Xác thực cấu hình .env + probe provider trước khi chạy bot."""
import sys
import asyncio
import logging
import config


def _check() -> list:
    errs = []
    if not config.BOT_TOKEN:
        errs.append("BOT_TOKEN")
    if config.AI_PROVIDER == "custom":
        if not config.CUSTOM_API_KEY:
            errs.append("CUSTOM_API_KEY")
        if not config.CUSTOM_API_URL:
            errs.append("CUSTOM_API_URL")
        if not config.CUSTOM_MODEL:
            errs.append("CUSTOM_MODEL (chưa chọn model — dùng /set_model)")
    elif config.AI_PROVIDER == "opencode":
        if not config.OPENCODE_MODEL:
            errs.append("OPENCODE_MODEL (chưa chọn model — dùng /set_model)")
    return errs


async def _probe_provider() -> str:
    from providers import get_provider
    prov = get_provider(config.AI_PROVIDER)
    cur_model = config.OPENCODE_MODEL if config.AI_PROVIDER == "opencode" else config.CUSTOM_MODEL
    if not cur_model:
        return "skip"
    try:
        await prov.chat("Xin chào", max_tokens=8)
        return "OK"
    except Exception as exc:
        return f"Lỗi: {exc}"


def main():
    errs = _check()
    if errs:
        print("❌ CẤU HÌNH THIẾU:")
        for e in errs:
            print(f"  - {e}")
        print("Chạy: nhatnam config")
        sys.exit(1)

    res = asyncio.run(_probe_provider())
    if res == "skip":
        print("⚠️  Chưa chọn model — chạy /set_model để chọn.")
    elif res == "OK":
        print("✅ Cấu hình OK — provider sẵn sàng.")
    else:
        print(f"⚠️  Provider: {res}")
        print("⚠️  Provider lỗi — bot chạy nhưng tính năng AI sẽ thất bại.")
    sys.exit(0)


if __name__ == "__main__":
    main()
