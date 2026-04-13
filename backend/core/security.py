# =====================================================
# 安全核心模块 (core/security.py)
#
# 这个文件集中管理所有"安全相关"的功能：
# 1. 密码哈希与验证（bcrypt算法）
# 2. JWT令牌的生成与解码
# 3. get_current_user 依赖函数（验证请求是否已登录）
#
# 为什么单独放在 core/ 目录？
# 安全功能会被多个路由模块复用，集中管理可以：
# - 避免代码重复（DRY原则：Don't Repeat Yourself）
# - 统一修改一处即可影响全局（比如换加密算法）
# - 更清晰的项目结构
# =====================================================

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import get_db, settings
from database.models import User


# =====================================================
# 一、密码哈希工具
# =====================================================

# CryptContext：密码哈希的"上下文配置器"
# schemes=["bcrypt"]：指定使用 bcrypt 算法
# deprecated="auto"：当有更新的哈希策略时，自动标记旧的哈希需要升级
#
# 什么是 bcrypt？
# 它是专门为密码存储设计的哈希算法，有几个特性：
# 1. 慢速（故意的）：暴力破解成本极高
# 2. 加盐（自动）：每次哈希结果都不同，防止彩虹表攻击
# 3. 不可逆：从哈希值无法推算出原始密码
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    验证明文密码与哈希值是否匹配

    参数：
    - plain_password：用户输入的原始密码（如 "mypassword123"）
    - hashed_password：数据库中存储的哈希字符串（如 "$2b$12$..."）

    返回：True 表示密码正确，False 表示错误

    原理：bcrypt会用同样的盐值（内嵌在哈希字符串中）对输入密码
    重新哈希，然后比较两个哈希值是否相同。
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    将明文密码转换为安全的哈希字符串

    参数：
    - password：用户设置的明文密码

    返回：类似 "$2b$12$eImiTXuWVxfM37uY3Jhb.eMkG0SY6Bm1..." 的哈希字符串

    这个哈希字符串会存入数据库，原始密码绝不保存。
    即使数据库被黑客拿到，他们也无法直接得知用户密码。
    """
    return pwd_context.hash(password)


# =====================================================
# 二、JWT令牌工具
# =====================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    生成JWT访问令牌

    参数：
    - data：要编码进令牌的数据，通常是 {"sub": "用户ID字符串"}
      "sub" 是JWT标准字段名（subject，主体），约定俗成用来存用户标识
    - expires_delta：自定义有效期；不传则使用 settings 中配置的默认值

    返回：JWT令牌字符串（三段式：header.payload.signature）

    JWT结构示例（可在 https://jwt.io 解码查看）：
    eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9  ← header（算法信息）
    .eyJzdWIiOiIxIiwiZXhwIjoxNzM...         ← payload（用户数据+过期时间）
    .SflKxwRJSMeKKF2QT4fwpMeJf36...         ← signature（数字签名，防篡改）
    """
    # 复制数据，避免修改传入的原始字典
    to_encode = data.copy()

    # 计算过期时间（UTC时区）
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # 使用配置文件中的默认有效期（settings.access_token_expire_minutes）
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # 将过期时间写入令牌载荷
    # "exp" 是JWT标准保留字段，验证时会自动检查是否过期
    to_encode.update({"exp": expire})

    # 用 SECRET_KEY 对数据进行签名，生成最终的JWT字符串
    # algorithm：签名算法，HS256（HMAC-SHA256），速度快、安全性足够
    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm
    )
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    解码并验证JWT令牌

    参数：
    - token：JWT令牌字符串

    返回：
    - 成功：令牌中的载荷数据（字典）
    - 失败（过期/篡改/格式错误）：返回 None

    说明：python-jose 在解码时会自动验证：
    1. 签名是否合法（防止伪造）
    2. 是否已过期（exp字段）
    如果任一验证失败，会抛出 JWTError 异常。
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]  # 注意这里是列表，支持多种算法
        )
        return payload
    except JWTError:
        return None


# =====================================================
# 三、OAuth2 令牌提取配置
# =====================================================

# OAuth2PasswordBearer 告诉 FastAPI 如何从请求中提取令牌：
# 它会自动从请求头 "Authorization: Bearer <token>" 中提取 <token> 部分
#
# tokenUrl：这是 Swagger 文档中"Authorize"按钮使用的登录接口地址
# 注意：包含完整路径前缀 /api/v1/auth/login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# =====================================================
# 四、用户身份验证依赖函数
# =====================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    FastAPI 依赖函数：从JWT令牌中解析并返回当前登录用户

    这是"守门员"函数：所有需要登录才能访问的接口，
    只需在参数中加上 current_user: User = Depends(get_current_user)，
    FastAPI 就会自动在请求到达之前先验证身份。

    工作流程：
    1. OAuth2PasswordBearer 从请求头提取 Bearer Token
    2. 解码令牌，取出用户ID
    3. 用用户ID查询数据库，确认用户存在且激活
    4. 返回用户对象（或抛出401错误）

    用法示例：
        @router.get("/protected-route")
        async def protected(current_user: User = Depends(get_current_user)):
            return {"message": f"你好，{current_user.username}"}
    """
    # 定义统一的认证失败错误（故意不区分"令牌无效"和"用户不存在"）
    # 安全原因：不给攻击者提供"哪里错了"的线索
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},  # 标准响应头，告知客户端认证方式
    )

    # 第一步：解码令牌
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    # 第二步：从载荷中取出用户ID
    # "sub" 是我们在 create_access_token 中存入的用户ID
    user_id_str: Optional[str] = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    # 将字符串形式的ID转为整数（我们存储时用了 str(user.id)）
    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise credentials_exception

    # 第三步：查询数据库，确认用户真实存在
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # 第四步：检查账号是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号已被禁用，请联系管理员"
        )

    return user
