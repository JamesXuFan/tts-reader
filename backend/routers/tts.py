# =====================================================
# TTS（文字转语音）路由
#
# 接口列表：
# POST /tts/synthesize       —— 将文字转换为音频（核心功能）
# GET  /tts/languages        —— 获取支持的语言列表
# GET  /tts/voices           —— 获取可用的声音列表
# POST /tts/synthesize/guest —— 游客模式TTS（不需要登录，有限制）
#
# 注意：具体的Gemini TTS调用逻辑在 services/gemini_tts.py 中实现
# 这个文件只负责接收HTTP请求、调用服务、返回响应
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, List
import hashlib
import base64

from database.database import get_db
from database.models import TTSCache, Favorite
from routers.auth import get_current_user, User


router = APIRouter(prefix="/tts", tags=["语音合成"])


# =====================================================
# 支持的语言配置
# =====================================================

SUPPORTED_LANGUAGES = [
    {"code": "zh-CN", "name": "中文（普通话）", "flag": ""},
    {"code": "zh-TW", "name": "中文（繁体）", "flag": ""},
    {"code": "en-US", "name": "英语（美式）", "flag": ""},
    {"code": "en-GB", "name": "英语（英式）", "flag": ""},
    {"code": "ja-JP", "name": "日语", "flag": ""},
    {"code": "ko-KR", "name": "韩语", "flag": ""},
    {"code": "fr-FR", "name": "法语", "flag": ""},
    {"code": "de-DE", "name": "德语", "flag": ""},
    {"code": "es-ES", "name": "西班牙语", "flag": ""},
    {"code": "it-IT", "name": "意大利语", "flag": ""},
    {"code": "pt-BR", "name": "葡萄牙语（巴西）", "flag": ""},
    {"code": "ru-RU", "name": "俄语", "flag": ""},
    {"code": "ar-SA", "name": "阿拉伯语", "flag": ""},
    {"code": "th-TH", "name": "泰语", "flag": ""},
    {"code": "vi-VN", "name": "越南语", "flag": ""},
]

# Gemini TTS 支持的声音名称（部分）
# 完整列表见：https://ai.google.dev/gemini-api/docs/speech-generation
AVAILABLE_VOICES = [
    {"name": "Zephyr", "description": "明亮活泼", "gender": "female"},
    {"name": "Puck", "description": "轻快有趣", "gender": "male"},
    {"name": "Charon", "description": "沉稳低沉", "gender": "male"},
    {"name": "Kore", "description": "温柔清晰", "gender": "female"},
    {"name": "Fenrir", "description": "激情有力", "gender": "male"},
    {"name": "Aoede", "description": "悦耳流畅", "gender": "female"},
    {"name": "Leda", "description": "年轻自然", "gender": "female"},
    {"name": "Orus", "description": "稳重专业", "gender": "male"},
    {"name": "Schedar", "description": "清晰标准", "gender": "male"},
    {"name": "Umbriel", "description": "轻柔平静", "gender": "male"},
]


# =====================================================
# Pydantic 数据模型
# =====================================================

class TTSSynthesizeRequest(BaseModel):
    """TTS合成请求体"""
    text: str                                   # 要转换的文字
    language: Optional[str] = "zh-CN"          # 语言代码
    voice_name: Optional[str] = "Kore"         # 声音名称
    favorite_id: Optional[int] = None          # 关联的收藏ID（可选，用于更新播放次数）


class TTSResponse(BaseModel):
    """TTS合成响应体"""
    audio_base64: str       # Base64编码的音频数据
    audio_format: str       # 音频格式（mp3/wav等）
    from_cache: bool        # 是否来自缓存
    text_length: int        # 文字长度（字符数）


class LanguageItem(BaseModel):
    """语言列表项"""
    code: str
    name: str
    flag: str


class VoiceItem(BaseModel):
    """声音列表项"""
    name: str
    description: str
    gender: str


def generate_cache_key(text: str, language: str, voice_name: str) -> str:
    """
    生成TTS缓存的唯一键

    相同的文字+语言+声音组合，生成相同的缓存键
    这样下次请求相同内容时，可以直接从数据库取缓存
    """
    content = f"{text}|{language}|{voice_name}"
    return hashlib.md5(content.encode("utf-8")).hexdigest()


