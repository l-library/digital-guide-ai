#!/usr/bin/env bash
# =============================================================================
# digital-guide-ai 后端一键引导脚本
#
# 作用：在新机器上拉起 digital-guide-ai 后端所需运行环境、模型与数据。
#
# 用法（在仓库根目录执行）：
#   bash backend/scripts/bootstrap.sh
#
# 完成后请：
#   1. cp backend/.env.example backend/.env  并填写密钥与路径
#   2.（如需数字人）将 LiveTalking 模型放到 backend/LiveTalking/models/
#   3. bash backend/scripts/run.sh 启动服务
#
# 前置条件：
#   - 已安装 conda 并能在 shell 中执行 conda 命令
#   - 已安装 NVIDIA 显卡驱动 + CUDA 13.x（仅数字人/Whisper 需要 GPU）
#   - 已安装 ffmpeg 且在 PATH 中（ASR / TTS 流水线依赖，非 Python 包）
#   - 可访问 https://hf-mirror.com 与 https://download.pytorch.org
# =============================================================================
set -euo pipefail

# ─── 路径常量 ────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$BACKEND_DIR/.." && pwd)"
ENV_NAME="DGA"
REQ_FILE="$BACKEND_DIR/requirements.txt"
ENV_YML="$BACKEND_DIR/environment.yml"
ENV_FILE="$BACKEND_DIR/.env"
ENV_EXAMPLE="$BACKEND_DIR/.env.example"

# ─── 颜色输出 ────────────────────────────────────────────────────────────────
c_red=$'\033[31m';   c_grn=$'\033[32m';  c_yel=$'\033[33m'
c_blu=$'\033[34m';   c_end=$'\033[0m'
log()  { printf "${c_blu}[bootstrap]${c_end} %s\n" "$*"; }
warn() { printf "${c_yel}[warn]${c_end} %s\n" "$*"; }
ok()   { printf "${c_grn}[ok]${c_end} %s\n" "$*"; }
die()  { printf "${c_red}[fatal]${c_end} %s\n" "$*" >&2; exit 1; }

# ─── 工具检查 ────────────────────────────────────────────────────────────────
command -v conda >/dev/null || die "未找到 conda，请先安装 Anaconda/Miniconda 并初始化 (conda init)。"

# 非交互模式下确保 conda 可用
if [ -z "${CONDA_EXE:-}" ]; then
    # shellcheck disable=SC1091
    for c in "$HOME/anaconda3/etc/profile.d/conda.sh" \
             "$HOME/miniconda3/etc/profile.d/conda.sh" \
             "/opt/conda/etc/profile.d/conda.sh"; do
        [ -f "$c" ] && source "$c" && break
    done
fi
[ -z "${CONDA_EXE:-}" ] && die "无法定位 conda.sh，请手动 conda init 后重开 shell 再运行。"

# ─── 第 1 步：创建/确认 conda 环境 DGA ───────────────────────────────────────
log "步骤 1/7：创建 conda 环境 $ENV_NAME"
if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    ok "conda 环境 $ENV_NAME 已存在，跳过创建。"
else
    conda env create -f "$ENV_YML" || die "创建 conda 环境失败。"
    ok "已创建 conda 环境 $ENV_NAME"
fi
# shellcheck disable=SC1091
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate "$ENV_NAME"
ok "已进入 conda 环境：$(python --version 2>&1)"
python -c 'import sys; sys.exit(0 if "3.10" in sys.version else 1)' \
    || die "Python 不是 3.10.x，请检查 environment.yml 安装结果。"

# ─── 第 2 步：安装 PyTorch（GPU/CPU 自动选择）──────────────────────────────
log "步骤 2/7：安装 PyTorch"
if python -c "import torch; assert torch.__version__.startswith('2.11')" 2>/dev/null; then
    ok "torch 2.11 已安装：$(python -c 'import torch;print(torch.__version__)')"
