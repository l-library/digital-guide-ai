# 景区导览服务AI数字人 — 产品部署和使用手册

> 版本：v1.0  
> 最后更新：2026年7月  
> 适用对象：运维人员、系统管理员、终端用户

---

## 一、系统环境要求

### 1.1 服务器端（后端 + 数字人引擎）

| 项目 | 推荐配置 | 说明 |
|------|---------|------|
| **操作系统** | Ubuntu 24.04 LTS | 开发和测试均在此环境进行 |
| **CPU** | 8 核以上 | ASR（Whisper）推理为 CPU 密集型 |
| **GPU** | NVIDIA RTX 3060 或更高，显存 ≥ 8GB | CosyVoice TTS 和 wav2lip 数字人均依赖 GPU |
| **CUDA** | 13.x | 与 PyTorch cu130 版本匹配 |
| **内存** | 32GB | 同时加载多个 AI 模型（BGE + Whisper + CosyVoice） |
| **磁盘** | 50GB 以上可用空间 | 模型文件约 5GB，另需预留音频文件和向量库空间 |
| **网络** | 可访问 api.deepseek.com | LLM API 调用 |
| **网络** | 可访问 hf-mirror.com | 首次部署下载嵌入模型 |
| **软件** | Anaconda / Miniconda | 虚拟环境管理 |
| **软件** | ffmpeg | ASR/TTS 音频流水线依赖 |

### 1.2 客户端（游客终端 / 管理端）

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 10+ / Ubuntu 22.04+ / macOS 12+ |
| **Qt 运行时** | Qt 6.10+ |
| **网络** | 能访问后端服务器的 8000 和 8010 端口 |

> 客户端为桌面应用程序。如果要在 Windows 上分发，需确保目标机器已安装 Qt 6.10 运行时，或用静态链接打包。

---

## 二、快速开始：第一次部署就上手

整个部署流程从零开始大约需要 30-60 分钟（取决于网络速度和 GPU 型号）。下面每一步都有详细说明，按顺序执行即可。

### 2.0 前置检查

在开始之前，确认以下四项：

```bash
# 1. conda 可用
conda --version

# 2. NVIDIA 驱动正常，CUDA 可用
nvidia-smi

# 3. ffmpeg 已安装（如果没有，稍后 bootstrap 脚本会提醒你）
ffmpeg -version

# 4. 确认磁盘空间足够（至少 50GB）
df -h
```

### 2.1 克隆仓库并进入目录

```bash
git clone <仓库地址> digital-guide-ai
cd digital-guide-ai
```

### 2.2 一键引导安装

在仓库根目录执行：

```bash
bash backend/scripts/bootstrap.sh
```

这个脚本会自动完成以下 8 件事：

1. **创建 conda 虚拟环境** `DGA`（Python 3.10）
2. **安装 PyTorch**（自动检测 GPU 型号，选择 cu130 或 CPU 版本）
3. **安装 Python 依赖** `pip install -r backend/requirements.txt`
4. **交互式询问**是否克隆并安装 CosyVoice 仓库（TTS 依赖，建议选 yes）
5. **检查 LiveTalking**：验证 Python import 完整性，检查模型文件是否就位
6. **下载嵌入模型** `bge-small-zh-v1.5` 到 `backend/models/`
7. **构建向量库**：如果检测到源文档（.docx），自动运行 `ingest_guide.py` 生成向量数据
8. **生成配置文件**：从 `backend/.env.example` 复制模板到 `backend/.env`

