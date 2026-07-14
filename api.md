# 景区导览AI数字人 — 前后端通信接口规范

> 协议：HTTP + WebSocket
> 基础路径：`/api/v1`（WebSocket 除外，为 `/ws/chat`）
> 数据格式：JSON（除文件上传外）
> 认证方式：JWT Bearer Token（除登录/注册外，所有含敏感操作接口均需在 Header 中携带 `Authorization: Bearer <token>`）

---

## 通用约定

### 响应信封

```json
{
  "code": 200,
  "message": "success",
  "data": {}
}
```

| 字段      | 类型         | 说明                                     |
| --------- | ------------ | ---------------------------------------- |
| `code`    | int          | 200 成功，4xx 客户端错误，5xx 服务端错误 |
| `message` | string       | 成功为 "success"，失败为具体错误描述     |
| `data`    | object/array | 业务数据，成功时必含                     |

### 分页参数

列表接口统一支持以下查询参数：

| 参数        | 类型 | 默认值 | 说明                 |
| ----------- | ---- | ------ | -------------------- |
| `page`      | int  | 1      | 页码                 |
| `page_size` | int  | 20     | 每页条数（最大 100） |

分页响应 `data` 结构：

```json
{
  "items": [],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 错误码

| code | 含义                   |
| ---- | ---------------------- |
| 200  | 成功                   |
| 400  | 请求参数错误           |
| 401  | 未认证 / Token 过期    |
| 403  | 无权限                 |
| 404  | 资源不存在             |
| 409  | 资源冲突（如重复创建） |
| 500  | 服务端内部错误         |

---

## 一、认证模块

### 1.1 注册

```
POST /auth/register
```

**Request Body:**

```json
{
  "username": "string (3-32位，字母数字下划线)",
  "password": "string (6-64位)",
  "confirm_password": "string (需与password一致)",
  "display_name": "string (昵称，1-50位)"
}
```

**Response `data`:**

```json
{
  "user_id": 1,
  "username": "visitor1",
  "display_name": "游客小王",
  "role": "visitor",
  "avatar_url": "",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-29T12:00:00Z"
}
```

### 1.2 登录

```
POST /auth/login
```

**Request Body:**

```json
{
  "username": "string",
  "password": "string"
}
```

**Response `data`:**

```json
{
  "user_id": 1,
  "username": "visitor1",
  "display_name": "游客小王",
  "role": "visitor",
  "avatar_url": "",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-29T12:00:00Z"
}
```

> `role` 取值：`visitor`（游客）、`admin`（管理员）。
> 被禁用用户登录返回 403。

### 1.3 验证 Token

```
GET /auth/verify
```

**Request Header:** `Authorization: Bearer <token>`

**Response `data`:**

```json
{
  "valid": true,
  "user_id": 1,
  "username": "visitor1",
  "display_name": "游客小王",
  "role": "visitor",
  "avatar_url": ""
}
```

### 1.4 退出登录

```
POST /auth/logout
```

**Request Header:** `Authorization: Bearer <token>`

**Response `data`:**

```json
{}
```

### 1.5 更新个人资料

```
PUT /auth/profile
```

**Request Header:** `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "display_name": "string (1-50位)",
  "avatar_url": "string (可选，最大512位)"
}
```

**Response `data`:**

```json
{
  "user_id": 1,
  "username": "visitor1",
  "display_name": "新昵称",
  "role": "visitor",
  "avatar_url": ""
}
```

### 1.6 修改密码

```
PUT /auth/password
```

**Request Header:** `Authorization: Bearer <token>`

**Request Body:**

```json
{
  "old_password": "string (6-64位)",
  "new_password": "string (6-64位)"
}
```

**Response `data`:**

```json
{}
```

> 旧密码错误返回 400。

### 1.7 刷新 Token（未实现）

> ⚠️ **未实现**：JWT 7天过期，当前无需刷新端点。以下保留供后续扩展。

```
POST /auth/refresh
```

---

## 二、游客交互模块（会话与问答）

### 2.1 流式文本问答（SSE）

```
POST /chat/stream
```

游客发送文本消息，通过 SSE 流式获得逐 token 数字人回复（打字机效果）。支持多轮对话历史。

**Request Body:**

```json
{
  "conversation_id": 1,
  "content": "故宫建于哪一年？",
  "response_type": 1,
  "digital_human_id": 0
}
```

| 字段               | 类型   | 必填 | 说明                                               |
| ------------------ | ------ | ---- | -------------------------------------------------- |
| `conversation_id`  | int    | 是   | 当前对话 ID                                        |
| `content`          | string | 是   | 用户消息                                           |
| `response_type`    | int    | 是   | 1 = 语音+文字输出（含逐句 TTS 音频），0 = 仅文字输出 |
| `digital_human_id` | int    | 否   | 固定为 0（预留，前端已移除选择入口）                |

**SSE 事件流：**

1. **token 事件**（LLM 逐 token 输出）：
```
data: {"type": "token", "conversation_id": 1, "content": "故宫"}
```

2. **sentence_audio 事件**（`response_type=1` 时，每句 TTS 完成后推送）：
```
data: {"type": "sentence_audio", "conversation_id": 1, "content": "第一句文本", "audio_url": "/api/v1/download_audio?filename=xxx.wav", "eventpoint": 0}
```

3. **audio_queued 事件**（`response_type=1` 时，音频预推送至 LiveTalking 队列）：
```
data: {"type": "audio_queued", "conversation_id": 1, "content": "同上", "eventpoint": 1}
```

4. **done 事件**：
```
data: {"type": "done", "conversation_id": 1, "message_id": 42, "full_content": "故宫（紫禁城）建于明永乐四年...", "knowledge_sources": ["景区知识库"], "audio_url": null}
```

5. **error 事件**：
```
data: {"type": "error", "conversation_id": 1, "message": "错误描述"}
```

> `eventpoint`：0 = 本句是最后一句，1 = 后面还有更多句（用于前端预推送调度）。

### 2.2 非流式文本问答

```
POST /chat/text
```

普通 HTTP 响应，等待 LLM 完整回复 + TTS 合成后一次性返回。

**Request Body：** 与 `/chat/stream` 相同。

**Response `data`:**

```json
{
  "conversation_id": 1,
  "message_id": 42,
  "role": "assistant",
  "content": "故宫（紫禁城）建于明永乐四年（1406年）...",
  "audio_url": "/api/v1/download_audio?filename=xxx.wav",
  "knowledge_sources": ["景区知识库"],
  "title_updated": null
}
```

### 2.2a 纯文本问答（简单版，无持久化）

```
POST /chat
```

不依赖对话上下文，不持久化消息，仅用于快速测试。

**Request Body:**

```json
{
  "question": "故宫建于哪一年？"
}
```

**Response:**

```json
{
  "status": "success",
  "question": "故宫建于哪一年？",
  "answer": "故宫（紫禁城）建于明永乐四年..."
}
```

### 2.3 语音问答（SSE 流式）

```
POST /chat_voice
```

上传语音文件，ASR 识别后流式返回识别文本 + LLM 回复。编码格式：`multipart/form-data`。响应为 SSE 流。

**Form Data:**

| 字段               | 类型 | 必填 | 说明                                          |
| ------------------ | ---- | ---- | --------------------------------------------- |
| `audio_file`       | File | 是   | 语音文件，WAV/MP3/OGG                         |
| `conversation_id`  | int  | 是   | 当前对话 ID                                   |
| `response_type`    | int  | 否   | 1 = 语音+文字输出，0 = 仅文字输出，默认 1     |
| `digital_human_id` | int  | 否   | 固定为 0                                      |

**SSE 事件流：** 同 `/chat/stream`，额外增加 `transcribed_text` 事件作为首条：

```
data: {"type": "transcribed_text", "conversation_id": 1, "content": "故宫建于哪一年？"}
```

### 2.3a 语音流式问答（别名）

```
POST /chat/voice_stream
```

参数和返回与 `/chat_voice` 完全相同。

**Form Data:**

| 字段               | 类型 | 必填 | 说明                                          |
| ------------------ | ---- | ---- | --------------------------------------------- |
| `audio`            | File | 是   | 语音文件                                      |
| `conversation_id`  | int  | 是   | 当前对话 ID                                   |
| `digital_human_id` | int  | 否   | 固定为 0                                      |
| `response_type`    | int  | 否   | 默认 1                                        |

### 2.4 下载语音文件

```
GET /download_audio?filename=xxx.wav
```

**Response:** 二进制音频流（Content-Type: audio/wav）。

完整 URL 示例：`http://localhost:8000/api/v1/download_audio?filename=abc123.wav`

