# 景区导览服务AI数字人 — 产品总体设计文档

> 版本：v1.0  
> 最后更新：2026年7月  
> 适用对象：开发团队、项目评审、技术决策者

---

## 一、产品概述

### 1.1 产品定位

「景区导览服务AI数字人」是一套面向景区场景的智能导览系统。它通过 AI 数字人技术，为游客提供 7×24 小时在线导游服务——支持语音和文字两种交互方式，数字人以合成的视频画面配合口型同步的语音进行回答，模拟真人导游的面对面讲解体验。同时，系统为景区管理方提供完整的数据分析后台，覆盖游客洞察、知识库管理、用户管理等运营需求。

### 1.2 解决的痛点

| 传统方式 | 本系统 |
|----------|--------|
| 导游资源有限，旺季供不应求 | 7×24 在线，无限并发服务 |
| 讲解固定，无法互动提问 | 多轮自由对话，游客想问就问 |
| 游客行为一片黑盒 | 数据大屏 + 情感报告，运营有数可依 |
| 人工培训导游成本高 | 上传知识文档即可更新讲解内容 |

### 1.3 核心能力一览

- **多模态交互**：支持语音输入（ASR 中文识别）和文字输入；数字人以视频帧 + 逐句语音 + 口型同步的方式回答
- **智能问答**：基于 RAG（检索增强生成）技术，利用景区专属知识库回答历史、文化、景点等常见问题
- **流式对话**：WebSocket 或 HTTP SSE 双通道打字机效果输出，多轮对话上下文记忆，首轮对话自动生成标题
- **个性化推荐**：LLM 自动从对话历史中推断游客兴趣偏好，生成个性化游览路线推荐
- **管理后台**：用户管理、知识库文档上传与管理、数据大屏（实时统计 + 热门问答 + 满意度趋势）、游客感受度分析报告

### 1.4 产品形态

- **游客端**：桌面应用程序（Qt6 / QML），运行在景区自助终端或游客个人设备上
- **管理端**：集成在同一应用中，通过角色切换进入后台管理界面
- **后端服务**：部署在景区服务器上，对外暴露 HTTP REST + WebSocket 接口

---

## 二、系统架构

### 2.1 总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        游客端 / 管理端                            │
│                   (Qt6 + QML 桌面应用)                            │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐      │
│  │ 登录注册  │ │ 聊天页面  │ │ 历史对话  │ │ 管理后台       │      │
│  │LoginPage │ │ChatPage  │ │HistoryPage│ │AdminPage      │      │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘      │
│                        │                                         │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              C++ 业务层（14 个 Manager 类）                │    │
│  │  ApiService │ LoginManager │ ConversationManager │ ...    │    │
│  │  VoiceInterface │ LiveTalkingClient │ SettingsManager   │    │
│  └─────────────────────────────────────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
               HTTP REST / SSE / WebSocket
                            │
┌───────────────────────────┴─────────────────────────────────────┐
│                    后端服务 (Python + FastAPI)                     │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   API 层（48+ HTTP + 1 WS）                 │   │
│  │  认证 │ 聊天 │ 对话管理 │ 数字人控制 │ 知识库 │ 管理后台   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                   服务层（15 个模块）                       │   │
│  │                                                          │   │
│  │  RAG服务     LLM服务      ASR服务      TTS服务           │   │
│  │  认证服务    管理员服务   数据大屏     报告服务           │   │
│  │  推荐服务    知识库管理   数字人客户端  数字人会话管理     │   │
│  │  消费分析    流式工具                                      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    数据层                                  │   │
│  │  SQLite (用户/对话/消息/文档)  │  Chroma (向量存储)       │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP
┌───────────────────────────┴─────────────────────────────────────┐
│                LiveTalking 数字人引擎 (外部服务)                   │
│                                                                  │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐       │
│  │ wav2lip     │  │ Edge TTS     │  │ WebRTC 视频流    │       │
│  │ 口型驱动    │  │ 语音合成     │  │ 实时推流         │       │
│  └─────────────┘  └──────────────┘  └──────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 技术选型理由

