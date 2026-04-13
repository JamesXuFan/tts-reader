# =====================================================
# Pydantic 数据验证模型（Schemas）
#
# 什么是 Pydantic Schema？
# 如果说 models.py 里的类描述的是"数据库长什么样"，
# 那么这里的类描述的是"API接口收发的数据长什么样"。
#
# 类比理解：
# - 数据库模型（models.py） = 仓库货架的摆放规则
# - Pydantic Schema（本文件） = 快递单的格式规范
#   客户填快递单（请求数据）→ 验证格式 → 入库
#   从仓库取货（数据库数据）→ 打包成快递单格式 → 返回给客户
#
# 主要作用：
# 1. 请求验证：自动检查用户发来的数据是否合法（类型、长度、格式等）
# 2. 响应格式化：控制返回给前端的数据包含哪些字段（不泄露密码等敏感字段）
# 3. 自动生成API文档：FastAPI根据Schema自动生成Swagger文档
# =====================================================

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# =====================================================
# 通用响应模型
# =====================================================

class MessageResponse(BaseModel):
    """通用消息响应，用于操作成功/失败的提示"""
    message: str = Field(..., description="操作结果提示信息")
    success: bool = Field(default=True, description="操作是否成功")


# =====================================================
# 用户相关 Schemas（对应 users 表）
# =====================================================

class UserCreate(BaseModel):
    """
    用户注册请求体
    当前端发送 POST /auth/register 时，请求体必须符合这个格式

    field_validator：自定义验证规则，比如检查用户名不含特殊字符
    Field(...)：... 表示这个字段是必填的
    Field(..., min_length=3)：限制最小长度为3个字符
    """
    username: str = Field(
        ...,
        min_length=2,
        max_length=50,
        description="用户名，2-50个字符"
    )
    email: EmailStr = Field(
        ...,
        description="邮箱地址，Pydantic会自动验证格式"
    )
    password: str = Field(
        ...,
        min_length=6,
        max_length=100,
        description="密码，最少6个字符"
    )

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        """验证用户名只能包含字母、数字、下划线和中文"""
        import re
        # 只允许：英文字母、数字、下划线、中文字符
        if not re.match(r'^[\w\u4e00-\u9fff]+$', v):
            raise ValueError("用户名只能包含字母、数字、下划线和中文字符")
        return v.strip()


class UserLogin(BaseModel):
    """用户登录请求体"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """
    用户信息响应体（返回给前端的用户数据）

    注意：不包含 hashed_password 字段！
    这是 Schema 的重要作用之一：控制哪些字段对外可见
    """
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱")
    is_active: bool = Field(..., description="账号是否激活")
    created_at: datetime = Field(..., description="注册时间")

    # model_config 是 Pydantic v2 的配置方式
    # from_attributes=True 允许从 SQLAlchemy 模型对象直接转换
    # （等价于旧版的 class Config: orm_mode = True）
    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """JWT登录令牌响应"""
    access_token: str = Field(..., description="JWT访问令牌")
    token_type: str = Field(default="bearer", description="令牌类型，固定为bearer")
    expires_in: int = Field(..., description="令牌有效期（秒）")
    user: UserResponse = Field(..., description="当前用户信息")


# =====================================================
# 收藏分组相关 Schemas（对应 groups 表）
# =====================================================

class GroupCreate(BaseModel):
    """
    创建分组请求体
    POST /groups/
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="分组名称"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="分组描述（可选）"
    )
    color: Optional[str] = Field(
        default="#4A90E2",
        description="分组颜色，HEX格式，如 #4A90E2"
    )
    sort_order: Optional[int] = Field(
        default=0,
        ge=0,           # ge = greater than or equal（大于等于0）
        description="排列顺序"
    )

    @field_validator("color")
    @classmethod
    def color_must_be_hex(cls, v: Optional[str]) -> Optional[str]:
        """验证颜色值是否为合法的HEX颜色代码"""
        if v is None:
            return v
        import re
        if not re.match(r'^#[0-9A-Fa-f]{6}$', v):
            raise ValueError("颜色必须是6位HEX格式，例如 #4A90E2")
        return v