else
    # 检测 NVIDIA 驱动
    if command -v nvidia-smi >/dev/null && nvidia-smi >/dev/null 2>&1; then
        log "检测到 NVIDIA GPU，安装 cu130 版本 torch ..."
        pip install --no-cache-dir torch==2.11.0 torchaudio==2.11.0 \
            --index-url https://download.pytorch.org/whl/cu130 \
            || die "torch cu130 安装失败，请检查网络或换用 CPU 版本（见脚本第 90 行附近）。"
    else
        warn "未检测到 NVIDIA GPU，安装 CPU 版本 torch（性能受限，数字人/Whisper 不可用）。"
        pip install --no-cache-dir torch==2.11.0 torchaudio==2.11.0 \
            --index-url https://download.pytorch.org/whl/cpu \
            || die "torch CPU 版本安装失败。"
    fi
    ok "torch 安装完成：$(python -c 'import torch;print(torch.__version__)')"
fi

# ─── 第 3 步：安装其余依赖 ───────────────────────────────────────────────────
log "步骤 3/7：安装 requirements.txt"
pip install --no-cache-dir -r "$REQ_FILE" \
    || die "requirements.txt 安装失败，请查看上面的报错信息。"
ok "Python 依赖安装完成"

# ─── 3.5：检查 ffmpeg（ASR / TTS 通过 subprocess 调用，非 pip 包）─────────
if command -v ffmpeg >/dev/null 2>&1; then
    ok "ffmpeg 已在 PATH：$(ffmpeg -version 2>&1 | head -1)"
else
    warn "未检测到 ffmpeg。ASR / TTS 流水线依赖它，请通过以下任一方式安装："
    warn "  conda install -c conda-forge ffmpeg     # 推荐在 DGA 环境里装"
    warn "  sudo apt-get install ffmpeg            # Debian/Ubuntu"
    warn "  sudo dnf install ffmpeg                # Fedora/RHEL"
fi

# ─── 第 4 步：克隆并安装 CosyVoice（TTS，仅语音导览需要）─────────────────────
log "步骤 4/8：检查 CosyVoice"
COSYVOICE_DIR="${COSYVOICE_DIR:-$HOME/CosyVoice}"
if [ -d "$COSYVOICE_DIR" ] && [ -f "$COSYVOICE_DIR/setup.py" ]; then
    ok "已存在 CosyVoice 目录：$COSYVOICE_DIR"
else
    warn "CosyVoice 不存在：$COSYVOICE_DIR"
    read -r -p "是否克隆并安装 CosyVoice？（数字人语音需要，[y/N]）" ans
    if [[ "${ans:-N}" =~ ^[Yy]$ ]]; then
        git clone https://github.com/FunAudioLLM/CosyVoice.git "$COSYVOICE_DIR" \
            || die "克隆 CosyVoice 失败。"
        git -C "$COSYVOICE_DIR" submodule update --init --recursive \
            || warn "CosyVoice 子模块初始化失败，请稍后手动执行。"
        pip install --no-cache-dir -e "$COSYVOICE_DIR" \
            || die "pip install -e CosyVoice 失败。"
        pip install --no-cache-dir -e "$COSYVOICE_DIR/third_party/Matcha-TTS" \
            || die "Matcha-TTS 安装失败。"
        ok "CosyVoice 安装完成：$COSYVOICE_DIR"
        warn "还需手动下载 CosyVoice-300M-SFT 模型到 $COSYVOICE_DIR/pretrained_models/"
    else
        warn "跳过 CosyVoice。后端能启动，但 chat_voice 的 TTS 部分会不可用。"
    fi
fi

# ─── 第 5 步：检查 LiveTalking 数字人依赖与模型 ───────────────────────────────
log "步骤 5/8：检查 LiveTalking 数字人"
LIVETALKING_DIR="$BACKEND_DIR/LiveTalking"
LT_MODELS_DIR="$LIVETALKING_DIR/models"
if [ ! -d "$LIVETALKING_DIR" ] || [ ! -f "$LIVETALKING_DIR/service.py" ]; then
    warn "未找到 $LIVETALKING_DIR/service.py，跳过 LiveTalking 检查。"
    warn "数字人功能不可用（文本聊天正常）。"