| 组件 | 选型 | 理由 |
|------|------|------|
| **后端框架** | FastAPI | 原生异步支持（SSE/WebSocket 的核心需求）；自动生成 OpenAPI 文档便于前后端联调 |
| **LLM** | DeepSeek V4 flash | 中文能力强；兼容 OpenAI 协议，切换成本低；性价比高 |
| **嵌入模型** | BAAI/bge-small-zh-v1.5 | 中文语义检索的标杆轻量模型；CPU 可运行，降低部署门槛 |
| **向量数据库** | Chroma | 轻量嵌入式模式，无需额外部署；支持父子文档（parent-child）检索 |
| **ASR** | OpenAI Whisper Base | 开源免费；中文识别准确率在景区场景可接受；CPU 可运行 |
| **TTS** | CosyVoice-300M-SFT | 中文语音合成质量领先；支持流式分句合成，延迟可控 |
| **数字人引擎** | LiveTalking (wav2lip) | 成熟的口型同步方案；提供标准 HTTP API 便于集成 |
| **关系数据库** | SQLite | 零配置部署；单机场景下性能足够；不引入额外运维负担 |
| **前端框架** | Qt6 + QML | 跨平台桌面应用；原生性能；成熟的多媒体支持（音频录制、视频播放） |

### 2.3 通信架构

系统采用三种通信模式，各司其职：

- **HTTP REST**：常规 CRUD 操作（登录、对话列表、用户管理等）。请求/响应模式，适合一次性数据交换。
- **HTTP SSE（Server-Sent Events）**：流式聊天的主要通道。服务端单向推送 token 和音频 URL 事件，客户端通过 `EventSource` 接收。相比 WebSocket 更简单，无需维护长连接状态。
- **WebSocket**：实时双向通信。用于聊天场景的备用通道，支持心跳保活、断线重连。也是前端接收 LiveTalking 视频帧的通道。

服务端到 LiveTalking 之间使用 HTTP REST（控制指令和音频文件推送），LiveTalking 到前端使用 WebSocket 推送视频帧。

---

## 三、后端设计

### 3.1 项目结构

```
backend/
├── app/
│   ├── main.py                  # FastAPI 应用入口，生命周期管理
│   ├── database.py              # SQLAlchemy 引擎 + SQLite 连接
│   ├── models.py                # ORM 模型（7 张表）
│   ├── logging_config.py        # 日志配置
│   ├── config/
│   │   ├── paths.py             # 路径常量（DB、模型、向量库）
│   │   ├── prompts.yaml         # LLM 提示词模板
│   │   └── prompt_loader.py     # 提示词加载器
│   ├── api/
│   │   └── api_v1/
│   │       ├── api.py           # 路由汇总注册
│   │       └── endpoints/       # 各模块端点（10 个文件）
│   └── services/                # 业务逻辑层（15 个模块）
├── scripts/                     # 部署和运维脚本（18 个）
├── data/                        # 运行时数据（DB、上传文件、临时音频）
├── models/                      # 本地模型文件（嵌入模型）
├── vector_store/                # Chroma 持久化向量数据
└── requirements.txt             # Python 依赖清单
```

### 3.2 服务模块详述

#### 3.2.1 核心AI服务

**rag_service — RAG 检索服务**

实现双通道 Chroma 向量检索 + 意图识别。采用父子文档（parent-child）结构：子块（小段落）用于向量相似度匹配，父文档（完整段落）用作 LLM 的上下文。这种设计在检索精度和上下文完整性之间取得平衡。

检索流程：
1. 用户问题 → BGE 嵌入模型向量化
2. Chroma 向量相似度检索 → 返回 Top-K 子块
3. 子块 → 映射到父文档 → 拼接为完整上下文
4. 意图识别判断问题类型（事实查询/路线推荐/闲聊等）
5. 上下文 + 提示词模板 → 送入 LLM 生成回答

嵌入模型 `bge-small-zh-v1.5` 在 FastAPI 启动时预加载，避免首次请求的冷启动延迟。

**llm_service — LLM 服务**

封装 DeepSeek V4 flash 的调用，兼容 OpenAI API 协议。提供三种调用模式：

- **同步调用**：`chat()` — 用于非流式问答和后台任务（如标题生成）
- **异步调用**：`achat()` — 用于 FastAPI 异步端点
- **流式调用**：`astream()` — 用于 SSE/WebSocket 逐 token 输出，实现打字机效果

