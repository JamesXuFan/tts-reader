# =====================================================
# 认证路由（用户注册 & 登录）
#
# 这个文件处理所有和用户身份相关的API接口：
# POST /auth/register  —— 注册新账号
# POST /auth/login     —— 登录获取JWT令牌
# GET  /auth/me        —— 获取当前登录用户信息
#
# 什么是JWT（JSON Web Token）？
# 想象成一张"通行证"：
# 1. 用户登录成功后，服务器发给用户一个JWT令牌
# 2. 用户之后的每次请求都带上这个令牌
# 3. 服务器验证令牌有效就认可这个用户的身份
# 4. 令牌有过期时间，过期后需要重新登录
# =====================================================

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, field_validator

from database.database import get_db, settings
from database.models import User


# ---- 创建路由对象 ----
# prefix="/auth" 表示这个路由下所有接口都以 /auth 开头
# tags=["认证"] 用于在API文档中分组显示
router = APIRouter(prefix="/auth", tags=["认证"])


# ---- 密码加密工具 ----
# CryptContext：密码哈希上下文，使用bcrypt算法
# bcrypt是目前最安全的密码哈希算法之一，专门为存储密码设计
# deprecated="auto"：自动处理旧版本的哈希升级
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---- JWT令牌获取方式 ----
# OAuth2PasswordBearer：告诉FastAPI从请求头的 Authorization: Bearer <token> 中提取令牌
# tokenUrl 是用于获取令牌的接口路径（登录接口）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =====================================================
# Pydantic 数据模型（请求/响应的数据结构定义）
# =====================================================

class UserRegisterRequest(BaseModel):
    """注册请求体：前端发送的注册数据格式"""
    username: str
    email: EmailStr  # EmailStr会自动验证邮箱格式
    password: str

    @field_validator("username")
    @classmethod
    def username_must_be_valid(cls, v: str) -> str:
        """验证用户名：3-50个字符，只允许字母数字和下划线"""
        v = v.strip()
        if len(v) < 3:
            raise ValueError("用户名至少需要3个字符")
        if len(v) > 50:
            raise ValueError("用户名不能超过50个字符")
        return v

    @field_validator("password")
    @classmethod
    def password_must_be_strong(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError("密码至少需要6个字符")
        return v


class UserLoginResponse(BaseModel):
    """登录成功的响应体：返回给前端的数据"""
    access_token: str      # JWT令牌字符串
    token_type: str = "bearer"  # 令牌类型，固定为"bearer"
    user_id: int
    username: str
    email: str


class UserInfoResponse(BaseModel):
    """用户信息响应体"""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True  # 允许从SQLAlchemy模型对象直接转换


class TokenData(BaseModel):
    """JWT令牌中存储的数据"""
    user_id: Optional[int] = None


# =====================================================
# 工具函数
# =====================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码：将输入的明文密码与数据库中的哈希值对比"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """将明文密码转换为哈希值（用于注册时存储）"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成JWT令牌

    参数：
    - data: 要存入令牌的数据（通常是用户ID）
    - expires_delta: 令牌有效期，不传则使用默认配置
    """
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode.update({"exp": expire})  # 将过期时间加入令牌数据

    # 用SECRET_KEY和算法对数据进行签名，生成令牌字符串
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    依赖函数：从JWT令牌中解析当前登录用户

    在需要登录才能访问的路由中，将这个函数作为Depends参数传入
    FastAPI会自动调用它验证令牌并返回用户对象

    例如：
    @router.get("/profile")
    async def get_profile(current_user: User = Depends(get_current_user)):
        return current_user
    """
    # 定义认证失败时的错误信息
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # 解码JWT令牌
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
        user_id: int = payload.get("sub")  # "sub"是JWT标准字段，存储主体（这里存用户ID）
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=int(user_id))
    except JWTError:
        raise credentials_exception

    # 从数据库查询用户
    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已被禁用"
        )

    return user


# =====================================================
# API 路由接口
# =====================================================

@router.post("/register", response_model=UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    注册新用户

    流程：
    1. 检查用户名和邮箱是否已被注册
    2. 对密码进行哈希加密
    3. 将新用户存入数据库
    4. 自动为新用户创建一个"默认分组"
    5. 生成JWT令牌并返回（注册即登录）
    """
    # 检查用户名是否已存在
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被注册"
        )

    # 检查邮箱是否已存在
    result = await db.execute(select(User).where(User.email == request.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该邮箱已被注册"
        )

    # 创建新用户（密码哈希后存储，绝对不存明文）
    new_user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password)
    )
    db.add(new_user)
    await db.flush()  # flush将对象写入数据库但不提交，这样可以获取自动生成的id

    # 为新用户自动创建默认分组
    from database.models import Group
    default_group = Group(
        name="默认分组",
        description="我的第一个收藏分组",
        color="#4A90E2",
        user_id=new_user.id
    )
    db.add(default_group)
    # 事务会在 get_db 的 yield 之后自动提交

    # 生成JWT令牌（注册成功即视为登录）
    access_token = create_access_token(data={"sub": str(new_user.id)})

    return UserLoginResponse(
        access_token=access_token,
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email
    )


@router.post("/login", response_model=UserLoginResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # OAuth2标准表单：username + password
    db: AsyncSession = Depends(get_db)
):
    """
    用户登录

    注意：OAuth2PasswordRequestForm 要求前端用表单格式发送，
    字段名固定为 username 和 password
    我们允许用用户名或邮箱登录

    流程：
    1. 用用户名（或邮箱）查找用户
    2. 验证密码
    3. 生成并返回JWT令牌
    """
    # 先尝试用用户名查找，再尝试用邮箱查找
    result = await db.execute(
        select(User).where(
            (User.username == form_data.username) | (User.email == form_data.username)
        )
    )
    user = result.scalar_one_or_none()

    # 验证用户存在且密码正确
    # 注意：无论是用户名不存在还是密码错误，都返回相同的错误信息
    # 这是安全实践：不让攻击者知道用户名是否存在
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已被禁用，请联系管理员"
        )

    # 生成JWT令牌
    access_token = create_access_token(data={"sub": str(user.id)})

    return UserLoginResponse(
        access_token=access_token,
        user_id=user.id,
        username=user.username,
        email=user.email
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息

    这个接口需要登录才能访问
    FastAPI会通过 Depends(get_current_user) 自动验证JWT令牌
    """
    return current_user
