# =====================================================
# 收藏内容路由
#
# 接口列表（完整路径包含 main.py 的 /api/v1 前缀）：
# GET    /api/v1/favorites/              —— 获取收藏列表（支持分组过滤/搜索/分页）
# POST   /api/v1/favorites/              —— 添加新收藏
# PUT    /api/v1/favorites/{id}          —— 修改收藏（内容/备注/移动分组）
# DELETE /api/v1/favorites/{id}          —— 删除收藏
# POST   /api/v1/favorites/{id}/speak    —— 朗读某条收藏（复用TTS缓存）
#
# 安全设计：
# - 所有接口都需要 JWT 认证
# - 所有查询都加 user_id == current_user.id 条件，防止越权访问
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import math

from database.database import get_db
from database.models import Favorite, Group
from core.security import get_current_user
from database.models import User
# 导入 TTS 服务函数（复用已有的合成逻辑，包含缓存机制）
from services.gemini_tts import synthesize_speech


router = APIRouter(prefix="/favorites", tags=["收藏内容"])


# =====================================================
# Pydantic 请求/响应数据模型
# =====================================================

class FavoriteCreateRequest(BaseModel):
    """添加收藏的请求体"""
    title: str                             # 必填：收藏标题
    text_content: str                      # 必填：要朗读的文字内容
    language: Optional[str] = "zh-CN"     # 选填：语言代码，默认中文
    note: Optional[str] = None             # 选填：用户备注
    group_id: Optional[int] = None         # 选填：所属分组ID，不传则为"未分组"


class FavoriteUpdateRequest(BaseModel):
    """
    修改收藏的请求体（所有字段可选，只传要改的字段）
    合并了"修改内容"和"移动分组"两个操作，一个接口搞定
    """
    title: Optional[str] = None
    text_content: Optional[str] = None
    language: Optional[str] = None
    note: Optional[str] = None
    # group_id 设为 Optional[int]，允许传 null（表示移出分组，变为未分组）
    # 注意：Python 中 None 代表 JSON 中的 null
    group_id: Optional[int] = None


class FavoriteResponse(BaseModel):
    """收藏信息响应体"""
    id: int
    title: str
    text_content: str
    language: str
    note: Optional[str] = None
    play_count: int
    group_id: Optional[int] = None
    group_name: Optional[str] = None    # 附加字段：分组名称（方便前端展示，省去前端再查一次）
    group_color: Optional[str] = None  # 附加字段：分组颜色（方便前端显示彩色标签）
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FavoriteListResponse(BaseModel):
    """
    收藏列表响应体（带分页信息）

    什么是分页？
    当收藏很多时，一次返回所有数据会很慢（想象1000条数据一次传输）。
    分页把数据分成若干"页"，每次只返回一页（比如20条）。
    就像翻书一样，每次只看一页。

    page=1, page_size=20 表示第1页，每页20条
    page=2, page_size=20 表示第2页（第21-40条）
    """
    items: List[FavoriteResponse]  # 当前页的收藏列表
    total: int                      # 总条数（不受分页影响）
    page: int                       # 当前页码（从1开始）
    page_size: int                  # 每页条数
    total_pages: int                # 总页数（供前端渲染页码导航）


# =====================================================
# 辅助函数
# =====================================================

async def get_favorite_or_404(favorite_id: int, user_id: int, db: AsyncSession) -> Favorite:
    """
    通用辅助函数：查询收藏，若不存在或不属于当前用户则抛出404

    越权防护：同时检查 id 和 user_id，确保用户只能操作自己的收藏
    """
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == user_id  # 关键：归属权验证
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在或无权限操作"
        )
    return favorite


async def check_group_ownership(group_id: int, user_id: int, db: AsyncSession) -> Group:
    """
    验证分组存在且属于当前用户
    将收藏放入某个分组时调用，防止把收藏放入别人的分组
    """
    result = await db.execute(
        select(Group).where(
            Group.id == group_id,
            Group.user_id == user_id
        )
    )
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定的分组不存在或无权限使用"
        )
    return group