所有调用通过环境变量配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL_NAME`，方便切换模型。

**asr_service — 语音识别服务**

基于 OpenAI Whisper Base 模型，在 CPU 上运行中文识别。为提升景区场景的识别准确率，内置领域提示词增强机制——将景区专属词汇（景点名、历史术语）注入解码器。模型在 FastAPI 启动时预热加载。

**tts_service / tts_streaming / cosyvoice_tts — 语音合成服务**

TTS 模块是三文件协作结构：
- `cosyvoice_tts.py`：CosyVoice 模型的底层封装，负责加载模型和单次合成
- `tts_service.py`：上层接口，管理模型初始化和调用
- `tts_streaming.py`：流式分句合成管道——将 LLM 的长文本回复按标点分句，逐句送入 CosyVoice 合成，每完成一句立即回调通知。这使得前端可以在全部 TTS 完成前就开始播放，显著降低首句延迟

#### 3.2.2 数字人集成

**digital_human_client — LiveTalking HTTP 客户端**

封装与 LiveTalking 外部服务的所有 HTTP 交互，包括会话创建/销毁、音频播放、队列管理等。

**digital_human_session — 会话映射管理**

维护 conversation_id 到 LiveTalking session_id 的映射关系。支持前端自行创建 LiveTalking 会话后注册映射。

**逐句音频推送机制**：TTS 每完成一句 → 生成 WAV 文件 → 推送给 LiveTalking → LiveTalking 驱动 wav2lip 口型渲染 → WebSocket 推送视频帧到前端。

**预推送队列（play-audio-queue/flush）**：为避免当前句播放期间下一句视频帧抢占 GPU 导致卡顿，音频先暂存到 LiveTalking 待处理队列。前端在当前句播放接近结束时调用 flush，触发下一句推理。eventpoint 字段告知前端哪句是最后一句。

#### 3.2.3 业务管理服务

**auth_service — 认证服务**

- 密码哈希：bcrypt
- 令牌签发：JWT HS256，7 天有效期
- 令牌撤销：token_version 机制——管理员禁用用户时递增 token_version，该用户已签发的所有 Token 立即失效，无需维护黑名单
- 种子管理员：首次启动时自动创建 super_admin 账号（id=1）

**admin_service — 管理员服务**

用户 CRUD（含级联删除——同时删除对话、消息、Chroma 向量数据）、启用/禁用管理、超级管理员保护。

**knowledge_service — 知识库管理**

文档上传 → MarkItDown 解析（支持 .docx / .pdf / .txt / .md）→ LangChain 分块 → BGE 向量化 → Chroma 写入。整个过程异步后台执行，上传后立即返回，前端轮询状态。

**dashboard_service — 数据大屏**

基于 SQL 聚合统计，提供概览指标、服务趋势（按小时/日/月）、热门问答排行、满意度关键词启发式分析。

**report_service — 游客报告**

分析游客对话数据：情感趋势（正负面词库匹配）、关注点分类（关键词聚类）、LLM 自动生成服务改进建议。

**recommend_service — 个性化推荐**

从用户近期对话中提取关键词，LLM 推断兴趣标签（如"历史""建筑""美食"），结合 RAG 检索相关知识生成个性化游览路线。新用户无对话历史时使用冷启动兜底推荐。兴趣推断结果缓存 1 小时。

**consumption_service — 消费分析**

管理端消费分析模块的后端，基于 `visitor_consumption` 表中的模拟游客消费数据提供统计分析接口。

### 3.3 数据库设计

使用 SQLite，共 7 张业务表：

```
users                          conversations
┌─────────────────────┐       ┌──────────────────────┐
│ id (PK)             │──┐    │ id (PK)              │
│ username (UNIQUE)   │  │    │ user_id (FK → users) │──┐
│ password_hash       │  │    │ title                │  │
│ display_name        │  │    │ knowledge_doc_id     │  │
│ role                │  │    │ created_at           │  │
│ is_active           │  │    │ updated_at           │  │
│ token_version       │  │    └──────────────────────┘  │
│ phone / email       │  │                              │
│ avatar_url          │  │    messages                  │
│ interests (JSON)    │  │    ┌──────────────────────┐  │
│ created_at          │  │    │ id (PK)              │  │
└─────────────────────┘  │    │ conversation_id (FK) │──┘
                          │    │ role                 │