---

## 三、个性化推荐

### 3.1 个性化路线推荐

```
POST /recommend/route
```

**Request Header:** `Authorization: Bearer <token>`（visitor 即可）

根据游客近期对话自动推断兴趣，基于 RAG + LLM 生成个性化游览路线推荐。

**Request Body:**

```json
{
  "user_id": 1
}
```

| 字段      | 类型 | 必填 | 说明                                        |
| --------- | ---- | ---- | ------------------------------------------- |
| `user_id` | int  | 是   | 用户 ID（从历史对话中推断兴趣）             |

**Response `data`:**

```json
{
  "route": {
    "name": "历史文化精华路线",
    "duration_minutes": 180,
    "spots": [
      {
        "name": "太和殿",
        "description": "故宫最宏伟的建筑...",
        "estimated_minutes": 30
      }
    ],
    "highlights": ["中轴线核心建筑群"],
    "match_reason": "根据您对历史和建筑的偏好推荐"
  },
  "interests": ["历史", "建筑"]
}
```

> 兴趣推断缓存 1 小时。新用户无对话历史时使用冷启动兜底推荐。

### 3.2 获取讲解重点（未实现）

> ⚠️ **未实现**：以下接口定义保留供后续扩展。

```
POST /recommend/focus
```

---

## 四、数字人控制