async def build_favorite_response(fav: Favorite, db: AsyncSession) -> FavoriteResponse:
    """
    将 Favorite 数据库对象转换为响应体
    同时附加关联的分组名称和颜色（避免前端再发一次查询请求）

    这是一个"数据组装"辅助函数，多个接口都会用到，抽取出来避免重复代码
    """
    group_name = None
    group_color = None

    # 如果收藏有所属分组，查询分组信息
    if fav.group_id:
        group_result = await db.execute(
            select(Group).where(Group.id == fav.group_id)
        )
        group = group_result.scalar_one_or_none()
        if group:
            group_name = group.name
            group_color = group.color

    return FavoriteResponse(
        id=fav.id,
        title=fav.title,
        text_content=fav.text_content,
        language=fav.language,
        note=fav.note,
        play_count=fav.play_count,
        group_id=fav.group_id,
        group_name=group_name,
        group_color=group_color,
        created_at=fav.created_at,
        updated_at=fav.updated_at
    )


# =====================================================
# 接口 1：GET /favorites/ — 获取收藏列表（支持过滤、搜索、分页）
# =====================================================

@router.get("/", response_model=FavoriteListResponse)
async def get_favorites(
    # --- 过滤参数（通过 URL 查询字符串传入，如 ?group_id=5&search=你好&page=1）---
    group_id: Optional[int] = Query(
        None,
        description="按分组过滤：传0=只看未分组，传具体ID=看该分组，不传=看全部"
    ),
    search: Optional[str] = Query(
        None,
        description="关键词搜索，同时在标题和文字内容中匹配"
    ),
    # --- 分页参数 ---
    page: int = Query(
        default=1,
        ge=1,                # ge = greater or equal（大于等于1，页码从1开始）
        description="页码，从1开始"
    ),
    page_size: int = Query(
        default=20,
        ge=1,
        le=100,              # le = less or equal（最多每页100条，防止返回过多数据）
        description="每页条数，1-100之间"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    获取当前用户的收藏列表，支持：
    - 按分组过滤（group_id=0 表示只看未分组）
    - 关键词搜索（标题 OR 内容中包含关键词）
    - 分页（避免一次返回太多数据）

    示例请求：
    GET /api/v1/favorites/?page=1&page_size=20
    GET /api/v1/favorites/?group_id=3&search=你好&page=2&page_size=10
    """
    # 构建基础查询条件（基础：只查当前用户的数据）
    base_conditions = [Favorite.user_id == current_user.id]

    # 添加分组过滤条件
    if group_id is not None:
        if group_id == 0:
            # group_id=0 是特殊约定：查询没有分组的收藏（group_id IS NULL）
            base_conditions.append(Favorite.group_id.is_(None))
        else:
            base_conditions.append(Favorite.group_id == group_id)

    # 添加关键词搜索条件（标题 OR 内容中包含搜索词）
    if search:
        search_condition = or_(
            Favorite.title.contains(search),
            Favorite.text_content.contains(search)
        )
        base_conditions.append(search_condition)

    # --- 第一步：查询总数（用于计算总页数） ---
    # 注意：统计总数和查询数据用的是同样的过滤条件
    count_query = select(func.count(Favorite.id)).where(*base_conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 计算总页数（向上取整：比如 25条数据，每页10条，共3页）
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    # --- 第二步：查询当前页的数据 ---
    # offset：跳过前面几条记录（第2页要跳过第1页的20条）
    # limit：最多返回多少条
    offset = (page - 1) * page_size
    data_query = (
        select(Favorite)
        .where(*base_conditions)
        .order_by(Favorite.created_at.desc())  # 按创建时间倒序（最新的在最前面）
        .offset(offset)
        .limit(page_size)
    )
    data_result = await db.execute(data_query)
    favorites = data_result.scalars().all()

    # 构建响应，附加分组信息
    items = []
    for fav in favorites:
        item = await build_favorite_response(fav, db)
        items.append(item)

    return FavoriteListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


# =====================================================
# 接口 2：POST /favorites/ — 添加新收藏
# =====================================================

@router.post("/", response_model=FavoriteResponse, status_code=status.HTTP_201_CREATED)
async def create_favorite(
    request: FavoriteCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    添加新收藏

    如果指定了 group_id，会先验证该分组属于当前用户
    防止用户把收藏放入别人的分组（越权操作）
    """
    # 如果指定了分组，验证分组存在且属于当前用户
    if request.group_id:
        await check_group_ownership(request.group_id, current_user.id, db)

    # 创建新收藏对象
    new_favorite = Favorite(
        title=request.title,
        text_content=request.text_content,
        language=request.language or "zh-CN",
        note=request.note,
        group_id=request.group_id,
        user_id=current_user.id  # 强制绑定当前用户，防止伪造 user_id
    )
    db.add(new_favorite)
    await db.flush()  # 让数据库分配 ID，但尚未提交事务

    return await build_favorite_response(new_favorite, db)


# =====================================================
# 接口 3：PUT /favorites/{favorite_id} — 修改收藏
# =====================================================

@router.put("/{favorite_id}", response_model=FavoriteResponse)
async def update_favorite(
    favorite_id: int,
    request: FavoriteUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    修改收藏内容

    功能合并：这个接口同时支持：
    1. 修改标题/文字内容/语言/备注
    2. 移动到其他分组（传 group_id=新分组ID）
    3. 移出分组变为未分组（传 group_id=null，但注意JSON中null对应Python的None）

    关于 group_id=null 的说明：
    JSON: {"group_id": null}  →  Python: request.group_id = None
    但"不传 group_id"和"传 group_id=null"在 Pydantic 中都是 None，无法区分。
    解决方案：用特殊值 0 代表"移出分组"，负值代表"不修改"
    或者：单独提供一个 PATCH /favorites/{id}/move 接口（更语义化）
    这里采用简单方案：group_id=0 表示移出分组，不传则不修改
    """
    # 查询收藏（含越权检查）
    favorite = await get_favorite_or_404(favorite_id, current_user.id, db)

    # 局部更新：只更新请求中传入的非None字段
    if request.title is not None:
        favorite.title = request.title
    if request.text_content is not None:
        favorite.text_content = request.text_content
    if request.language is not None:
        favorite.language = request.language
    if request.note is not None:
        favorite.note = request.note

    # 处理分组移动
    # group_id=0：特殊约定，表示移出分组（设为未分组）
    # group_id=正整数：移入指定分组（先验证归属权）
    # group_id=None（不传）：不修改分组
    if request.group_id is not None:
        if request.group_id == 0:
            # 移出分组，设为未分组
            favorite.group_id = None
        else:
            # 验证目标分组属于当前用户，防止越权
            await check_group_ownership(request.group_id, current_user.id, db)
            favorite.group_id = request.group_id

    return await build_favorite_response(favorite, db)


# =====================================================
# 接口 4：DELETE /favorites/{favorite_id} — 删除收藏
# =====================================================

@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    删除收藏

    越权防护：通过 get_favorite_or_404 确保只能删除自己的收藏
    """
    favorite = await get_favorite_or_404(favorite_id, current_user.id, db)
    await db.delete(favorite)
    # 204 No Content：删除成功，无需返回内容


# =====================================================
# 接口 5：POST /favorites/{favorite_id}/speak — 朗读收藏
# =====================================================

@router.post(
    "/{favorite_id}/speak",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "WAV 格式的音频字节流"
        },
        404: {"description": "收藏不存在或无权限"},
        503: {"description": "TTS服务暂时不可用"},
    },
    summary="朗读收藏内容",
    description="将指定收藏的文字内容转换为语音，复用 TTS 缓存机制"
)
async def speak_favorite(
    favorite_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    朗读某条收藏

    为什么单独设置这个接口而不直接用 POST /tts/speak？
    1. 这里直接读取收藏的 text_content 和 language，前端不需要再传这些参数
    2. 自动累加收藏的 play_count（播放次数统计）
    3. 复用 synthesize_speech() 的缓存机制，相同内容不重复调用 Gemini API

    工作流程：
    1. 查询收藏（含越权检查）
    2. 调用 synthesize_speech()：先查缓存，缓存没有才调 Gemini API
    3. play_count + 1（记录这次播放）
    4. 返回音频字节流
    """
    # 查询收藏（含越权检查：用户只能朗读自己的收藏）
    favorite = await get_favorite_or_404(favorite_id, current_user.id, db)

    # 调用 TTS 服务（与 /tts/speak 接口共用同一套逻辑，包含缓存）
    try:
        audio_bytes, from_cache = await synthesize_speech(
            text=favorite.text_content,
            language=favorite.language,
            voice_name=None,   # 使用该语言的默认声音
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"语音合成服务暂时不可用：{exc}"
        )

    # 累加播放次数（记录用户的使用频率）
    favorite.play_count += 1

    # 在响应头中附加一些有用的信息（方便前端调试）
    headers = {
        "X-From-Cache": "true" if from_cache else "false",
        "X-Favorite-Id": str(favorite_id),
        "X-Play-Count": str(favorite.play_count),
        "Access-Control-Expose-Headers": "X-From-Cache, X-Favorite-Id, X-Play-Count",
    }

    # 返回音频字节流，前端用 <audio> 标签或 Web Audio API 播放
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers=headers,
    )