knowledge_docs            │    │ content              │
┌──────────────────┐     │    │ audio_url            │
│ id (PK)          │     │    │ knowledge_sources    │
│ title            │     │    │ created_at           │
│ file_type/size   │     │    └──────────────────────┘
│ file_path        │     │
│ status           │     │    recommend_logs
│ chunk_count      │     │    ┌──────────────────────┐
│ content_preview  │     │    │ id (PK)              │
│ user_id (FK)     │     │    │ user_id (FK)         │──┘
│ created_at       │     │    │ interests_used       │
└──────────────────┘     │    │ created_at           │
                          │    └──────────────────────┘
visitor_consumption       │
┌──────────────────────┐  │
│ id (PK)              │  │
│ tourist_id           │  │
│ attraction_name      │  │
│ visit_date           │  │
│ ticket/food/shopping │  │
│ total_cost           │  │
│ satisfaction (1-5)   │  │
│ group_size           │  │
└──────────────────────┘  │
                          │
                          ▼
                     Chroma 向量存储
                     ┌──────────────────────┐
                     │ collection: guide    │
                     │ 父文档 → 子块列表    │
                     │ 嵌入向量 (512 维)    │
                     └──────────────────────┘
```

**设计要点**：
- `user.token_version`：增量计数器，签发 JWT 时嵌入 version 字段。校验时比对当前 version，不符则拒绝。管理员禁用用户或修改敏感属性时递增，实现即时令牌失效。
- `conversation.knowledge_doc_id`：为 -1 时使用全部知识库，指定具体文档 ID 时仅检索该文档。为多景区或多主题场景预留。
- `message.knowledge_sources`：JSON 数组，记录本条回复引用了哪些知识文档，支持溯源。
- 推荐日志保留 90 天自动清理，避免无限增长。

### 3.4 应用生命周期

FastAPI 使用 lifespan 钩子管理服务启动和关闭：

```
启动阶段（顺序执行）:
  1. 日志系统初始化
  2. 数据库表创建 + 列迁移检测
  3. 种子管理员创建（首次）
  4. RAG 服务预热 → 加载 BGE 嵌入模型
  5. 预摄入文档同步
  6. ASR 模型预热 → 加载 Whisper Base
  7. TTS 模型预热 → 加载 CosyVoice-300M-SFT

运行阶段:
  接受 HTTP 和 WebSocket 请求

关闭阶段:
  清理资源，记录日志
```

首次请求不再有模型加载延迟，全部在启动时完成。TTS 加载失败时记录警告但不阻塞启动。

---

## 四、前端设计

### 4.1 技术栈

- **框架**：Qt 6.10+ / C++17 / QML
- **Qt 模块**：Quick、QuickControls2、Network、WebSockets、QuickEffects、Multimedia
- **构建**：CMake 3.16+

### 4.2 页面结构

```
Main.qml (根页面，导航容器)
├── LoginPage.qml          # 登录/注册
├── ChatPage.qml           # 游客聊天主页面
│   ├── MessageBubble.qml  # 聊天气泡组件
│   └── DigitalHumanView.qml # 数字人视频渲染组件
├── HistoryPage.qml        # 对话历史列表
├── SettingsPage.qml       # 个人设置/服务器配置
├── AdminPage.qml          # 管理后台容器（仅 admin 可见）
│   ├── DashboardTab.qml   # 数据大屏
│   ├── ReportTab.qml      # 游客报告
│   ├── RecommendTab.qml   # 推荐管理
│   └── ConsumptionTab.qml # 消费分析
```

### 4.3 C++ 业务模块

每个 Manager 类负责一块独立的前端业务逻辑，通过 Qt 信号/槽机制与 QML 层交互：

| 模块 | 职责 | 关键能力 |
|------|------|----------|
| **ApiService** | HTTP 请求基础封装 | Token 注入、错误拦截、统一超时 |
| **LoginManager** | 登录/注册/Token 管理 | 记住我、自动登录、Token 过期检测 |
| **ConversationManager** | 对话交互 | SSE/WS 流式接收、消息管理 |
| **VoiceInterface** | 语音录制与上传 | QAudioSource 录音、WAV 编码、分块上传 |
| **LiveTalkingClient** | 数字人视频帧接收 | WebSocket 连接、JPEG/PNG 帧解码、QImage 渲染 |
| **AudioPlayer** | TTS 音频播放 | QMediaPlayer 封装、预加载下一句 |
| **HistoryManager** | 对话历史管理 | 列表/分组/搜索/删除 |
| **SettingsManager** | 配置管理 | config.json 读写、后端地址配置 |
| **DashboardManager** | 数据大屏数据获取 | 30s 自动刷新、Canvas 图表数据 |
| **ReportManager** | 游客报告 | 日期范围查询、报告展示 |
| **RecommendManager** | 个性化推荐 | 路线推荐请求与展示 |
| **ConsumptionManager** | 消费分析 | 消费数据请求与展示 |
| **AdminManager** | 管理端（用户/知识库） | 分页列表、用户CRUD、文档上传 |

### 4.4 数字人渲染流程

LiveTalking 与前端之间的视频渲染是一个独立的 WebSocket 通道：

```
LiveTalking (8010端口)                      Qt 前端
    │                                          │
    │──── WebSocket 连接 ────────────────────→│ LiveTalkingClient
    │                                          │
    │←── 视频帧 (JPEG/PNG 二进制) ───────────│ QImage 解码
    │                                          │
    │←── 音频流 (配合口型) ──────────────────│ QMediaPlayer 播放
    │                                          │
    │                                          ├── DigitalHumanView.qml
    │                                          │   渲染 QImage 到屏幕
