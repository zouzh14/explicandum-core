"""
用户管理API模块
提供管理员用户管理功能的API端点
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc, asc
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.base import get_db
from app.database.models import User, InvitationCode
from app.schema.models import UserResponse
from app.core.auth import get_password_hash
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings
import traceback
from jose import jwt

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    from app.core import auth

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = auth.decode_access_token(token)
    if payload is None:
        raise credentials_exception
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


router = APIRouter(prefix="/admin/users", tags=["user-management"])


def check_admin_permission(current_user: User):
    """检查管理员权限"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )


@router.get("/", response_model=dict)
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    role: Optional[str] = Query(None, description="角色筛选"),
    is_temp: Optional[bool] = Query(None, description="是否临时用户"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序顺序"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户列表（分页）
    """
    check_admin_permission(current_user)

    # 构建查询
    query = db.query(User)

    # 搜索过滤
    if search:
        search_filter = or_(
            User.username.ilike(f"%{search}%"),
            User.email.ilike(f"%{search}%"),
            User.id.ilike(f"%{search}%"),
        )
        query = query.filter(search_filter)

    # 角色过滤
    if role:
        query = query.filter(User.role == role)

    # 临时用户过滤
    if is_temp is not None:
        query = query.filter(User.is_temp == is_temp)

    # 排序
    if hasattr(User, sort_by):
        sort_column = getattr(User, sort_by)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

    # 总数统计
    total = query.count()

    # 分页
    offset = (page - 1) * size
    users = query.offset(offset).limit(size).all()

    # 转换为响应格式
    user_list = []
    for user in users:
        user_response = UserResponse(
            id=user.id,
            username=user.username,
            email=user.email or "",
            role=user.role,
            tokenQuota=user.token_quota,
            tokensUsed=user.tokens_used,
            requestCount=user.request_count,
            lastRequestAt=int(user.last_request_at.timestamp() * 1000)
            if user.last_request_at
            else None,
            createdAt=int(user.created_at.timestamp() * 1000),
            registrationIp=user.registration_ip or "unknown",
            isTemp=user.is_temp,
            expiresAt=int(user.expires_at.timestamp() * 1000)
            if user.expires_at
            else None,
        )
        user_list.append(user_response.model_dump())

    return {
        "users": user_list,
        "pagination": {
            "page": page,
            "size": size,
            "total": total,
            "pages": (total + size - 1) // size,
        },
    }


@router.get("/stats", response_model=dict)
async def get_user_stats(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    获取用户统计信息
    """
    check_admin_permission(current_user)

    # 基础统计
    total_users = db.query(User).count()
    admin_count = db.query(User).filter(User.role == "admin").count()
    researcher_count = db.query(User).filter(User.role == "researcher").count()
    user_count = db.query(User).filter(User.role == "user").count()
    temp_count = db.query(User).filter(User.is_temp == True).count()

    # 活跃用户统计（最近7天有活动）
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    active_users = db.query(User).filter(User.last_request_at >= seven_days_ago).count()

    # 新用户统计（最近30天）
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    new_users = db.query(User).filter(User.created_at >= thirty_days_ago).count()

    # Token使用统计
    try:
        total_tokens_used = db.query(db.func.sum(User.tokens_used)).scalar() or 0
        total_token_quota = db.query(db.func.sum(User.token_quota)).scalar() or 0

        # 配额使用率
        quota_utilization = (
            (total_tokens_used / total_token_quota * 100)
            if total_token_quota > 0
            else 0
        )
    except Exception as e:
        # 如果统计查询失败，使用默认值
        total_tokens_used = 0
        total_token_quota = 0
        quota_utilization = 0

    return {
        "total_users": total_users,
        "role_distribution": {
            "admin": admin_count,
            "researcher": researcher_count,
            "user": user_count,
            "temp": temp_count,
        },
        "active_users": active_users,
        "new_users": new_users,
        "token_stats": {
            "total_used": total_tokens_used,
            "total_quota": total_token_quota,
            "utilization_percent": round(quota_utilization, 2),
        },
    }


@router.get("/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取用户详细信息
    """
    check_admin_permission(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # 获取用户的邀请码使用记录
    invitations = (
        db.query(InvitationCode)
        .filter(
            or_(InvitationCode.created_by == user_id, InvitationCode.used_by == user_id)
        )
        .all()
    )

    user_response = UserResponse(
        id=user.id,
        username=user.username,
        email=user.email or "",
        role=user.role,
        tokenQuota=user.token_quota,
        tokensUsed=user.tokens_used,
        requestCount=user.request_count,
        lastRequestAt=int(user.last_request_at.timestamp() * 1000)
        if user.last_request_at
        else None,
        createdAt=int(user.created_at.timestamp() * 1000),
        registrationIp=user.registration_ip or "unknown",
        isTemp=user.is_temp,
        expiresAt=int(user.expires_at.timestamp() * 1000) if user.expires_at else None,
    )

    return {
        "user": user_response.model_dump(),
        "invitations": [
            {
                "id": inv.id,
                "code": inv.code,
                "created_by": inv.created_by,
                "used_by": inv.used_by,
                "is_used": inv.is_used,
                "used_count": inv.used_count,
                "max_uses": inv.max_uses,
            }
            for inv in invitations
        ],
    }


@router.put("/{user_id}", response_model=dict)
async def update_user(
    user_id: str,
    update_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    更新用户信息
    """
    check_admin_permission(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # 防止管理员修改自己的角色为非管理员
    if user_id == current_user.id and "role" in update_data:
        if update_data["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove admin role from yourself",
            )

    # 允许更新的字段
    allowed_fields = {
        "role",
        "token_quota",
        "tokens_used",
        "request_count",
        "is_temp",
        "expires_at",
        "upgrade_token",
    }

    # 过滤允许更新的字段
    filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}

    # 特殊处理：如果设置is_temp=False，清除临时用户相关字段
    if "is_temp" in filtered_data and filtered_data["is_temp"] is False:
        filtered_data["expires_at"] = None
        filtered_data["upgrade_token"] = None

    # 更新用户信息
    for field, value in filtered_data.items():
        if field == "expires_at" and value:
            # 处理时间戳转换
            if isinstance(value, (int, float)):
                filtered_data[field] = datetime.fromtimestamp(value / 1000)
        elif field == "upgrade_token" and value is None:
            # 清除升级token
            filtered_data[field] = None
        else:
            setattr(user, field, value)

    db.commit()
    db.refresh(user)

    return {
        "message": "User updated successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "token_quota": user.token_quota,
            "tokens_used": user.tokens_used,
            "is_temp": user.is_temp,
        },
    }


@router.post("/{user_id}/reset-password", response_model=dict)
async def reset_user_password(
    user_id: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    重置用户密码
    """
    check_admin_permission(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # 临时用户没有密码，不能重置
    if user.is_temp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reset password for temporary user",
        )

    # 重置密码
    user.hashed_password = get_password_hash(new_password)
    db.commit()

    return {
        "message": "Password reset successfully",
        "user_id": user_id,
        "username": user.username,
    }


@router.post("/{user_id}/upgrade-temp", response_model=dict)
async def upgrade_temp_user(
    user_id: str,
    upgrade_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    升级临时用户为正式用户
    """
    check_admin_permission(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if not user.is_temp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a temporary user",
        )

    # 设置必填字段
    if "email" not in upgrade_data or not upgrade_data["email"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is required for upgrade",
        )

    if "username" not in upgrade_data or not upgrade_data["username"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is required for upgrade",
        )

    # 检查用户名和邮箱是否已存在
    existing_user = (
        db.query(User)
        .filter(
            or_(
                User.username == upgrade_data["username"],
                User.email == upgrade_data["email"],
            )
        )
        .filter(User.id != user_id)
        .first()
    )

    if existing_user:
        if existing_user.username == upgrade_data["username"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
            )

    # 升级用户
    user.username = upgrade_data["username"]
    user.email = upgrade_data["email"]
    user.role = upgrade_data.get("role", "user")
    user.is_temp = False
    user.expires_at = None
    user.upgrade_token = None

    # 设置密码（如果提供）
    if "password" in upgrade_data and upgrade_data["password"]:
        user.hashed_password = get_password_hash(upgrade_data["password"])

    # 调整配额（如果提供）
    if "token_quota" in upgrade_data:
        user.token_quota = upgrade_data["token_quota"]

    db.commit()

    return {
        "message": "Temporary user upgraded successfully",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_temp": user.is_temp,
        },
    }


@router.delete("/{user_id}", response_model=dict)
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    删除用户
    """
    check_admin_permission(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # 防止管理员删除自己
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself"
        )

    # 记录删除信息
    username = user.username
    email = user.email

    # 删除用户（级联删除相关数据）
    db.delete(user)
    db.commit()

    return {
        "message": "User deleted successfully",
        "deleted_user": {"id": user_id, "username": username, "email": email},
    }


@router.post("/batch-update", response_model=dict)
async def batch_update_users(
    batch_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量更新用户
    """
    check_admin_permission(current_user)

    user_ids = batch_data.get("user_ids", [])
    update_fields = batch_data.get("update_fields", {})

    if not user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User IDs are required"
        )

    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Update fields are required"
        )

    # 允许批量更新的字段
    allowed_fields = {"token_quota", "role", "tokens_used"}
    filtered_fields = {k: v for k, v in update_fields.items() if k in allowed_fields}

    if not filtered_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid update fields provided",
        )

    # 批量更新
    updated_count = 0
    for user_id in user_ids:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            # 防止批量操作影响当前管理员
            if user_id != current_user.id or "role" not in filtered_fields:
                for field, value in filtered_fields.items():
                    setattr(user, field, value)
                updated_count += 1

    db.commit()

    return {
        "message": f"Batch update completed",
        "updated_count": updated_count,
        "requested_count": len(user_ids),
    }
