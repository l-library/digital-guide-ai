# 景区导览AI数字人 — 前后端通信接口规范

> 协议：HTTP + WebSocket
> 基础路径：`/api/v1`
> 数据格式：JSON（除文件上传外）
> 认证方式：JWT Bearer Token（除登录/注册外，所有请求均需在 Header 中携带 `Authorization: Bearer <token>`）

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
  "display_name": "string (昵称)"
}
```

**Response `data`:**

```json
{
  "user_id": 1,
  "username": "visitor1",
  "display_name": "游客小王",
  "role": "visitor",
  "token": "eyJhbGciOiJIUzI1NiIs..."
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
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-29T12:00:00Z"
}
```

> `role` 取值：`visitor`（游客）、`admin`（管理员）。

### 1.3 刷新 Token

```
POST /auth/refresh
```

**Request Body:**

```json
{
  "token": "string (当前有效token)"
}
```

**Response `data`:**

```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "expires_at": "2026-04-29T12:00:00Z"
}
```

### 1.4 验证 Token

```
GET /auth/verify
```

**Response `data`:**

```json
{
  "valid": true,
  "user_id": 1,
  "role": "visitor"
}
```

### 1.5 退出登录

```
POST /auth/logout
```

**Request Body:**

```json
{
  "user_id": 1
}
```

**Response `data`:**

```json
{}
```

---

## 二、游客交互模块（会话与问答）

### 2.1 文本问答

```
POST /chat/text
```

游客发送一条文本消息，获得数字人回复。

**Request Body:**

```json
{
  "conversation_id": 1,
  "content": "故宫建于哪一年？",
  "response_type" : 1,
  "digital_human_id": 1
}
```

| 字段               | 类型   | 必填 | 说明                                     |
| ------------------ | ------ | ---- | ---------------------------------------- |
| `conversation_id`  | int    | 是   | 当前对话 ID                              |
| `content`          | string | 是   | 用户消息                                 |
| `response_type`    | int    | 是   | 需要的输出方式，1为语音+文字输出，0为仅文字输出。当输出模式为"数字人"时应传1，为"文字输出"时应传0 |
| `digital_human_id` | int    | 否   | 数字人形象 ID，不传使用默认              |

**Response `data`:**

```json
{
  "conversation_id": 1,
  "message_id": 42,
  "role": "assistant",
  "content": "故宫（紫禁城）建于明永乐四年（1406年），历时14年于永乐十八年（1420年）建成...",
  "audio_url": "/api/v1/download_audio?filename=xxx.mp3",
  "knowledge_sources": ["故宫介绍.docx"]
}
```

| 字段                | 类型          | 说明                                         |
| ------------------- | ------------- | -------------------------------------------- |
| `audio_url`         | string        | TTS 音频下载链接（可能为空，表示仅文本回复） |
| `knowledge_sources` | array[string] | 回答引用的知识来源文档名（可选）             |

### 2.2 语音问答

```
POST /chat/voice
```

上传语音文件，返回文字+语音回复。编码格式：`multipart/form-data`。

**Form Data:**

| 字段               | 类型 | 必填 | 说明                             |
| ------------------ | ---- | ---- | -------------------------------- |
| `audio`            | File | 是   | 语音文件，WAV/MP3/OGG，最大 10MB |
| `conversation_id`  | int  | 是   | 当前对话 ID                      |
| `digital_human_id` | int  | 否   | 数字人形象 ID                    |

**Response `data`:**

```json
{
  "conversation_id": 1,
  "transcribed_text": "故宫建于哪一年？",
  "message_id": 42,
  "role": "assistant",
  "content": "故宫（紫禁城）建于明永乐四年（1406年）...",
  "audio_url": "/api/v1/download_audio?filename=xxx.mp3"
}
```

> 前端拿到 `audio_url` 后可直接播放，同时显示 `content` 文本。

### 2.2a 语音流式问答

```
POST /chat/voice_stream
```

上传语音文件，流式返回识别文本与 LLM 回复。编码格式：`multipart/form-data`。响应为 SSE（Server-Sent Events）流。

**Form Data:**

| 字段               | 类型 | 必填 | 说明                             |
| ------------------ | ---- | ---- | -------------------------------- |
| `audio`            | File | 是   | 语音文件，WAV/MP3/OGG，最大 10MB |
| `conversation_id`  | int  | 是   | 当前对话 ID                      |
| `digital_human_id` | int  | 否   | 数字人形象 ID                    |
| `response_type`    | int  | 否   | 输出方式，1为语音+文字输出，0为仅文字输出，默认1 |

**SSE 事件流：**

1. **识别结果事件**（ASR 完成后立即推送）：

```
data: {"type": "transcribed_text", "conversation_id": 1, "content": "故宫建于哪一年？"}
```

2. **LLM token 事件**（逐 token 流式输出）：

```
data: {"type": "token", "conversation_id": 1, "content": "故宫"}
data: {"type": "token", "conversation_id": 1, "content": "（紫禁城）"}
```

3. **完成事件**：

```
data: {"type": "done", "conversation_id": 1, "message_id": 42, "full_content": "故宫（紫禁城）建于明永乐四年（1406年）...", "audio_url": "/api/v1/download_audio?filename=xxx.mp3", "knowledge_sources": ["景区知识库"]}
```

4. **错误事件**：

```
data: {"type": "error", "conversation_id": 1, "message": "语音识别失败: ..."}
```

| type              | 说明                                       |
| ----------------- | ------------------------------------------ |
| `transcribed_text` | ASR 识别结果，前端应立即将其显示为用户消息 |
| `token`           | LLM 逐 token 流式输出                      |
| `done`            | 回复结束，携带完整信息                     |
| `error`           | 错误消息                                   |

> **交互流程：** 前端录音 → 上传音频 → 收到 `transcribed_text` 事件后显示识别文本 → 收到 `token` 事件逐字追加 AI 回复 → 收到 `done` 结束。
>
> **与 WebSocket 的对比：** 此接口使用 HTTP SSE，无需建立 WebSocket 连接，适合一次性语音问答场景。

### 2.3 下载语音文件

```
GET /download_audio?filename=xxx.mp3
```

**Response:** 二进制音频流（Content-Type: audio/mpeg）。

### 2.4 个性化路线推荐（待定）

```
POST /recommend/route
```

根据游客兴趣偏好推荐游览路线。

**Request Body:**

```json
{
  "interests": ["历史", "建筑"],
  "duration_minutes": 180,
  "scenic_spot": "故宫"
}
```

| 字段               | 类型          | 必填 | 说明                                             |
| ------------------ | ------------- | ---- | ------------------------------------------------ |
| `interests`        | array[string] | 是   | 兴趣标签，如 `["历史","建筑","自然风光","美食"]` |
| `duration_minutes` | int           | 是   | 期望游览时长（分钟）                             |
| `scenic_spot`      | string        | 是   | 景区名称                                         |

**Response `data`:**

```json
{
  "routes": [
    {
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
    }
  ]
}
```

### 2.5 获取讲解重点（待定）

```
POST /recommend/focus
```

根据游客兴趣，返回某个景点的个性化讲解重点内容。

**Request Body:**

```json
{
  "spot_name": "太和殿",
  "interests": ["建筑", "历史事件"]
}
```

**Response `data`:**

```json
{
  "spot_name": "太和殿",
  "focus_points": [
    {"title": "建筑特色", "content": "太和殿面阔11间..."},
    {"title": "历史典故", "content": "太和殿曾多次被焚毁重建..."}
  ]
}
```

---

## 三、WebSocket 实时通信

用于流式输出数字人回复（打字机效果）、表情驱动指令下发。

### 3.1 连接

```
WebSocket /ws/chat?token=<JWT_TOKEN>
```

连接时通过查询参数传入 Token 进行鉴权。

### 3.2 客户端 → 服务端消息

```json
{
  "type": "chat_message",
  "conversation_id": 1,
  "content": "故宫建于哪一年？",
  "digital_human_id": 1,
  "response_type": 1
}
```

```json
{
  "type": "ping"
}
```

### 3.3 服务端 → 客户端消息

```json
{
  "type": "token",
  "conversation_id": 1,
  "content": "故宫"  // LLM 逐 token 输出
}
```

```json
{
  "type": "done",
  "conversation_id": 1,
  "message_id": 42,
  "full_content": "故宫（紫禁城）建于明永乐四年（1406年）...",
  "audio_url": "/api/v1/download_audio?filename=xxx.mp3",
  "knowledge_sources": ["故宫介绍.docx"],
  "digital_human_expression": "speaking"  // 表情指令
}
```

| type    | 说明                                          |
| ------- | --------------------------------------------- |
| `token` | LLM 逐 token 流式输出，前端即时渲染打字机效果 |
| `done`  | 回复结束，携带完整信息                        |
| `error` | 错误消息                                      |
| `pong`  | 心跳回复                                      |

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

> 前端收到 `token` 消息后，逐字追加到气泡中；收到 `done` 后结束渲染，并触发 TTS 播放和数字人口型驱动。

### 3.4 数字人表情指令

在 `done` 消息中携带 `digital_human_expression` 字段，或在独立消息中下发：

```json
{
  "type": "expression",
  "expression": "smile",
  "duration_ms": 3000
}
```

| 表情值     | 含义                 |
| ---------- | -------------------- |
| `idle`     | 待机/自然            |
| `speaking` | 说话中               |
| `smile`    | 微笑                 |
| `think`    | 思考                 |
| `surprise` | 惊讶                 |
| `listen`   | 倾听（等待用户输入） |

---

## 四、对话管理

### 4.1 创建对话

```
POST /conversations
```

**Request Body:**

```json
{
  "user_id": 1,
  "title": "故宫历史咨询",
  "knowledge_doc_id": 1
}
```

| 字段               | 类型 | 必填 | 说明                                             |
| ------------------ | ---- | ---- | ------------------------------------------------ |
| `knowledge_doc_id` | int  | 否   | 绑定特定知识文档，为 -1 或不传表示使用全部知识库 |

**Response `data`:**

```json
{
  "conversation_id": 1,
  "title": "故宫历史咨询",
  "created_at": "2026-04-28T10:00:00Z"
}
```

### 4.2 获取对话列表

```
GET /conversations?user_id=1
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

