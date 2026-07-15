"""
消费分析服务模块（管理端）

提供基于 `visitor_consumption` 表的纯 SQL 聚合函数，覆盖：
  - 概览指标（总营收、人均消费、平均满意度、平均停留时长等）
  - 营收趋势（按月/按周）
  - 消费类别分布（门票/餐饮/购物/交通/娱乐）
  - 客群画像（年龄段 + 性别维度）

所有函数只接收 SQLAlchemy Session 及过滤参数，返回符合管理端响应信封规范的 dict。
不依赖任何外部 LLM 服务——纯粹的数据库聚合即可满足管理端展示需求。
"""
from datetime import date, timedelta

from sqlalchemy import func

from app.models import VisitorConsumption


# ── 年龄段分桶口径（与前端 QML 对齐）─────────────────────────────────
_AGE_BUCKETS = [
    ("<20", 0, 20),
    ("20-30", 20, 30),
    ("30-40", 30, 40),
    ("40-50", 40, 50),
    ("50-60", 50, 60),
    ("60+", 60, 200),
]


def _date_range(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    """根据入参计算实际查询的 [start, end) 区间。

    缺省时回退到：最早一条记录的日期 → 今天 + 1 天。
    `end_date` 视为闭区间，因此内部加一天转成开区间，方便 SQL 比较。
    """
    if start_date is None or end_date is None:
        # 不传日期就取全局范围
        return date(2000, 1, 1), date(2100, 1, 1)
    return start_date, end_date + timedelta(days=1)


# ============================================================
# 公开函数
# ============================================================

def get_overview(db, start_date: date | None = None, end_date: date | None = None):
    """消费概览指标。

    返回:
      {
        "total_revenue": float,        # 总营收（元）
        "total_visitors": int,          # 消费记录总数（≈ 访客人次）
        "avg_spending": float,          # 人均消费（元）
        "avg_satisfaction": float,      # 平均满意度（0-5）
        "avg_stay_duration": float,     # 平均停留时长（小时）
        "avg_group_size": float,        # 平均同行人数
        "median_spending": float,       # 中位数消费（剔除极端值）
      }
    """
    lo, hi = _date_range(start_date, end_date)

    total_revenue = db.query(func.sum(VisitorConsumption.total_cost)).filter(
        VisitorConsumption.visit_date >= lo,
        VisitorConsumption.visit_date < hi,
    ).scalar() or 0.0

    total_visitors = db.query(func.count(VisitorConsumption.id)).filter(
        VisitorConsumption.visit_date >= lo,
        VisitorConsumption.visit_date < hi,
    ).scalar() or 0

    if total_visitors == 0:
        return {
            "total_revenue": 0.0,
            "total_visitors": 0,
            "avg_spending": 0.0,
            "avg_satisfaction": 0.0,
            "avg_stay_duration": 0.0,
            "avg_group_size": 0.0,
            "median_spending": 0.0,
        }

    avg_spending = round(total_revenue / total_visitors, 2)

    avg_satisfaction = db.query(
        func.avg(VisitorConsumption.satisfaction)
    ).filter(
        VisitorConsumption.visit_date >= lo,
        VisitorConsumption.visit_date < hi,
    ).scalar() or 0.0

    avg_stay = db.query(func.avg(VisitorConsumption.stay_duration)).filter(
        VisitorConsumption.visit_date >= lo,
        VisitorConsumption.visit_date < hi,
    ).scalar() or 0.0

    avg_group = db.query(func.avg(VisitorConsumption.group_size)).filter(
        VisitorConsumption.visit_date >= lo,
        VisitorConsumption.visit_date < hi,
    ).scalar() or 0.0

    # 中位数：取全部 total_cost 升序排列，取中间值。SQLite 没有 PERCENTILE，Python 端计算。
    all_costs = [
        r[0] for r in db.query(VisitorConsumption.total_cost)
        .filter(VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi)
        .order_by(VisitorConsumption.total_cost.asc())
        .all()
    ]
    n = len(all_costs)
    if n == 0:
        median = 0.0
    elif n % 2 == 1:
        median = float(all_costs[n // 2])
    else:
        median = round((all_costs[n // 2 - 1] + all_costs[n // 2]) / 2.0, 2)

    return {
        "total_revenue": round(float(total_revenue), 2),
        "total_visitors": total_visitors,
        "avg_spending": avg_spending,
        "avg_satisfaction": round(float(avg_satisfaction), 2),
        "avg_stay_duration": round(float(avg_stay), 2),
        "avg_group_size": round(float(avg_group), 2),
        "median_spending": median,
    }


def get_revenue_trend(db, period: str = "month",
                      start_date: date | None = None,
                      end_date: date | None = None):
    """营收趋势：按月或按周聚合。

    返回:
      {"period": "month", "stats": [{"time": "2025-08", "revenue": float, "visitors": int}, ...]}
    """
    lo, hi = _date_range(start_date, end_date)

    if period == "week":
        # 按周用 SQLite 的 strftime('%Y-%W') （ISO 周编号）
        time_expr = func.strftime("%Y-%W", VisitorConsumption.visit_date)
    else:
        # month（默认）：YYYY-MM
        time_expr = func.strftime("%Y-%m", VisitorConsumption.visit_date)

    rows = (
        db.query(
            time_expr.label("time"),
            func.sum(VisitorConsumption.total_cost).label("revenue"),
            func.count(VisitorConsumption.id).label("visitors"),
        )
        .filter(VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi)
        .group_by("time")
        .order_by("time")
        .all()
    )

    stats = [
        {
            "time": row.time,
            "revenue": round(float(row.revenue or 0), 2),
            "visitors": int(row.visitors or 0),
        }
        for row in rows
    ]
    return {"period": period, "stats": stats}


def get_category_breakdown(db, start_date: date | None = None,
                           end_date: date | None = None):
    """消费类别分布：门票/餐饮/购物/交通/娱乐的金额与占比。

    返回:
      {
        "total": float,
        "categories": [
          {"name": "门票", "key": "ticket", "amount": float, "percentage": float},
          ...
        ]
      }
    """
    lo, hi = _date_range(start_date, end_date)

    ticket = db.query(func.sum(VisitorConsumption.ticket_cost)).filter(
        VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi
    ).scalar() or 0.0
    food = db.query(func.sum(VisitorConsumption.food_cost)).filter(
        VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi
    ).scalar() or 0.0
    shopping = db.query(func.sum(VisitorConsumption.shopping_cost)).filter(
        VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi
    ).scalar() or 0.0
    transport = db.query(func.sum(VisitorConsumption.transport_cost)).filter(
        VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi
    ).scalar() or 0.0
    entertainment = db.query(func.sum(VisitorConsumption.entertainment_cost)).filter(
        VisitorConsumption.visit_date >= lo, VisitorConsumption.visit_date < hi
    ).scalar() or 0.0

    total = ticket + food + shopping + transport + entertainment

    def _pct(x: float) -> float:
        return round(x / total * 100, 1) if total > 0 else 0.0

    return {
        "total": round(float(total), 2),
        "categories": [
            {"name": "门票", "key": "ticket", "amount": round(float(ticket), 2), "percentage": _pct(ticket)},
            {"name": "餐饮", "key": "food", "amount": round(float(food), 2), "percentage": _pct(food)},
            {"name": "购物", "key": "shopping", "amount": round(float(shopping), 2), "percentage": _pct(shopping)},
            {"name": "交通", "key": "transport", "amount": round(float(transport), 2), "percentage": _pct(transport)},
            {"name": "娱乐", "key": "entertainment", "amount": round(float(entertainment), 2), "percentage": _pct(entertainment)},
        ],
    }


def get_demographics(db, start_date: date | None = None,
                      end_date: date | None = None):
    """客群画像：年龄段 + 性别维度的消费对比。

    返回:
      {
        "age_groups": [
          {"group": "20-30", "visitors": int, "revenue": float, "avg_spending": float},
          ...
        ],
        "gender": [
          {"gender": "男", "visitors": int, "revenue": float, "avg_spending": float},
          ...
        ]
      }
    """
    lo, hi = _date_range(start_date, end_date)

    # 年龄段
    age_groups = []
    for label, lo_age, hi_age in _AGE_BUCKETS:
        rows = (
            db.query(
                func.count(VisitorConsumption.id).label("visitors"),
                func.sum(VisitorConsumption.total_cost).label("revenue"),
            )
            .filter(
                VisitorConsumption.visit_date >= lo,
                VisitorConsumption.visit_date < hi,
                VisitorConsumption.age >= lo_age,
                VisitorConsumption.age < hi_age,
            )
            .all()
        )
        visitors = int(rows[0].visitors or 0)
        revenue = float(rows[0].revenue or 0)
        age_groups.append({
            "group": label,
            "visitors": visitors,
            "revenue": round(revenue, 2),
            "avg_spending": round(revenue / visitors, 2) if visitors > 0 else 0.0,
        })

    # 性别
    gender_rows = (
        db.query(
            VisitorConsumption.gender.label("gender"),
            func.count(VisitorConsumption.id).label("visitors"),
            func.sum(VisitorConsumption.total_cost).label("revenue"),
        )
        .filter(
            VisitorConsumption.visit_date >= lo,
            VisitorConsumption.visit_date < hi,
        )
        .group_by(VisitorConsumption.gender)
        .all()
    )
    gender = []
    for r in gender_rows:
        visitors = int(r.visitors or 0)
        revenue = float(r.revenue or 0)
        gender.append({
            "gender": r.gender or "未知",
            "visitors": visitors,
            "revenue": round(revenue, 2),
            "avg_spending": round(revenue / visitors, 2) if visitors > 0 else 0.0,
        })

    return {"age_groups": age_groups, "gender": gender}


def get_full(db, start_date: date | None = None, end_date: date | None = None):
    """合并返回消费分析所需的全部数据，减少前端请求次数。

    返回:
      {
        "overview": {...},
        "revenue_trend": [...],         # 月度营收趋势
        "category_breakdown": {...},
        "demographics": {...}
      }
    """
    return {
        "overview": get_overview(db, start_date, end_date),
        "revenue_trend": get_revenue_trend(db, "month", start_date, end_date)["stats"],
        "category_breakdown": get_category_breakdown(db, start_date, end_date),
        "demographics": get_demographics(db, start_date, end_date),
    }