#!/usr/bin/env bash
# =====================================================
# CÀI ĐẶT AI AGENT NEWS BOT — chạy được từ Termux mới
#   curl -sL https://raw.githubusercontent.com/nhatnamdev662/news-agent/main/install.sh | bash
# =====================================================
set -euo pipefail

STEP=0
TOTAL=8

step() { STEP=$((STEP+1)); echo ""; echo "━━━ [${STEP}/${TOTAL}] $1 ━━━"; }
ok()   { echo "  ✅ $1"; }
fail() { echo "  ❌ $1"; exit 1; }

echo "🚀 CÀI ĐẶT AI AGENT NEWS BOT"
echo "============================="

# ---------- 1) Nhận diện môi trường ----------
step "Nhận diện môi trường"
IS_TERMUX="no"
if [ -n "${PREFIX:-}" ] && [ -d "${PREFIX}" ]; then
    IS_TERMUX="yes"
    ok "Termux (Android)"
else
    ok "Linux"
fi

# ---------- 2) Cài công cụ cơ bản ----------
step "Cài công cụ cơ bản (git, python)"
ensure_tools() {
    local need=""
    command -v git >/dev/null 2>&1 || need="${need} git"
    command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || need="${need} python"

    if [ -z "${need}" ]; then
        ok "Đã có git + python"
        return 0
    fi

    echo "  ⏳ Đang cài:${need} ..."
    if [ "${IS_TERMUX}" = "yes" ]; then
        pkg update -y 2>/dev/null || true
        pkg install -y ${need}
    else
        if command -v apt-get >/dev/null 2>&1; then
            sudo apt-get update -y 2>/dev/null || true
            sudo apt-get install -y ${need}
        else
            fail "Không có apt — hãy cài thủ công git, python3 rồi chạy lại"
        fi
    fi

    command -v git >/dev/null 2>&1 || fail "Vẫn thiếu git"
    command -v python3 >/dev/null 2>&1 || command -v python >/dev/null 2>&1 || fail "Vẫn thiếu python"
    ok "Đã cài xong công cụ"
}
ensure_tools

# ---------- 3) Clone mã nguồn ----------
step "Lấy mã nguồn"
REPO_URL="https://github.com/nhatnamdev662/news-agent.git"
if [ -f "bot.py" ]; then
    REPO_DIR="$(pwd)"
    ok "Đang chạy từ thư mục mã nguồn: ${REPO_DIR}"
else
    DEST="${HOME}/news-agent"
    if [ -d "${DEST}/.git" ]; then
        ok "Repo đã có — đang cập nhật..."
        git -C "${DEST}" pull --ff-only || true
    else
        if [ -d "${DEST}" ] && [ -z "$(ls -A "${DEST}" 2>/dev/null)" ]; then
            rmdir "${DEST}"
        fi
        echo "  ⏳ Đang clone về ${DEST}..."
        git clone --depth 1 "${REPO_URL}" "${DEST}" || fail "Clone thất bại — kiểm tra mạng"
    fi
    REPO_DIR="${DEST}"
    ok "Mã nguồn sẵn sàng"
fi
cd "${REPO_DIR}"

# ---------- 4) Cài thư viện Python ----------
step "Cài thư viện Python"
if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi

# Termux: KHÔNG upgrade pip (bị cấm)
if [ "${IS_TERMUX}" = "yes" ]; then
    ok "Bỏ qua upgrade pip (Termux cấm)"
else
    echo "  ⏳ Nâng cấp pip..."
    "${PY}" -m pip install --upgrade pip 2>/dev/null || ok "pip đã mới nhất"
fi

echo "  ⏳ Cài thư viện theo requirements.txt..."
if "${PY}" -m pip install -r requirements.txt 2>/dev/null; then
    ok "Thư viện đã cài xong"
elif "${PY}" -m pip install --break-system-packages -r requirements.txt 2>/dev/null; then
    ok "Thư viện đã cài xong"
else
    fail "Cài thư viện thất bại. Thử: ${PY} -m pip install -r requirements.txt"
fi

# ---------- 5) Tạo .env ----------
step "Tạo cấu hình .env"
if [ ! -f ".env" ]; then
    cat > .env << 'ENVEOF'
# AI Agent News Bot — cấu hình
# Nhập: nhatnam config

BOT_TOKEN=
CUSTOM_API_KEY=
CUSTOM_API_URL=https://api.darkapi.dev/v1
CUSTOM_MODEL=laguna-s-2.1-free
ADMIN_CHAT_ID=
MAX_ARTICLES=6
SCAN_MINUTES=5
ENVEOF
    ok "Đã tạo .env mẫu"
else
    ok ".env đã tồn tại"
fi

# ---------- 6) Cài lệnh nhatnam ----------
step "Cài lệnh nhatnam vào PATH"
if [ "${IS_TERMUX}" = "yes" ]; then
    BIN_DIR="${PREFIX}/bin"
    BOOT_DIR="${HOME}/.termux/boot"
else
    BIN_DIR="${HOME}/.local/bin"
    BOOT_DIR="${HOME}/.config/news-agent/boot"
fi
mkdir -p "${BIN_DIR}" "${BOOT_DIR}" data logs providers

cat > "${BIN_DIR}/nhatnam" << EOF
#!/usr/bin/env bash
exec bash "${REPO_DIR}/nhatnam" "\$@"
EOF
chmod +x "${BIN_DIR}/nhatnam"
ok "Lệnh nhatnam: ${BIN_DIR}/nhatnam"

# ---------- 7) Boot tự động ----------
step "Cài boot tự động (Termux:Boot / @reboot)"
cat > "${BOOT_DIR}/news-agent.sh" << EOF
#!/usr/bin/env bash
exec bash "${REPO_DIR}/run.sh"
EOF
chmod +x "${BOOT_DIR}/news-agent.sh"

if [ "${IS_TERMUX}" != "yes" ] && command -v crontab >/dev/null 2>&1; then
    ( crontab -l 2>/dev/null | grep -v "news-agent/run.sh" ; \
      echo "@reboot bash ${REPO_DIR}/run.sh" ) | crontab - || true
fi
ok "Đã cài script boot: ${BOOT_DIR}/news-agent.sh"

# ---------- 8) Hoàn tất ----------
step "Hoàn tất"
mkdir -p data logs providers
echo ""
echo "============================================================"
echo "✅ CÀI ĐẶT HOÀN TẤT!"
echo "============================================================"
echo ""
echo "Bước tiếp theo:"
echo "  1) nhatnam config   → nhập token bot + key AI"
echo "  2) nhatnam          → chạy bot (tắt bằng Ctrl+C)"