### 4.3 按日期分组的对话列表

```
GET /conversations/grouped?user_id=1
```

**Response `data`:**

```json
{
  "groups": [
    {
      "date": "今天",
      "conversations": []
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

### 4.4 获取对话详情

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

### 4.5 删除对话

```
DELETE /conversations/{conversation_id}
```

**Response `data`:**

```json
{}
```

### 4.6 获取对话消息列表

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
      "content": "故宫（紫禁城）建于明永乐四年（1406年）...",
      "audio_url": "/api/v1/download_audio?filename=xxx.mp3",
      "knowledge_sources": ["故宫介绍.docx"],
      "created_at": "2026-04-28T10:00:02Z"
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 50
}
```

| 字段                | 类型          | 说明                       |
| ------------------- | ------------- | -------------------------- |
| `role`              | string        | `user` 或 `assistant`      |
| `audio_url`         | string/null   | assistant 消息可能附带音频 |
| `knowledge_sources` | array[string] | 仅 assistant 消息含此字段  |

### 4.7 导出对话

```
POST /conversations/{conversation_id}/export
```

**Response `data`:**

```json
{
  "format": "json",
  "filename": "conversation_1.json",
  "content": "..."  // 结构化对话内容，包含完整消息列表
}
```

---

## 五、知识库管理（管理员）

