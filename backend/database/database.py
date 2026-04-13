# =====================================================
# 数据库连接配置文件
#
# 这里做了什么？
# 1. 创建数据库引擎（engine）—— 理解为"连接数据库的工具"
# 2. 创建会话工厂（SessionLocal）—— 每次操作数据库都需要开启一个"会话"
# 3. 定义所有模型的基类（Base）—— 所有数据表模型都要继承这个类
# 4. 提供 get_db 依赖函数 —— FastAPI路由通过它获取数据库连接
#
# 关于"异步"：
# 普通写法：程序等数据库返回结果才继续（像排队买票）
# 异步写法：程序发出请求后去做别的事，等数据库好了再回来（像叫号取票）
# 异步能让服务器同时处理更多请求，性能更好
# =====================================================

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

# 加载 .env 文件中的环境变量
load_dotenv()


# ---- 配置类：从环境变量读取配置 ----
class Settings(BaseSettings):
    """
    pydantic_settings 会自动从环境变量或 .env 文件读取这些值
    字段名就是环境变量名（不区分大小写）
    """
    database_url: str = "sqlite+aiosqlite:///./tts_reader.db"
    secret_key: str = "dev-secret-key-please-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # 30天
    gemini_api_key: str = ""
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"         # 指定从哪个文件读取
        env_file_encoding = "utf-8"


# 全局设置对象，其他模块通过 from database.database import settings 来使用
settings = Settings()


# ---- 创建数据库引擎 ----
# create_async_engine：创建异步数据库引擎
# echo=True：开发时打印所有SQL语句（方便调试），生产环境改为False
engine = create_async_engine(
    settings.database_url,
    echo=True,   # 调试模式：在控制台打印执行的SQL语句
    future=True  # 使用SQLAlchemy 2.0的新API风格
)


# ---- 创建异步会话工厂 ----
# 每次需要操作数据库时，调用 AsyncSessionLocal() 创建一个新会话
# expire_on_commit=False：提交后对象不过期，避免一些常见的异步问题
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


# ---- 定义模型基类 ----
# 所有数据表模型（在models.py中定义）都要继承这个Base类
# Base帮助SQLAlchemy追踪所有模型，在创建表时使用
class Base(DeclarativeBase):
    pass


# ---- 数据库依赖函数 ----
async def get_db():
    """
    FastAPI的依赖注入函数

    用法：在路由函数的参数中写 db: AsyncSession = Depends(get_db)
    FastAPI会自动调用这个函数并将数据库会话传进去

    使用 async with 确保会话在使用完毕后一定会被关闭
    即使中途发生错误也会正确关闭，防止连接泄漏
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session          # 将数据库会话提供给路由函数使用
            await session.commit() # 路由函数正常结束后提交事务
        except Exception:
            await session.rollback()  # 发生错误时回滚事务（撤销所有修改）
            raise                     # 重新抛出异常，让FastAPI处理


# ---- 初始化数据库（创建所有表） ----
async def init_db():
    """
    在应用启动时调用，根据模型定义自动创建数据库表
    如果表已存在，不会重复创建（checkfirst=True是默认行为）
    """
    # 需要在这里导入models，确保所有模型类都被注册到Base中
    from database import models  # noqa: F401（告诉代码检查工具这个导入是故意的）

    async with engine.begin() as conn:
        # create_all：根据Base下所有模型自动创建对应的数据库表
        await conn.run_sync(Base.metadata.create_all)

    print("数据库表初始化完成")
