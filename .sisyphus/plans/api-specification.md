# 前后端通信接口规范 — api.md 编写

## TL;DR

> **Summary**: 根据赛题需求和现有项目结构，编写一份完整的前后端通信接口规范文档 `api.md`，覆盖认证、对话、消息、知识库管理、数字人管理、数据看板、游客感受度报告、系统设置、WebSocket 流式通信等模块。
> **Deliverables**: 1 份文件 — `api.md`（项目根目录）
> **Effort**: Short
> **Parallel**: NO（单文件）
> **Critical Path**: 探索分析 → 设计输出 → 文件写入 → 校验

## Context

### Original Request

> "根据这个题目和当前项目的具体情况，设计一套前后端通信接口规范，并写入到 api.md 文件中"

### Interview Summary

用户提供了 `subject.txt`（赛题要求）和当前项目代码。经过充分探索：

- 后端已有：`/api/v1/chat`（文本问答）、`/api/v1/chat_voice`（语音问答）、`/api/v1/download_audio`
- `admin.py` 和 `dashboard.py` 为空文件，尚未实现路由
- 前端 `ApiService` 定义了完整的方法签名（auth、conversations、messages、knowledge docs、digital humans、settings、export），但当前均使用 `QTimer` 模拟数据，未对接真实 API
- 前端 `voiceinterface.h` 定义了语音交互状态机
- 项目技术栈：FastAPI + Qt6/QML + SQLite + Chroma

### Metis Review (gaps addressed)

- 前端现有的 `ApiService` 信号签名与后端 API 需要严格对齐
- WebSocket 流式接口对于 <5s 延迟体验至关重要
- 所有管理侧接口需要 JWT + 角色鉴权

## Work Objectives

### Core Objective

编写一份完整的 `api.md`，作为前后端开发人员（以及 AI 编码代理）的通信契约。

### Deliverables

- `api.md`：包含全部 REST + WebSocket 接口定义、数据模型、错误码规范、前后端映射表

### Definition of Done

- 文件 `api.md` 存在于项目根目录
- 覆盖 subject.txt 中列出的全部业务场景（游客交互侧 + 管理后台侧）
- REST API 的请求/响应格式具体到字段级别
- WebSocket 接口定义了完整消息类型和时序
- 包含错误码规范
- 包含前端现有 ApiService 信号到 API 的完整映射表
- 数据模型（User、Conversation、Message、KnowledgeDoc、DigitalHuman、DashboardOverview、SentimentReport）均已定义

### Must Have

- 认证模块（登录/注册/登出/Token 验证）
- 对话管理 CRUD
- 消息查询（分页）
- 文本问答 + 语音问答 REST 接口
- WebSocket 流式聊天接口（流式输出的核心体验）
- 知识文档上传、列表、删除
- 数字人列表、配置更新
- 数据看板概览 + 热门问答 + 满意度趋势
- 游客感受度报告获取
- 系统设置读取/写入
- 统一的 JSON 响应格式（code/message/data）
- 分页规范
- JWT Bearer Token 认证说明

### Must NOT Have

- 不包含数据库建表 SQL 语句
- 不包含后端代码实现
- 不包含前端 C++/QML 代码改动
- 不涉及部署或 CI/CD 配置

## Verification Strategy

> ZERO HUMAN INTERVENTION — 文件生成后自动验证。

- **Test decision**: 无（文档规范，不可自动测试）
- **QA policy**: 文件内容完整性检查（通过 grep 确认所有必要章节存在）
- **Evidence**: 通过 grep 验证章节标题覆盖率 ≥ 90%

## Execution Strategy

### Parallel Execution Waves

Wave 1: [单文件编写] — 单个任务

### Dependency Matrix

| Task | Blocks | Blocked By |
| ---- | ------ | ---------- |
| 1    | —     | —         |

### Agent Dispatch Summary

Wave 1 → 1 task → 文档编写

## TODOs

