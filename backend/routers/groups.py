# =====================================================
# 收藏分组路由
#
# 接口列表：
# GET    /groups/          —— 获取当前用户的所有分组
# POST   /groups/          —— 创建新分组
# PUT    /groups/{id}      —— 修改分组信息
# DELETE /groups/{id}      —— 删除分组
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.database import get_db
from database.models import Group, Favorite
from routers.auth import get_current_user, User


router = APIRouter(prefix="/groups", tags=["收藏分组"])


# =====================================================
# Pydantic 数据模型
# =====================================================

class GroupCreateRequest(BaseModel):
    """创建分组的请求体"""
    name: str
    description: Optional[str] = None
    color: Optional[str] = "#4A90E2"  # 默认蓝色
    sort_order: Optional[int] = 0


class GroupUpdateRequest(BaseModel):
    """修改分组的请求体（所有字段都是可选的）"""
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None


class GroupResponse(BaseModel):
    """分组信息响应体"""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    sort_order: int
    created_at: datetime
    favorites_count: int = 0  # 该分组下的收藏数量（附加信息）

    class Config:
        from_attributes = True


# =====================================================
# API 路由
# =====================================================

@router.get("/", response_model=List[GroupResponse])
async def get_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的所有分组，按 sort_order 排序

    注意：只返回当前登录用户自己的分组
    """
    result = await db.execute(
        select(Group)
        .where(Group.user_id == current_user.id)
        .order_by(Group.sort_order, Group.created_at)
    )
    groups = result.scalars().all()

    # 为每个分组附加收藏数量信息
    response = []
    for group in groups:
        count_result = await db.execute(
            select(Favorite).where(Favorite.group_id == group.id)
        )
        favorites_count = len(count_result.scalars().all())

        response.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            sort_order=group.sort_order,
            created_at=group.created_at,
            favorites_count=favorites_count
        ))

    return response


@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """创建新分组"""
    # 检查同名分组是否已存在
    result = await db.execute(
        select(Group).where(
            Group.user_id == current_user.id,
            Group.name == request.name
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分组名称 '{request.name}' 已存在"
        )

    new_group = Group(
        name=request.name,
        description=request.description,
        color=request.color or "#4A90E2",
        sort_order=request.sort_order or 0,
        user_id=current_user.id
    )
    db.add(new_group)
    await db.flush()

    return GroupResponse(
        id=new_group.id,
        name=new_group.name,
        description=new_group.description,
        color=new_group.color,
        sort_order=new_group.sort_order,
        created_at=new_group.created_at,
        favorites_count=0
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    request: GroupUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改分组信息（名称、描述、颜色等）"""
    # 查找分组，确保存在且属于当前用户
    result = await db.execute(
        select(Group).where(
            Group.id == group_id,
            Group.user_id == current_user.id
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分组不存在或无权限修改"
        )

    # 如果要修改名称，检查新名称是否与其他分组重复
    if request.name and request.name != group.name:
        name_check = await db.execute(
            select(Group).where(
                Group.user_id == current_user.id,
                Group.name == request.name,
                Group.id != group_id  # 排除自身
            )
        )
        if name_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分组名称 '{request.name}' 已存在"
            )

    # 更新字段（只更新传入的非None值）
    if request.name is not None:
        group.name = request.name
    if request.description is not None:
        group.description = request.description
    if request.color is not None:
        group.color = request.color
    if request.sort_order is not None:
        group.sort_order = request.sort_order

    # 统计收藏数量
    count_result = await db.execute(
        select(Favorite).where(Favorite.group_id == group.id)
    )
    favorites_count = len(count_result.scalars().all())

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        sort_order=group.sort_order,
        created_at=group.created_at,
        favorites_count=favorites_count
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除分组

    注意：删除分组后，该分组下的收藏不会被删除
    而是变成"未分组"状态（group_id设为NULL）
    这由数据库的 ondelete="SET NULL" 外键约束自动处理
    """
    result = await db.execute(
        select(Group).where(
            Group.id == group_id,
            Group.user_id == current_user.id
        )
    )
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分组不存在或无权限删除"
        )

    await db.delete(group)
    # 返回204 No Content，不需要响应体