> **注意**：如果步骤 4 选择了安装 CosyVoice，还需手动下载 `CosyVoice-300M-SFT` 预训练模型放到指定目录。详见 [2.4 TTS 模型配置](#24-tts-模型配置)。

### 2.3 配置环境变量

编辑 `backend/.env` 文件：

```bash
nano backend/.env
```

需要填写的内容如下：

```bash
# ─── LLM（必填）─────────────────────────────────
LLM_API_KEY=sk-你的DeepSeek密钥
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-v4-flash

# ─── JWT 密钥（必填，用 openssl rand -hex 32 生成）───
JWT_SECRET_KEY=你生成的随机字符串至少32位

# ─── CosyVoice TTS（使用 TTS 和语音功能时必填）────
COSYVOICE_DIR=/home/你的用户名/CosyVoice
COSYVOICE_MATCHA_DIR=/home/你的用户名/CosyVoice/third_party/Matcha-TTS
COSYVOICE_MODEL_DIR=/home/你的用户名/CosyVoice/pretrained_models/CosyVoice-300M-SFT

# ─── LiveTalking 数字人（使用数字人时必填）────────
LIVETALKING_BASE_URL=http://localhost:8010

# ─── 可选配置 ──────────────────────────────────
TTS_SPEAKER=中文女       # 默认音色
LOG_LEVEL=INFO           # DEBUG/INFO/WARNING/ERROR
HF_ENDPOINT=https://hf-mirror.com  # 国内加速
```

> **JWT_SECRET_KEY 生成方法**：执行 `openssl rand -hex 32`，将输出粘贴为密钥。

### 2.4 TTS 模型配置

CosyVoice 需要两步才能工作：先 clone 仓库，再下载模型文件。

**第 1 步：clone 仓库**

如果 bootstrap 时跳过了 CosyVoice 安装，可以手动补装：

```bash
git clone https://github.com/FunAudioLLM/CosyVoice.git /home/你的用户名/CosyVoice
cd /home/你的用户名/CosyVoice
git submodule update --init --recursive
pip install -e .
```

**第 2 步：下载预训练模型**

从 HuggingFace 下载 `CosyVoice-300M-SFT` 模型：

```bash
# 方法一：使用 huggingface-cli（推荐）
pip install huggingface_hub
huggingface-cli download FunAudioLLM/CosyVoice-300M-SFT \
  --local-dir /home/你的用户名/CosyVoice/pretrained_models/CosyVoice-300M-SFT

# 方法二：如果国内直接下载慢，设置镜像
export HF_ENDPOINT=https://hf-mirror.com
huggingface-cli download FunAudioLLM/CosyVoice-300M-SFT \
  --local-dir /home/你的用户名/CosyVoice/pretrained_models/CosyVoice-300M-SFT
```

### 2.5 LiveTalking 数字人模型配置

数字人依赖 wav2lip 模型权重文件，总计约 2.6 GB。将模型文件放到以下目录：

```bash
backend/LiveTalking/models/
├── wav2lip_gan.pth          # wav2lip 主模型
├── s3fd.pth                 # 人脸检测模型
└── ... (其他模型文件)
```

> 模型文件不在仓库中（体积过大），请从 LiveTalking 项目官方获取。

### 2.6 启动服务

一切就绪后，用一条命令启动后端和数字人：

```bash
# 同时启动后端（8000）和数字人引擎（8010）
bash backend/scripts/run.sh

# 如果不需要数字人功能（纯文本问答），可以跳过数字人
bash backend/scripts/run.sh --no-livetalking
```

启动成功后你应该看到类似输出：

```
INFO:     Started server process
INFO:     正在初始化数据库...
INFO:     数据库就绪。
INFO:     正在预热RAG服务，加载embedding模型...
INFO:     预热完成，服务就绪。
INFO:     正在预热ASR服务，加载Whisper模型...
INFO:     ASR服务就绪。
INFO:     正在预热TTS服务，加载CosyVoice模型...
INFO:     CosyVoice 模型加载完成
INFO:     Application startup complete.
```

验证服务是否正常：

```bash
# 检查后端
curl http://localhost:8000/
# 应该返回: {"status":"ok","message":"数字人服务已成功启动，模型已就绪!"}

# 检查 API 文档
# 浏览器打开: http://localhost:8000/docs
```

停止服务：在启动终端按 `Ctrl+C`，脚本会自动清理所有子进程。

---

## 三、前端构建与运行

### 3.1 安装 Qt 6.10+

前端需要 Qt 6.10 或更高版本。推荐通过 Qt 官方在线安装器安装，或使用系统包管理器：

```bash
# Ubuntu 上使用 apt（如果仓库版本够新）
sudo apt install qt6-base-dev qt6-declarative-dev qt6-multimedia-dev \
  qt6-websockets-dev qt6-quick3d-dev qt6-quickeffects-dev

# 或者下载 Qt 在线安装器
# https://www.qt.io/download-qt-installer
```

### 3.2 编译

```bash
cd frontend
mkdir -p build && cd build
cmake ..
cmake --build .
```

编译成功后，可执行文件位于 `frontend/build/appdigital_guide_ai`。

### 3.3 配置前端连接地址

首次启动前，编辑 `frontend/config.json`：

```json
{
    "backend": {
        "ip": "http://你的服务器IP",
        "port": 8000
    },
    "livetalking": {
        "host": "http://你的服务器IP",
        "port": 8010
    }
}
```

如果前端与后端在同一台机器上，保持 `localhost` 即可。

### 3.4 运行

```bash
cd frontend/build
./appdigital_guide_ai
```

也可以在应用内的设置页面（SettingsPage）中修改后端地址，无需重新编译。

---

## 四、游客端使用指南

### 4.1 注册和登录

1. 打开应用，进入登录页面
2. 首次使用点击「注册」：
   - 输入用户名（3-32 位，字母数字下划线）
   - 输入密码（6-64 位）
   - 输入昵称（显示名称）
3. 注册成功自动登录
4. 勾选「记住我」可以在 7 天内免登录

### 4.2 开始对话

登录后进入聊天页面（ChatPage），这是游客的主要交互界面。

**文字提问**：
1. 在底部输入框输入问题，例如"灵山胜境有哪些主要景点？"
2. 按回车发送
3. 数字人开始讲解，文字以打字机效果逐字出现
4. 如果启用了语音回复，每说完一句话，数字人的口型会同步变化

**语音提问**：
1. 点击麦克风按钮开始录音
2. 说出你的问题
3. 再次点击麦克风停止录音
4. 等待语音识别完成（约 1-3 秒）
5. 数字人开始回复

### 4.3 对话管理

- **新建对话**：点击左上角"+"按钮
- **查看历史**：切换到历史页面（HistoryPage），查看所有对话
- **搜索对话**：在历史页面顶部搜索框输入关键词
- **重命名对话**：长按/右键对话标题 → 重命名
- **删除对话**：长按/右键对话 → 删除

> 首轮对话会自动根据内容生成标题，无需手动命名。

### 4.4 个性化路线推荐

1. 在聊天页面点击"推荐路线"按钮
2. 系统会分析你最近的对话内容，判断你的兴趣偏好
3. 返回一条个性化的游览路线推荐，包含：
   - 路线名称和建议时长
   - 途经景点列表和每站建议停留时间
   - 路线亮点
   - 推荐理由（为什么适合你）

> 如果你是新用户，还没有对话记录，系统会给出通用热门路线推荐。

### 4.5 设置

在设置页面（SettingsPage）可以：
- 修改昵称和头像
- 修改密码
- 配置后端服务器地址
- 查看当前登录状态

---

## 五、管理端使用指南

> 管理端功能仅对角色为 `admin` 的用户开放。默认管理员账号在首次启动时自动创建。

### 5.1 进入管理后台

登录 admin 账号后，在导航栏会看到「管理」入口，点击进入 AdminPage。

### 5.2 数据大屏（Dashboard）

数据大屏是管理端的默认页面，展示景区 AI 服务的实时运营数据：

- **核心指标卡片**：今日服务次数、今日服务游客数、本周服务总量、知识文档数等
- **服务趋势图**：可选择按日/周/月查看服务量的变化曲线
- **热门问答排行**：游客问得最多的问题 TOP 10，带上升/下降/平稳趋势标记
- **满意度趋势**：游客情感评分的变化曲线
- **自动刷新**：每 30 秒自动更新数据

### 5.3 游客感受度报告（Report）

在报告页面，选择日期范围后点击查询，可以看到：

- **游客洞察**：统计时间段内的游客总数、对话总数、活跃时段分布、兴趣偏好排名、平均对话长度
- **情感趋势**：正面/中性/负面情绪的占比变化曲线 + LLM 自动生成的情感总结（如"游客整体情感以积极为主，负面情绪集中在排队等候问题"）
- **关注点分析**：游客最关心的主题分类和占比（如"门票与开放时间""历史文化""餐饮推荐"等）
- **服务建议**：LLM 根据对话数据自动生成的 3-5 条改进建议（如"游客频繁询问卫生间位置，建议在景区入口及主要节点增加导引标识"），每条建议标注优先级（高/中/低）

### 5.4 知识库管理

在 AdminPage 中的知识库管理区域：

**上传知识文档**：
1. 点击「上传文档」
2. 选择文件（支持 .docx / .pdf / .txt / .md，最大 50MB）
3. 填写文档标题
4. 点击确认上传
5. 文档状态显示为「处理中」，系统自动在后台解析文本、分块、向量化
6. 变成「就绪」状态后，该文档的内容即可被 RAG 检索到

**查看文档列表**：列表显示所有知识文档，含标题、类型、状态、分块数、上传时间

**重新处理**：如果文档处理失败，可以点击「重新处理」重试

**删除文档**：删除文档会同时清除文件、数据库记录和 Chroma 向量数据

### 5.5 用户管理

- **用户列表**：分页展示所有注册用户，支持按用户名/昵称搜索
- **创建用户**：管理员可以手动创建游客账号
- **编辑用户**：修改昵称、手机号、邮箱等资料
- **禁用/启用用户**：禁用后该用户所有已签发 Token 立即失效，无法登录
- **删除用户**：级联删除——同时清除该用户的对话、消息和 Chroma 向量数据

> 默认超级管理员（id=1）不能被删除或禁用。

### 5.6 消费分析（Consumption）

展示景区游客消费数据的统计分析，辅助运营决策。

---

## 六、日常维护操作

### 6.1 启动和停止

```bash
# 启动服务（包含后端 + 数字人）
bash backend/scripts/run.sh

# 仅启动后端
bash backend/scripts/run.sh --no-livetalking

# 停止：Ctrl+C
```

### 6.2 更新知识库

你有三种方式更新知识库：

**方式一：通过管理端上传（推荐）**

在管理后台 → 知识库管理 → 上传文档。系统自动完成解析和向量化。

**方式二：替换源文档后重建**

1. 将新的 `.docx` 文件放到 `backend/scripts/` 目录
2. 编辑 `backend/scripts/config_guide.py`，更新文件路径和 Chroma collection 配置
3. 进入 conda 环境，运行重建脚本：

```bash
conda activate DGA
cd backend/scripts
python ingest_guide.py
```

**方式三：通过管理端 API 触发重新处理**

如果之前的文档处理失败，可以通过管理端或 API 重新触发。

### 6.3 查看日志

服务端日志直接输出在启动终端中。如需更详细的调试信息，可以在 `.env` 中设置：

```bash
LOG_LEVEL=DEBUG
```

然后重启服务。

### 6.4 数据库备份

SQLite 数据库文件位于 `backend/data/app.db`。备份只需复制这个文件：

```bash
cp backend/data/app.db backend/data/app.db.backup.$(date +%Y%m%d)
```

Chroma 向量库位于 `backend/vector_store/`，同样可以整体复制备份：

```bash
cp -r backend/vector_store/ backend/vector_store.backup.$(date +%Y%m%d)/
```

### 6.5 模型更新

- **嵌入模型**：替换 `backend/models/` 下的模型文件，重启服务即生效。如果更换模型类型（例如从 bge-small 换为 bge-large），需要重建向量库。
- **TTS 模型**：更新 CosyVoice 模型文件后，修改 `.env` 中的 `COSYVOICE_MODEL_DIR` 路径，重启服务。
- **LLM 模型**：修改 `.env` 中的 `LLM_MODEL_NAME` 即可切换，无需重启（下次请求生效）。

---

## 七、故障排查

### 7.1 服务无法启动

**现象**：运行 `run.sh` 后报错退出

**排查步骤**：

```bash
# 1. 确认 conda 环境存在
conda activate DGA

# 2. 确认 .env 文件存在且配置正确
cat backend/.env | head -20

# 3. 手动启动后端，查看完整错误信息
conda activate DGA
export $(grep -v '^#' backend/.env | xargs)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**常见原因**：
- `.env` 中的 `LLM_API_KEY` 未填写或无效
- CosyVoice 模型路径配置错误（如果不需要 TTS，用 `--no-livetalking` 启动也会跳过 TTS 加载，TTS 失败只是警告而非报错）
- 端口 8000 或 8010 已被占用（用 `lsof -i :8000` 检查）

### 7.2 LLM 回复失败

**现象**：聊天返回错误

**排查**：
```bash
# 测试 LLM API 连通性
curl https://api.deepseek.com/v1/models \
  -H "Authorization: Bearer $LLM_API_KEY"
```

如果返回 401，说明 API Key 无效或已过期。如果返回超时，检查网络是否可访问 `api.deepseek.com`。

### 7.3 向量检索无结果

**现象**：AI 回答"抱歉，我暂时无法回答这个问题"

**排查**：
```bash
# 检查向量库是否存在
ls -la backend/vector_store/

# 手动测试检索
conda activate DGA
cd backend
python test_query.py
```

如果向量库为空，运行 `ingest_guide.py` 重建：

```bash
conda activate DGA
cd backend/scripts
python ingest_guide.py
```

### 7.4 TTS 语音没有声音

**现象**：AI 有文字回复，但数字人不说话

**排查**：
1. 确认 `response_type` 设为 1（语音+文字模式）
2. 检查 CosyVoice 是否正确加载（启动日志中是否有 "CosyVoice 模型加载完成"）
3. 检查 `backend/data/temp_audios/` 目录是否有生成的 WAV 文件
4. 检查 CosyVoice 模型路径 `.env` 配置是否正确

### 7.5 数字人画面不显示

**现象**：聊天正常但看不到数字人

**排查**：
1. 确认 LiveTalking 服务在运行：`curl http://localhost:8010`
2. 确认前端 `config.json` 中 LiveTalking 地址正确
3. 确认 LiveTalking 模型文件在 `backend/LiveTalking/models/` 下
4. 运行验证脚本检查集成状态：

```bash
conda activate DGA
cd backend
python scripts/verify_integration.py
```

### 7.6 前端编译失败

**现象**：`cmake --build .` 报错

**排查**：
```bash
# 确认 Qt 版本
qmake6 --version  # 或 qmake --version

# 确认 CMake 能找到 Qt6
cmake .. 2>&1 | grep -i qt
```

常见原因：Qt 6.10 未安装、CMake 版本太低（需要 3.16+）、缺少必需的 Qt 模块。

---

## 八、项目脚本速查表

| 脚本 | 位置 | 用途 |
|------|------|------|
| `bootstrap.sh` | `backend/scripts/` | 首次部署引导：创建环境、安装依赖、下载模型 |
| `run.sh` | `backend/scripts/` | 日常启动后端 + 数字人 |
| `start_livetalking.sh` | `backend/scripts/` | 单独启动 LiveTalking 数字人服务 |
| `download_model.py` | `backend/scripts/` | 下载 bge 嵌入模型 |
| `ingest_guide.py` | `backend/scripts/` | 从 Word 文档构建向量库 |
| `ingest_dataset.py` | `backend/scripts/` | 从数据集构建向量库（多文档） |
| `ingest_consumption.py` | `backend/scripts/` | 导入游客消费模拟数据 |
| `init_db.py` | `backend/scripts/` | 初始化 SQLite 数据库表结构 |
| `test_query.py` | `backend/` | 手动测试 RAG 检索效果（3 个示例查询） |
| `test_admin.py` | `backend/` | 管理功能测试 |
| `test_recommend.py` | `backend/` | 推荐功能测试 |
| `verify_integration.py` | `backend/scripts/` | 检查 LiveTalking 集成完整性（只读） |
| `verify_cosyvoice.py` | `backend/scripts/` | 检查 CosyVoice 安装状态 |
| `generate_mock_data.py` | `backend/scripts/` | 生成模拟用户交互数据 |
| `test_audio.py` | `backend/scripts/` | 音频功能测试 |
| `test_markitdown.py` | `backend/scripts/` | 文档解析功能测试 |

### 手动启动（不使用脚本）

如果不想依赖启动脚本，也可以手动分步操作：

```bash
# 终端1：启动后端
conda activate DGA
export $(grep -v '^#' backend/.env | xargs)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 终端2：启动数字人引擎
conda activate DGA
bash backend/scripts/start_livetalking.sh
```

---

## 九、性能参考

以下数据基于推荐硬件配置（RTX 3060 / 32GB RAM）在灵山胜境景区知识库上测得，仅供参考：

| 指标 | 典型值 | 说明 |
|------|--------|------|
| 服务启动时间 | 30-60 秒 | 含 4 个 AI 模型加载 |
| 首次文本回复 | 2-5 秒 | 含 RAG 检索 + LLM 生成 + TTS 首句 |
| 后续文本回复 | 1-3 秒 | 模型已预热 |
| 语音识别转写 | 1-3 秒 | Whisper Base CPU 模式，10 秒以内语音 |
| TTS 每句合成 | 0.5-1.5 秒 | CosyVoice GPU，短句 |
| RAG 检索延迟 | 50-200 ms | Chroma 本地向量检索 |
| 并发对话数 | 10-20 路 | 受限于 GPU 显存（TTS 多实例） |

> 注意：LLM 回复延迟受 DeepSeek API 服务端影响，高峰期可能有波动。如果只需要文字回复（不含 TTS），延迟通常在 1-2 秒内。

---

## 附录：配置文件参考

### backend/.env（完整示例）

```bash
# LLM
LLM_API_KEY=sk-65d54b40f8a0480c86dedb316ce13304
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL_NAME=deepseek-v4-flash

# JWT
JWT_SECRET_KEY=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0

# CosyVoice TTS
COSYVOICE_DIR=/home/liborui/CosyVoice
COSYVOICE_MATCHA_DIR=/home/liborui/CosyVoice/third_party/Matcha-TTS
COSYVOICE_MODEL_DIR=/home/liborui/CosyVoice/pretrained_models/CosyVoice-300M-SFT
TTS_SPEAKER=中文女

# LiveTalking
LIVETALKING_BASE_URL=http://localhost:8010

# 可选
LOG_LEVEL=INFO
HF_ENDPOINT=https://hf-mirror.com
```

### frontend/config.json（完整示例）

```json
{
    "backend": {
        "ip": "http://192.168.1.100",
        "port": 8000
    },
    "livetalking": {
        "host": "http://192.168.1.100",
        "port": 8010
    }
}
```
