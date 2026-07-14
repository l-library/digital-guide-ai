#!/usr/bin/env bash
# =============================================================================
# digital-guide-ai 后端启动脚本
#
# 作用：在 conda 环境 DGA 中同时启动
#   - FastAPI 后端（端口 8000）
#   - LiveTalking 数字人服务（端口 8010，可选）
#
# 用法（在仓库任意目录执行）：
#   bash backend/scripts/run.sh
#   bash backend/scripts/run.sh --no-livetalking      # 仅起后端
#
# 前置：bootstrap.sh 已成功执行，backend/.env 已配置好
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$BACKEND_DIR/.env"
ENV_NAME="DGA"

# ─── 颜色输出 ────────────────────────────────────────────────────────────────
c_red=$'\033[31m'; c_grn=$'\033[32m'; c_yel=$'\033[33m'
c_blu=$'\033[34m'; c_end=$'\033[0m'
log()  { printf "${c_blu}[run]${c_end} %s\n" "$*"; }
warn() { printf "${c_yel}[warn]${c_end} %s\n" "$*"; }
ok()   { printf "${c_grn}[ok]${c_end} %s\n" "$*"; }
die()  { printf "${c_red}[fatal]${c_end} %s\n" "$*" >&2; exit 1; }

# ─── 参数解析 ────────────────────────────────────────────────────────────────
RUN_LIVETALKING=1
for arg in "$@"; do
    case "$arg" in
        --no-livetalking) RUN_LIVETALKING=0 ;;
        --help|-h)
            sed -n '2,15p' "$0"; exit 0 ;;
        *) warn "未知参数：$arg" ;;
    esac
done

# ─── 工具检查 ────────────────────────────────────────────────────────────────
command -v conda >/dev/null || die "未找到 conda，请先 conda init。"
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME" || die "conda 环境 $ENV_NAME 不存在，请先运行 bootstrap.sh。"

[ -f "$ENV_FILE" ] || die "$ENV_FILE 不存在，请先 cp backend/.env.example backend/.env 并填写。"

# 自动加载 .env 到本进程环境（供 uvicorn / FastAPI 读取）
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

# ─── 子进程注册（用于退出时清理）────────────────────────────────────────────
BACKEND_PID=""
LT_PID=""
cleanup() {
    log "收到退出信号，正在关闭服务..."
    [ -n "$LT_PID"     ] && kill "$LT_PID"     2>/dev/null
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    wait 2>/dev/null || true
    ok "已退出"
}
trap cleanup INT TERM EXIT

# ─── 1) 启动后端（FastAPI / uvicorn）────────────────────────────────────────
log "启动 FastAPI 后端（端口 8000）..."
(
    cd "$BACKEND_DIR"
    exec python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
) &
BACKEND_PID=$!
ok "后端 PID=$BACKEND_PID"

# 等待后端就绪（最长 90 秒，首次须加载 embedding + whisper 模型）
log "等待后端就绪（最长 90 秒）..."
for i in $(seq 1 90); do
    if curl -fsS http://localhost:8000/ >/dev/null 2>&1; then
        ok "后端已就绪：http://localhost:8000"
        break
    fi
    sleep 1
    [ "$i" -eq 90 ] && { warn "后端 90 秒内未就绪，可能仍在加载模型。继续启动 LiveTalking。"; }
done

# ─── 2) 启动 LiveTalking 数字人（可选）──────────────────────────────────────
if [ "$RUN_LIVETALKING" -eq 1 ]; then
    LIVETALKING_DIR="$BACKEND_DIR/LiveTalking"
    if [ ! -d "$LIVETALKING_DIR" ] || [ ! -f "$LIVETALKING_DIR/service.py" ]; then
        warn "未找到 $LIVETALKING_DIR/service.py，跳过 LiveTalking。"
        warn "数字人功能将不可用（文本聊天正常）。"
    elif [ -z "$(ls -A "$LIVETALKING_DIR/models" 2>/dev/null)" ]; then
        warn "LiveTalking/models 目录为空，跳过启动。"
        warn "请把 wav2lip 等模型放入 backend/LiveTalking/models/ 之后重试。"
    else
        log "启动 LiveTalking 数字人服务（端口 8010）..."
        bash "$SCRIPT_DIR/start_livetalking.sh" &
        LT_PID=$!
        ok "LiveTalking PID=$LT_PID"
    fi
else
    warn "已通过 --no-livetalking 跳过数字人服务。"
fi

# ─── 3) 前台等待 ─────────────────────────────────────────────────────────────
log "服务已启动。Ctrl+C 退出并清理子进程。"
log "  后端 API 文档：http://localhost:8000/docs"
[ -n "$LT_PID" ] && log "  LiveTalking 状态：http://localhost:8010"

wait