### 5.1 上传知识文档

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
  "status": "uploaded",
  "created_at": "2026-04-28T10:00:00Z"
}
```

| `status`     | 说明                 |
| ------------ | -------------------- |
| `uploaded`   | 已上传，待处理       |
| `processing` | 正在向量化           |
| `ready`      | 处理完成，可用于问答 |
| `failed`     | 处理失败             |

### 5.2 获取知识文档列表

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

### 5.3 获取文档详情

```
GET /admin/knowledge-docs/{doc_id}
```

**Response `data`:**

```json
{
  "doc_id": 1,
  "title": "故宫完整导游词",
  "file_type": "docx",
  "file_size": 2048000,
  "status": "ready",
  "chunk_count": 256,
  "content_preview": "故宫位于北京中轴线的中心...",
  "created_at": "2026-04-28T10:00:00Z",
  "updated_at": "2026-04-28T10:05:00Z"
}
```

### 5.4 更新文档信息

```
PUT /admin/knowledge-docs/{doc_id}
```

**Request Body:**

```json
{
  "title": "故宫导游词（2026修订版）"
}
```

**Response `data`:**

```json
{
  "doc_id": 1,
  "title": "故宫导游词（2026修订版）",
  "updated_at": "2026-04-28T11:00:00Z"
}
```

### 5.5 删除文档

```
DELETE /admin/knowledge-docs/{doc_id}
```

**Response `data`:**

```json
{}
```

### 5.6 触发文档向量化

```
POST /admin/knowledge-docs/{doc_id}/process
```

**Response `data`:**

```json
{
  "doc_id": 1,
  "status": "processing"
}
```

> 客户端可通过 `GET /admin/knowledge-docs/{doc_id}` 轮询 `status` 直到变为 `ready`。

---

## 六、数字人形象管理（管理员）

### 6.1 创建数字人形象

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

| 字段           | 类型   | 必填 | 说明                                                |
| -------------- | ------ | ---- | --------------------------------------------------- |
| `appearance`   | string | 是   | 外观分类，如 `classic_chinese`, `modern`, `cartoon` |
| `costume`      | string | 否   | 服装标识                                            |
| `voice_type`   | string | 否   | 语音类型，如 `soft_female`, `gentle_male`           |
| `model_config` | object | 否   | 数字人引擎配置                                      |

**Response `data`:**

```json
{
  "digital_human_id": 1,
  "name": "小景（古典风）",
  "created_at": "2026-04-28T10:00:00Z"
}
```

### 6.2 获取数字人列表

```
GET /admin/digital-humans
```

**Response `data`:**

```json
{
  "items": [
    {
      "digital_human_id": 1,
      "name": "小景（古典风）",
      "appearance": "classic_chinese",
      "costume": "hanfu_red",
      "voice_type": "soft_female",
      "is_default": true,
      "avatar_url": "https://cdn.example.com/avatars/dh1.png",
      "created_at": "2026-04-28T10:00:00Z"
    }
  ]
}
```

### 6.3 获取数字人详情

```
GET /admin/digital-humans/{digital_human_id}
```

**Response `data`:**

```json
{
  "digital_human_id": 1,
  "name": "小景（古典风）",
  "appearance": "classic_chinese",
  "costume": "hanfu_red",
  "voice_type": "soft_female",
  "is_default": true,
  "avatar_url": "https://cdn.example.com/avatars/dh1.png",
  "model_config": {
    "animation": "2d_live2d",
    "mute_model": "facefusion_v1"
  },
  "created_at": "2026-04-28T10:00:00Z",
  "updated_at": "2026-04-28T10:00:00Z"
}
```

### 6.4 更新数字人配置

```
PUT /admin/digital-humans/{digital_human_id}
```

**Request Body:**

```json
{
  "name": "小景（宫廷风）",
  "costume": "hanfu_yellow",
  "voice_type": "elegant_female"
}
```

**Response `data`:**

```json
{
  "digital_human_id": 1,
  "updated_at": "2026-04-28T11:00:00Z"
}
```

### 6.5 删除数字人

```
DELETE /admin/digital-humans/{digital_human_id}
```

**Response `data`:**

```json
{}
```

### 6.6 设为默认

```
PUT /admin/digital-humans/{digital_human_id}/default
```

**Response `data`:**

```json
{
  "digital_human_id": 1,
  "is_default": true
}
```

---

## 七、数据大屏（管理员）

### 7.1 概览数据

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
  "avg_response_time_ms": 1200
}
```

