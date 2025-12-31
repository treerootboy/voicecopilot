# 声纹识别功能使用示例

## 简介

本文档提供声纹识别功能的实际使用示例。

## 前提条件

1. **网络连接**: 首次使用时需要从 HuggingFace Hub 下载 SpeechBrain 模型（约 80MB）
2. **音频文件**: 准备用于注册的音频文件（WAV 格式，≥3秒）

## 使用示例

### 1. 准备音频样本

创建一个测试音频文件或使用现有的音频文件：

```bash
# 如果有麦克风，可以使用 arecord 录音（Linux）
arecord -f cd -t wav -d 5 user1_sample.wav

# 或使用其他录音工具
```

### 2. 注册用户声纹

```bash
# 注册第一个用户
uv run python src/voiceprint_cli.py register user001 "张三" user1_sample.wav

# 注册第二个用户
uv run python src/voiceprint_cli.py register user002 "李四" user2_sample.wav
```

预期输出：
```
2024-12-31 10:00:00 - voiceprint-cli - INFO - 正在为用户 张三(user001) 注册声纹...
2024-12-31 10:00:05 - voiceprint-manager - INFO - 正在加载 SpeechBrain 声纹识别模型...
2024-12-31 10:00:15 - voiceprint-manager - INFO - 声纹识别模型加载完成
2024-12-31 10:00:16 - voiceprint-manager - INFO - 用户 张三(user001) 声纹注册成功，质量评分: 0.75
2024-12-31 10:00:16 - voiceprint-cli - INFO - ✓ 声纹注册成功
2024-12-31 10:00:16 - voiceprint-cli - INFO -   质量评分: 0.75
```

### 3. 查看已注册的声纹

```bash
uv run python src/voiceprint_cli.py list
```

预期输出：
```
2024-12-31 10:01:00 - voiceprint-cli - INFO - 共有 2 个注册用户:
2024-12-31 10:01:00 - voiceprint-cli - INFO - ------------------------------------------------------------
2024-12-31 10:01:00 - voiceprint-cli - INFO -   用户ID: user001              姓名: 张三              质量: 0.75
2024-12-31 10:01:00 - voiceprint-cli - INFO -   用户ID: user002              姓名: 李四              质量: 0.82
2024-12-31 10:01:00 - voiceprint-cli - INFO - ------------------------------------------------------------
```

### 4. 验证声纹

```bash
# 使用测试音频验证身份
uv run python src/voiceprint_cli.py verify test_audio.wav
```

成功识别时的输出：
```
2024-12-31 10:02:00 - voiceprint-cli - INFO - 正在验证音频文件: test_audio.wav
2024-12-31 10:02:02 - voiceprint-manager - INFO - 识别到用户: 张三 (相似度: 0.1234)
2024-12-31 10:02:02 - voiceprint-cli - INFO - ✓ 识别成功!
2024-12-31 10:02:02 - voiceprint-cli - INFO -   用户ID: user001
2024-12-31 10:02:02 - voiceprint-cli - INFO -   姓名: 张三
2024-12-31 10:02:02 - voiceprint-cli - INFO -   相似度: 0.1234
```

未识别时的输出：
```
2024-12-31 10:03:00 - voiceprint-cli - INFO - 正在验证音频文件: unknown.wav
2024-12-31 10:03:02 - voiceprint-manager - WARNING - 未识别到注册用户 (最佳相似度: 0.5678)
2024-12-31 10:03:02 - voiceprint-cli - WARNING - ✗ 未识别到注册用户
```

### 5. 更新声纹

```bash
# 只更新名称
uv run python src/voiceprint_cli.py update user001 --name "张三丰"

# 只更新声纹
uv run python src/voiceprint_cli.py update user001 --audio-file new_sample.wav

# 同时更新名称和声纹
uv run python src/voiceprint_cli.py update user001 --name "张三丰" --audio-file new_sample.wav
```

### 6. 删除声纹

```bash
uv run python src/voiceprint_cli.py delete user002
```

预期输出：
```
2024-12-31 10:04:00 - voiceprint-cli - INFO - 正在删除用户 user002 的声纹...
2024-12-31 10:04:00 - voiceprint-manager - INFO - 用户 user002 声纹已删除
2024-12-31 10:04:00 - voiceprint-cli - INFO - ✓ 声纹删除成功
```

## 在 Agent 中使用

### 启用声纹验证

在 `.env.local` 中设置：

```bash
# 启用声纹验证
ENABLE_VOICEPRINT_VERIFICATION=true

# 声纹数据目录
VOICEPRINT_DATA_DIR=voiceprints
```

### 运行 Agent

```bash
# 下载所需模型（首次运行）
uv run python src/agent.py download-files

# 在控制台模式下运行
uv run python src/agent.py console

# 或在开发模式下运行
uv run python src/agent.py dev
```

### 工作流程

1. **用户说话**: Agent 接收到音频输入
2. **声纹验证**: 系统提取声纹并与注册用户比对
3. **识别成功**: 
   - 音频被转录为文本
   - LLM 生成回复
   - TTS 合成语音回复
4. **识别失败**:
   - 音频被丢弃
   - 不进行转录和回复
   - 日志记录未识别事件

### 日志输出示例

识别成功：
```
2024-12-31 10:05:00 - voiceprint-manager - INFO - 识别到用户: 张三 (相似度: 0.1234)
2024-12-31 10:05:00 - voiceprint-stt - INFO - 识别到用户: 张三, 开始语音转录
2024-12-31 10:05:01 - zhipu-stt-tts - INFO - STT 识别结果: 你好
```

