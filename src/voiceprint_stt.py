"""
声纹验证 STT 适配器
在 STT 处理之前进行声纹验证，只处理认证用户的音频
"""

import logging
from typing import Optional

from livekit.agents import APIConnectOptions, stt
from livekit.agents.utils import AudioBuffer

from voiceprint_manager import VoiceprintManager

logger = logging.getLogger("voiceprint-stt")


class VoiceprintSTT(stt.STT):
    """
    带声纹验证的 STT 包装器
    只有通过声纹验证的音频才会被转录
    """

    def __init__(
        self,
        base_stt: stt.STT,
        voiceprint_manager: VoiceprintManager,
        enable_verification: bool = True,
    ):
        """
        初始化声纹验证 STT

        Args:
            base_stt: 基础 STT 实例
            voiceprint_manager: 声纹管理器
            enable_verification: 是否启用声纹验证
        """
        super().__init__(capabilities=base_stt.capabilities)
        self.base_stt = base_stt
        self.voiceprint_manager = voiceprint_manager
        self.enable_verification = enable_verification
        self._current_speaker: Optional[dict] = None

    async def _recognize_impl(
        self,
        buffer: AudioBuffer,
        *,
        language: str | None = None,
        conn_options: APIConnectOptions,
    ) -> stt.SpeechEvent:
        """
        识别音频，带声纹验证

        Args:
            buffer: 音频缓冲区
            language: 语言
            conn_options: 连接选项

        Returns:
            语音事件
        """
        # 如果禁用验证，直接调用基础 STT
        if not self.enable_verification:
            return await self.base_stt._recognize_impl(
                buffer, language=language, conn_options=conn_options
            )

        # 进行声纹验证
        speaker = self.voiceprint_manager.verify_speaker(buffer)

        if speaker is None:
            # 未识别到注册用户，返回空结果
            logger.warning("未识别到注册用户，跳过语音转录")
            self._current_speaker = None
            return stt.SpeechEvent(
                type=stt.SpeechEventType.FINAL_TRANSCRIPT,
                alternatives=[
                    stt.SpeechData(
                        text="",  # 返回空文本
                        language=language or "zh",
                    )
                ],
            )

        # 识别到注册用户，进行 STT 转录
        self._current_speaker = speaker
        logger.info(f"识别到用户: {speaker['name']}, 开始语音转录")

        return await self.base_stt._recognize_impl(
            buffer, language=language, conn_options=conn_options
        )

    def get_current_speaker(self) -> Optional[dict]:
        """
        获取当前识别的说话人

        Returns:
            说话人信息字典，如果未识别返回 None
        """
        return self._current_speaker

    def enable_voiceprint_verification(self, enable: bool = True):
        """
        启用或禁用声纹验证

        Args:
            enable: 是否启用
        """
        self.enable_verification = enable
        logger.info(f"声纹验证已{'启用' if enable else '禁用'}")
