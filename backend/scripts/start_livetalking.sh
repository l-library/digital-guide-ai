#!/bin/bash
# LiveTalking 数字人服务启动脚本
# 使用方法: bash backend/scripts/start_livetalking.sh [options]
#
# 前置条件:
#   1. conda activate DGA
#   2. export LLM_API_KEY=sk-xxx (如需 LLM)
#   3. 确保 backend/LiveTalking/models/ 下有嵌入模型文件
#
# 注意: 本脚本不会自动激活 conda 环境，请先手动激活。

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LIVETALKING_DIR="$PROJECT_DIR/backend/LiveTalking"

# 默认参数
MODEL="${MODEL:-wav2lip}"
TRANSPORT="${TRANSPORT:-webrtc}"
TTS="${TTS:-edgetts}"
AVATAR_ID="${AVATAR_ID:-wav2lip256_avatar1}"
WATERMARK="${WATERMARK:-景区导览AI数字人}"
MAX_SESSION="${MAX_SESSION:-3}"
LISTENPORT="${LISTENPORT:-8010}"

# HuggingFace 镜像（国内加速）
export HF_ENDPOINT="${HF_ENDPOINT:-https://hf-mirror.com}"

echo "========================================="
echo "  LiveTalking 数字人服务"
echo "========================================="
echo "  模型:     $MODEL"
echo "  传输:     $TRANSPORT"
echo "  TTS:      $TTS"
echo "  Avatar:   $AVATAR_ID"
echo "  水印:     $WATERMARK"
echo "  最大会话: $MAX_SESSION"
echo "  端口:     $LISTENPORT"
echo "========================================="

cd "$LIVETALKING_DIR"
python3 service.py \
  --model "$MODEL" \
  --transport "$TRANSPORT" \
  --tts "$TTS" \
  --avatar_id "$AVATAR_ID" \
  --watermark "$WATERMARK" \
  --max_session "$MAX_SESSION" \
  --listenport "$LISTENPORT"