```

LiveTalkingClient 负责维持 WebSocket 连接、帧解码、异常重连，将解码后的 QImage 通过信号发送给 QML 层的 DigitalHumanView 组件进行实时渲染。

---

## 五、核心业务流程

### 5.1 文本问答流程（游客端主要交互）

```
游客输入文字 "故宫建于哪一年？"
        │
        ▼
[前端] ApiService → POST /api/v1/chat/stream (SSE)
        │
        ▼
[后端] chat 端点
        │
        ├──→ 保存用户消息到 messages 表
        │
        ├──→ RAG 检索：用户问题 → 向量化 → Chroma 检索 → 父文档上下文
        │
        ├──→ LLM 流式生成：上下文 + 提示词 → DeepSeek V4 flash
        │       │
        │       └──→ 逐 token 推送 SSE: {"type":"token","content":"故"}
        │                                        {"type":"token","content":"宫"}
        │                                        {"type":"token","content":"建"} ...
        │
        ├──→ TTS 流式合成（若 response_type=1）
        │       │
        │       ├── LLM 完整回复 → 按标点分句
        │       ├── 逐句送入 CosyVoice → 生成 WAV
        │       ├── 推送 sentence_audio: {"type":"sentence_audio","audio_url":"...","eventpoint":0/1}
        │       └── 推送音频到 LiveTalking 队列
        │
        └──→ 保存 AI 回复到 messages 表
                │
                └──→ 发送 done: {"type":"done","message_id":42,"full_content":"..."}
```

### 5.2 语音问答流程

在文本问答的基础上，前端增加了录音→上传→等待转写的环节：

```
游客点击录音按钮
        │
        ▼
[前端] VoiceInterface → QAudioSource 录音 → WAV 编码
        │
        ▼
[前端] multipart/form-data → POST /api/v1/chat_voice
        │
        ▼
[后端] ASR: Whisper Base 转写 → 中文文本
        │
        ├──→ 推送 transcribed_text: {"type":"transcribed_text","content":"故宫建于哪一年？"}
        │
        └──→ 后续流程与 5.1 文本问答完全相同
```

### 5.3 个性化推荐流程

```
游客请求推荐路线
        │
        ▼
[后端] recommend_service
        │
        ├──→ 查询用户 interests 字段（1 小时内有效则直接用）
        │       或
        ├──→ LLM 分析近期对话 → 推断兴趣标签 → 写入 interests + 缓存
        │       （新用户无对话 → 冷启动兜底推荐）
        │
        ├──→ RAG 检索：兴趣标签 + "推荐路线" → 相关知识
        │
        └──→ LLM 生成：知识 + 兴趣 → 结构化推荐路线
                {
                  "name": "历史文化精华路线",
                  "duration_minutes": 180,
                  "spots": [...],
                  "highlights": [...],
                  "match_reason": "..."
                }
```

### 5.4 知识库更新流程（管理员）

```
管理员上传 Word 文档
        │
        ▼
[后端] knowledge_service.upload_doc()
        │
        ├──→ 保存文件到 data/knowledge_docs/
        ├──→ 写入 knowledge_docs 表 (status="uploaded")
        └──→ 触发后台异步任务
                │
                ├──→ 状态更新为 "processing"
                ├──→ MarkItDown 解析文档 → 提取纯文本
                ├──→ LangChain RecursiveCharacterTextSplitter 分块
                │       ├── 父块：大段落（完整语义单元）
                │       └── 子块：小段落（精细检索单元）
                ├──→ BGE 向量化 → Chroma 写入
                ├──→ 状态更新为 "ready"，写入 chunk_count
                └──→ 失败则状态 = "failed"
