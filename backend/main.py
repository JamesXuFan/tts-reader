# =====================================================
# TCC朗读网站 - FastAPI 应用入口
#
# 这是整个后端应用的"总指挥"文件：
# 1. 加载 .env 环境变量（SECRET_KEY、GEMINI_API_KEY 等）
# 2. 创建FastAPI应用实例
# 3. 配置CORS（跨域资源共享）
# 4. 注册所有路由（告诉应用哪些URL对应哪些处理函数）
# 5. 配置应用启动/关闭时的初始化操作
#
# 什么是CORS（跨域资源共享）？
# 浏览器出于安全考虑，不允许前端页面直接访问不同域名的API
# 例如：前端在 localhost:5173，后端在 localhost:8000
# 这就叫"跨域"——两个不同的端口视为不同的"域"
# 配置CORS就是告诉后端："允许来自前端地址的请求"
# =====================================================

# ---- 第一步：加载 .env 文件（必须在其他导入之前） ----
# python-dotenv 会读取 .env 文件并将其中的键值对设置为环境变量
# 这样 pydantic_settings 的 Settings 类就能读取到 SECRET_KEY、GEMINI_API_KEY 等
from dotenv import load_dotenv
import os

# 找到 .env 文件的绝对路径（与 main.py 同目录）
_env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(_env_path)  # 显式指定路径，确保无论从哪里启动都能找到

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from database.database import init_db, settings
from routers import auth, tts, groups, favorites


# ---- 应用生命周期管理 ----
# @asynccontextmanager 装饰器让我们定义应用启动和关闭时的逻辑
# yield 之前的代码在启动时执行（初始化）
# yield 之后的代码在关闭时执行（清理）
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    启动时：初始化数据库（创建表结构）
    关闭时：可以在这里关闭数据库连接池等
    """
    print("=" * 50)
    print("正在启动 TCC朗读网站 后端服务...")

    # 打印关键配置项（脱敏显示，方便调试）
    print(f"  SECRET_KEY 已加载: {'是' if settings.secret_key and settings.secret_key != 'dev-secret-key-please-change-in-production' else '使用默认值（建议修改）'}")
    print(f"  GEMINI_API_KEY 已配置: {'是' if settings.gemini_api_key else '否（TTS功能不可用）'}")
    print(f"  数据库: {settings.database_url}")

    # 初始化数据库（如果表不存在则创建）
    await init_db()
    print("数据库初始化完成")
    print("=" * 50)

    yield  # 应用正常运行阶段

    # 应用关闭时的清理工作
    print("后端服务正在关闭...")


# ---- 创建FastAPI应用实例 ----
app = FastAPI(
    title="TCC朗读网站 API",
    description="""
## TCC朗读网站后端API

### 功能模块
- **认证**：用户注册、登录、JWT令牌验证
- **TTS语音合成**：使用Google Gemini API将文字转换为语音
- **收藏管理**：收藏文字内容，支持分组管理
- **分组管理**：创建、编辑、删除收藏分组

### 如何测试需要登录的接口
1. 先调用 `POST /api/v1/auth/register` 或 `POST /api/v1/auth/login`
2. 复制返回的 `access_token` 值
3. 点击页面右上角的 **Authorize** 按钮
4. 在弹窗中输入 `Bearer 你的token值`（注意Bearer后面有空格）
5. 点击 Authorize，之后的请求会自动携带令牌
    """,
    version="1.0.0",
    lifespan=lifespan  # 注册生命周期管理器
)


# ---- 配置CORS跨域 ----
# 允许前端开发服务器（React/Vue Vite默认端口5173）访问后端
# 生产环境需要将 allow_origins 改为真实的前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,    # 从 .env 文件读取的前端地址
        "http://localhost:5173",  # Vite开发服务器默认端口
        "http://localhost:3000",  # 备用端口（Create React App默认）
        "http://127.0.0.1:5173",  # 有时候浏览器用127.0.0.1而不是localhost
    ],
    allow_credentials=True,   # 允许携带Cookie
    allow_methods=["*"],      # 允许所有HTTP方法（GET, POST, PUT, DELETE等）
    allow_headers=["*"],      # 允许所有请求头（包括Authorization头）
)


# ---- 注册路由（统一添加 /api/v1 前缀） ----
# include_router 相当于把 router 中定义的所有接口都加入主应用
# prefix="/api/v1" 是API版本控制的常见做法：
# 将来如果API需要大改，可以新增 /api/v2 路由，而不影响旧版客户端
API_PREFIX = "/api/v1"

app.include_router(auth.router,      prefix=API_PREFIX)  # 认证：/api/v1/auth/...
app.include_router(tts.router,       prefix=API_PREFIX)  # TTS：/api/v1/tts/...
app.include_router(groups.router,    prefix=API_PREFIX)  # 分组：/api/v1/groups/...
app.include_router(favorites.router, prefix=API_PREFIX)  # 收藏：/api/v1/favorites/...


# ---- 根路由（健康检查） ----
@app.get("/", tags=["健康检查"])
async def root():
    """
    根路径，用于快速确认服务是否正常运行
    访问 http://localhost:8000/ 可以检查后端是否在线
    """
    return {
        "status": "running",
        "message": "TCC朗读网站后端服务正常运行",
        "docs_url": "http://localhost:8000/docs",
        "api_prefix": API_PREFIX,
        "version": "1.0.0"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """详细健康检查接口（监控系统可定期调用）"""
    return {
        "status": "healthy",
        "database": "connected",
        "gemini_api": "configured" if settings.gemini_api_key else "not_configured"
    }


# =====================================================
# 启动说明（在 backend/ 目录下运行）
# =====================================================
# 开发模式（文件改动自动重启）：
#   uvicorn main:app --reload
#
# 指定端口：
#   uvicorn main:app --reload --port 8000
#
# 访问API文档：
#   Swagger UI：http://localhost:8000/docs   ← 推荐，可直接测试
#   ReDoc：     http://localhost:8000/redoc  ← 适合阅读文档
# =====================================================
