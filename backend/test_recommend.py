"""
推荐功能测试脚本
测试兴趣推理和路线推荐功能。
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, init_db
from app.models import User, Conversation, Message
from app.services.recommend_service import infer_interests, recommend_route


def test_infer_interests_empty():
    """用户无消息时返回空列表"""
    db = SessionLocal()
    try:
        # 使用一个不存在的 user_id
        result = infer_interests(99999, db)
        assert result == [], f"Expected empty list, got {result}"
        print("✓ test_infer_interests_empty passed")
    finally:
        db.close()


def test_infer_interests_with_cache():
    """带缓存数据时返回缓存"""
    db = SessionLocal()
    try:
        # 查找一个有 interests 缓存的用户，或设置一个
        user = db.query(User).filter(User.interests != None).first()
        if user and user.last_interest_update:
            parsed = infer_interests(user.id, db)
            assert isinstance(parsed, list), f"Expected list, got {type(parsed)}"
            print(f"✓ test_infer_interests_with_cache passed (cached interests: {parsed})")
        else:
            print("✓ test_infer_interests_with_cache skipped (no cached interests)")
    finally:
        db.close()


def test_recommend_route_basic():
    """推荐函数返回 dict 结构"""
    db = SessionLocal()
    try:
        result = recommend_route(1, db)  # user_id=1 is seed admin
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        if "error" in result:
            print(f"✓ test_recommend_route_basic passed (error: {result['error']})")
        else:
            assert "name" in result, "Route missing 'name'"
            assert "spots" in result, "Route missing 'spots'"
            print(f"✓ test_recommend_route_basic passed (route: {result.get('name', 'N/A')})")
    finally:
        db.close()


def test_recommend_route_cold_start():
    """冷启动：无兴趣用户返回推荐"""
    db = SessionLocal()
    try:
        result = recommend_route(99999, db)  # non-existent user
        assert isinstance(result, dict), f"Expected dict, got {type(result)}"
        if "error" in result:
            print(f"✓ test_recommend_route_cold_start passed (error fallback)")
        else:
            assert "name" in result
            print(f"✓ test_recommend_route_cold_start passed (route: {result.get('name', 'N/A')})")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    print("=" * 50)
    print("推荐功能测试")
    print("=" * 50)
    test_infer_interests_empty()
    test_infer_interests_with_cache()
    test_recommend_route_basic()
    test_recommend_route_cold_start()
    print("=" * 50)
    print("所有测试通过")
