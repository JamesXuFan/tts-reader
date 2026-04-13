# =====================================================
# 收藏内容路由
#
# 接口列表：
# GET    /favorites/           —— 获取收藏列表（支持按分组过滤）
# POST   /favorites/           —— 添加新收藏
# PUT    /favorites/{id}       —— 修改收藏
# DELETE /favorites/{id}       —— 删除收藏
# PATCH  /favorites/{id}/move  —— 移动收藏到其他分组
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from database.database import get_db
from database.models import Favorite, Group
from routers.auth import get_current_user, User


router = APIRouter(prefix="/favorites", tags=["收藏内容"])


# =====================================================
# Pydantic 数据模型
# =====================================================

class FavoriteCreateRequest(BaseModel):
    """添加收藏的请求体"""
    title: str
    text_content: str
    language: Optional[str] = "zh-CN"
    group_id: Optional[int] = None  # 不传则为"未分组"


class FavoriteUpdateRequest(BaseModel):
    """修改收藏的请求体（所有字段可选）"""
    title: Optional[str] = None
    text_content: Optional[str] = None
    language: Optional[str] = None


class FavoriteMoveRequest(BaseModel):
    """移动收藏到其他分组的请求体"""
    group_id: Optional[int] = None  # None 表示移到"未分组"


class FavoriteResponse(BaseModel):
    """收藏信息响应体"""
    id: int
    title: str
    text_content: str
    language: str
    play_count: int
    group_id: Optional[int] = None
    group_name: Optional[str] = None  # 附加：分组名称（方便前端显示）
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# =====================================================
# 辅助函数
# =====================================================

async def check_group_ownership(group_id: int, user_id: int, db: AsyncSession):
    """验证分组存在且属于当前用户"""
    result = await db.execute(
        select(Group).where(Group.id == group_id, Group.user_id == user_id)
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定的分组不存在或无权限"
        )
    return group


# =====================================================
# API 路由
# =====================================================

@router.get("/", response_model=List[FavoriteResponse])
async def get_favorites(
    group_id: Optional[int] = Query(None, description="按分组过滤，不传则返回所有收藏"),
    search: Optional[str] = Query(None, description="搜索关键词，在标题和内容中搜索"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取收藏列表

    支持过滤：
    - group_id=0  : 只返回未分组的收藏
    - group_id=5  : 只返回ID为5的分组下的收藏
    - 不传        : 返回所有收藏
    - search=关键词: 在标题和内容中搜索
    """
    query = select(Favorite).where(Favorite.user_id == current_user.id)

    # 按分组过滤
    if group_id is not None:
        if group_id == 0:
            # 0 表示查询未分组
            query = query.where(Favorite.group_id.is_(None))
        else:
            query = query.where(Favorite.group_id == group_id)

    # 关键词搜索（在标题和内容中搜索）
    if search:
        from sqlalchemy import or_
        query = query.where(
            or_(
                Favorite.title.contains(search),
                Favorite.text_content.contains(search)
            )
        )

    query = query.order_by(Favorite.created_at.desc())
    result = await db.execute(query)
    favorites = result.scalars().all()

    # 构建响应，附加分组名称
    response = []
    for fav in favorites:
        group_name = None
        if fav.group_id:
            group_result = await db.execute(select(Group).where(Group.id == fav.group_id))
            group = group_result.scalar_one_or_none()
            if group:
                group_name = group.name

        response.append(FavoriteResponse(
            id=fav.id,
            title=fav.title,
            text_content=fav.text_content,
            language=fav.language,
            play_count=fav.play_count,
            group_id=fav.group_id,
            group_name=group_name,
            created_at=fav.created_at,
            updated_at=fav.updated_at
        ))

    return response


@router.post("/", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    request: FavoriteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """添加新收藏"""
    # 如果指定了分组，验证分组属于当前用户
    group = None
    if request.group_id:
        group = await check_group_ownership(request.group_id, current_user.id, db)

    new_favorite = Favorite(
        title=request.title,
        text_content=request.text_content,
        language=request.language or "zh-CN",
        group_id=request.group_id,
        user_id=current_user.id
    )
    db.add(new_favorite)
    await db.flush()

    return FavoriteResponse(
        id=new_favorite.id,
        title=new_favorite.title,
        text_content=new_favorite.text_content,
        language=new_favorite.language,
        play_count=new_favorite.play_count,
        group_id=new_favorite.group_id,
        group_name=group.name if group else None,
        created_at=new_favorite.created_at,
        updated_at=new_favorite.updated_at
    )


@router.put("/{favorite_id}", response_model=FavoriteResponse)
async def update_favorite(
    favorite_id: int,
    request: FavoriteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """修改收藏内容"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == current_user.id
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在或无权限修改"
        )

    if request.title is not None:
        favorite.title = request.title
    if request.text_content is not None:
        favorite.text_content = request.text_content
    if request.language is not None:
        favorite.language = request.language

    # 获取分组名称
    group_name = None
    if favorite.group_id:
        group_result = await db.execute(select(Group).where(Group.id == favorite.group_id))
        group = group_result.scalar_one_or_none()
        if group:
            group_name = group.name

    return FavoriteResponse(
        id=favorite.id,
        title=favorite.title,
        text_content=favorite.text_content,
        language=favorite.language,
        play_count=favorite.play_count,
        group_id=favorite.group_id,
        group_name=group_name,
        created_at=favorite.created_at,
        updated_at=favorite.updated_at
    )


@router.patch("/{favorite_id}/move", response_model=FavoriteResponse)
async def move_favorite(
    favorite_id: int,
    request: FavoriteMoveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    移动收藏到其他分组

    request.group_id = None  : 移到"未分组"
    request.group_id = 5     : 移到ID为5的分组
    """
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == current_user.id
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在或无权限"
        )

    # 验证目标分组
    group = None
    if request.group_id:
        group = await check_group_ownership(request.group_id, current_user.id, db)

    favorite.group_id = request.group_id

    return FavoriteResponse(
        id=favorite.id,
        title=favorite.title,
        text_content=favorite.text_content,
        language=favorite.language,
        play_count=favorite.play_count,
        group_id=favorite.group_id,
        group_name=group.name if group else None,
        created_at=favorite.created_at,
        updated_at=favorite.updated_at
    )


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """删除收藏"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == current_user.id
        )
    )
    favorite = result.scalar_one_or_none()

    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在或无权限删除"
        )

    await db.delete(favorite)
