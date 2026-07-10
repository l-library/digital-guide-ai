"""
游客感受度报告服务：基于 LLM 和关键词启发的游客体验分析。
为管理员后台提供情感趋势、游客洞察、关注点分析、服务建议、活跃时段等数据。
"""
import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func

from app.models import Conversation, Message
from app.services.llm_service import generate


# =============================================================================
# 情感分析 — 关键词启发（快速、无 LLM 成本）
# =============================================================================

_POSITIVE_KEYWORDS = [
    "谢谢", "很好", "不错", "太好了", "棒", "赞", "帮助", "感谢",
    "明白了", "清楚", "好的", "知道了", "优秀", "真棒", "厉害",
    "满意", "喜欢", "开心", "方便", "实用", "好用",
]

_NEGATIVE_KEYWORDS = [
    "不对", "不好", "不行", "没用", "差", "错误", "不理解",
    "不懂", "骗人", "假的", "失望", "垃圾", "太差", "糟糕",
    "没用处", "听不懂", "胡说", "乱说",
]


def _classify_sentiment(text: str) -> str:
    """根据关键词判断单条消息的情感倾向"""
    text_lower = text.lower()
    for kw in _POSITIVE_KEYWORDS:
        if kw in text_lower:
            return "positive"
    for kw in _NEGATIVE_KEYWORDS:
        if kw in text_lower:
            return "negative"
    return "neutral"


def _sentiment_distribution(messages: list) -> dict:
    """计算消息列表的情感分布比例"""
    if not messages:
        return {"positive": 0.0, "neutral": 0.0, "negative": 0.0}
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    for msg in messages:
        counts[_classify_sentiment(msg.content)] += 1
    total = len(messages)
    return {
        "positive": round(counts["positive"] / total, 2),
        "neutral": round(counts["neutral"] / total, 2),
        "negative": round(counts["negative"] / total, 2),
    }


# =============================================================================
# 关注点分析 — 纯关键词匹配（快速、确定性）
# =============================================================================

_CATEGORY_RULES = [
    (re.compile(r"门票|票价|价格|多少钱|收费|免费|优惠|半价|开放时间|几点开门|几点关门|开园|闭园|时间"), "门票与开放时间"),
    (re.compile(r"历史|朝代|皇帝|建造|修建|年代|古代|朝代|乾隆|康熙|明朝|清朝"), "历史文化"),
    (re.compile(r"建筑|风格|结构|设计|造型|屋檐|屋顶|柱子|雕刻|装饰"), "建筑特色"),
    (re.compile(r"路线|怎么走|游览|推荐|攻略|路线图|导航|地图|位置|在哪"), "游览路线"),
    (re.compile(r"卫生间|厕所|洗手间|餐饮|吃饭|餐厅|停车场|停车|设施|服务|商店"), "景区设施"),
    (re.compile(r"故事|传说|典故|神话|民间|据说|听说|流传"), "历史典故"),
]


def _categorize_message(text: str) -> str:
    """根据关键词将消息归类"""
    for pattern, category in _CATEGORY_RULES:
        if pattern.search(text):
            return category
    return "其他咨询"


# =============================================================================
# 公共辅助
# =============================================================================

