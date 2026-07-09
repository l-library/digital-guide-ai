"""管理员用户管理服务：用户 CRUD、级联删除、状态切换"""
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models import User, Conversation, Message
from app.services.auth_service import hash_password


def list_users(db: Session, page: int = 1, page_size: int = 20, search: str = ""):
    """分页查询用户列表，search 匹配 username 或 display_name"""
    query = db.query(User)
    if search:
        query = query.filter(
            or_(
                User.username.contains(search),
                User.display_name.contains(search),
            )
        )
    total = query.count()
    users = (
        query.order_by(User.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [u.to_dict() for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def create_user(db: Session, username: str, password: str, display_name: str) -> User:
    """创建新用户（角色为 visitor，默认激活）"""
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise ValueError("用户名已存在")
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name=display_name,
        role="visitor",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_detail(db: Session, user_id: int):
    """获取用户详情，包含对话数量统计"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None
    conv_count = (
        db.query(func.count(Conversation.id))
        .filter(Conversation.user_id == user_id)
        .scalar()
    )
    detail = user.to_dict()
    detail["conversation_count"] = conv_count
    return detail


def update_user(
    db: Session,
    user_id: int,
    display_name: str | None = None,
    phone: str | None = None,
    email: str | None = None,
    avatar_url: str | None = None,
    is_active: bool | None = None,
):
    """部分更新用户信息，is_active 切换时递增 token_version，禁止修改超级管理员的 is_active"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # 禁止修改超级管理员的激活状态
    if user_id == 1 and is_active is not None:
        raise ValueError("不能修改超级管理员的激活状态")

    # 部分更新传入的非 None 字段
    if display_name is not None:
        user.display_name = display_name
    if phone is not None:
        user.phone = phone
    if email is not None:
        user.email = email
    if avatar_url is not None:
        user.avatar_url = avatar_url

    # is_active 发生变化时递增 token_version，使旧 token 失效
    if is_active is not None and is_active != user.is_active:
        user.is_active = is_active
        user.token_version += 1

    db.commit()
    db.refresh(user)
    return user


def delete_user_cascade(db: Session, user_id: int):
    """级联删除用户及其所有对话、消息，并清理 Chroma 向量"""
    if user_id == 1:
        raise ValueError("不能删除超级管理员")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False

    # 查询该用户所有对话 ID（用于后续 Chroma 清理）
    conversations = (
        db.query(Conversation.id)
        .filter(Conversation.user_id == user_id)
        .all()
    )
    conversation_ids = [c[0] for c in conversations]

    # 事务：删除关联 Message → 删除 Conversation → 删除 User
    if conversation_ids:
        db.query(Message).filter(
            Message.conversation_id.in_(conversation_ids)
        ).delete(synchronize_session=False)
        db.query(Conversation).filter(
            Conversation.user_id == user_id
        ).delete(synchronize_session=False)

    db.delete(user)
    db.commit()

    # 事务提交后，best-effort 清理 Chroma 向量
    _cleanup_user_vectors(user_id, conversation_ids)

    return True


def toggle_user_status(db: Session, user_id: int):
    """翻转用户激活状态，递增 token_version，禁止禁用超级管理员"""
    if user_id == 1:
        raise ValueError("不能禁用超级管理员")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    user.is_active = not user.is_active
    user.token_version += 1
    db.commit()
    db.refresh(user)
    return user.is_active


def _cleanup_user_vectors(user_id: int, conversation_ids: list[int]) -> None:
    """best-effort 清理 Chroma 向量库中该用户的对话向量"""
    if not conversation_ids:
        return

    try:
        from langchain_chroma import Chroma
        from app.services.knowledge_service import VECTOR_STORE_DIR, _get_embeddings

        embeddings = _get_embeddings()
        vectorstore = Chroma(
            collection_name="lingshan_knowledge",
            persist_directory=VECTOR_STORE_DIR,
            embedding_function=embeddings,
        )

        for conv_id in conversation_ids:
            try:
                vectorstore.delete(where={"conversation_id": str(conv_id)})
                print(f"Chroma 向量已清理: user_id={user_id}, conversation_id={conv_id}")
            except Exception as e:
                print(f"Chroma 向量清理失败: user_id={user_id}, conversation_id={conv_id}, 错误: {e}")
    except Exception as e:
        print(f"Chroma 连接/清理失败: user_id={user_id}, 错误: {e}")
