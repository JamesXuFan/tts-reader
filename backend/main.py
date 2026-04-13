# =====================================================
# TCC朗读网站 - FastAPI 应用入口
#
# 这是整个后端应用的"总指挥"文件：
# 1. 创建FastAPI应用实例
# 2. 配置CORS（跨域资源共享）
# 3. 注册所有路由（告诉应用哪些URL对应哪些处理函数）
# 4. 配置应用启动/关闭时的初始化操作
#
# 什么是CORS（跨域资源共享）？
# 浏览器出于安全考虑，不允许前端页面直接访问不同域名的API
# 例如：前端在 localhost:5173，后端在 localhost:8000
# 这就叫"跨域"——两个不同的端口视为不同的"域"
# 配置CORS就是告诉后端："允许来自前端地址的请求"
# =====================================================

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
    print("正在启动 TCC朗读网站 后端服务...")

    # 初始化数据库（如果表不存在则创建）
    await init_db()
    print("数据库初始化完成")

    yield  # 应用正常运行阶段

    # 应用关闭时的清理工作（目前不需要特殊处理）
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

    ### 认证方式
    所有需要登录的接口使用 **Bearer Token** 认证。
    先调用 `/auth/login` 获取token，然后在请求头中加入：
    `Authorization: Bearer <your_token>`
    """,
    version="1.0.0",
    lifespan=lifespan  # 注册生命周期管理器
)


# ---- 配置CORS跨域 ----
# 允许前端开发服务器（React Vite默认端口5173）访问后端
# 生产环境需要将 allow_origins 改为真实的前端域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,    # 从环境变量读取前端地址（如 http://localhost:5173）
        "http://localhost:5173",  # Vite开发服务器默认端口
        "http://localhost:3000",  # 备用端口（create-react-app默认）
        "http://127.0.0.1:5173",  # 有时候浏览器用127.0.0.1而不是localhost
    ],
    allow_credentials=True,   # 允许携带Cookie（JWT令牌通过Header传递，这里主要是兼容性）
    allow_methods=["*"],      # 允许所有HTTP方法（GET, POST, PUT, DELETE等）
    allow_headers=["*"],      # 允许所有请求头（包括自定义的Authorization头）
)


# ---- 注册路由 ----
# 将各个功能模块的路由"挂载"到主应用上
# include_router 相当于把 router 中定义的所有接口都加入主应用
app.include_router(auth.router)       # 认证相关：/auth/register, /auth/login 等
app.include_router(tts.router)        # TTS相关：/tts/synthesize 等
app.include_router(groups.router)     # 分组相关：/groups/ 等
app.include_router(favorites.router)  # 收藏相关：/favorites/ 等


# ---- 根路由（健康检查） ----
@app.get("/", tags=["健康检查"])
async def root():
    """
    根路径，用于检查服务是否正常运行

    访问 http://localhost:8000/ 可以快速确认后端在线
    """
    return {
        "status": "running",
        "message": "TCC朗读网站后端服务正常运行",
        "docs_url": "http://localhost:8000/docs",
        "version": "1.0.0"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """详细健康检查接口"""
    return {
        "status": "healthy",
        "database": "connected",
        "gemini_api": "configured" if settings.gemini_api_key else "not_configured"
    }


# =====================================================
# 启动说明（仅在直接运行此文件时显示）
# =====================================================
# 正常启动方式（在 backend/ 目录下运行）：
#   uvicorn main:app --reload
#
# 参数说明：
#   main   → 文件名（main.py）
#   app    → FastAPI实例变量名
#   --reload → 文件改动时自动重启（开发模式专用）
#
# 访问API文档：
#   Swagger UI：http://localhost:8000/docs
#   ReDoc：     http://localhost:8000/redoc
# =====================================================
