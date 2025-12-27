"""
智谱 AI 的自定义 STT 和 TTS 实现
基于官方 API 文档实现

STT API: https://docs.bigmodel.cn/api-reference/模型-api/语音转文本
TTS API: https://docs.bigmodel.cn/api-reference/模型-api/文本转语音

参考: https://github.com/livekit/livekit/issues/3176
"""

import io
import logging
import os
import wave
import base64
import json
from typing import Optional
import aiohttp

from livekit.agents import (
    stt,
    tts,
    utils,
    APIConnectOptions,
)
from livekit.agents.utils import AudioBuffer

logger = logging.getLogger("zhipu-stt-tts")


class ZhipuSTT(stt.STT):
    """
    智谱 AI 语音识别 STT 实现 (GLM-ASR-2512)
    文档: https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E8%AF%AD%E9%9F%B3%E8%BD%AC%E6%96%87%E6%9C%AC
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        model: str = "glm-asr-2512",  # 智谱 ASR 模型
        prompt: Optional[str] = None,  # 上下文提示，长文本场景下建议小于8000字
        hotwords: Optional[list[str]] = None,  # 热词表，最多100个
    ):
        super().__init__(
            capabilities=stt.STTCapabilities(
                streaming=False,  # 使用非流式模式，配合 StreamAdapter 使用
                interim_results=False
            )
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self._model_name = model  # 使用 _model_name 避免与父类 model 属性冲突
        self.prompt = prompt
        self.hotwords = hotwords or []

    async def _recognize_impl(
        self, 
        buffer: AudioBuffer, 
        *, 
        language: str | None = None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """
        将音频缓冲区转换为文本
        支持格式: wav, mp3
        限制: 文件大小 ≤ 25 MB，音频时长 ≤ 30 秒
        """
        # 合并音频帧
        buffer = utils.merge_frames(buffer)
        io_buffer = io.BytesIO()

        # 转换为 WAV 格式
        with wave.open(io_buffer, "wb") as wav:
            wav.setnchannels(buffer.num_channels)
            wav.setsampwidth(2)  # 16-bit
            wav.setframerate(buffer.sample_rate)
            wav.writeframes(buffer.data)

        io_buffer.seek(0)

        try:
            # 调用智谱 ASR API
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                }
                
                # 智谱 API 端点
                url = f"{self.base_url}/audio/transcriptions"
                
                data = aiohttp.FormData()
                data.add_field(
                    "file",
                    io_buffer.getvalue(),
                    filename="audio.wav",
                    content_type="audio/wav"
                )
                data.add_field("model", self._model_name)
                data.add_field("stream", "false")  # 非流式
                
                # 添加可选参数
                if self.prompt:
                    data.add_field("prompt", self.prompt)
                if self.hotwords:
                    data.add_field("hotwords", json.dumps(self.hotwords))

                async with session.post(url, headers=headers, data=data) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"智谱 STT API 错误: {response.status} - {error_text}")
                        result_text = ""
                    else:
                        result = await response.json()
                        result_text = result.get("text", "")
                        logger.info(f"STT 识别结果: {result_text}")

        except Exception as e:
            logger.error(f"STT 识别错误: {e}")
            result_text = ""

        return stt.SpeechEvent(
            type=stt.SpeechEventType.FINAL_TRANSCRIPT,
            alternatives=[
                stt.SpeechData(
                    text=result_text,
                    language=language or "zh"
                )
            ],
        )


class ZhipuTTS(tts.TTS):
    """
    智谱 AI GLM-TTS 实现
    文档: https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E6%96%87%E6%9C%AC%E8%BD%AC%E8%AF%AD%E9%9F%B3
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://open.bigmodel.cn/api/paas/v4",
        model: str = "glm-tts",
        voice: str = "tongtong",  # tongtong(彤彤), chuichui(锤锤), xiaochen(小陈), jam, kazi, douji, luodo
        speed: float = 1.0,  # 语速,范围 [0.5, 2]
        volume: float = 1.0,  # 音量,范围 (0, 10]
        watermark_enabled: bool = True,  # 是否添加水印
        sample_rate: int = 24000,  # 智谱返回 24000Hz
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(
                streaming=True,  # 智谱支持流式
            ),
            sample_rate=sample_rate,
            num_channels=1,
        )
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url.rstrip("/")
        self._model_name = model  # 使用 _model_name 避免与父类 model 属性冲突
        self.voice = voice
        self.speed = speed
        self.volume = volume
        self.watermark_enabled = watermark_enabled
        self._sample_rate = sample_rate
        self._session = None

    def _ensure_session(self):
        """确保 HTTP session 存在"""
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session

    def synthesize(self, text: str, *, conn_options: APIConnectOptions = None) -> tts.ChunkedStream:
        """
        合成语音（非流式模式,不推荐使用）
        注意: 智谱 TTS 主要支持流式模式,这里为了兼容性提供此方法
        """
        raise NotImplementedError(
            "ChunkedStream is not implemented for Zhipu TTS, please use stream() instead"
        )

    def stream(self, *, conn_options: APIConnectOptions = None) -> "ZhipuTTSStream":
        """
        创建流式 TTS 会话
        """
        return ZhipuTTSStream(tts=self, conn_options=conn_options)

    async def aclose(self):
        """关闭 HTTP session"""
        if self._session:
            await self._session.close()
            self._session = None


