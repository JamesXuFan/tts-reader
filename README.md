# TCC 朗读 / TCC Reader

> 多语言文字转语音工具，支持收藏管理与分组  
> Multi-language text-to-speech tool with favorites and group management

**Tech Stack:** Google Gemini TTS · FastAPI · React · SQLite · Tailwind CSS

---

## 功能特性 / Features

| 功能 | Feature |
|------|---------|
| 多语言语音合成（中/英/日/韩/法/德） | Multi-language TTS (ZH/EN/JA/KO/FR/DE) |
| 多种声音选择（Kore、Puck、Aoede 等） | Multiple voices (Kore, Puck, Aoede, etc.) |
| 音频播放器（进度条、倍速、下载） | Audio player with seek, speed control & download |
| TTS 结果缓存，相同内容不重复调用 API | TTS caching — identical text reuses stored audio |
| 用户注册 / 登录（JWT 认证） | User registration & login (JWT auth) |
| 收藏文字内容，随时回放 | Save text as favorites for later playback |
| 收藏分组管理（创建、删除、归组） | Favorites group management |
| 搜索收藏内容 | Search across saved favorites |
| 响应式布局，支持移动端 | Responsive layout, mobile-friendly |

---

## 快速开始 / Quick Start

### 前置要求 / Prerequisites

- Python 3.12+
- Node.js 18+
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### 后端启动 / Backend Setup

```bash
cd backend

# 创建并激活虚拟环境 / Create and activate virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖 / Install dependencies
pip install -r requirements.txt

# 配置环境变量 / Configure environment variables
cp .env.example .env
# 编辑 .env，填入 GEMINI_API_KEY
# Edit .env and set your GEMINI_API_KEY

# 启动服务 / Start server
uvicorn main:app --reload
# API 文档 / API docs: http://localhost:8000/docs
```

### 前端启动 / Frontend Setup

```bash
cd frontend

# 安装依赖 / Install dependencies
npm install

# 启动开发服务器 / Start dev server
npm run dev
# 访问 / Visit: http://localhost:5173
```

### 环境变量 / Environment Variables

在 `backend/.env` 中配置以下变量 / Configure the following in `backend/.env`:

| 变量 | 说明 | Default |
|------|------|---------|
| `GEMINI_API_KEY` | Google Gemini API 密钥 / API key | *(required)* |
| `SECRET_KEY` | JWT 签名密钥 / JWT signing secret | *(change in production)* |
| `DATABASE_URL` | 数据库连接 / Database URL | `sqlite+aiosqlite:///./tts_reader.db` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token 有效期（分钟）/ Token TTL | `43200` (30 days) |
| `FRONTEND_URL` | 前端地址（CORS）/ Frontend origin | `http://localhost:5173` |

---

## 项目结构 / Project Structure

```
tts-reader/
├── backend/
│   ├── main.py                 # FastAPI 应用入口 / App entry
│   ├── requirements.txt
│   ├── .env                    # 环境变量（不提交）/ Env vars (gitignored)
│   ├── core/
│   │   └── security.py         # JWT 认证 / JWT auth
│   ├── database/
│   │   ├── database.py         # 数据库连接 / DB connection
│   │   └── models.py           # ORM 模型 / ORM models
│   ├── routers/
│   │   ├── auth.py             # 注册/登录 / Register & login
│   │   ├── tts.py              # 语音合成 / TTS synthesis
│   │   ├── favorites.py        # 收藏管理 / Favorites CRUD
│   │   └── groups.py           # 分组管理 / Groups CRUD
│   └── services/
│       └── gemini_tts.py       # Gemini TTS 服务层 / TTS service
└── frontend/
    ├── src/
    │   ├── api/client.js       # Axios API 客户端 / API client
    │   ├── store/useAppStore.js # Zustand 全局状态 / Global state
    │   ├── components/         # 复用组件 / Reusable components
    │   │   ├── Layout.jsx
    │   │   ├── AudioPlayer.jsx
    │   │   ├── FavoriteButton.jsx
    │   │   ├── LanguageSelector.jsx
    │   │   └── Toast.jsx
    │   └── pages/              # 页面组件 / Page components
    │       ├── HomePage.jsx
    │       ├── LoginPage.jsx
    │       └── FavoritesPage.jsx
    └── vite.config.js
```

---

## API 文档 / API Reference

启动后端后访问 / After starting the backend, visit:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### 主要接口 / Main Endpoints

| Method | Path | 说明 / Description |
|--------|------|-------------------|
| `POST` | `/api/v1/auth/register` | 注册 / Register |
| `POST` | `/api/v1/auth/login` | 登录 / Login |
| `POST` | `/api/v1/tts/speak` | 文字转语音 / Text to speech |
| `GET`  | `/api/v1/tts/languages` | 支持的语言列表 / Supported languages |
| `GET`  | `/api/v1/favorites/` | 收藏列表 / List favorites |
| `POST` | `/api/v1/favorites/` | 新建收藏 / Create favorite |
| `PUT`  | `/api/v1/favorites/{id}` | 更新收藏/移动分组 / Update / move group |
| `GET`  | `/api/v1/groups/` | 分组列表 / List groups |
| `POST` | `/api/v1/groups/` | 新建分组 / Create group |

---

## 开发进度 / Development Progress

- [x] Step 1: FastAPI 后端骨架 / FastAPI backend scaffold
- [x] Step 2: SQLite 数据库建表 / SQLite schema setup
- [x] Step 3: 用户注册/登录接口 / Auth endpoints
- [x] Step 4: 接入 Gemini TTS API / Gemini TTS integration
- [x] Step 5: 收藏和分组接口 / Favorites & groups API
- [x] Step 6: React 前端 / React frontend
- [x] Step 7: TTS 缓存优化 / TTS response caching
- [x] Step 8: UI 完善 / UI polish

---

## License

MIT
