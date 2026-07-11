"""
管理后台数据看板服务模块
提供纯 SQL 聚合统计函数，不依赖外部 LLM 服务。
每个函数只接收 SQLAlchemy Session 参数，返回符合 api.md 第七章规范的 dict。
"""
from datetime import datetime, timedelta
from sqlalchemy import func, text
from app.models import Conversation, Message, KnowledgeDoc, RecommendLog

# ---- 情感词词典（启发式方法，替代 report_service） ----

_POSITIVE_WORDS = ['谢谢', '很好', '不错', '太好了', '棒', '赞', '帮助', '感谢', '明白了', '清楚']
_NEGATIVE_WORDS = ['不对', '不好', '不行', '没用', '差', '错误', '不理解', '不懂']


def _classify_sentiment(content: str) -> str:
    """基于关键词的简单情感分类，返回 'positive' / 'negative' / 'neutral'"""
    if not content:
        return 'neutral'
    for word in _POSITIVE_WORDS:
        if word in content:
            return 'positive'
    for word in _NEGATIVE_WORDS:
        if word in content:
            return 'negative'
    return 'neutral'


def _calc_satisfaction(db, start_date=None, end_date=None):
    """计算满意度比率（0.0-1.0），可选日期范围过滤"""
    query = db.query(Message).filter(Message.role == 'user')
    if start_date is not None:
        query = query.filter(Message.created_at >= start_date)
    if end_date is not None:
        query = query.filter(Message.created_at < end_date)

    messages = query.all()
    if not messages:
        return 0.0

    positive = sum(1 for m in messages if _classify_sentiment(m.content) == 'positive')
    negative = sum(1 for m in messages if _classify_sentiment(m.content) == 'negative')
    neutral  = sum(1 for m in messages if _classify_sentiment(m.content) == 'neutral')
    total = positive + negative + neutral

    return round(positive / total, 4) if total > 0 else 0.0


# ============================================================
# 公开函数
# ============================================================

def get_overview(db):
    """
    概览数据（对应 api.md 7.1）

    返回:
      {
        "today_service_count": int,       # 今日用户消息数
        "today_visitor_count": int,       # 今日活跃访客数（去重 user_id）
        "week_service_count": int,        # 近 7 天用户消息数
        "total_knowledge_docs": int,      # 知识文档总数
        "avg_satisfaction": float,        # 平均满意度 (0.0 - 1.0)
        "avg_response_time_ms": float,    # 平均响应时间（毫秒）
      }
    """
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    # ---- 今日服务次数 ----
    today_service_count = db.query(func.count(Message.id)).filter(
        Message.role == 'user',
        Message.created_at >= today_start,
    ).scalar() or 0

    # ---- 今日访客数：今日有消息的对话的去重 user_id ----
    today_visitor_count = db.query(func.count(func.distinct(Conversation.user_id))).join(
        Message, Message.conversation_id == Conversation.id,
    ).filter(
        Message.created_at >= today_start,
    ).scalar() or 0

    # ---- 近 7 天服务次数 ----
    week_service_count = db.query(func.count(Message.id)).filter(
        Message.role == 'user',
        Message.created_at >= week_start,
    ).scalar() or 0

    # ---- 知识文档总数 ----
    total_knowledge_docs = db.query(func.count(KnowledgeDoc.id)).scalar() or 0

    # ---- 平均满意度（全体用户消息） ----
    avg_satisfaction = _calc_satisfaction(db)

    # ---- 推荐次数（今日） ----
    recommend_count = db.query(func.count(RecommendLog.id)).filter(
        RecommendLog.created_at >= today_start,
    ).scalar() or 0

    # ---- 平均响应时间：同一对话中连续 user → assistant 的时间差均值 ----
    sql = text("""
        WITH ranked AS (
            SELECT conversation_id, role, created_at,
                   ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY created_at) AS rn
            FROM messages
            WHERE role IN ('user', 'assistant')
        )
        SELECT AVG(
            (julianday(a.created_at) - julianday(u.created_at)) * 86400000
        )
        FROM ranked u
        JOIN ranked a ON u.conversation_id = a.conversation_id AND u.rn + 1 = a.rn
        WHERE u.role = 'user' AND a.role = 'assistant'
    """)
    result = db.execute(sql).scalar()
    avg_response_time_ms = round(float(result), 2) if result else 0.0

    return {
        "today_service_count": today_service_count,
        "today_visitor_count": today_visitor_count,
        "week_service_count": week_service_count,
        "total_knowledge_docs": total_knowledge_docs,
        "avg_satisfaction": round(avg_satisfaction * 5.0, 1),
        "avg_response_time_ms": avg_response_time_ms,
        "recommend_count": recommend_count,
    }