class GroupUpdate(BaseModel):
    """
    更新分组请求体（所有字段可选，只传需要修改的字段）
    PUT /groups/{group_id}

    Optional 表示字段可以不传，默认为 None
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    color: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None, ge=0)


class GroupResponse(BaseModel):
    """分组响应体"""
    id: int
    name: str
    description: Optional[str] = None
    color: str
    sort_order: int
    created_at: datetime
    user_id: int
    # 这个分组下的收藏数量（由路由层计算后填入，不来自数据库字段）
    favorites_count: Optional[int] = Field(default=0, description="该分组下的收藏数量")

    model_config = {"from_attributes": True}


# =====================================================
# 收藏内容相关 Schemas（对应 favorites 表）
# =====================================================

class FavoriteCreate(BaseModel):
    """
    创建收藏请求体
    POST /favorites/
    """
    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="收藏标题"
    )
    text_content: str = Field(
        ...,
        min_length=1,
        max_length=5000,   # 限制文本长度，避免TTS费用过高
        description="要朗读的文字内容"
    )
    language: Optional[str] = Field(
        default="zh-CN",
        description="语言代码，如 zh-CN, en-US, ja-JP"
    )
    note: Optional[str] = Field(
        default=None,
        max_length=500,
        description="用户备注（可选）"
    )
    group_id: Optional[int] = Field(
        default=None,
        description="所属分组ID，不填则为未分组"
    )

    @field_validator("language")
    @classmethod
    def language_must_be_valid(cls, v: str) -> str:
        """验证语言代码是否在支持列表中"""
        supported = [
            "zh-CN",  # 普通话（中国大陆）
            "zh-TW",  # 繁体中文（台湾）
            "en-US",  # 英语（美国）
            "en-GB",  # 英语（英国）
            "ja-JP",  # 日语
            "ko-KR",  # 韩语
            "fr-FR",  # 法语
            "de-DE",  # 德语
            "es-ES",  # 西班牙语
            "it-IT",  # 意大利语
            "pt-BR",  # 葡萄牙语（巴西）
            "ru-RU",  # 俄语
        ]
        if v not in supported:
            raise ValueError(f"不支持的语言代码 '{v}'，支持的语言：{', '.join(supported)}")
        return v


class FavoriteUpdate(BaseModel):
    """更新收藏请求体（所有字段可选）"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    text_content: Optional[str] = Field(default=None, min_length=1, max_length=5000)
    language: Optional[str] = Field(default=None)
    note: Optional[str] = Field(default=None, max_length=500)
    group_id: Optional[int] = Field(default=None, description="传 null 表示移出分组")


class FavoriteResponse(BaseModel):
    """收藏内容响应体"""
    id: int
    title: str
    text_content: str
    language: str
    note: Optional[str] = None
    is_favorite: bool
    play_count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    user_id: int
    group_id: Optional[int] = None
    # 关联的分组信息（如果有的话），返回分组名和颜色方便前端展示
    group: Optional[GroupResponse] = None

    model_config = {"from_attributes": True}


class FavoriteListResponse(BaseModel):
    """收藏列表响应（带分页信息）"""
    items: List[FavoriteResponse] = Field(..., description="收藏列表")
    total: int = Field(..., description="总条数")
    page: int = Field(..., description="当前页码（从1开始）")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")


# =====================================================
# TTS语音合成相关 Schemas（对应 tts_cache 表）
# =====================================================

class TTSRequest(BaseModel):
    """
    TTS合成请求体
    POST /tts/synthesize

    这是调用Gemini TTS API的核心请求格式
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="要转换为语音的文字内容"
    )
    language: Optional[str] = Field(
        default="zh-CN",
        description="语言代码"
    )
    voice_name: Optional[str] = Field(
        default=None,
        description="指定使用的声音名称（如 Kore, Charon, Puck 等Gemini声音）"
    )
    # 是否使用缓存（相同内容不重复调用API，节省费用）
    use_cache: Optional[bool] = Field(
        default=True,
        description="是否使用缓存，默认开启"
    )
    # 如果这次TTS是从收藏发起的，传入收藏ID（用于记录关联和统计播放次数）
    favorite_id: Optional[int] = Field(
        default=None,
        description="关联的收藏ID（可选）"
    )


class TTSResponse(BaseModel):
    """TTS合成响应体"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    audio_format: str = Field(..., description="音频格式，如 mp3, wav")
    from_cache: bool = Field(..., description="是否来自缓存（True=缓存命中，False=新生成）")
    duration_ms: Optional[int] = Field(default=None, description="音频时长（毫秒，如果能获取）")
    cache_key: Optional[str] = Field(default=None, description="本次缓存的Key")


class TTSVoiceInfo(BaseModel):
    """单个声音信息"""
    name: str = Field(..., description="声音名称（API参数值）")
    display_name: str = Field(..., description="显示名称（中文）")
    language: str = Field(..., description="适用语言")
    gender: Optional[str] = Field(default=None, description="性别特征：男/女/中性")
    description: Optional[str] = Field(default=None, description="声音风格描述")


class TTSVoiceListResponse(BaseModel):
    """支持的声音列表响应"""
    voices: List[TTSVoiceInfo] = Field(..., description="声音列表")
    total: int = Field(..., description="声音总数")


# =====================================================
# 播放历史 / 统计相关 Schemas
# =====================================================

class PlayCountUpdate(BaseModel):
    """更新收藏播放次数请求（每次播放后调用）"""
    favorite_id: int = Field(..., description="收藏ID")


# =====================================================
# 分页查询参数（通用）
# =====================================================

class PaginationParams(BaseModel):
    """
    分页查询参数
    通常通过 URL 查询参数传递，如：GET /favorites/?page=1&page_size=20
    """
    page: int = Field(default=1, ge=1, description="页码，从1开始")
    page_size: int = Field(default=20, ge=1, le=100, description="每页条数，最大100")


# =====================================================
# 错误响应 Schemas
# =====================================================

class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    detail: str = Field(..., description="错误详情")
    error_code: Optional[str] = Field(default=None, description="错误代码（方便前端处理特定错误）")