### 7.2 服务统计（按时间）

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

### 7.3 热门问答排行

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

### 7.4 满意度趋势

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

### 7.5 核心运营指标（数据大屏完整数据）

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

> 各字段结构与 7.1-7.4 中对应接口的 `data` 一致。

---

## 八、游客感受度报告（管理员）

### 8.1 游客洞察报告

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

### 8.2 情感趋势

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

### 8.3 关注点分析

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
    },
    {
      "category": "游览路线",
      "percentage": 20,
      "trend": "down"
    }
  ]
}
```

### 8.4 服务建议

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
    },
    {
      "issue": "下午2-4点为咨询高峰期响应延迟",
      "suggestion": "建议高峰期增加计算资源或启用缓存策略",
      "priority": "medium"
    }
  ]
}
```

| `priority` | 说明                   |
| ---------- | ---------------------- |
| `high`     | 高优先级，建议立即处理 |
| `medium`   | 中优先级               |
| `low`      | 低优先级               |

---

## 九、设置

### 9.1 获取用户设置

```
GET /settings?user_id=1
```

**Response `data`:**

```json
{
  "user_id": 1,
  "settings": {
    "tts_enabled": true,
    "default_digital_human_id": 1,
    "theme": "light",
    "language": "zh-CN"
  }
}
```

### 9.2 更新设置

```
PUT /settings
```

**Request Body:**

```json
{
  "user_id": 1,
  "settings": {
    "tts_enabled": false,
    "default_digital_human_id": 2
  }
}
```

**Response `data`:**

```json
{
  "saved": true
}
```

---

## 附录：WebSocket 通信流程

```
客户端                          服务端
  |                               |
  |--- WSS /ws/chat?token=xxx --->|  连接建立
  |<-- {"type":"pong"} ----------|  握手确认
  |                               |
  |--- {"type":"chat_message",   |  发送消息
  |     "content":"故宫建于哪年"}-->|
  |                               |
  |<-- {"type":"token",          |  LLM 逐 token 流式输出
  |     "content":"故宫"}--------|
  |<-- {"type":"token",          |
  |     "content":"（紫禁城）"}----|
  |<-- ...更多token...           |
  |                               |
  |<-- {"type":"done",           |  回复结束
  |     "full_content":"...",    |
  |     "audio_url":"...",       |
  |     "expression":"speaking"}->|
  |                               |
  |<-- {"type":"expression",     |  表情指令（可选独立下发）
  |     "expression":"smile",    |
  |     "duration_ms":3000}------|
```

### 心跳机制

- 客户端每 30 秒发送 `{"type": "ping"}`
- 服务端回复 `{"type": "pong"}`
- 连续 3 次未收到 pong 则客户端主动断开重连
