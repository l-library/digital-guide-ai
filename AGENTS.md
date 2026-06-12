# AGENTS.md - digital-guide-ai

## 写在最前面

给用户的反馈应当以中文输出。
不要尝试进行git提交，版本控制由用户自己负责。

## 项目结构

两个独立应用：

- `backend/` — Python + FastAPI（异步）
- `frontend/` — Qt6 C++ / QML（CMake 构建）

无单体仓库工具。无共享工作区配置。

## 后端

**入口文件：** `backend/app/main.py`（FastAPI 应用，包含生命周期钩子，启动时预加载嵌入模型）

**API 路由：** `backend/app/api/api_v1/` — 当前包含 `/chat`（文本）和 `/chat_voice`（ASR→RAG→LLM→TTS 流水线，TTS/ASR 已注释）

**服务模块：**

- `rag_service.py` — Chroma 向量存储，父子文档结构；使用 `bge-small-zh-v1.5` 嵌入模型
- `llm_service.py` — 兼容 OpenAI 的客户端（通过环境变量配置为 DeepSeek V4 flash）

**需要的环境变量**

```
export LLM_API_KEY=sk-65d54b40f8a0480c86dedb316ce13304
export LLM_BASE_URL=https://api.deepseek.com
export LLM_MODEL_NAME=deepseek-v4-flash
export JWT_SECRET_KEY=<your-jwt-secret>  # 用于 JWT 签名和验证
```

**依赖管理：**
使用

```bash
conda activate DGA
```

启动虚拟环境，这个环境由用户自己管理，不要自行尝试安装依赖，碰到未安装的依赖就停下来，告知用户即可。

**Git 忽略的运行产物：**

- `backend/models/` — 嵌入模型（bge-small-zh-v1.5）
- `backend/vector_store/` — Chroma 持久化存储
- `backend/data/temp_audios/` — 上传/合成的音频
- `.env`

**数据导入脚本：** `backend/scripts/ingest_guide.py` 从 Word 文档构建向量存储。配置位于 `config_guide.py`。从 `backend/` 目录运行。

**手动测试：** `python backend/test_query.py`（预加载模型，运行 3 个示例查询并计时）。

**首次请求较慢** — 嵌入模型在 FastAPI 生命周期启动时加载，而非导入时加载。

## 前端

**构建系统：** 需要 CMake 3.16+、Qt 6.10+。

**入口：** `frontend/main.cpp` → 通过 `qt_add_qml_module` 实现 QML 应用

**QML 界面文件：** `frontend/qml/` — Main.qml、LoginPage.qml、ChatPage.qml、HistoryPage.qml、SettingsPage.qml

**C++ 后端类：** `frontend/src/` — ApiService、LoginManager、ConversationManager、HistoryManager、SettingsManager、VoiceInterface、DigitalHumanManager

**使用的 Qt 模块：** Quick、QuickControls2、Network、QuickEffects

**构建命令：**

```bash
cd frontend && mkdir -p build && cd build && cmake .. && cmake --build .
```

## 约定

- 代码使用中文（注释、提示、打印输出）。
- RAG 提示要求回复不超过 150 字符，无表情符号，无动作描述。
- 父子文档检索：子块用于相似度匹配，父文档用于上下文。
- 两个应用均未配置测试、CI、代码检查器或格式化工具。
- `PLAN.md` 为中文冲刺计划（8 周时间线）。
- `api.md` 为约定的前后端交互api

## 编码指南

减少常见LLM编码错误的行为指南。根据项目需求合并使用。

**权衡：** 本指南倾向于谨慎而非速度。对于简单任务，请自行判断。

### 1. 先思考，后编码

**不要假设。不要隐藏困惑。明确权衡。**

在实施之前：

- 明确说明你的假设。如果不确定，请提问。
- 如果存在多种解释，请全部列出——不要默默选择。
- 如果有更简单的方法，请提出来。必要时提出反对意见。
- 如果有不清楚的地方，停下来。指出困惑点。提问。

### 2. 简洁至上

**用最少的代码解决问题。不要推测性编码。**

- 不添加超出要求的特性。
- 不为一次性使用的代码设计抽象。
- 不提供未被要求的"灵活性"或"可配置性"。
- 不为不可能发生的场景编写错误处理。
- 如果你写了200行而本可以只用50行，重写它。

问问自己："资深工程师会觉得这过于复杂吗？"如果是，请简化。

### 3. 外科手术式修改

**只改动必须改动的部分。只清理自己的遗留问题。**

编辑现有代码时：

- 不要"改进"相邻的代码、注释或格式。
- 不要重构没有问题的部分。
- 遵循现有风格，即使你会有不同的做法。
- 如果发现不相关的死代码，提出来——不要删除它。

当你的改动产生遗留代码时：

- 移除因你的改动而变为未使用的导入/变量/函数。
- 除非被要求，不要删除已有的死代码。

检验标准：每一行改动都应直接追溯到用户的需求。

### 4. 目标驱动执行

**定义成功标准。循环验证直至达标。**

将任务转化为可验证的目标：

- "添加验证" → "编写针对无效输入的测试，然后使其通过"
- "修复Bug" → "编写可复现该Bug的测试，然后使其通过"
- "重构X" → "确保测试在重构前后都能通过"

对于多步骤任务，简要说明计划：

```
1. [步骤] → 验证：[检查项]
2. [步骤] → 验证：[检查项]
3. [步骤] → 验证：[检查项]
```

明确的成功标准让你能够独立迭代。模糊的标准（"让它工作"）则需要不断澄清。

---

**这些指南有效时表现为：** 差异对比中不必要的改动减少，因过度复杂化导致的重写减少，澄清性问题在实施之前而非错误之后提出。