class ZhipuTTSStream(tts.SynthesizeStream):
    """处理智谱 TTS 流式响应"""

    def __init__(
        self,
        tts: ZhipuTTS,
        conn_options: APIConnectOptions = None,
    ):
        super().__init__(tts=tts, conn_options=conn_options or APIConnectOptions())
        self._tts = tts

    async def _run(self, output_emitter: tts.AudioEmitter):
        """运行流式 TTS"""
        # 初始化输出
        request_id = utils.shortuuid()
        output_emitter.initialize(
            request_id=request_id,
            sample_rate=self._tts._sample_rate,
            num_channels=1,
            stream=True,
            mime_type="audio/pcm",
        )
        
        # 开始segment
        output_emitter.start_segment(segment_id=request_id)
        
        # 收集输入文本
        input_text = ""
        async for data in self._input_ch:
            if isinstance(data, self._FlushSentinel):
                continue
            if isinstance(data, str):
                input_text += data
        
        if not input_text:
            output_emitter.end_segment()
            return
        
        # 限制文本长度
        input_text = input_text[:1024]
        
        session = self._tts._ensure_session()
        
        headers = {
            "Authorization": f"Bearer {self._tts.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._tts._model_name,
            "input": input_text,
            "voice": self._tts.voice,
            "speed": self._tts.speed,
            "volume": self._tts.volume,
            "watermark_enabled": self._tts.watermark_enabled,
            "response_format": "pcm",
            "encode_format": "base64",
            "stream": True,
        }

        url = f"{self._tts.base_url}/audio/speech"
        
        try:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"智谱 TTS API 错误: {response.status} - {error_text}")
                    output_emitter.end_segment()
                    return

                # 处理流式响应 - 逐字节读取并查找换行符
                buffer = b""
                async for chunk in response.content.iter_any():
                    buffer += chunk
                    
                    # 按行分割
                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        line_text = line.decode("utf-8").strip()
                        
                        if not line_text or not line_text.startswith("data:"):
                            continue

                        # 移除 "data: " 前缀
                        json_str = line_text[5:].strip()
                        
                        if not json_str or json_str == "[DONE]":
                            continue

                        try:
                            data = json.loads(json_str)
                            
                            # 检查是否结束
                            if "choices" in data and data["choices"]:
                                choice = data["choices"][0]
                                if choice.get("finish_reason") == "stop":
                                    break
                                
                                # 提取音频数据
                                if "delta" in choice and "content" in choice["delta"]:
                                    audio_base64 = choice["delta"]["content"]
                                    
                                    if audio_base64:
                                        # 解码 base64
                                        audio_data = base64.b64decode(audio_base64)
                                        
                                        # 推送音频数据
                                        output_emitter.push(audio_data)
                                        self._mark_started()

                        except json.JSONDecodeError as e:
                            logger.error(f"JSON 解析错误: {e}, data: {json_str[:100]}")
                            continue

        except Exception as e:
            logger.error(f"TTS 流式处理错误: {e}")
        finally:
            output_emitter.end_segment()
