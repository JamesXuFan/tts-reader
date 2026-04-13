# =====================================================
# TTS（文字转语音）路由
#
# 接口列表：
# POST /api/v1/tts/speak      —— 文字转音频，直接返回音频字节流（核心功能）
# GET  /api/v1/tts/languages  —— 获取支持的语言列表及对应声音
#
# 设计原则：
# - 路由层只负责 HTTP 层的事情：接收参数、验证、调服务、返回响应
# - 真正的 TTS 逻辑全部在 services/gemini_tts.py 里
# - 两个接口都不要求登录（游客模式），降低使用门槛
# =====================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional, List

from database.database import get_db
from services.gemini_tts import synthesize_speech, get_supported_languages


router = APIRouter(prefix="/tts", tags=["语音合成"])


# =====================================================
# Pydantic 请求 / 响应模型
# =====================================================

class SpeakRequest(BaseModel):
    """
    POST /tts/speak 的请求体

    前端发送 JSON，例如：
    {
        "text": "你好，世界",
        "language": "zh-CN",
        "voice_name": "Kore"
    }
    """
    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="要转换为语音的文字内容，最多5000个字符"
    )
    language: Optional[str] = Field(
        default="zh-CN",
        description="语言代码，如 zh-CN、en-US、ja-JP"
    )
    voice_name: Optional[str] = Field(
        default=None,
        description="声音名称，如 Kore、Puck、Aoede；不填则自动选择该语言的默认声音"
    )


class VoiceInfo(BaseModel):
    """单条声音信息"""
    name: str = Field(..., description="声音名称（传给 API 用的参数值）")


class LanguageInfo(BaseModel):
    """单条语言信息"""
    code: str = Field(..., description="语言代码，如 zh-CN")
    name: str = Field(..., description="语言的中文显示名称")
    voices: List[str] = Field(..., description="该语言支持的声音名称列表")
    default_voice: str = Field(..., description="该语言的默认声音")


# =====================================================
# 各语言的默认声音（与 services/gemini_tts.py 保持同步）
# =====================================================
_DEFAULT_VOICES = {
    "zh-CN": "Kore",
    "en-US": "Puck",
    "ja-JP": "Aoede",
    "ko-KR": "Charon",
    "fr-FR": "Aoede",
    "de-DE": "Fenrir",
}


# =====================================================
# 接口 1：POST /tts/speak
# 文字转语音，直接返回音频字节流
# =====================================================

@router.post(
    "/speak",
    response_class=Response,
    responses={
        200: {
            "content": {"audio/wav": {}},
            "description": "WAV 格式的音频字节流，前端用 <audio> 标签播放即可"
        },
        400: {"description": "请求参数有误（文字为空或超长）"},
        503: {"description": "Gemini TTS 服务暂不可用"},
    },
    summary="文字转语音",
    description="将输入的文字转换为 WAV 音频，支持多语言、多声音。未登录用户也可使用。"
)
async def speak(
    request: SpeakRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    文字转语音核心接口

    流程：
    1. 参数校验（FastAPI + Pydantic 自动完成大部分）
    2. 调用 synthesize_speech()，内部先查缓存、再按需调 Gemini
    3. 把音频 bytes 直接写入 HTTP 响应体，Content-Type 设为 audio/wav
    4. commit 数据库（保存本次生成的缓存）

    为什么直接返回 bytes 而不是 Base64 JSON？
    - 直接返回 bytes：前端拿到 Blob，赋给 <audio src> 即可播放
    - 返回 Base64 JSON：前端还需要 atob() 解码再构造 Blob，多一步
    - 直接返回 bytes 的传输体积也更小（Base64 会增加约 33% 的大小）
    """
    text = request.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文字内容不能为空"
        )

    # 调用服务层（带缓存：传入 db）
    try:
        audio_bytes, from_cache = await synthesize_speech(
            text=text,
            language=request.language or "zh-CN",
            voice_name=request.voice_name,   # None 时服务层会自动选默认声音
            db=db,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"语音合成服务暂时不可用：{exc}"
        )

    # 注意：不需要在这里手动 commit。
    # database.py 的 get_db() 依赖函数在路由函数正常结束后会自动 commit。
    # 在这里额外 commit 反而会导致"重复提交"的问题。

    # 在响应头里告诉前端是否命中了缓存，方便调试
    headers = {
        "X-From-Cache": "true" if from_cache else "false",
        "X-Text-Length": str(len(text)),
        # 允许前端 JS 读取这两个自定义响应头
        "Access-Control-Expose-Headers": "X-From-Cache, X-Text-Length",
    }

    # 直接返回音频字节流，Content-Type 设为 audio/wav
    return Response(
        content=audio_bytes,
        media_type="audio/wav",
        headers=headers,
    )


# =====================================================
# 接口 2：GET /tts/languages
# 返回支持的语言列表及每种语言对应的声音
# =====================================================

@router.get(
    "/languages",
    response_model=List[LanguageInfo],
    summary="获取支持的语言列表",
    description="返回所有支持的语言代码、显示名称，以及每种语言可用的声音列表。"
)
async def get_languages():
    """
    返回支持的语言和声音配置

    这个接口不调用任何外部 API，只是返回一份静态配置。
    前端可以用这份数据来渲染"语言选择下拉框"和"声音选择下拉框"。

    示例响应：
    [
        {
            "code": "zh-CN",
            "name": "普通话（中国大陆）",
            "voices": ["Kore", "Charon"],
            "default_voice": "Kore"
        },
        ...
    ]
    """
    languages_config = get_supported_languages()

    result = []
    for code, info in languages_config.items():
        result.append(LanguageInfo(
            code=code,
            name=info["name"],
            voices=info["voices"],
            default_voice=_DEFAULT_VOICES.get(code, info["voices"][0]),
        ))

    return result
