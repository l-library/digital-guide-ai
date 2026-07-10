"""
数据大屏 API 路由（管理员）
提供概览、服务统计、热门问答、满意度趋势、完整数据等 5 个端点。
前缀 /admin/dashboard 由 api.py 统一添加。
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import require_admin
from app.services.dashboard_service import (
    get_overview,
    get_service_stats,
    get_hot_questions,
    get_satisfaction_trend,
    get_full,
)

router = APIRouter()


# ── 7.1 概览数据 ──────────────────────────────────────────────────────


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/dashboard/overview — 今日/本周概览数据"""
    data = get_overview(db)
    return {"code": 200, "message": "success", "data": data}


# ── 7.2 服务统计（按时间）──────────────────────────────────────────────


@router.get("/service-stats")
def service_stats(
    period: str = Query("week", pattern="^(day|week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/dashboard/service-stats?period=week — 按时间聚合服务次数"""
    data = get_service_stats(db, period)
    return {"code": 200, "message": "success", "data": data}


# ── 7.3 热门问答排行 ───────────────────────────────────────────────────


@router.get("/hot-questions")
def hot_questions(
    top: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/dashboard/hot-questions?top=10 — 热门问答排行（含趋势）"""
    data = get_hot_questions(db, top)
    return {"code": 200, "message": "success", "data": data}


# ── 7.4 满意度趋势 ─────────────────────────────────────────────────────


@router.get("/satisfaction-trend")
def satisfaction_trend(
    period: str = Query("month", pattern="^(week|month)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/dashboard/satisfaction-trend?period=month — 满意度按日趋势"""
    data = get_satisfaction_trend(db, period)
    return {"code": 200, "message": "success", "data": data}


# ── 7.5 核心运营指标（数据大屏完整数据）────────────────────────────────


@router.get("/full")
def full(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """GET /admin/dashboard/full — 合并返回大屏所需的全部数据"""
    data = get_full(db)
    return {"code": 200, "message": "success", "data": data}
