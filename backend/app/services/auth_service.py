"""认证服务：密码哈希、JWT 生成/验证、获取当前用户依赖、种子管理员初始化"""
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User

# 密码哈希（bcrypt）
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_ctx.verify(plain_password, hashed_password)


# JWT 令牌（HS256）
# SECRET_KEY 必须在环境变量中设置，不提供硬编码默认值
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if SECRET_KEY is None:
    raise RuntimeError(
        "环境变量 JWT_SECRET_KEY 未设置。请设置一个足够复杂的密钥。"
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 7 * 24 * 60


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    创建 JWT access token。

    参数:
        data: 至少包含 "sub"（用户 ID）和 "role" 的字典
        expires_delta: 可选的自定义过期时间，默认 7 天
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta if expires_delta else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


# FastAPI 依赖：获取当前用户
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证令牌或令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌中缺少用户标识",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证令牌中的用户标识无效",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# 种子管理员初始化

def init_seed_user(db: Session) -> None:
    existing = db.query(User).filter(User.id == 1).first()
    if existing is not None:
        return

    admin_user = User(
        id=1,
        username="admin",
        password_hash=hash_password("admin123"),
        display_name="管理员",
        role="admin",
    )
    db.add(admin_user)
    db.commit()
    print("[auth] 种子管理员账号已创建（admin/admin123）")