else
    # 5.1 运行时依赖：经 AST 扫描，wav2lip + edgetts + webrtc 模式所需
    #     第三方包都已包含在主 backend/requirements.txt 中，无需额外安装。
    #     此处仅运行 import 完整性验证，不重复 pip install。
    log "LiveTalking 运行时依赖已包含在主 backend/requirements.txt，进行 import 验证..."
    if python "$SCRIPT_DIR/verify_integration.py" >/tmp/lt_verify.log 2>&1; then
        ok "LiveTalking import 完整性验证通过"
    else
        warn "LiveTalking import 验证失败，详见 /tmp/lt_verify.log"
        warn "如仅用文本聊天可忽略；若需数字人请按主 requirements.txt 补齐依赖。"
    fi
    # 5.2 模型文件存在性检查
    if [ -n "$(ls -A "$LT_MODELS_DIR" 2>/dev/null)" ]; then
        ok "LiveTalking 模型目录已就绪：$LT_MODELS_DIR"
        ls -1 "$LT_MODELS_DIR" | sed 's/^/    - /' | head -10
    else
        warn "LiveTalking/models 目录为空，数字人无法启动。"
        warn "请将 wav2lip 等模型（约 2.6 GB）放入：$LT_MODELS_DIR/"
        warn "提示：LiveTalking/requirements.txt 含训练/GUI 包，已在主 requirements 中涵盖"
        warn "     运行时子集；不要直接 pip install -r LiveTalking/requirements.txt"
        warn "     （会引入 opencv-python 覆盖 headless 版、typeguard 旧版固定等冲突）。"
    fi
fi

# ─── 第 6 步：下载 bge-small-zh-v1.5 嵌入模型 ────────────────────────────────
log "步骤 6/8：检查 bge 嵌入模型"
BGE_DIR="$BACKEND_DIR/models/bge-small-zh-v1.5"
if [ -d "$BGE_DIR" ] && [ -n "$(ls -A "$BGE_DIR" 2>/dev/null)" ]; then
    ok "bge 模型已存在：$BGE_DIR"
else
    log "正在下载 bge-small-zh-v1.5（约 100 MB，来源 hf-mirror）..."
    python "$SCRIPT_DIR/download_model.py" \
        || die "下载 bge 模型失败，请检查 https://hf-mirror.com 是否可访问。"
    ok "bge 模型下载完成"
fi

# ─── 第 7 步：重建向量库（如缺失）────────────────────────────────────────────
log "步骤 7/8：检查景区向量库"
LISHAN_STORE="$BACKEND_DIR/vector_store/lingshan"
DOCX_FILE="$BACKEND_DIR/data/灵山胜境：历史、文化、景点特色与个性化游览指南.docx"
if [ -d "$LISHAN_STORE" ] && [ -f "$LISHAN_STORE/chroma.sqlite3" ]; then
    ok "景区向量库已存在：$LISHAN_STORE"
else
    if [ ! -f "$DOCX_FILE" ]; then
        warn "未找到源文档：$DOCX_FILE"
        warn "向量库无法自动重建。请从原作者处获取 Word 资料放入 backend/data/，"
        warn "之后手动执行：cd backend/scripts && python ingest_guide.py"
    else
        log "正在重建景区向量库（ingest_guide.py）..."
        # ingest_guide.py 使用相对 ../data ../vector_store 路径，必须在 scripts/ 下运行
        (
            cd "$SCRIPT_DIR"
            python ingest_guide.py \
                || die "ingest_guide.py 失败，请查看错误输出。"
        )
        ok "向量库重建完成"
    fi
fi

# ─── 第 8 步：生成 .env 提示 ──────────────────────────────────────────────────
log "步骤 8/8：检查 .env 配置"
if [ -f "$ENV_FILE" ]; then
    ok "已存在 backend/.env"
else
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn "已从模板生成 backend/.env，请打开 $ENV_FILE 填写以下必填项："
    warn "  - LLM_API_KEY / LLM_BASE_URL / LLM_MODEL_NAME"
    warn "  - JWT_SECRET_KEY（可用：openssl rand -hex 32 生成）"
    warn "  - 如需数字人/TTS：COSYVOICE_DIR / COSYVOICE_MODEL_DIR / COSYVOICE_MATCHA_DIR"
    warn "  - 如需数字人：把 LiveTalking 模型放到 backend/LiveTalking/models/"
fi

# ─── 总结 ────────────────────────────────────────────────────────────────────
echo ""
ok "引导完成。接下来的步骤："
echo "  1. 编辑 $ENV_FILE 填写真实密钥与 CosyVoice 路径"
echo "  2.（如需数字人）将 wav2lip 等模型放到 $BACKEND_DIR/LiveTalking/models/"
echo "  3. 启动服务：bash $SCRIPT_DIR/run.sh"
echo ""
warn "如跳过了 CosyVoice，文本聊天不受影响，但语音 + 数字人功能不可用。"