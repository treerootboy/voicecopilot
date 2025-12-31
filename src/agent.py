import logging
import os

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    room_io,
    stt,
)
from livekit.plugins import noise_cancellation, openai, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# 导入声纹管理模块
from voiceprint_manager import VoiceprintManager
from voiceprint_stt import VoiceprintSTT

# 导入智谱 AI 自定义 STT/TTS
from zhipu_stt_tts import ZhipuSTT, ZhipuTTS

logger = logging.getLogger("agent")

load_dotenv(".env.local")


class Assistant(Agent):
    def __init__(self) -> None:
        # 从环境变量读取 system prompt，如果没有设置则使用默认值
        system_prompt = os.getenv(
            "AGENT_INSTRUCTIONS",
            """你是一个有帮助的中文语音 AI 助手。用户通过语音与你交互。
            你会热心地回答用户的问题,提供准确的信息。
            你的回答简洁明了,不使用复杂的格式或标点符号,包括表情符号、星号或其他特殊符号。
            你好奇、友好,并且富有幽默感。""",
        )
        super().__init__(instructions=system_prompt)

    # To add tools, use the @function_tool decorator.
    # Here's an example that adds a simple weather tool.
    # You also have to add `from livekit.agents import function_tool, RunContext` to the top of this file
    # @function_tool
    # async def lookup_weather(self, context: RunContext, location: str):
    #     """Use this tool to look up current weather information in the given location.
    #
    #     If the location is not supported by the weather service, the tool will indicate this. You must tell the user the location's weather is unavailable.
    #
    #     Args:
    #         location: The location to look up weather information for (e.g. city name)
    #     """
    #
    #     logger.info(f"Looking up weather for {location}")
    #
    #     return "sunny with a temperature of 70 degrees."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    # 初始化声纹管理器
    proc.userdata["voiceprint_manager"] = VoiceprintManager(
        data_dir=os.getenv("VOICEPRINT_DATA_DIR", "voiceprints")
    )


server.setup_fnc = prewarm


@server.rtc_session()
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # 创建智谱 STT 实例
    zhipu_stt = ZhipuSTT(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL"),
        model="glm-asr-2512",
    )

    # 使用 StreamAdapter 包装 STT，配合 VAD 使用
    # StreamAdapter 会缓冲音频直到 VAD 检测到说话结束
    adapted_stt = stt.StreamAdapter(stt=zhipu_stt, vad=ctx.proc.userdata["vad"])

    # 是否启用声纹验证（从环境变量读取，默认启用）
    enable_voiceprint = (
        os.getenv("ENABLE_VOICEPRINT_VERIFICATION", "true").lower() == "true"
    )

    # 如果启用声纹验证，使用 VoiceprintSTT 包装
    if enable_voiceprint:
        voiceprint_manager = ctx.proc.userdata["voiceprint_manager"]
        final_stt = VoiceprintSTT(
            base_stt=adapted_stt,
            voiceprint_manager=voiceprint_manager,
            enable_verification=True,
        )
        logger.info("声纹验证已启用")
    else:
        final_stt = adapted_stt
        logger.info("声纹验证未启用")

    # Set up a voice AI pipeline using 智谱 AI (GLM)
    session = AgentSession(
        # Speech-to-text (STT) - 使用智谱 GLM-ASR-2512 with StreamAdapter and optional voiceprint verification
        stt=final_stt,
        # 如果智谱 STT 不可用，可以使用 OpenAI Whisper 作为替代
        # stt=openai.STT(
        #     model="whisper-1",
        #     base_url=os.getenv("OPENAI_STT_BASE_URL"),
        #     api_key=os.getenv("OPENAI_API_KEY"),
        #     language="zh",
        # ),
        # A Large Language Model (LLM) - 使用智谱 GLM-4
        llm=openai.LLM(
            model="glm-4.5-air",
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY"),
        ),
        # Text-to-speech (TTS) - 使用智谱 GLM-TTS
        tts=ZhipuTTS(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL"),
            voice="tongtong",  # 可选: tongtong(彤彤), chuichui(锤锤), xiaochen(小陈), jam, kazi, douji, luodo
            speed=1.0,
            volume=1.0,
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: noise_cancellation.BVCTelephony()
                if params.participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                else noise_cancellation.BVC(),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()


if __name__ == "__main__":
    cli.run_app(server)