```

---

## 六、API 设计

完整的 API 规范见 `api.md`，此处概述设计原则。

### 6.1 设计原则

- **统一响应信封**：`{"code": 200, "message": "success", "data": {}}`，前端可做统一拦截处理
- **分页标准化**：所有列表接口统一 `page` / `page_size` 参数和响应结构
- **HTTP 状态码语义化**：200 成功、400 参数错误、401 未认证、403 无权限、404 不存在、409 冲突、500 服务端错误
- **SSE 事件类型化**：每个事件携带 `type` 字段（token / sentence_audio / audio_queued / done / error），前端按类型分发处理

### 6.2 接口模块概览

| 模块 | 端点数量 | 主要功能 |
|------|---------|----------|
| 认证 | 7 | 注册、登录、验证、登出、个人资料、修改密码、（刷新预留） |
| 聊天 | 5 | 流式/非流式文本、纯文本测试、语音问答、音频下载 |
| 数字人控制 | 9 | 会话创建/销毁/注册、播报、打断、播放音频、预推送、刷新队列、状态查询 |
| 对话管理 | 7 | 创建、列表、分组列表、详情、更新标题、删除、消息查询 |
| 知识库管理 | 4 | 上传、列表、处理触发、删除 |
| 个性化推荐 | 1 | 路线推荐 |
| WebSocket | 1 | 实时双向聊天 |
| 数据大屏 | 5 | 概览、服务统计、热门问答、满意度趋势、完整聚合 |
| 游客报告 | 4 | 游客洞察、情感趋势、关注点分析、服务建议 |
| 用户管理 | 6 | 列表、创建、详情、编辑、删除、状态管理 |

### 6.3 安全机制

- **JWT Bearer Token**：所有敏感接口必须携带 `Authorization: Bearer <token>` 头
- **token_version 即时失效**：管理员禁用用户后，该用户所有已签发 Token 立即失效
- **bcrypt 密码哈希**：数据库不存储明文密码
- **角色权限控制**：visitor（游客）和 admin（管理员）两角色；管理类端点校验 role=admin
- **超级管理员保护**：id=1 的超级管理员不能被删除或禁用
- **WebSocket 认证**：连接时通过查询参数 `?token=xxx` 传入 JWT

---

## 七、部署架构

```
┌──────────────────────────────────────────────────┐
│              部署服务器 (Ubuntu 24.04)              │
│                                                   │
│  ┌─────────────────────┐  ┌───────────────────┐  │
│  │  FastAPI 后端       │  │  LiveTalking      │  │
│  │  Port 8000          │  │  Port 8010        │  │
│  │  (conda env: DGA)   │  │  (conda env: DGA) │  │
│  └─────────────────────┘  └───────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  本地资源                                    │ │
│  │  • SQLite DB: backend/data/app.db           │ │
│  │  • Chroma DB: backend/vector_store/         │ │
│  │  • 嵌入模型: backend/models/                 │ │
│  │  • TTS模型: CosyVoice-300M-SFT              │ │
│  │  • LiveTalking 模型: wav2lip 权重           │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  外部依赖                                    │ │
│  │  • DeepSeek API (api.deepseek.com)          │ │
│  │  • HuggingFace 镜像 (hf-mirror.com)         │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
         │
         │ 局域网 / 互联网
         │
         ▼
┌──────────────────────────────────────────────────┐
│              游客终端 (Windows/Linux/macOS)        │
│                                                   │
│  Qt6 桌面应用 → 连接后端 8000 + LiveTalking 8010  │
└──────────────────────────────────────────────────┘
```

推荐硬件配置：
- **CPU**：8 核以上（ASR、TTS 推理）
- **GPU**：NVIDIA RTX 3060 或以上，显存 ≥ 8GB（TTS/CosyVoice + 数字人/wav2lip 并行运行）
- **内存**：32GB（模型加载 + 并发推理）
- **磁盘**：50GB 可用空间（模型文件约 5GB + 向量库和 DB 数十 MB + 预留音频文件空间）
- **操作系统**：Ubuntu 24.04 LTS
- **网络**：稳定访问 api.deepseek.com（LLM API）
