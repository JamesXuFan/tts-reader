# =====================================================
# 认证路由（用户注册 & 登录）
#
# 这个文件处理所有和用户身份相关的API接口：
# POST /api/v1/auth/register  —— 注册新账号
# POST /api/v1/auth/login     —— 登录获取JWT令牌
# GET  /api/v1/auth/me        —— 获取当前登录用户信息
#
# 什么是JWT（JSON Web Token）？
# 想象成一张"通行证"：
# 1. 用户登录成功后，服务器发给用户一个JWT令牌
# 2. 用户之后的每次请求都带上这个令牌（放在请求头里）
# 3. 服务器验证令牌有效就认可这个用户的身份
# 4. 令牌有过期时间，过期后需要重新登录
#
# 注意：密码哈希、JWT生成/验证等核心安全函数
# 已统一放在 core/security.py 中，这里直接导入使用
# =====================================================

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, field_validator

from database.database import get_db
from database.models import User

# 从核心安全模块导入工具函数（统一管理，避免重复）
from core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)


# ---- 创建路由对象 ----
# prefix="/auth" 表示这个路由下所有接口都以 /auth 开头
# 挂载到 main.py 时加上 /api/v1 前缀，最终路径是 /api/v1/auth/...
# tags=["认证"] 用于在API文档中分组显示
router = APIRouter(prefix="/auth", tags=["认证"])


# =====================================================
# Pydantic 数据模型（请求/响应的数据结构定义）
# =====================================================

class UserRegisterRequest(BaseModel):
    """注册请求体：前端发送的注册数据格式"""
    username: str
    email: EmailStr       # EmailStr 会自动验证邮箱格式是否合法
    password: str

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        """验证用户名：3-50个字符"""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("用户名至少需要3个字符")
        if len(v) > 50:
            raise ValueError("用户名不能超过50个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        """验证密码强度：最少6个字符"""
        if len(v) < 6:
            raise ValueError("密码至少需要6个字符")
        return v


class UserLoginResponse(BaseModel):
    """登录/注册成功的响应体：返回给前端的数据"""
    access_token: str           # JWT令牌字符串，前端需要保存这个值
    token_type: str = "bearer"  # 令牌类型，固定为"bearer"（OAuth2规范）
    user_id: int
    username: str
    email: str


class UserInfoResponse(BaseModel):
    """
    用户信息响应体（/me 接口返回的数据）

    注意：这里故意 不包含 hashed_password 字段！
    这是安全设计：API永远不应该将密码（哪怕是哈希值）返回给前端
    """
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从SQLAlchemy模型对象直接转换（Pydantic v1写法）


class TokenData(BaseModel):
    """JWT令牌载荷中存储的数据结构"""
    user_id: Optional[int] = None


# =====================================================
# API 路由接口
# =====================================================

@router.post(
    "/register",
    response_model=UserLoginResponse,
    status_code=status.HTTP_201_CREATED,  # 201 Created：资源成功创建
    summary="用户注册",
    description="注册新账号，注册成功后自动登录并返回JWT令牌"
)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    注册新用户

    流程：
    1. 检查用户名和邮箱是否已被注册（避免重复）
    2. 对密码进行 bcrypt 哈希加密
    3. 将新用户存入数据库
    4. 自动为新用户创建一个"默认分组"（方便立即使用收藏功能）
    5. 生成JWT令牌并返回（注册成功即视为登录）
    """
    # ---- 第一步：检查用户名是否已存在 ----
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被注册"
        )

    # ---- 第二步：检查邮箱是否已存在 ----
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    # ---- 第三步：创建新用户（密码必须哈希后存储，绝不存明文） ----
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password)  # 来自 core/security.py
    )
    db.add(new_user)

    # flush 将对象写入数据库（触发自增ID生成）但不提交事务
    # 这样我们可以在同一个事务中继续操作，获取 new_user.id
    await db.flush()

    # ---- 第四步：为新用户自动创建默认分组 ----
    from database.models import Group
    default_group = Group(
        name="默认分组",
        description="我的第一个收藏分组",
        color="#4A90E2",    # 蓝色
        user_id=new_user.id
    )
    db.add(default_group)
    # 事务会在 get_db 的 yield 之后由 session.commit() 自动提交

    # ---- 第五步：生成JWT令牌（注册成功即登录） ----
    # "sub" 存用户ID（字符串格式，符合JWT规范）
    access_token = create_access_token(data={"sub": str(new_user.id)})

    return UserLoginResponse(
        access_token=access_token,
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email
    )


@router.post(
    "/login",
    response_model=UserLoginResponse,
    summary="用户登录",
    description="用用户名或邮箱 + 密码登录，返回JWT令牌"
)
async def login(
    # OAuth2PasswordRequestForm 是 FastAPI 内置的表单数据模型
    # 它要求请求以 application/x-www-form-urlencoded 格式发送
    # 字段名固定为 username 和 password（OAuth2标准规定）
    # 在 Swagger 文档中，点击"Authorize"按钮使用的就是这个格式
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录

    支持用 用户名 或 邮箱 登录（两者均可）

    安全细节：
    - 无论是用户名不存在还是密码错误，都返回相同的错误信息
    - 这是故意的：不让攻击者通过错误信息判断用户名是否存在（枚举攻击防护）
    """
    # ---- 第一步：查找用户（支持用户名或邮箱登录） ----
    # | 是 SQLAlchemy 的 OR 运算符，等价于 WHERE username=? OR email=?
    result = await db.execute(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    # ---- 第二步：验证密码 ----
    # 故意将"用户不存在"和"密码错误"合并为同一个错误提示
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},  # 标准响应头
        )

    # ---- 第三步：检查账号状态 ----
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已被禁用，请联系管理员"
        )

    # ---- 第四步：生成并返回JWT令牌 ----
    access_token = create_access_token(data={"sub": str(user.id)})

    return UserLoginResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        email=user.email
    )


@router.get(
    "/me",
    response_model=UserInfoResponse,
    summary="获取当前用户信息",
    description="需要登录（在请求头携带 Bearer Token）才能访问"
)
async def get_me(
    # Depends(get_current_user) 是FastAPI的"依赖注入"
    # 请求到达前，FastAPI自动调用 get_current_user：
    # 1. 从请求头提取 Bearer Token
    # 2. 验证Token有效性
    # 3. 查询数据库返回User对象
    # 如果Token无效，直接返回401，不会执行函数体
    current_user: User = Depends(get_current_user)
):
    """
    获取当前登录用户的详细信息

    这是保护路由（Protected Route）的标准写法。
    只需添加 Depends(get_current_user) 参数，FastAPI自动处理认证。
    """
    return current_user
