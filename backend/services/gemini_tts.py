# =====================================================
# Google Gemini TTS 服务层
#
# 这个文件封装了所有与 Gemini API 交互的逻辑
# 路由文件（routers/tts.py）通过调用这里的函数来生成语音
#
# 为什么要单独抽一个服务层？
# 分层架构的好处：
# - 路由层只负责HTTP请求/响应（接收数据、验证、返回结果）
# - 服务层只负责业务逻辑（调用外部API、处理数据）
# - 如果以后要换其他TTS服务（如OpenAI TTS），只改这个文件
#   路由层完全不用改动
# =====================================================

import base64
import hashlib

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.database import settings
from database.models import TTSCache


# =====================================================
# 支持的语言和对应声音配置
#
# 为什么要限制"语言对应声音"？
# Gemini 的每个声音在某些语言下效果更好。
# 虽然技术上任何声音都能读任何语言，但对应关系是官方推荐的最佳搭配。
# =====================================================

SUPPORTED_LANGUAGES = {
    "zh-CN": {"name": "普通话（中国大陆）", "voices": ["kore", "charon"]},
    "en-US": {"name": "英语（美国）",        "voices": ["puck", "aoede", "fenrir"]},
    "ja-JP": {"name": "日语",               "voices": ["aoede", "kore"]},
    "ko-KR": {"name": "韩语",               "voices": ["charon"]},
    "fr-FR": {"name": "法语",               "voices": ["aoede"]},
    "de-DE": {"name": "德语",               "voices": ["fenrir"]},
}

# 每种语言的默认声音（当用户没有指定声音时使用）
DEFAULT_VOICES = {
    "zh-CN": "kore",
    "en-US": "puck",
    "ja-JP": "aoede",
    "ko-KR": "charon",
    "fr-FR": "aoede",
    "de-DE": "fenrir",
}

# 全局默认声音（语言不在上面列表中时的兜底值）
FALLBACK_VOICE = "kore"


def _build_cache_key(text: str, language: str, voice_name: str) -> str:
    """
    生成缓存键（MD5哈希值）

    相同的 文字 + 语言 + 声音 三元组，
    总是产生相同的 32 位十六进制字符串。
    用这个字符串作为数据库查找键，速度极快。

    示例：
    "你好_zh-CN_Kore" -> "a3f2c1d8..." (固定32位)
    """
    raw = f"{text}_{language}_{voice_name}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


async def synthesize_speech(
    text: str,
    language: str = "zh-CN",
    voice_name: str | None = None,
    db: AsyncSession | None = None,
) -> tuple[bytes, bool]:
    """
    将文字转换为语音（带缓存逻辑）

    参数：
    - text:       要转换的文字内容
    - language:   语言代码（如 zh-CN、en-US、ja-JP）
    - voice_name: 声音名称；传 None 时自动选择该语言的默认声音
    - db:         数据库 Session；传入时启用缓存，传 None 时跳过缓存

    返回：
    - (audio_bytes, from_cache)
      audio_bytes: 音频 PCM/WAV 二进制数据
      from_cache:  True 表示来自数据库缓存，False 表示新生成

    异常：
    - RuntimeError: API Key 未配置、或 Gemini 调用失败时抛出
    """
    # 1. 确定最终使用的声音名称
    if not voice_name:
        voice_name = DEFAULT_VOICES.get(language, FALLBACK_VOICE)

    # 2. 尝试读取缓存（只有在传入 db 时才启用）
    if db is not None:
        cache_key = _build_cache_key(text, language, voice_name)
        result = await db.execute(
            select(TTSCache).where(TTSCache.cache_key == cache_key)
        )
        cached = result.scalar_one_or_none()

        if cached:
            # 缓存命中：直接把 Base64 字符串解码成 bytes 返回
            # 存的时候用 base64 编码，取的时候解码，得到原始音频字节流
            audio_bytes = base64.b64decode(cached.audio_data)
            return audio_bytes, True

    # 3. 缓存未命中，调用 Gemini TTS API
    audio_bytes = await _call_gemini_tts(text, voice_name)

    # 4. 把结果写入缓存（只有传入 db 时才写缓存）
    if db is not None:
        cache_key = _build_cache_key(text, language, voice_name)
        # 音频是二进制数据，数据库存文本更方便，所以先 Base64 编码再存
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
        new_cache = TTSCache(
            cache_key=cache_key,
            text_content=text,
            language=language,
            voice_name=voice_name,
            audio_data=audio_base64,
            audio_format="wav",   # Gemini TTS 返回的是 PCM/WAV 格式
        )
        db.add(new_cache)
        # 注意：这里不 commit，由路由层统一 commit
        # 这样路由层可以把"写缓存"和"更新播放次数"放在同一个事务里

    return audio_bytes, False


async def _call_gemini_tts(text: str, voice_name: str) -> bytes:
    """
    实际调用 Gemini TTS REST API（不含缓存逻辑）

    直接使用 httpx 调用 REST API，比 SDK 更可靠，参数更透明。

    参数：
    - text:       要转换的文字
    - voice_name: Gemini 声音名称（如 Kore、Puck、Aoede）

    返回：
    - bytes: 原始音频数据（PCM 格式）
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("未配置 GEMINI_API_KEY，请在 .env 文件中设置")

    # Gemini REST API 地址
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    )

    # 请求体：直接用 REST API 的 JSON 格式（camelCase）
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": text}]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name
                    }
                }
            }
        }
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, json=payload)
        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini API 调用失败 {response.status_code}: {response.text}"
            )
        data = response.json()

    # 从响应中提取 Base64 编码的音频数据
    try:
        audio_b64 = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Gemini API 响应解析失败，未找到音频数据: {exc}") from exc

    # 解码 Base64 得到原始音频字节
    return base64.b64decode(audio_b64)


def get_supported_languages() -> dict:
    """返回支持的语言配置字典（供路由层调用）"""
    return SUPPORTED_LANGUAGES
