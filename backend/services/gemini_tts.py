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

import httpx
import base64
from database.database import settings


async def synthesize_speech(
    text: str,
    language: str = "zh-CN",
    voice_name: str = "Kore"
) -> bytes:
    """
    调用 Google Gemini API 将文字转换为语音

    参数：
    - text: 要转换的文字内容
    - language: 语言代码（如 zh-CN、en-US、ja-JP）
    - voice_name: 声音名称（如 Kore、Puck、Zephyr）

    返回：
    - bytes: 音频数据的二进制内容（MP3格式）

    异常：
    - RuntimeError: API调用失败时抛出，包含错误详情
    """
    api_key = settings.gemini_api_key
    if not api_key:
        raise RuntimeError("未配置 GEMINI_API_KEY，请在 .env 文件中设置")

    # Gemini TTS API 端点
    # 使用 gemini-2.5-flash-preview-tts 模型（支持多语言TTS）
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-2.5-flash-preview-tts:generateContent?key={api_key}"
    )

    # 构建请求体
    # Gemini TTS API 的格式参考：
    # https://ai.google.dev/gemini-api/docs/speech-generation
    request_body = {
        "contents": [
            {
                "parts": [
                    {
                        "text": text
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],  # 指定返回音频
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name  # 声音名称
                    }
                }
            }
        }
    }

    # 使用 httpx 发起异步HTTP请求
    # timeout=60.0：TTS生成可能需要几秒，设置60秒超时
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(api_url, json=request_body)

        # 检查HTTP状态码
        if response.status_code != 200:
            error_detail = response.text[:500]  # 取前500字符避免日志过长
            raise RuntimeError(
                f"Gemini API 返回错误 {response.status_code}: {error_detail}"
            )

        response_data = response.json()

    # 解析API响应，提取音频数据
    try:
        # 响应结构：candidates[0].content.parts[0].inlineData.data
        candidates = response_data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini API 返回了空的candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise RuntimeError("Gemini API 返回了空的parts")

        inline_data = parts[0].get("inlineData", {})
        if not inline_data:
            raise RuntimeError("Gemini API 响应中没有找到音频数据")

        # 音频数据是Base64编码的字符串，解码为二进制
        audio_base64 = inline_data.get("data", "")
        if not audio_base64:
            raise RuntimeError("Gemini API 返回了空的音频数据")

        audio_bytes = base64.b64decode(audio_base64)
        return audio_bytes

    except (KeyError, IndexError) as e:
        raise RuntimeError(f"解析 Gemini API 响应失败: {str(e)}")


def get_language_instruction(language: str) -> str:
    """
    根据语言代码生成语言指令文字
    （有些情况下需要在prompt中指定语言）

    例如：zh-CN -> "请用普通话朗读以下内容"
    """
    language_map = {
        "zh-CN": "请用普通话朗读",
        "zh-TW": "請用繁體中文朗讀",
        "en-US": "Please read in American English",
        "en-GB": "Please read in British English",
        "ja-JP": "日本語で読んでください",
        "ko-KR": "한국어로 읽어주세요",
        "fr-FR": "Veuillez lire en français",
        "de-DE": "Bitte auf Deutsch lesen",
    }
    return language_map.get(language, "")