def _parse_date_range(start_date: str, end_date: str) -> tuple:
    """解析日期字符串为 datetime 对象，end_date 含当天全天"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
    return start, end


def _period_dict(start_date: str, end_date: str) -> dict:
    return {"start": start_date, "end": end_date}


# =============================================================================
# 1. analyze_emotion — 情感趋势分析
# =============================================================================

def analyze_emotion(db, start_date: str, end_date: str) -> dict:
    """
    分析用户情感分布与趋势。
    - 分布统计：纯关键词启发（快速、不消耗 LLM）
    - 摘要：调用 LLM 生成文字总结
    """
    start, end = _parse_date_range(start_date, end_date)

    # 查询日期范围内所有用户消息
    messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Message.role == "user")
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .order_by(Message.created_at)
        .all()
    )

    # 按日期分组
    daily_groups = defaultdict(list)
    for msg in messages:
        date_key = msg.created_at.strftime("%Y-%m-%d") if msg.created_at else None
        if date_key:
            daily_groups[date_key].append(msg)

    # 每日趋势（按日期升序）
    trend = []
    for date_key in sorted(daily_groups.keys()):
        dist = _sentiment_distribution(daily_groups[date_key])
        trend.append({"date": date_key, **dist})

    # 整体分布
    overall = _sentiment_distribution(messages)

    # LLM 摘要（仅当有消息时才调用）
    summary = "暂无足够数据生成摘要"
    if messages:
        # 采样最多 30 条消息用于摘要分析
        sample = messages[:30] if len(messages) > 30 else messages
        questions_text = "\n".join(f"- {m.content[:100]}" for m in sample)
        from app.config.prompt_loader import get_emotion_summary_prompt
        prompt = get_emotion_summary_prompt(questions_text)
        try:
            summary = generate(prompt).strip()
        except Exception:
            summary = "情感摘要生成失败，请稍后重试"

    return {
        "period": _period_dict(start_date, end_date),
        "overall": overall,
        "trend": trend,
        "summary": summary,
    }


# =============================================================================
# 2. get_visitor_insight — 游客洞察报告
# =============================================================================

def get_visitor_insight(db, start_date: str, end_date: str) -> dict:
    """
    游客洞察：总游客数、总会话数、活跃时段、关注热点、平均会话长度。
    其中 top_interests 复用 analyze_focus 的结果进行转换。
    """
    start, end = _parse_date_range(start_date, end_date)

    # 日期范围内有消息的会话
    conv_subquery = (
        db.query(Message.conversation_id)
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .distinct()
        .subquery()
    )

    # 总游客数（DISTINCT user_id）
    total_visitors = (
        db.query(func.count(func.distinct(Conversation.user_id)))
        .filter(Conversation.id.in_(db.query(conv_subquery.c.conversation_id)))
        .scalar()
    ) or 0

    # 总会话数
    total_conversations = (
        db.query(func.count(func.distinct(conv_subquery.c.conversation_id)))
        .scalar()
    ) or 0

    # 活跃时段（按小时统计消息数）
    active_hours = get_active_hours(db, start_date, end_date)

    # 关注热点（复用 analyze_focus，转换 category → interest）
    focus_result = analyze_focus(db, start_date, end_date)
    top_interests = []
    for cat in focus_result.get("categories", []):
        top_interests.append({
            "interest": cat["category"],
            "percentage": cat["percentage"],
        })

    # 平均会话长度
    msg_counts = (
        db.query(
            Message.conversation_id,
            func.count(Message.id).label("cnt"),
        )
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .group_by(Message.conversation_id)
        .all()
    )
    if msg_counts:
        avg_conv_length = round(sum(c.cnt for c in msg_counts) / len(msg_counts), 1)
    else:
        avg_conv_length = 0.0

    return {
        "period": _period_dict(start_date, end_date),
        "total_visitors": total_visitors,
        "total_conversations": total_conversations,
        "active_hours": active_hours,
        "top_interests": top_interests,
        "avg_conversation_length": avg_conv_length,
    }


# =============================================================================
# 3. analyze_focus — 关注点分析（纯关键词）
# =============================================================================

def analyze_focus(db, start_date: str, end_date: str) -> dict:
    """
    分析游客关注点分类分布及趋势。
    纯关键词匹配，不调用 LLM。
    """
    start, end = _parse_date_range(start_date, end_date)

    messages = (
        db.query(Message)
        .filter(Message.role == "user")
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .order_by(Message.created_at)
        .all()
    )

    if not messages:
        return {
            "period": _period_dict(start_date, end_date),
            "categories": [],
        }

    # 按类别计数
    category_counts = defaultdict(int)
    first_half_counts = defaultdict(int)
    second_half_counts = defaultdict(int)

    mid_idx = len(messages) // 2
    for i, msg in enumerate(messages):
        cat = _categorize_message(msg.content)
        category_counts[cat] += 1
        if i < mid_idx:
            first_half_counts[cat] += 1
        else:
            second_half_counts[cat] += 1

    total = sum(category_counts.values())

    # 计算百分比和趋势
    categories = []
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        pct = round(count / total * 100, 1)
        first = first_half_counts.get(cat, 0)
        second = second_half_counts.get(cat, 0)
        if first > 0:
            change = (second - first) / first * 100
        elif second > 0:
            change = 100  # 从无到有视为上升
        else:
            change = 0

        if change > 20:
            trend = "up"
        elif change < -20:
            trend = "down"
        else:
            trend = "stable"

        categories.append({
            "category": cat,
            "percentage": pct,
            "trend": trend,
        })

    # 限制前 6 个类别
    categories = categories[:6]

    return {
        "period": _period_dict(start_date, end_date),
        "categories": categories,
    }


# =============================================================================
# 4. generate_suggestions — 改进建议（LLM）
# =============================================================================

def generate_suggestions(db, start_date: str, end_date: str) -> dict:
    """
    基于游客提问内容，通过 LLM 生成 3-5 条服务改进建议。
    """
    start, end = _parse_date_range(start_date, end_date)

    messages = (
        db.query(Message)
        .filter(Message.role == "user")
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .order_by(Message.created_at)
        .all()
    )

    if not messages:
        return {
            "period": _period_dict(start_date, end_date),
            "suggestions": [],
        }

    # 采样最多 50 条
    sample = messages[:50] if len(messages) > 50 else messages
    questions_text = "\n".join(f"- {m.content[:200]}" for m in sample)

    from app.config.prompt_loader import get_service_suggestions_prompt
    prompt = get_service_suggestions_prompt(questions_text)

    try:
        raw = generate(prompt).strip()
        # 清理可能的 markdown 代码块标记
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        suggestions = json.loads(raw)
        if not isinstance(suggestions, list):
            suggestions = []
    except Exception:
        suggestions = []

    return {
        "period": _period_dict(start_date, end_date),
        "suggestions": suggestions,
    }


# =============================================================================
# 5. get_active_hours — 活跃时段统计
# =============================================================================

def get_active_hours(db, start_date: str, end_date: str) -> dict:
    """
    按小时统计消息数量，返回 {"HH:00": count, ...}。
    """
    start, end = _parse_date_range(start_date, end_date)

    rows = (
        db.query(
            func.strftime("%H", Message.created_at).label("hour"),
            func.count(Message.id).label("cnt"),
        )
        .filter(Message.created_at >= start)
        .filter(Message.created_at < end)
        .group_by("hour")
        .order_by("hour")
        .all()
    )

    result = {}
    for row in rows:
        hour_key = f"{row.hour}:00"
        result[hour_key] = row.cnt

    return result