> 数字人交互基于 LiveTalking 外部服务（默认 `http://localhost:8010`），后端作为代理转发控制指令。

### 4.1 创建数字人会话

```
POST /digital-human/session
```

在 LiveTalking 中创建数字人会话（用于驱动口型动画）。

**Request Body:**

```json
{
  "conversation_id": 1,
  "avatar": null
}
```

**Response `data`:**

```json
{
  "session_id": "live_session_abc123",
  "conversation_id": 1
}
```

### 4.2 销毁数字人会话

```
DELETE /digital-human/session/{conversation_id}
```

**Response:**

```json
{"code": 200, "message": "success"}
```

### 4.3 注册已有会话

```
POST /digital-human/register_session
```

前端自行创建 LiveTalking 会话后，注册 conversation_id → session_id 映射到后端。

**Request Body:**

```json
{
  "conversation_id": 1,
  "session_id": "live_session_abc123"
}
```

### 4.4 数字人播报

```
POST /digital-human/speak
```

驱动数字人说出指定文本（echo 模式，非主要使用方式）。

**Request Body:**

```json
{
  "conversation_id": 1,
  "text": "欢迎来到灵山胜境"
}
```

### 4.5 打断播报

```
POST /digital-human/interrupt
```

立即中断当前数字人播报。

**Request Body:**

```json
{
  "conversation_id": 1
}
```

### 4.6 播放音频（驱动口型）

```
POST /digital-human/play-audio
```

将指定 WAV 文件发送给 LiveTalking，驱动数字人口型动画并立即开始推理。

**别名（顶层路由）：** `POST /play-audio`（请求体相同）

**Request Body:**

```json
{
  "conversation_id": 1,
  "audio_filename": "abc123.wav"
}
```

### 4.7 预推送音频

```
POST /digital-human/play-audio-queue
```

将 WAV 暂存到 LiveTalking 的待处理队列（不立即推理），等前端调用 `/flush` 后再开始。用于避免当前句播放期间下一句视频帧抢占 GPU。

**别名（顶层路由）：** `POST /play-audio-queue`（请求体相同）

**Request Body:** 同 `/play-audio`

### 4.8 刷新队列

```
POST /digital-human/flush
```

通知 LiveTalking 从待处理队列取下一句音频开始推理。

**别名（顶层路由）：** `POST /flush`（请求体相同）

**Request Body:**

```json
{
  "conversation_id": 1
}
```

### 4.9 查询状态

```
GET /digital-human/status/{conversation_id}
```