def get_service_stats(db, period='week'):
    """
    服务统计 - 按时间聚合（对应 api.md 7.2）

    参数:
      period: 'day'（逐小时）、'week'（逐日，默认）、'month'（逐日）
    返回:
      {"period": "...", "stats": [{"time": "2026-07-10 10:00", "count": int}, ...]}
    """
    now = datetime.utcnow()

    if period == 'day':
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        time_fmt = '%H:00'
    elif period == 'month':
        start = now - timedelta(days=30)
        time_fmt = '%Y-%m-%d'
    else:
        # week（默认）
        start = now - timedelta(days=7)
        time_fmt = '%Y-%m-%d'

    time_expr = func.strftime(time_fmt, Message.created_at)

    rows = (
        db.query(time_expr.label('time'), func.count(Message.id).label('count'))
        .filter(Message.role == 'user', Message.created_at >= start)
        .group_by('time')
        .order_by('time')
        .all()
    )

    stats = [{"time": row.time, "count": row.count} for row in rows]

    return {
        "period": period,
        "stats": stats,
    }


def get_hot_questions(db, top=10):
    """
    热门问答排行（对应 api.md 7.3）

    参数:
      top: 返回条数（默认 10）
    返回:
      {"items": [{"question": str, "count": int, "trend": "up"|"down"|"stable"}, ...]}

    trend 判定: 本周 vs 上周同问题计数变化 >20% → up/down，否则 stable
    """
    now = datetime.utcnow()
    this_week_start = now - timedelta(days=7)
    last_week_start = now - timedelta(days=14)
    last_week_end = this_week_start

    # ---- 本周 Top N 问题 ----
    this_week = dict(
        db.query(Message.content, func.count(Message.id))
        .filter(
            Message.role == 'user',
            Message.created_at >= this_week_start,
        )
        .group_by(Message.content)
        .order_by(func.count(Message.id).desc())
        .limit(top)
        .all()
    )

    if not this_week:
        return {"items": []}

    # ---- 上周同样问题的计数 ----
    questions = list(this_week.keys())
    last_week = dict(
        db.query(Message.content, func.count(Message.id))
        .filter(
            Message.role == 'user',
            Message.content.in_(questions),
            Message.created_at >= last_week_start,
            Message.created_at < last_week_end,
        )
        .group_by(Message.content)
        .all()
    )

    items = []
    for question, count in this_week.items():
        prev_count = last_week.get(question, 0)
        if prev_count == 0:
            trend = "up" if count > 0 else "stable"
        else:
            change = (count - prev_count) / prev_count
            if change > 0.2:
                trend = "up"
            elif change < -0.2:
                trend = "down"
            else:
                trend = "stable"
        items.append({"question": question, "count": count, "trend": trend})

    return {"items": items}


def get_satisfaction_trend(db, period='month'):
    """
    满意度趋势（对应 api.md 7.4）

    参数:
      period: 'week'（近 7 天）或 'month'（近 30 天，默认）
    返回:
      {"period": "month", "trend": [{"date": "2026-07-10", "avg_score": float, "response_count": int}, ...]}

    avg_score 按 (positive_count / total) * 5.0 计算，范围 0-5
    """
    now = datetime.utcnow()
    days = 7 if period == 'week' else 30

    trend = []
    # 从最早到最新
    for i in range(days - 1, -1, -1):
        date = now - timedelta(days=i)
        date_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        date_end = date_start + timedelta(days=1)

        messages = (
            db.query(Message)
            .filter(
                Message.role == 'user',
                Message.created_at >= date_start,
                Message.created_at < date_end,
            )
            .all()
        )

        total = len(messages)
        if total == 0:
            continue  # 无数据日期跳过

        positive = sum(1 for m in messages if _classify_sentiment(m.content) == 'positive')
        avg_score = round((positive / total) * 5.0, 1)

        trend.append({
            "date": date_start.strftime('%Y-%m-%d'),
            "avg_score": avg_score,
            "response_count": total,
        })

    return {
        "period": period,
        "trend": trend,
    }


def get_full(db):
    """
    核心运营指标 - 数据大屏完整数据（对应 api.md 7.5）

    合并 7.1-7.4 全部数据，减少前端请求次数。
    返回:
      {
        "overview": {...},           # get_overview 返回值
        "service_stats": [...],      # get_service_stats(period='week') 的 stats 数组
        "hot_questions": [...],      # get_hot_questions() 的 items 数组
        "satisfaction_trend": [...], # get_satisfaction_trend(period='month') 的 trend 数组
      }
    """
    overview = get_overview(db)
    service_stats_data = get_service_stats(db, 'week')
    hot_questions_data = get_hot_questions(db)
    satisfaction_trend_data = get_satisfaction_trend(db, 'month')

    return {
        "overview": overview,
        "service_stats": service_stats_data["stats"],
        "hot_questions": hot_questions_data["items"],
        "satisfaction_trend": satisfaction_trend_data["trend"],
    }
