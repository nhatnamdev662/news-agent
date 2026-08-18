import sys
import asyncio
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
            errs.append("CUSTOM_MODEL")
    elif config.AI_PROVIDER == "opencode":
        if not config.OPENCODE_MODEL:
            errs.append("OPENCODE_MODEL")
    return errs


async def _probe_provider() -> str:
    from providers import get_provider
    prov = get_provider(config.AI_PROVIDER)
    cur_model = config.OPENCODE_MODEL if config.AI_PROVIDER == "opencode" else config.CUSTOM_MODEL
    if not cur_model:
        return "skip"
    try:
        await prov.chat("Xin chao", max_tokens=8)
        return "OK"
    except Exception as exc:
        return f"Loi: {exc}"


def main():
    errs = _check()
    if errs:
        print("❌ CAU HINH THIEU:")
        for e in errs:
            print(f"  - {e}")
        print("Chay: nhatnam config")
        sys.exit(1)

    res = asyncio.run(_probe_provider())
    if res == "skip":
        print("⚠️  Chua chon model — chay nhatnam config de chon.")
    elif res == "OK":
        print("✅ Cau hinh OK — provider san sang.")
    else:
        print(f"⚠️  Provider: {res}")
        print("⚠️  Provider loi — bot chay nhung tinh nang AI se that bai.")
    sys.exit(0)


if __name__ == "__main__":
    main()
