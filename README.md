# 景区导览服务 AI 数字人

基于 AI 数字人技术的智能景区导览系统，为游客提供 7×24 小时在线的智能导游服务，同时为景区管理方提供完整的数据分析与用户管理后台。

## 项目概述

本项目针对景区传统导览服务的痛点（导游资源稀缺、无法互动、管理盲区），构建具备多模态交互能力的 AI 数字人导游系统。

### 核心能力

- **多模态交互**：支持语音输入（ASR → 中文语音识别）和文本输入，数字人以视频帧 + 口型同步 + 逐句语音的方式回答
- **智能问答**：基于 RAG 技术（双通道 Chroma 向量检索 + 意图识别），准确回答景区历史、文化、景点特色等常见问题
- **流式对话**：支持 WebSocket 和 HTTP SSE 双通道的流式回复（打字机效果），多轮对话上下文记忆，首轮对话自动标题生成
- **个性化推荐**：LLM 自动推断游客兴趣标签（基于近期对话），结合 RAG 生成个性化游览路线推荐
- **管理后台**：用户管理（CRUD + 启用/禁用）、知识库文档上传与管理、数据大屏（实时服务统计 + 热门问题 + 满意度趋势 Canvas 图表）、游客感受度分析报告（情感趋势 + 关注点分析 + LLM 改进建议）

### 技术架构

```
前端 (Qt6 + QML)
    └── C++ 模块：ApiService、LoginManager、ConversationManager、VoiceInterface、
                  LiveTalkingClient、HistoryManager、DashboardManager、ReportManager 等
    └── QML 页面：Login、Chat、History、Settings、Admin（Dashboard/Report/用户管理）

后端 (Python + FastAPI 异步)
    └── API 层（48+ HTTP 端点 + 1 WebSocket）
    └── 服务层（15 个模块）：
        RAG 服务（Chroma 双通道向量检索 + 意图识别）
        LLM 服务（DeepSeek V4 flash，同步+异步+流式）
        ASR 服务（Whisper Base 中文识别，含领域提示词增强）
        TTS 服务（CosyVoice-300M-SFT + 流式分句合成管道）
        数字人集成（LiveTalking HTTP 客户端 + 会话映射 + 逐句音频推送 + 预推送队列）
        认证服务（bcrypt + JWT HS256 7天 + token_version 即时失效）
        管理员服务（用户 CRUD + 级联删除 + Chroma 向量清理）
        数据大屏服务（SQL 聚合统计 + 满意度关键词启发式分析）
        报告服务（情感分析 + 关注点分类 + LLM 服务建议生成）
        推荐服务（LLM 兴趣推断 + RAG 路线推荐 + 冷启动兜底）
        知识库管理（MarkItDown 文档解析 + LangChain 分块 + Chroma 向量化）
    └── 数据库：SQLite（用户/对话/消息/文档/推荐日志）+ Chroma（向量持久化）

通信：HTTP REST + HTTP SSE + WebSocket
```

## 技术栈

| 层级         | 技术                                      |
| ------------ | ----------------------------------------- |
| 前端框架     | Qt 6.10+ / C++ / QML                      |
| Qt 模块      | Quick、QuickControls2、Network、WebSockets、Multimedia |
| 后端框架     | Python / FastAPI (异步)                   |
| 向量数据库   | Chroma（父子文档结构）                    |
| 嵌入模型     | BAAI/bge-small-zh-v1.5                    |
| 大模型       | DeepSeek V4 flash (兼容 OpenAI API)       |
| 语音识别     | OpenAI Whisper Base (CPU)                 |
| 语音合成     | CosyVoice-300M-SFT (GPU)                  |
| 数字人引擎   | LiveTalking (wav2lip + Edge TTS)          |
| 关系数据库   | SQLite                                    |

## 开发环境
Ubuntu 24.04 LTS
Linux kernel 6.8.0-134-generic
CUDA 13.0
Cmake version 4.3.4
Python 3.10.20

