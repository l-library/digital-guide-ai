"""
个性化推荐 API 路由
POST /recommend/route — 根据用户兴趣生成个性化游览路线
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import get_current_user  # visitor auth, NOT require_admin
from app.services.recommend_service import recommend_route

router = APIRouter()


@router.post("/route")
def get_route(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /recommend/route
    从 JWT 提取 user_id，自动推断兴趣并生成路线推荐。
    不需要客户端传 interests 参数。
    """
    result = recommend_route(current_user.id, db)
    if "error" in result:
        return {"code": 503, "message": result["error"], "data": {}}
    # Wrap single route in routes[] per api.md 2.4 schema
    return {
        "code": 200,
        "message": "success",
        "data": {"routes": [result]},
    }