**Response `data`:**

```json
{
  "is_speaking": false
}
```

---

## 五、WebSocket 实时通信

用于实时双向流式聊天（打字机效果 + 逐句 TTS 音频）。

### 5.1 连接

```
WebSocket /ws/chat?token=<JWT_TOKEN>
```

> ⚠️ WebSocket 不使用 `/api/v1` 前缀。连接时通过查询参数传入 Token 进行鉴权。

### 5.2 客户端 → 服务端消息

```json
{
  "type": "chat_message",
  "conversation_id": 1,
  "content": "故宫建于哪一年？",
  "digital_human_id": 0,
  "response_type": 1
}
```

```json
{
  "type": "ping"
}
```

### 5.3 服务端 → 客户端消息

```json
{
  "type": "token",
  "conversation_id": 1,
  "content": "故宫"
}
```

```json
{
  "type": "sentence_audio",
  "conversation_id": 1,
  "content": "第一句文本",
  "audio_url": "/api/v1/download_audio?filename=xxx.wav",
  "eventpoint": 0
}
```

```json
{
  "type": "audio_queued",
  "conversation_id": 1,
  "content": "同上",
  "eventpoint": 1
}
```

```json
{
  "type": "done",
  "conversation_id": 1,
  "message_id": 42,
  "full_content": "故宫（紫禁城）建于明永乐四年...",
  "knowledge_sources": ["景区知识库"],
  "audio_url": null
}
```

```json
{
  "type": "error",
  "conversation_id": 1,
  "message": "服务器处理超时"
}
```

```json
{
  "type": "pong"
}
```

| type             | 说明                                                |
| ---------------- | --------------------------------------------------- |
| `token`          | LLM 逐 token 流式输出，前端即时渲染打字机效果       |
| `sentence_audio` | 每句 TTS 完成，携带音频 URL（`response_type=1` 时） |
| `audio_queued`   | 音频已预推送至 LiveTalking 队列                     |
| `done`           | 回复结束，携带完整信息                              |
| `error`          | 错误消息                                            |
| `pong`           | 心跳回复                                            |

### 心跳机制

- 客户端每 30 秒发送 `{"type": "ping"}`
- 服务端回复 `{"type": "pong"}`
- 连续 3 次未收到 pong 则客户端主动断开重连

---

## 六、对话管理

### 6.1 创建对话

```
POST /conversations
```

**Request Body:**

```json
{
  "user_id": 1,
  "title": "新对话",
  "knowledge_doc_id": -1
}
```

| 字段               | 类型 | 必填 | 说明                                             |
| ------------------ | ---- | ---- | ------------------------------------------------ |
| `knowledge_doc_id` | int  | 否   | 绑定特定知识文档，为 -1 或不传表示使用全部知识库 |

**Response `data`:**

```json
{
  "conversation_id": 1,
  "title": "新对话",
  "created_at": "2026-04-28T10:00:00Z"
}
```

### 6.2 获取对话列表

```
GET /conversations?user_id=1&page=1&page_size=20
```

**Response `data`:**