# =====================================================
# API 路由
# =====================================================

@router.get("/languages", response_model=List[LanguageItem])
async def get_languages():
    """获取支持的语言列表（不需要登录）"""
    return SUPPORTED_LANGUAGES


@router.get("/voices", response_model=List[VoiceItem])
async def get_voices():
    """获取可用的声音列表（不需要登录）"""
    return AVAILABLE_VOICES


@router.post("/synthesize", response_model=TTSResponse)
async def synthesize_tts(
    request: TTSSynthesizeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    将文字转换为语音（需要登录）

    流程：
    1. 检查数据库中是否有缓存（相同文字+语言+声音）
    2. 有缓存 → 直接返回缓存的音频数据
    3. 无缓存 → 调用Gemini API生成音频 → 存入缓存 → 返回
    4. 如果指定了favorite_id，更新该收藏的播放次数

    为什么要缓存？
    - 避免重复调用付费API
    - 减少响应时间（缓存直接返回，无需等待AI生成）
    """
    # 验证文字不为空
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文字内容不能为空"
        )

    # 限制文字长度（防止滥用）
    if len(text) > 5000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文字内容不能超过5000个字符"
        )

    voice_name = request.voice_name or "Kore"
    language = request.language or "zh-CN"

    # 生成缓存键
    cache_key = generate_cache_key(text, language, voice_name)

    # 查询缓存
    cache_result = await db.execute(
        select(TTSCache).where(TTSCache.cache_key == cache_key)
    )
    cached = cache_result.scalar_one_or_none()

    if cached:
        # 命中缓存，直接返回
        # 更新收藏播放次数（如果指定了）
        if request.favorite_id:
            await _increment_play_count(request.favorite_id, current_user.id, db)

        return TTSResponse(
            audio_base64=cached.audio_data,
            audio_format=cached.audio_format,
            from_cache=True,
            text_length=len(text)
        )

    # 未命中缓存，调用Gemini API
    from services.gemini_tts import synthesize_speech
    try:
        audio_bytes = await synthesize_speech(
            text=text,
            language=language,
            voice_name=voice_name
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"语音合成服务暂时不可用：{str(e)}"
        )

    # 将音频数据Base64编码后存入缓存
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    new_cache = TTSCache(
        cache_key=cache_key,
        text_content=text,
        language=language,
        voice_name=voice_name,
        audio_data=audio_base64,
        audio_format="mp3",
        favorite_id=request.favorite_id
    )
    db.add(new_cache)

    # 更新收藏播放次数
    if request.favorite_id:
        await _increment_play_count(request.favorite_id, current_user.id, db)

    return TTSResponse(
        audio_base64=audio_base64,
        audio_format="mp3",
        from_cache=False,
        text_length=len(text)
    )


@router.post("/synthesize/guest", response_model=TTSResponse)
async def synthesize_tts_guest(
    request: TTSSynthesizeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    游客模式TTS（不需要登录）

    限制：
    - 单次文字不超过200个字符
    - 不缓存结果（不占用数据库空间）
    - 可以限制频率（TODO：后续添加IP限流）
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="文字内容不能为空")

    # 游客模式字数限制
    if len(text) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="游客模式最多支持200个字符，请登录后使用完整功能"
        )

    from services.gemini_tts import synthesize_speech
    try:
        audio_bytes = await synthesize_speech(
            text=text,
            language=request.language or "zh-CN",
            voice_name=request.voice_name or "Kore"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"语音合成服务暂时不可用：{str(e)}"
        )

    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    return TTSResponse(
        audio_base64=audio_base64,
        audio_format="mp3",
        from_cache=False,
        text_length=len(text)
    )


# =====================================================
# 辅助函数
# =====================================================

async def _increment_play_count(favorite_id: int, user_id: int, db: AsyncSession):
    """增加收藏的播放次数"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.id == favorite_id,
            Favorite.user_id == user_id
        )
    )
    favorite = result.scalar_one_or_none()
    if favorite:
        favorite.play_count += 1
