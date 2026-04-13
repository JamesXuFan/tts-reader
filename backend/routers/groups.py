# =====================================================
# 收藏分组路由
#
# 接口列表（完整路径包含 main.py 的 /api/v1 前缀）：
# GET    /api/v1/groups/          —— 获取当前用户的所有分组
# POST   /api/v1/groups/          —— 创建新分组
# PUT    /api/v1/groups/{id}      —— 修改分组信息（名称/颜色/描述）
# DELETE /api/v1/groups/{id}      —— 删除分组（分组内收藏变为未分组）
#
# 安全设计：
# - 所有接口都需要 JWT 认证（通过 get_current_user 依赖）
# - 查询时强制加上 user_id == current_user.id 条件，防止越权访问
#   即：用户 A 无法读取或修改用户 B 的分组
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.database import get_db
from database.models import Group, Favorite
# get_current_user 和 User 都来自 core/security.py
# auth.py 也重新导出了这些，但直接从 security 导入更清晰
from core.security import get_current_user
from database.models import User


router = APIRouter(prefix="/groups", tags=["收藏分组"])


# =====================================================
# Pydantic 请求/响应数据模型
# （这里复用 schemas.py 的思路，直接在路由内定义，方便学习对照）
# =====================================================

class GroupCreateRequest(BaseModel):
    """创建分组的请求体"""
    name: str                              # 必填：分组名称
    description: Optional[str] = None     # 选填：分组描述
    color: Optional[str] = "#4A90E2"      # 选填：颜色，默认蓝色
    sort_order: Optional[int] = 0         # 选填：排序权重，数字越小越靠前


class GroupUpdateRequest(BaseModel):
    """
    修改分组的请求体（所有字段都是可选的）
    前端只传需要修改的字段，其余字段保持原值
    """
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
    favorites_count: int = 0  # 该分组下的收藏数量（由路由层计算填入）

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 对象直接转换


# =====================================================
# 辅助函数
# =====================================================

async def get_group_or_404(group_id: int, user_id: int, db: AsyncSession) -> Group:
    """
    通用辅助函数：查询分组，若不存在或不属于当前用户则抛出404

    为什么把404和403合并成一个404返回？
    安全考虑：如果区分"分组不存在"和"分组存在但不是你的"，
    攻击者可以通过枚举ID来探测哪些分组ID存在——这是信息泄露。
    统一返回404让攻击者无从判断。
    """
    result = await db.execute(
        select(Group).where(
            Group.id == group_id,
            Group.user_id == user_id  # 关键：同时验证归属权
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="分组不存在或无权限操作"
        )
    return group


async def get_favorites_count(group_id: int, db: AsyncSession) -> int:
    """
    统计某个分组下的收藏数量
    使用 func.count() 在数据库层面统计，比 len(list) 效率更高
    （数据库只返回一个数字，不用把所有记录都传到Python再计数）
    """
    result = await db.execute(
        select(func.count(Favorite.id)).where(Favorite.group_id == group_id)
    )
    return result.scalar() or 0


# =====================================================
# 接口 1：GET /groups/ — 获取当前用户的所有分组
# =====================================================

@router.get("/", response_model=List[GroupResponse])
async def get_groups(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前登录用户的所有分组，按 sort_order 升序、创建时间升序排列

    越权防护：WHERE user_id = {当前用户ID}
    即使有人猜到别人的 group_id，也只能看到自己的分组列表
    """
    result = await db.execute(
        select(Group)
        .where(Group.user_id == current_user.id)
        .order_by(Group.sort_order, Group.created_at)
    )
    groups = result.scalars().all()

    # 为每个分组附加收藏数量
    response = []
    for group in groups:
        count = await get_favorites_count(group.id, db)
        response.append(GroupResponse(
            id=group.id,
            name=group.name,
            description=group.description,
            color=group.color,
            sort_order=group.sort_order,
            created_at=group.created_at,
            favorites_count=count
        ))

    return response


# =====================================================
# 接口 2：POST /groups/ — 创建新分组
# =====================================================

@router.post("/", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: GroupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    创建新分组

    注意：同一用户下不允许有同名分组（数据库有 UniqueConstraint 约束）
    这里在应用层提前检查，给用户更友好的错误提示
    （不然会抛出数据库层面的 IntegrityError，错误信息不友好）
    """
    # 检查当前用户是否已有同名分组
    existing = await db.execute(
        select(Group).where(
            Group.user_id == current_user.id,
            Group.name == request.name
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"分组名称 '{request.name}' 已存在，请换一个名称"
        )

    # 创建新分组对象（此时还没写入数据库）
    new_group = Group(
        name=request.name,
        description=request.description,
        color=request.color or "#4A90E2",
        sort_order=request.sort_order or 0,
        user_id=current_user.id  # 绑定到当前用户，防止伪造
    )
    db.add(new_group)

    # flush：把操作发送给数据库（执行INSERT），但还未提交事务
    # 目的：让数据库分配自增ID，这样 new_group.id 就有值了
    # 真正的提交（commit）由 database.py 的 get_db 依赖在函数结束后自动完成
    await db.flush()

    return GroupResponse(
        id=new_group.id,
        name=new_group.name,
        description=new_group.description,
        color=new_group.color,
        sort_order=new_group.sort_order,
        created_at=new_group.created_at,
        favorites_count=0  # 新建分组，收藏数量为0
    )


# =====================================================
# 接口 3：PUT /groups/{group_id} — 修改分组信息
# =====================================================

@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: int,
    request: GroupUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改分组信息（名称、描述、颜色、排序权重）

    越权防护：通过 get_group_or_404 辅助函数，确保只能修改自己的分组
    """
    # 查询分组（含越权检查，不存在或不是自己的都返回404）
    group = await get_group_or_404(group_id, current_user.id, db)

    # 如果要修改名称，检查新名称是否与其他分组重名
    if request.name is not None and request.name != group.name:
        name_check = await db.execute(
            select(Group).where(
                Group.user_id == current_user.id,
                Group.name == request.name,
                Group.id != group_id  # 排除自身，避免"改成相同名称"报错
            )
        )
        if name_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"分组名称 '{request.name}' 已存在"
            )

    # 局部更新：只更新请求中传入的非None字段
    # 这种模式叫 "PATCH 语义"，用 PUT 接口实现部分更新
    if request.name is not None:
        group.name = request.name
    if request.description is not None:
        group.description = request.description
    if request.color is not None:
        group.color = request.color
    if request.sort_order is not None:
        group.sort_order = request.sort_order

    # 无需手动 flush/commit，SQLAlchemy 会跟踪对象的变化
    # get_db 依赖在函数结束后会自动提交

    count = await get_favorites_count(group.id, db)

    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        color=group.color,
        sort_order=group.sort_order,
        created_at=group.created_at,
        favorites_count=count
    )


# =====================================================
# 接口 4：DELETE /groups/{group_id} — 删除分组
# =====================================================

@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除分组

    重要：删除分组不会删除该分组下的收藏！
    数据库模型中 Favorite.group_id 的外键配置了 ondelete="SET NULL"：
    当分组被删除时，该分组下所有收藏的 group_id 字段自动变为 NULL（未分组状态）

    这是一个"软删除分组，保留内容"的设计，符合用户预期（不会误删重要收藏）
    """
    # 查询分组（含越权检查）
    group = await get_group_or_404(group_id, current_user.id, db)

    # 删除分组
    await db.delete(group)

    # 返回 204 No Content：HTTP标准规定，DELETE 成功时通常返回无内容响应
    # FastAPI 检测到 status_code=204 时，自动不返回响应体