```json
{
  "items": [
    {
      "conversation_id": 1,
      "title": "故宫历史咨询",
      "message_count": 5,
      "last_message": "故宫建于哪一年？",
      "last_time": "2026-04-28T10:30:00Z",
      "created_at": "2026-04-28T10:00:00Z"
    }
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

### 6.3 按日期分组的对话列表

```
GET /conversations/grouped?user_id=1
```

**Response `data`:**

```json
{
  "groups": [
    {
      "date": "今天",
      "conversations": [
        {
          "conversation_id": 1,
          "title": "故宫历史咨询",
          "message_count": 5,
          "created_at": "2026-04-28T10:00:00Z",
          "updated_at": "2026-04-28T10:30:00Z"
        }
      ]
    },
    {
      "date": "昨天",
      "conversations": []
    },
    {
      "date": "更早",
      "conversations": []
    }
  ]
}
```

### 6.4 获取对话详情

```
GET /conversations/{conversation_id}
```

**Response `data`:**

```json
{
  "conversation_id": 1,
  "title": "故宫历史咨询",
  "user_id": 1,
  "knowledge_doc_id": 1,
  "created_at": "2026-04-28T10:00:00Z",
  "updated_at": "2026-04-28T10:30:00Z"
}
```

### 6.5 更新对话标题

```
PUT /conversations/{conversation_id}
```

**Request Body:**

```json
{
  "title": "故宫历史深度咨询"
}
```

**Response `data`:**

```json
{
  "conversation_id": 1,
  "title": "故宫历史深度咨询",
  "updated_at": "2026-04-28T11:00:00Z"
}
```

### 6.6 删除对话

```
DELETE /conversations/{conversation_id}
```

级联删除该对话下的所有消息。

**Response `data`:** `{}`

### 6.7 获取对话消息列表（分页）

```
GET /conversations/{conversation_id}/messages?page=1&page_size=50
```

**Response `data`:**

```json
{
  "items": [
    {
      "message_id": 1,
      "conversation_id": 1,
      "role": "user",
      "content": "故宫建于哪一年？",
      "audio_url": null,
      "created_at": "2026-04-28T10:00:00Z"
    },
    {
      "message_id": 2,
      "conversation_id": 1,
      "role": "assistant",
      "content": "故宫（紫禁城）建于明永乐四年...",
      "audio_url": "/api/v1/download_audio?filename=xxx.wav",
      "knowledge_sources": ["景区知识库"],
      "created_at": "2026-04-28T10:00:02Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50
}
```

### 6.8 获取对话全部消息

```
GET /conversations/{conversation_id}/messages/all
```

不分页，返回该对话的所有消息（按时间升序）。

**Response `data`:**

```json
{
  "items": [...],
  "total": 50
}
```

> 消息格式与 6.7 相同。
> ⚠️ `POST /conversations/{id}/export`（导出对话）当前未实现。

---

## 七、知识库管理（管理员）

> 所有端点需要 JWT Bearer Token 认证，且当前用户需具备管理员角色（role=admin）。

### 7.1 上传知识文档

```
POST /admin/knowledge-docs
```

编码格式：`multipart/form-data`。

**Form Data:**

| 字段      | 类型   | 必填 | 说明                                          |
| --------- | ------ | ---- | --------------------------------------------- |
| `file`    | File   | 是   | 文档文件，支持 .docx/.pdf/.txt/.md，最大 50MB |
| `title`   | string | 是   | 文档标题                                      |
| `user_id` | int    | 是   | 管理员用户 ID                                 |

**Response `data`:**

```json
{
  "doc_id": 1,
  "title": "故宫完整导游词",
  "file_type": "docx",
  "file_size": 2048000,
  "status": "processing",
  "chunk_count": null,
  "created_at": "2026-04-28T10:00:00Z"
}
```

| `status`     | 说明                 |
| ------------ | -------------------- |
| `uploaded`   | 已上传，待处理       |
| `processing` | 正在向量化           |
| `ready`      | 处理完成，可用于问答 |
| `failed`     | 处理失败             |

> 上传后自动触发后台异步向量化，状态立即变为 `processing`。

### 7.2 获取知识文档列表

```
GET /admin/knowledge-docs?page=1&page_size=20
```

**Response `data`:**

```json
{
  "items": [
    {
      "doc_id": 1,
      "title": "故宫完整导游词",
      "file_type": "docx",
      "file_size": 2048000,
      "status": "ready",
      "chunk_count": 256,
      "created_at": "2026-04-28T10:00:00Z",
      "updated_at": "2026-04-28T10:05:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20
}
```

### 7.3 触发文档向量化

```
POST /admin/knowledge-docs/{doc_id}/process
```

重新触发分词和向量化（如首次处理失败后重试）。

**Response `data`:**

```json
{
  "doc_id": 1,
  "status": "processing"
}
```

> 正在处理中的文档不会重复触发。客户端可通过 7.2 轮询 `status` 直到变为 `ready`。

### 7.4 删除文档

```
DELETE /admin/knowledge-docs/{doc_id}
```

删除物理文件、Chroma 向量库记录和 SQL 数据库记录。

**Response `data`:** `{}`

> ⚠️ `GET /admin/knowledge-docs/{doc_id}`（文档详情）和 `PUT /admin/knowledge-docs/{doc_id}`（更新文档信息）当前未实现。

---

## 八、数字人形象管理（管理员）

> ⚠️ **未实现**：数字人选择功能未在后端实现，前端已移除数字人选择入口。所有请求中的 `digital_human_id` 固定为 0（默认数字人）。数字人形象管理 CRUD 接口定义如下，供后续扩展参考。

### 8.1 创建数字人形象

```
POST /admin/digital-humans
```

**Request Body:**

```json
{
  "name": "小景（古典风）",
  "appearance": "classic_chinese",
  "costume": "hanfu_red",
  "voice_type": "soft_female",
  "description": "身穿红色汉服，适合历史文化景区",
  "avatar_url": "https://cdn.example.com/avatars/dh1.png",
  "model_config": {
    "animation": "2d_live2d",
    "mute_model": "facefusion_v1"
  }
}
```

### 8.2 获取数字人列表

```
GET /admin/digital-humans
```

### 8.3 获取数字人详情

```
GET /admin/digital-humans/{digital_human_id}
```

### 8.4 更新数字人配置

```
PUT /admin/digital-humans/{digital_human_id}
```

### 8.5 删除数字人

```
DELETE /admin/digital-humans/{digital_human_id}
```

### 8.6 设为默认

```
PUT /admin/digital-humans/{digital_human_id}/default
```

---

## 九、数据大屏（管理员）

> 所有端点需要 JWT Bearer Token 认证 + 管理员角色。

### 9.1 概览数据

```
GET /admin/dashboard/overview
```

**Response `data`:**

```json
{
  "today_service_count": 1256,
  "today_visitor_count": 342,
  "week_service_count": 8720,
  "total_knowledge_docs": 15,
  "avg_satisfaction": 4.6,
  "avg_response_time_ms": 1200,
  "recommend_count": 45
}
```

### 9.2 服务统计（按时间）

```
GET /admin/dashboard/service-stats?period=week
```

| 参数     | 类型   | 默认值 | 说明                                             |
| -------- | ------ | ------ | ------------------------------------------------ |
| `period` | string | `week` | `day`（逐小时）、`week`（逐日）、`month`（逐日） |

**Response `data`:**

```json
{
  "period": "week",
  "stats": [
    {"time": "2026-04-22", "count": 1250},
    {"time": "2026-04-23", "count": 1380}
  ]
}
```

### 9.3 热门问答排行

```
GET /admin/dashboard/hot-questions?top=10
```

| 参数  | 类型 | 默认值 | 说明     |
| ----- | ---- | ------ | -------- |
| `top` | int  | 10     | 返回条数 |

**Response `data`:**

```json
{
  "items": [
    {"question": "故宫门票多少钱", "count": 526, "trend": "up"},
    {"question": "故宫几点开门", "count": 423, "trend": "stable"}
  ]
}
```

| `trend`  | 说明     |
| -------- | -------- |
| `up`     | 上升趋势 |
| `down`   | 下降趋势 |
| `stable` | 平稳     |

### 9.4 满意度趋势

```
GET /admin/dashboard/satisfaction-trend?period=month
```

**Response `data`:**

```json
{
  "period": "month",
  "trend": [
    {"date": "2026-04-01", "avg_score": 4.5, "response_count": 320},
    {"date": "2026-04-02", "avg_score": 4.7, "response_count": 280}
  ]
}
```

> 满意度基于关键词启发式评分（正/负面词库匹配），非用户主动评分。

### 9.5 核心运营指标（数据大屏完整数据）

```
GET /admin/dashboard/full
```

合并返回大屏所需的全部数据，减少前端多次请求。

**Response `data`:**

```json
{
  "overview": {},
  "service_stats": [],
  "hot_questions": [],
  "satisfaction_trend": []
}
```

> 各字段结构与 9.1-9.4 中对应接口的 `data` 一致。

---

## 十、游客感受度报告（管理员）

> 所有端点需要 JWT Bearer Token 认证 + 管理员角色。
> 必选查询参数：`start_date` 和 `end_date`（YYYY-MM-DD 格式）。

### 10.1 游客洞察报告

```
GET /admin/reports/visitor-insight?start_date=2026-04-01&end_date=2026-04-28
```

**Response `data`:**

```json
{
  "period": {"start": "2026-04-01", "end": "2026-04-28"},
  "total_visitors": 5000,
  "total_conversations": 15000,
  "active_hours": {"10:00": 1200, "14:00": 1500},
  "top_interests": [
    {"interest": "历史", "percentage": 45},
    {"interest": "建筑", "percentage": 30},
    {"interest": "美食", "percentage": 15}
  ],
  "avg_conversation_length": 6.5
}
```

### 10.2 情感趋势

```
GET /admin/reports/emotion-trend?start_date=2026-04-01&end_date=2026-04-28
```

**Response `data`:**

```json
{
  "period": {"start": "2026-04-01", "end": "2026-04-28"},
  "trend": [
    {
      "date": "2026-04-01",
      "positive": 0.6,
      "neutral": 0.3,
      "negative": 0.1
    }
  ],
  "summary": "游客整体情感以积极为主，负面情绪集中在购票排队等非导览问题"
}
```

> `summary` 由 LLM 根据消息内容自动生成。

### 10.3 关注点分析

```
GET /admin/reports/focus-analysis?start_date=2026-04-01&end_date=2026-04-28
```

**Response `data`:**

```json
{
  "period": {"start": "2026-04-01", "end": "2026-04-28"},
  "categories": [
    {
      "category": "门票与开放时间",
      "percentage": 35,
      "trend": "up"
    },
    {
      "category": "历史文化",
      "percentage": 30,
      "trend": "stable"
    }
  ]
}
```

> 基于消息内容的关键词分类。

### 10.4 服务建议

```
GET /admin/reports/service-suggestions?start_date=2026-04-01&end_date=2026-04-28
```

**Response `data`:**

```json
{
  "period": {"start": "2026-04-01", "end": "2026-04-28"},
  "suggestions": [
    {
      "issue": "游客频繁询问卫生间位置",
      "suggestion": "建议在景区入口及主要节点增加导引标识",
      "priority": "high"
    }
  ]
}
```

| `priority` | 说明                   |
| ---------- | ---------------------- |
| `high`     | 高优先级，建议立即处理 |
| `medium`   | 中优先级               |
| `low`      | 低优先级               |

> 由 LLM 根据指定时间范围内的对话数据自动生成 3-5 条改进建议。

---

## 十一、用户管理（管理员）

> 所有端点需要 JWT Bearer Token 认证，且当前用户需具备管理员角色（role=admin）。

### 11.1 用户列表（分页+搜索）

```
GET /admin/users?page=1&page_size=20&search=张三
```

**Query 参数:**

| 参数        | 类型   | 默认值 | 说明                 |
| ----------- | ------ | ------ | -------------------- |
| `page`      | int    | 1      | 页码                 |
| `page_size` | int    | 20     | 每页条数（最大 100） |
| `search`    | string | 无     | 按用户名/昵称模糊搜索 |

**Response `data`:**

```json
{
  "items": [
    {
      "id": 2,
      "username": "visitor1",
      "display_name": "游客小王",
      "role": "visitor",
      "phone": "13800138000",
      "email": "a@example.com",
      "is_active": true,
      "avatar_url": null,
      "created_at": "2026-04-28T10:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}
```

### 11.2 创建用户

```
POST /admin/users
```

**Request Body:**

```json
{
  "username": "visitor2",
  "password": "abc123",
  "display_name": "游客小李"
}
```

| 字段           | 类型   | 必填 | 说明                        |
| -------------- | ------ | ---- | --------------------------- |
| `username`     | string | 是   | 用户名（3-32位，字母数字下划线） |
| `password`     | string | 是   | 密码（6-64位）              |
| `display_name` | string | 是   | 昵称                        |

**Response `data`:** 创建的用户信息（role 固定为 visitor）。

**错误码:**

| code | 说明                       |
| ---- | -------------------------- |
| 409  | 用户名已存在               |

### 11.3 用户详情

```
GET /admin/users/{user_id}
```

**Response `data`:**

```json
{
  "id": 2,
  "username": "visitor1",
  "display_name": "游客小王",
  "role": "visitor",
  "phone": "13800138000",
  "email": "a@example.com",
  "is_active": true,
  "avatar_url": null,
  "created_at": "2026-04-28T10:00:00Z",
  "conversation_count": 15
}
```

### 11.4 编辑用户

```
PUT /admin/users/{user_id}
```

**Request Body（所有字段可选）:**

```json
{
  "display_name": "游客小王（已改名）",
  "phone": "13900139000",
  "email": "new@example.com",
  "avatar_url": "https://cdn.example.com/avatars/u2.png",
  "is_active": true
}
```

**错误码:**

| code | 说明                         |
| ---- | ---------------------------- |
| 404  | 用户不存在                   |
| 403  | 不能修改超级管理员状态       |

> 修改 `is_active` 会递增 `token_version`，使该用户已签发的所有 Token 立即失效。

### 11.5 删除用户（级联）

```
DELETE /admin/users/{user_id}
```

> 级联删除用户的所有对话、消息和 Chroma 向量数据。

**错误码:**

| code | 说明                       |
| ---- | -------------------------- |
| 404  | 用户不存在                 |
| 403  | 不能删除超级管理员         |

### 11.6 启用/禁用用户

```
PUT /admin/users/{user_id}/status
```

**Request Body:**

```json
{
  "is_active": false
}
```

> `is_active` 不传则翻转当前状态。禁用用户后，其已签发的 Token 立即失效。

**Response `data`:**

```json
{
  "user_id": 2,
  "is_active": false
}
```

> **注意事项:**
> - 超级管理员（id=1）不能被删除或禁用
> - 管理员不能通过用户管理接口修改其他管理员的角色

---

## 附录 A：WebSocket 通信流程

```
客户端                          服务端
  |                               |
  |--- WS /ws/chat?token=xxx --->|  连接建立
  |<-- {"type":"pong"} ----------|  握手确认
  |                               |
  |--- {"type":"chat_message",   |  发送消息
  |     "content":"故宫建于哪年"}-->|
  |                               |
  |<-- {"type":"token",          |  LLM 逐 token 流式输出
  |     "content":"故宫"}--------|
  |<-- {"type":"sentence_audio",|  每句 TTS 完成
  |     "audio_url":"...",       |
  |     "eventpoint":0}----------|
  |<-- {"type":"done",           |  回复结束
  |     "full_content":"..."}---->|
```

---

## 附录 B：接口实现状态概览

| 模块               | 状态     | 说明                               |
| ------------------ | -------- | ---------------------------------- |
| 认证（注册/登录/验证/登出/资料/密码） | ✅ 已实现 | Token 7天有效期                    |
| 流式文本问答（SSE） | ✅ 已实现 | `/chat/stream`                     |
| 非流式文本问答     | ✅ 已实现 | `/chat/text`                       |
| 纯文本问答（测试用） | ✅ 已实现 | `/chat`                            |
| 语音问答（SSE）    | ✅ 已实现 | `/chat_voice`、`/chat/voice_stream` |
| 对话管理（CRUD）   | ✅ 已实现 | 含全部消息查询                     |
| 数字人控制         | ✅ 已实现 | LiveTalking 代理（9 个端点）        |
| 个性化路线推荐     | ✅ 已实现 | LLM 兴趣推断 + RAG 路线推荐         |
| 知识库管理（上传/列表/处理/删除） | ✅ 已实现 | 文档详情和更新未实现               |
| 数据大屏           | ✅ 已实现 | 含完整数据聚合接口                 |
| 游客报告           | ✅ 已实现 | 情感分析、洞察、建议               |
| 用户管理           | ✅ 已实现 | 含级联删除和状态管理               |
| WebSocket 聊天     | ✅ 已实现 | `/ws/chat`（无 `/api/v1` 前缀）    |
| 数字人形象管理 CRUD | ❌ 未实现 | digital_human_id 固定为 0          |
| Token 刷新         | ❌ 未实现 | JWT 7天过期，暂不需要              |
| 讲解重点推荐       | ❌ 未实现 | `/recommend/focus`                 |
| 对话导出           | ❌ 未实现 | 前端可本地导出                     |
| 设置管理           | ❌ 未实现 | 功能已合并至 auth/profile          |