识别失败：
```
2024-12-31 10:05:00 - voiceprint-manager - WARNING - 未识别到注册用户 (最佳相似度: 0.5678)
2024-12-31 10:05:00 - voiceprint-stt - WARNING - 未识别到注册用户，跳过语音转录
```

## Python API 使用

### 基本用法

```python
from voiceprint_manager import VoiceprintManager

# 创建管理器
manager = VoiceprintManager(
    data_dir="voiceprints",
    similarity_threshold=0.25,  # 相似度阈值
    min_audio_duration=3.0,     # 最小音频时长
    quality_threshold=0.5,       # 质量阈值
)

# 注册声纹
result = manager.register_voiceprint(
    user_id="user001",
    name="张三",
    audio_source="audio.wav"
)

if result["success"]:
    print(f"注册成功，质量: {result['quality_score']}")
else:
    print(f"注册失败: {result['message']}")

# 验证声纹
speaker = manager.verify_speaker("test_audio.wav")

if speaker:
    print(f"识别到: {speaker['name']}")
    print(f"相似度: {speaker['similarity']}")
else:
    print("未识别到注册用户")

# 列出所有声纹
voiceprints = manager.list_voiceprints()
for vp in voiceprints:
    print(f"{vp['user_id']}: {vp['name']} (质量: {vp['quality_score']})")

# 删除声纹
manager.delete_voiceprint("user001")
```

### 与 LiveKit Agents 集成

```python
from voiceprint_manager import VoiceprintManager
from voiceprint_stt import VoiceprintSTT
from livekit.agents import stt

# 初始化管理器
voiceprint_manager = VoiceprintManager()

# 创建带声纹验证的 STT
base_stt = YourSTTImplementation()  # 你的 STT 实现
voiceprint_stt = VoiceprintSTT(
    base_stt=base_stt,
    voiceprint_manager=voiceprint_manager,
    enable_verification=True
)

# 在 AgentSession 中使用
session = AgentSession(
    stt=voiceprint_stt,
    llm=your_llm,
    tts=your_tts,
)
```

## 故障排除

### 问题 1: 模型下载失败

**错误信息:**
```
LocalEntryNotFoundError: An error happened while trying to locate the file on the Hub
```

**解决方案:**
1. 检查网络连接
2. 确保可以访问 huggingface.co
3. 如果在防火墙后，配置代理：
   ```bash
   export HTTP_PROXY=http://your-proxy:port
   export HTTPS_PROXY=http://your-proxy:port
   ```

### 问题 2: 声纹质量不足

**错误信息:**
```
声纹质量不足（0.35 < 0.5），请重新录制更清晰的音频
```

**解决方案:**
1. 在安静环境中录音
2. 使用更好的麦克风
3. 增加录音时长（推荐 ≥ 5 秒）
4. 降低质量阈值（仅用于测试）：
   ```python
   manager = VoiceprintManager(quality_threshold=0.3)
   ```

### 问题 3: 识别率低

**原因:**
- 注册音频和使用音频环境差异大
- 说话方式变化（如感冒、情绪等）
- 音频质量差

**解决方案:**
1. 调整相似度阈值：
   ```python
   manager = VoiceprintManager(similarity_threshold=0.35)  # 放宽要求
   ```
2. 使用多个音频样本注册
3. 定期更新声纹

### 问题 4: 音频时长不足

**错误信息:**
```
音频时长 2.5s 小于最小要求 3.0s
```

**解决方案:**
录制更长的音频（建议 5-10 秒）

## 性能考虑

### 首次加载时间

- **模型下载**: 约 80MB，首次运行时自动下载
- **模型加载**: 约 5-10 秒

### 实时性能

- **声纹提取**: ~0.1-0.5 秒（取决于音频长度）
- **验证比对**: ~0.01 秒每个注册用户
- **内存占用**: 约 500MB（模型加载后）

### 优化建议

1. **预加载模型**: 在 Agent 启动时预加载（已实现）
2. **缓存声纹**: 声纹特征向量已缓存在本地
3. **批量验证**: 一次比对所有注册用户（已实现）

## 安全建议

1. **数据保护**: 
   - 声纹数据存储在本地 `voiceprints/` 目录
   - 设置适当的文件权限：`chmod 700 voiceprints/`

2. **隐私保护**:
   - 不保存原始音频，仅存储特征向量
   - 特征向量无法还原为音频

3. **访问控制**:
   - 限制对声纹数据的访问
   - 定期备份声纹数据

## 高级用法

### 自定义相似度阈值

```python
# 更严格的验证（降低误识别）
manager = VoiceprintManager(similarity_threshold=0.15)

# 更宽松的验证（提高识别率）
manager = VoiceprintManager(similarity_threshold=0.35)
```

### 动态启用/禁用验证

```python
# 在运行时控制验证
voiceprint_stt.enable_voiceprint_verification(False)  # 禁用
voiceprint_stt.enable_voiceprint_verification(True)   # 启用
```

### 获取当前说话人

```python
# 获取最近识别的说话人
speaker = voiceprint_stt.get_current_speaker()
if speaker:
    print(f"当前说话人: {speaker['name']}")
```

## 参考资源

- [SpeechBrain 文档](https://speechbrain.github.io/)
- [ECAPA-TDNN 模型说明](https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb)
- [LiveKit Agents 文档](https://docs.livekit.io/agents/)
