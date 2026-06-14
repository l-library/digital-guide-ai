"""认证端点：注册、登录、Token验证、登出"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

router = APIRouter(prefix="/auth", tags=["认证"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=32)
    password: str = Field(min_length=6, max_length=64)
    confirm_password: str
    display_name: str = Field(min_length=1, max_length=50, default="")


class LoginRequest(BaseModel):
    username: str
    password: str


def _make_token_data(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role})
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
    return {"token": token, "expires_at": expires_at}


def _user_brief(user: User) -> dict:
    return {
        "user_id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "avatar_url": user.avatar_url or "",
    }


@router.post("/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if req.password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="两次输入的密码不一致",
        )

    existing = db.query(User).filter(User.username == req.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="用户名已存在",
        )

    display_name = req.display_name if req.display_name else req.username

    user = User(
        username=req.username,
        password_hash=hash_password(req.password),
        display_name=display_name,
        role="visitor",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token_data = _make_token_data(user)
    return {
        "code": 200,
        "message": "注册成功",
        "data": {
            **_user_brief(user),
            **token_data,
        },
    }


@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == req.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token_data = _make_token_data(user)
    return {
        "code": 200,
        "message": "登录成功",
        "data": {
            **_user_brief(user),
            **token_data,
        },
    }


@router.get("/verify")
async def verify(current_user: User = Depends(get_current_user)):
    return {
        "code": 200,
        "message": "Token有效",
        "data": {
            "valid": True,
            "user_id": current_user.id,
            "username": current_user.username,
            "display_name": current_user.display_name,
            "role": current_user.role,
            "avatar_url": current_user.avatar_url or "",
        },
    }


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    return {"code": 200, "message": "已登出", "data": {}}


class UpdateProfileRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=50)
    avatar_url: str = Field(max_length=512, default="")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=64)
    new_password: str = Field(min_length=6, max_length=64)


@router.put("/profile")
def update_profile(req: UpdateProfileRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """更新当前用户的个人资料（昵称和头像）"""
    current_user.display_name = req.display_name
    current_user.avatar_url = req.avatar_url
    db.commit()
    db.refresh(current_user)
    return {
        "code": 200,
        "message": "个人资料已更新",
        "data": _user_brief(current_user),
    }


@router.put("/password")
def change_password(req: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """修改当前用户的密码"""
    if not verify_password(req.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码不正确",
        )
    current_user.password_hash = hash_password(req.new_password)
    db.commit()
    return {
        "code": 200,
        "message": "密码已修改",
        "data": {},
    }