- [x] **What to do**: 在项目根目录创建 `/home/liborui/Windows/digital-guide-ai/api.md`，内容需完整覆盖以下章节：


  1. **通用约定** — 响应格式（成功/错误/分页）、JWT 认证方式、用户角色（visitor/admin）、基础路径 `/api/v1`、通用请求头
  2. **数据模型定义** — User、Conversation、Message（含 role/content_type 枚举）、KnowledgeDoc（含 status 枚举）、DigitalHuman、DashboardOverview、SentimentReport 的完整 JSON Schema
  3. **接口总览表** — 全部 25+ 个接口的 Method + Path + 说明，按模块分组展示
  4. **认证模块** — POST /auth/login、POST /auth/register、POST /auth/logout、GET /auth/verify
  5. **对话模块** — POST /conversations、GET /conversations、GET /conversations/grouped、GET /conversations/{id}、DELETE /conversations/{id}、GET /conversations/{id}/export
  6. **消息模块** — GET /conversations/{conv_id}/messages（分页）
  7. **聊天模块** — POST /chat/text（已有）、POST /chat/voice（已有，保留原有路由）、GET /chat/audio/{filename}（已有）
  8. **知识库管理** — POST /admin/knowledge/upload（multipart）、GET /admin/knowledge、GET /admin/knowledge/{id}、DELETE /admin/knowledge/{id}、POST /admin/knowledge/{id}/reingest
  9. **数字人管理** — GET /admin/digital-humans、PUT /admin/digital-humans/{id}、PUT /admin/digital-humans/{id}/default
  10. **数据看板** — GET /admin/dashboard/overview、GET /admin/dashboard/popular-qa、GET /admin/dashboard/satisfaction-trend
  11. **游客感受度报告** — GET /admin/reports/sentiment、GET /admin/reports/sentiment/history
  12. **系统设置** — GET /settings/{key}、PUT /settings/{key}
  13. **WebSocket 流式接口** — ws://.../chat/stream，定义 6 种消息类型（text/audio 请求，ack/status/delta/done/recommendation/error 响应），含完整交互时序图
  14. **错误码规范** — 覆盖 40000-50005 的所有错误码
  15. **附录：前后端映射表** — 前端 ApiService 现有 15+ 个方法 → 对应 API 路径

  **Must NOT do**:

  - 不包含 SQL 或后端实现代码
  - 不修改任何现有文件
  - 不添加超出 subject.txt 范围的业务模块

  **Recommended Agent Profile**:

  - Category: `writing` - 文档编写任务，需要条理清晰的中文技术文档能力
  - Skills: 无
  - Omitted: 所有技能（纯文档不涉及编码）

  **Parallelization**: Can Parallel: NO | Wave 1 | Blocks: — | Blocked By: —

  **References**:

  - Pattern: `backend/app/api/api_v1/endpoints/chat.py` - 现有 chat/chat_voice/download_audio 路由定义，需要保持向后兼容
  - Pattern: `frontend/src/apiservice.h` - 前端所有 API 方法签名，必须全部映射到新 API
  - Pattern: `frontend/src/apiservice.cpp` - 现有 sendAiMessage 中硬编码的 `http://121.43.27.51:8000/chat` 端点，需要在新规范中覆盖
  - Pattern: `backend/app/main.py` - 基础路径配置 `/api/v1`
  - Pattern: `backend/app/api/api_v1/api.py` - 现有路由注册方式
  - External: `subject.txt` - 赛题对需求、业务场景、技术栈的完整描述
  - External: `AGENTS.md` - 项目约定（中文注释、RAG 限制 150 字等）
  - External: `PLAN.md` - 项目开发时间线，确保 API 规划匹配 Week 1-6 的开发节奏

  **Acceptance Criteria**:

  - [ ] 文件 `api.md` 存在于 `/home/liborui/Windows/digital-guide-ai/api.md`
  - [ ] 包含全部 15 个章节（可通过 grep "^## " 验证）
  - [ ] 所有 REST 接口路径以 `/api/v1` 开头
  - [ ] 每个接口均有明确的 Request/Response JSON 结构示例
  - [ ] 数据模型定义了至少 User、Conversation、Message、KnowledgeDoc、DigitalHuman 5 个实体
  - [ ] WebSocket 接口定义了完整的 6 种消息类型
  - [ ] 错误码覆盖了 auth(40100/40101/40102)、notfound(40400-40403)、server(50000-50005) 三类
  - [ ] 附录中包含前端 ApiService 信号到 API 的映射表

  **QA Scenarios**:

  ```
  Scenario: 验证文件存在和章节完整性
    Tool: Bash
    Steps: 
      - ls /home/liborui/Windows/digital-guide-ai/api.md 确认存在
      - grep "^## " /home/liborui/Windows/digital-guide-ai/api.md 列出所有二级标题
      - 统计二级标题数量应 ≥ 12 个
    Expected: 文件存在，二级标题覆盖主要模块
    Evidence: .sisyphus/evidence/api-md-sections.txt

  Scenario: 验证路径前缀一致性
    Tool: Bash
    Steps:
      - grep -oP '/api/v1/[a-z-]+' /home/liborui/Windows/digital-guide-ai/api.md | sort -u
    Expected: 所有路径以 /api/v1 开头，无遗漏
    Evidence: .sisyphus/evidence/api-md-paths.txt

  Scenario: 验证前端映射表完整性
    Tool: Bash
    Steps:
      - grep -c "api/v1" /home/liborui/Windows/digital-guide-ai/api.md
      - grep "|" 所在的 ApiService 方法行数（附录表格行数）
    Expected: 映射表行数 ≥ 15 行
    Evidence: .sisyphus/evidence/api-md-mapping.txt
  ```

  **Commit**: YES | Message: `docs: add frontend-backend API specification (api.md)` | Files: [api.md]

## Final Verification Wave (MANDATORY — after ALL implementation tasks)

- [ ] F1. Plan Compliance Audit — oracle
- [ ] F2. Code Quality Review — unspecified-high
- [ ] F3. Real Manual QA — unspecified-high
- [ ] F4. Scope Fidelity Check — deep

## Commit Strategy

不需要提交

## Success Criteria

- `api.md` 文件完整、格式规范
- 所有 subject.txt 中的业务场景均有对应 API 覆盖
- 前端现有 ApiService 方法均可在 API 中找到对应端点
