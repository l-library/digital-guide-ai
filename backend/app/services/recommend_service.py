"""
个性化推荐服务模块
提供兴趣推理和路线推荐功能。
"""
import json
import re
from datetime import datetime, timedelta

from app.models import User, Conversation, Message, RecommendLog
from app.services import llm_service, rag_service
from app.services import report_service

_SCENIC_SPOT_NAME = "故宫"  # TODO: make configurable

# 6 个已知的关注类别，用于兴趣推理 prompt
_KNOWN_CATEGORIES = [
    "历史文化",
    "建筑特色",
    "游览路线",
    "景区设施",
    "历史典故",
    "门票与开放时间",
]


# =============================================================================
# infer_interests — LLM 推断用户兴趣标签
# =============================================================================


def infer_interests(user_id: int, db) -> list[str]:
    """
    根据用户最近的聊天消息，通过 LLM 推断兴趣标签。
    若兴趣缓存仍在 1 小时内，直接返回缓存结果。
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return []

    # ---- 缓存守卫：1 小时内不重复调用 LLM ----
    if user.interests and user.last_interest_update:
        try:
            parsed = json.loads(user.interests)
            if parsed and isinstance(parsed, list):
                age = datetime.utcnow() - user.last_interest_update
                if age < timedelta(hours=1):
                    return parsed
        except json.JSONDecodeError:
            pass  # 缓存损坏，继续走 LLM 路径

    # ---- 查询最近 20 条用户消息 ----
    messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.user_id == user_id, Message.role == "user")
        .order_by(Message.created_at.desc())
        .limit(20)
        .all()
    )

    if len(messages) < 3:
        return []

    # ---- 构建内联 prompt ----
    user_lines = "\n".join(
        f"- {m.content[:100]}" for m in messages
    )
    categories_text = "、".join(_KNOWN_CATEGORIES)

    prompt = (
        f"你是一个景区导览系统的用户兴趣分析助手。以下是一位游客最近向导游AI提问的记录：\n\n"
        f"{user_lines}\n\n"
        f"请根据以上提问内容，推断这位游客最可能的兴趣领域。"
        f"从以下类别中选择最多 5 个：{categories_text}。\n\n"
        f"请只返回一个 JSON 数组，不要包含任何其他内容。\n"
        f'示例：["历史文化", "建筑特色"]'
    )

    # ---- 调用 LLM 并解析 ----
    parsed = _call_llm_and_parse_json(prompt)
    if not parsed:
        # 解析失败，保留旧兴趣（如果有的话），不覆盖
        if user.interests:
            try:
                return json.loads(user.interests)
            except json.JSONDecodeError:
                pass
        return []

    # ---- 持久化 ----
    user.interests = json.dumps(parsed, ensure_ascii=False)
    user.last_interest_update = datetime.utcnow()
    db.commit()

    return parsed


# =============================================================================
# recommend_route — 个性化路线推荐
# =============================================================================


def recommend_route(user_id: int, db) -> dict:
    """
    根据用户兴趣标签，结合 RAG 检索和 LLM 生成个性化游览路线。
    若兴趣为空则进入冷启动模式；若 RAG 无上下文则返回经典路线兜底。
    """
    interests = infer_interests(user_id, db)

    # ---- 冷启动：无兴趣标签时用全局热门类别 ----
    if not interests:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%d")
        focus = report_service.analyze_focus(db, thirty_days_ago, today)
        cats = focus.get("categories", [])
        if cats:
            interests = [c["category"] for c in cats[:3]]
        else:
            interests = ["历史文化", "建筑特色", "游览路线"]

    # ---- RAG 检索 ----
    query = f"{_SCENIC_SPOT_NAME} {' '.join(interests)} 景点推荐"
    context_list = rag_service.retrieve_context(query, k=5)

    # ---- RAG 空结果兜底 —— 跳过 LLM ----
    if not context_list:
        return {
            "name": "经典游览路线",
            "duration_minutes": 120,
            "spots": [
                {
                    "name": "主要景点",
                    "description": "请参考景区导览获取详细信息",
                    "estimated_minutes": 60,
                }
            ],
            "highlights": ["推荐根据个人兴趣进一步探索"],
            "match_reason": "暂无足够数据生成个性化推荐，已为您展示经典路线",
        }

    # ---- 构建内联 LLM prompt ----
    context_text = "\n\n---\n\n".join(context_list)
    interests_text = "、".join(interests)

    prompt = (
        f"你是一个景区导览系统的路线规划助手。请根据以下信息为游客生成一条个性化游览路线。\n\n"
        f"景区名称：{_SCENIC_SPOT_NAME}\n"
        f"游客兴趣标签：{interests_text}\n\n"
        f"参考资料：\n{context_text}\n\n"
        f"请返回一个 JSON 对象（不要包含任何其他内容），格式如下：\n"
        f'{{"name": "路线名称", "duration_minutes": 120, '
        f'"spots": [{{"name": "景点名", "description": "简介", "estimated_minutes": 30}}], '
        f'"highlights": ["亮点1", "亮点2"], "match_reason": "匹配理由"}}\n\n'
        f"要求：\n"
        f"- spots 中每个景点的 description 不超过 150 字\n"
        f"- duration_minutes 为整数\n"
        f"- match_reason 说明该路线为何适合该游客的兴趣\n"
        f"- 只返回 JSON，不要有任何解释或额外文字"
    )

    # ---- 调用 LLM ----
    try:
        raw = llm_service.generate(prompt)
        parsed = _parse_json(raw)
    except Exception:
        return {"error": "推荐服务暂不可用"}

    if parsed and isinstance(parsed, dict):
        # 记录推荐日志
        try:
            log = RecommendLog(
                user_id=user_id,
                interests_used=json.dumps(interests, ensure_ascii=False),
                created_at=datetime.utcnow(),
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()  # 日志记录失败不影响主流程
        return parsed

    return {"error": "推荐服务暂不可用"}


# =============================================================================
# 内部辅助
# =============================================================================


def _parse_json(raw: str):
    """
    解析 LLM 返回的 JSON 字符串，处理常见的格式问题。
    尝试 2 次：第一次直接解析，第二次去掉 markdown 代码块后重试。
    """
    attempts = [
        raw.strip(),
        re.sub(r"^```(?:json)?\s*\n?", "", raw.strip()),
    ]

    for i, text in enumerate(attempts):
        text = re.sub(r"\n?\s*```$", "", text)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if i == 0:
                continue  # 第一次失败，尝试清理后重试
    return None


def _call_llm_and_parse_json(prompt: str):
    """调用 LLM 并解析为 JSON，失败时重试一次。"""
    for attempt in range(2):
        try:
            raw = llm_service.generate(prompt)
            result = _parse_json(raw)
            if result is not None:
                return result
        except Exception:
            if attempt == 1:
                return None
    return None
