"""
消费分析 API 路由（管理员）

提供 5 个端点，用于管理端"消费分析"标签页的数据展示：

  GET /admin/consumption/overview          消费概览
  GET /admin/consumption/revenue-trend     营收趋势（按周/月）
  GET /admin/consumption/category-breakdown 消费类别分布
  GET /admin/consumption/demographics      客群画像
  GET /admin/consumption/full              完整数据（合并上述全部）

可选查询参数 `start_date` / `end_date`（YYYY-MM-DD），缺省时取全部记录。
前缀 /admin/consumption 由 api.py 统一添加。
"""
from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import require_admin
from app.services.consumption_service import (
    get_overview,
    get_revenue_trend,
    get_category_breakdown,
    get_demographics,
    get_full,
)

router = APIRouter()


def _parse_date(value: str | None) -> date | None:
    """Convert YYYY-MM-DD to date, or None if missing/invalid."""
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


# ── 概览 ──────────────────────────────────────────────────────────


@router.get("/overview")
def overview(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/consumption/overview — 总营收/人均消费/平均满意度等"""
    data = get_overview(db, _parse_date(start_date), _parse_date(end_date))
    return {"code": 200, "message": "success", "data": data}


# ── 营收趋势 ──────────────────────────────────────────────────────


@router.get("/revenue-trend")
def revenue_trend(
    period: str = Query("month", pattern="^(week|month)$"),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/consumption/revenue-trend?period=month — 营收按周/月聚合"""
    data = get_revenue_trend(db, period, _parse_date(start_date), _parse_date(end_date))
    return {"code": 200, "message": "success", "data": data}


# ── 消费类别分布 ──────────────────────────────────────────────────


@router.get("/category-breakdown")
def category_breakdown(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/consumption/category-breakdown — 门票/餐饮/购物/交通/娱乐金额与占比"""
    data = get_category_breakdown(db, _parse_date(start_date), _parse_date(end_date))
    return {"code": 200, "message": "success", "data": data}


# ── 客群画像 ──────────────────────────────────────────────────────


@router.get("/demographics")
def demographics(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/consumption/demographics — 年龄段 + 性别维度消费对比"""
    data = get_demographics(db, _parse_date(start_date), _parse_date(end_date))
    return {"code": 200, "message": "success", "data": data}


# ── 完整数据（合并）──────────────────────────────────────────────


@router.get("/full")
def full(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/consumption/full — 合并返回消费分析所需的全部数据"""
    data = get_full(db, _parse_date(start_date), _parse_date(end_date))
    return {"code": 200, "message": "success", "data": data}