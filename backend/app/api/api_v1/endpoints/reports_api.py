"""
游客感受度报告 API 端点。
所有端点均需 admin 权限。
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import require_admin
from app.services.report_service import (
    analyze_emotion,
    analyze_focus,
    generate_suggestions,
    get_visitor_insight,
)

router = APIRouter()


def ok(data):
    return {"code": 200, "message": "success", "data": data}


def fail(code: int, message: str):
    return {"code": code, "message": message, "data": {}}


def _validate_dates(start_date: str, end_date: str):
    """验证日期参数是否存在，不存在则抛出 400"""
    if not start_date or not end_date:
        raise HTTPException(
            status_code=400,
            detail="缺少必传参数 start_date 和 end_date（格式: YYYY-MM-DD）",
        )


@router.get("/visitor-insight")
def visitor_insight(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _validate_dates(start_date, end_date)
    data = get_visitor_insight(db, start_date, end_date)
    return ok(data)


@router.get("/emotion-trend")
def emotion_trend(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _validate_dates(start_date, end_date)
    data = analyze_emotion(db, start_date, end_date)
    return ok(data)


@router.get("/focus-analysis")
def focus_analysis(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _validate_dates(start_date, end_date)
    data = analyze_focus(db, start_date, end_date)
    return ok(data)


@router.get("/service-suggestions")
def service_suggestions(
    start_date: str = Query(...),
    end_date: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    _validate_dates(start_date, end_date)
    data = generate_suggestions(db, start_date, end_date)
    return ok(data)
