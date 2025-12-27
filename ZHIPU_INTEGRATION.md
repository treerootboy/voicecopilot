# 智谱 AI 集成说明

本项目集成了智谱 AI 的 GLM-ASR-2512 (STT) 和 GLM-TTS (TTS) 服务到 LiveKit Agents。

## 官方文档

- **STT API**: https://docs.bigmodel.cn/api-reference/模型-api/语音转文本
- **TTS API**: https://docs.bigmodel.cn/api-reference/模型-api/文本转语音
- **智谱 AI 平台**: https://open.bigmodel.cn/

## 文件说明

- `src/zhipu_stt_tts.py`: 智谱 AI 的自定义 STT/TTS 实现类
- `src/agent.py`: 主 agent 配置，已集成智谱 GLM-ASR 和 GLM-TTS

## 功能特性

### GLM-ASR-2512 (STT)
- ✅ 语音转文本（支持多语言）
- ✅ 流式实时转录
- ✅ 支持上下文提示（prompt）
- ✅ 热词表支持（最多100个）
- ✅ 文件大小限制：≤ 25 MB
- ✅ 音频时长限制：≤ 30 秒
- ✅ 支持格式：wav, mp3

### GLM-TTS
- ✅ 流式语音合成
- ✅ 7种音色选择（彤彤、锤锤、小陈、jam、kazi、douji、luodo）
- ✅ 可调节语速（0.5-2.0）和音量（0-10）
- ✅ 24kHz 高质量音频输出
- ✅ 可选水印功能
- ✅ 文本长度限制：1024 字符

## 环境配置

在 `.env.local` 中配置：

```bash
# LiveKit 配置
LIVEKIT_URL=ws://192.168.100.18:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret

# 智谱 AI API 配置
OPENAI_API_KEY=your_zhipu_api_key
OPENAI_BASE_URL=https://open.bigmodel.cn/api/paas/v4/

# 可选：单独配置 STT 服务（如果使用本地 Whisper）
OPENAI_STT_BASE_URL=http://localhost:8000/v1
```

## 使用方法

### 1. 完整使用智谱服务

```python
from zhipu_stt_tts import ZhipuSTT, ZhipuTTS

# 使用智谱 STT 和 TTS
session = AgentSession(
    stt=ZhipuSTT(
        model="glm-asr-2512",
        hotwords=["LiveKit", "智谱AI"],  # 可选：热词表
    ),
    llm=openai.LLM(model="glm-4-flash"),
    tts=ZhipuTTS(
        voice="tongtong",  # 彤彤音色
    ),
)
```

### 2. 自定义配置

```python
from zhipu_stt_tts import ZhipuSTT, ZhipuTTS

# 自定义智谱 STT 配置
stt = ZhipuSTT(
    api_key="your_api_key",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    model="glm-asr-2512",
    prompt="这是一段关于语音助手的对话",  # 上下文提示
    hotwords=["LiveKit", "智谱AI", "语音识别"],  # 热词表
)

# 自定义智谱 TTS 配置
tts = ZhipuTTS(
    api_key="your_api_key",
    base_url="https://open.bigmodel.cn/api/paas/v4/",
    voice="chuichui",     # 锤锤音色
    speed=1.2,            # 语速 (0.5 - 2.0)
    volume=1.5,           # 音量 (0 - 10)
    watermark_enabled=False,  # 关闭水印（需要权限）
)
```

### 3. 使用备用 STT

```python
# 如果智谱 STT 遇到问题，可以使用 OpenAI Whisper
session = AgentSession(
    stt=openai.STT(
        model="whisper-1",
        language="zh",
    ),
    llm=openai.LLM(model="glm-4-flash"),
    tts=ZhipuTTS(),
)
```

## API 文档参考

- **GLM-ASR-2512 (STT)**: https://docs.bigmodel.cn/api-reference/模型-api/语音转文本
- **GLM-TTS**: https://docs.bigmodel.cn/api-reference/模型-api/文本转语音
- **智谱 AI 开放平台**: https://open.bigmodel.cn/
- **LiveKit 集成参考**: https://github.com/livekit/livekit/issues/3176

## 可用音色

| 音色名称 | ID | 描述 |
|---------|-----|------|
| 彤彤（默认） | `tongtong` | 默认音色 |
| 锤锤 | `chuichui` | 动感音色 |
| 小陈 | `xiaochen` | 温和音色 |
| jam | `jam` | 动动动物圈 jam 音色 |
| kazi | `kazi` | 动动动物圈 kazi 音色 |
| douji | `douji` | 动动动物圈 douji 音色 |
| luodo | `luodo` | 动动动物圈 luodo 音色 |

## 运行测试

```bash
# 下载模型文件
uv run python src/agent.py download-files

# 运行控制台模式测试
uv run python src/agent.py console

# 运行开发模式（连接 LiveKit）
uv run python src/agent.py dev
```

## 注意事项

1. **STT 限制**: 
   - 文件大小 ≤ 25 MB
   - 音频时长 ≤ 30 秒
   - 支持格式：wav, mp3
   
2. **TTS 限制**:
   - 输入文本最大长度：1024 字符
   - 流式模式仅支持 PCM 格式
   - 建议采样率：24000 Hz

3. **热词表**: 最多支持 100 个热词，用于提升特定领域词汇识别率

4. **水印功能**: 需要在智谱平台开通去水印权限才能关闭水印

5. **流式输出**: 
   - STT 和 TTS 都支持流式处理
   - 实现了低延迟的实时语音交互

6. **错误处理**: 已添加完善的错误日志和异常处理

## 故障排查

### STT 识别失败
- 确认音频文件格式为 wav 或 mp3
- 检查音频文件大小 ≤ 25 MB
- 确认音频时长 ≤ 30 秒
- 查看日志中的具体错误信息

### TTS 无声音输出
- 检查 API key 是否正确
- 确认输入文本长度 ≤ 1024 字符
- 查看日志中的错误信息
- 确认智谱 API 配额未超限

### API 连接错误
- 确认网络连接正常
- 检查 `OPENAI_BASE_URL` 配置：`https://open.bigmodel.cn/api/paas/v4/`
- 验证 API key 是否有效
- 查看智谱平台是否有服务公告