## 后端部署与启动

后端是 Python + FastAPI 应用，依赖 GPU（NVIDIA + CUDA 13.x）以及若干模型文件。仓库已附引导脚本和启动脚本，按下面三步即可拉起。

### 前置条件

- 已安装 [Anaconda / Miniconda](https://docs.conda.io/) 并完成 `conda init`
- 已安装 NVIDIA 显卡驱动，且支持 CUDA 13.x（仅文本聊天可放宽到 CPU，但语音 / 数字人 / Whisper 必须有 GPU）
- 已安装 **ffmpeg** 且可在 PATH 中调用（ASR / TTS 流水线依赖，非 Python 包）。推荐：`conda install -c conda-forge ffmpeg`
- 可访问 `https://hf-mirror.com`（下载嵌入模型）与 `https://download.pytorch.org`
- 已准备好以下两类「外部资产」（仓库不包含，体积过大）：
  - **CosyVoice 仓库与预训练模型**（TTS 用，可选）
  - **LiveTalking 模型**（数字人用，可选）—— 放到 `backend/LiveTalking/models/`（约 2.6 GB，含 wav2lip 权重）

> LiveTalking 运行时（wav2lip + Edge TTS + WebRTC 模式）的 Python 依赖已**并入 `backend/requirements.txt`**，无需单独再装 `LiveTalking/requirements.txt`。后者保留为 LiveTalking 上游训练/GUI 用清单（含 `opencv-python`、`dearpygui`、`flask`、`trimesh` 等），直接装会引入版本冲突（`opencv-python` 覆盖 `headless`、`typeguard==2.13.3` 旧版固定破坏其他包）。具体运行时子集详见 `backend/LiveTalking/requirements-runtime.txt`。

### 第 1 步：一键引导（首次部署）

在仓库根目录执行：

```bash
bash backend/scripts/bootstrap.sh
```

脚本会自动完成（8 步）：

1. 创建 conda 环境 `DGA`（Python 3.10）
2. 安装 PyTorch（自动识别 GPU / CPU 选择 cu130 或 cpu 版本）
3. `pip install -r backend/requirements.txt` 安装其余依赖（含 ffmpeg 存在性检查）
4. 交互式询问是否克隆并安装 CosyVoice
5. 检查 LiveTalking：跑 `verify_integration.py` 验证 import 完整性，并检查 `LiveTalking/models/` 是否为空
6. 下载 `bge-small-zh-v1.5` 嵌入模型到 `backend/models/`
7. 检测景区向量库，缺失时若源 `.docx` 在位则自动跑 `ingest_guide.py` 重建
8. 从模板生成 `backend/.env`（若尚未存在）

> CosyVoice 仓库克隆后，还需手动下载 `CosyVoice-300M-SFT` 预训练模型放到 `COSYVOICE_DIR/pretrained_models/`。

### 第 2 步：配置环境变量

编辑 `backend/.env`（首次会从 `backend/.env.example` 复制而来），填写：

| 变量 | 是否必填 | 说明 |
| --- | --- | --- |
| `LLM_API_KEY` | 必填 | DeepSeek API 密钥 |
| `LLM_BASE_URL` | 必填 | 默认 `https://api.deepseek.com` |
| `LLM_MODEL_NAME` | 必填 | 默认 `deepseek-v4-flash` |
| `JWT_SECRET_KEY` | 必填 | JWT 签名密钥，可用 `openssl rand -hex 32` 生成 |
| `COSYVOICE_DIR` / `COSYVOICE_MODEL_DIR` / `COSYVOICE_MATCHA_DIR` | TTS 必填 | CosyVoice 仓库与模型路径 |
| `LIVETALKING_BASE_URL` | 数字人必填 | 默认 `http://localhost:8010` |
| `TTS_SPEAKER` | 可选 | 默认 `中文女` |
| `LOG_LEVEL` | 可选 | 默认 `INFO` |
| `HF_ENDPOINT` | 可选 | 默认 `https://hf-mirror.com` |

### 第 3 步：启动服务

```bash
# 同时启动后端（8000）与 LiveTalking 数字人（8010）
bash backend/scripts/run.sh

# 仅启动后端，跳过数字人
bash backend/scripts/run.sh --no-livetalking
```

启动后：

- 后端 API 文档：`http://localhost:8000/docs`
- LiveTalking 状态：`http://localhost:8010`
- 退出用 `Ctrl+C`，会自动清理子进程

### 手动启动（替代脚本）

如不想用脚本，也可分步操作：

```bash
conda activate DGA
export $(grep -v '^#' backend/.env | xargs)   # 加载环境变量
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 数字人另开一个终端：
conda activate DGA
bash backend/scripts/start_livetalking.sh
```

### 关键脚本说明

| 脚本 | 作用 |
| --- | --- |
| `backend/scripts/bootstrap.sh` | 首次部署引导，建立 conda 环境并下载依赖与模型 |
| `backend/scripts/run.sh` | 日常启动，编排后端 + 数字人两个进程 |
| `backend/scripts/start_livetalking.sh` | 单独启动 LiveTalking 数字人服务 |
| `backend/scripts/download_model.py` | 下载 bge 嵌入模型 |
| `backend/scripts/ingest_guide.py` | 从 Word 文档重建景区向量库（须在 `backend/scripts/` 目录下运行） |
| `backend/scripts/init_db.py` | 初始化 SQLite 数据库表结构 |
| `backend/scripts/verify_integration.py` | LiveTalking import 完整性 + 代码一致性的只读检查（gpu 不会启动） |
| `backend/LiveTalking/requirements-runtime.txt` | LiveTalking 运行时精简依赖清单（已在主 requirements 中涵盖） |

## 前端构建

```bash
cd frontend && mkdir -p build && cd build
cmake ..
cmake --build .
```

构建产物位于 `frontend/build/`，运行前请在 `SettingsPage` 里填写后端地址。

## 开发进度

详见 [PLAN.md](PLAN.md)（8 周冲刺计划全部完成）。

### 已实现功能清单

**游客端：**
- [x] 文本问答（HTTP SSE 流式 + WebSocket 实时 + 非流式）
- [x] 语音问答（录音 → 上传 → ASR 识别 → 流式回复）
- [x] 数字人视频渲染（LiveTalking WebSocket → QImage 帧解码）
- [x] 逐句口型同步（TTS 流水线 → LiveTalking 音频推送 + 预推送队列）
- [x] 多轮对话上下文记忆 + 首轮自动标题生成
- [x] 个性化路线推荐（LLM 兴趣推断 + RAG 推荐 + 冷启动兜底）
- [x] 对话管理（新建/列表/重命名/删除/搜索/按日期分组）

**用户系统：**
- [x] 注册/登录（JWT 7天 + "记住我"自动登录）
- [x] 角色区分（visitor / admin）
- [x] 个人资料编辑（昵称、头像、密码修改）
- [x] token_version 机制（管理员禁用用户后旧 Token 即时失效）

**管理员后台：**
- [x] 用户管理（分页列表 + 搜索 + CRUD + 启用/禁用）
- [x] 知识库管理（文档上传 → MarkItDown 解析 → Chroma 向量化 → 删除）
- [x] 数据大屏（概览指标 + 服务趋势折线图 + 热门问答 + 满意度趋势 + 30s 自动刷新）
- [x] 游客感受度报告（日期范围查询 + 情感趋势 + 关注点分析 + LLM 服务建议）
- [x] 级联删除（用户 → 对话 → 消息 → Chroma 向量自动清理）

### 已知限制

- ASR 硬编码 CPU 运行（未使用 GPU 加速）
