# 声纹识别功能文档

## 概述

本项目集成了声纹识别功能，支持：
1. 声纹注册（通过音频文件或麦克风）
2. 实时声纹验证（只有注册用户的语音才会被处理）
3. 声纹管理（增删改查）
4. 声纹质量评估

## 技术栈

- **SpeechBrain**: 最先进的说话人识别模型（ECAPA-TDNN）
- **PyTorch**: 深度学习框架
- **TorchAudio**: 音频处理

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

在 `.env.local` 文件中添加：

```bash
# 启用声纹验证（默认: true）
ENABLE_VOICEPRINT_VERIFICATION=true

# 声纹数据存储目录（默认: voiceprints）
VOICEPRINT_DATA_DIR=voiceprints
```

### 3. 声纹管理

#### 注册声纹

```bash
# 通过音频文件注册
uv run python src/voiceprint_cli.py register <user_id> <name> <audio_file.wav>

# 示例
uv run python src/voiceprint_cli.py register user001 "张三" voice_samples/zhangsan.wav
```

**要求：**
- 音频时长 ≥ 3 秒
- 音频格式：WAV, MP3 等常见格式
- 声纹质量评分 ≥ 0.5（自动评估）

#### 列出所有声纹

```bash
uv run python src/voiceprint_cli.py list
```

#### 验证声纹

```bash
# 测试音频文件是否匹配注册的声纹
uv run python src/voiceprint_cli.py verify <audio_file.wav>

# 示例
uv run python src/voiceprint_cli.py verify test_audio.wav
```

#### 更新声纹

```bash
# 更新用户名称
uv run python src/voiceprint_cli.py update <user_id> --name "新名称"

# 更新声纹音频
uv run python src/voiceprint_cli.py update <user_id> --audio-file new_voice.wav

# 同时更新名称和声纹
uv run python src/voiceprint_cli.py update <user_id> --name "新名称" --audio-file new_voice.wav
```

#### 删除声纹

```bash
uv run python src/voiceprint_cli.py delete <user_id>

# 示例
uv run python src/voiceprint_cli.py delete user001
```

## 工作原理

### 1. 声纹提取

使用 SpeechBrain 的 ECAPA-TDNN 模型提取声纹特征向量（embeddings）：

```python
from voiceprint_manager import VoiceprintManager

manager = VoiceprintManager()
embedding = manager.extract_embedding(audio_source)
```

### 2. 声纹注册

```python
result = manager.register_voiceprint(
    user_id="user001",
    name="张三",
    audio_source="voice.wav"
)

if result["success"]:
    print(f"注册成功，质量评分: {result['quality_score']}")
```

### 3. 声纹验证

在实时语音处理中，系统会自动验证说话人：

```python
speaker = manager.verify_speaker(audio_buffer)

if speaker:
    print(f"识别到用户: {speaker['name']}")
    print(f"相似度: {speaker['similarity']}")
else:
    print("未识别到注册用户")
```

### 4. 质量评估

系统自动评估声纹质量，确保注册的声纹可靠：

```python
quality_score = manager.evaluate_quality(embedding)
# quality_score: 0-1，越高越好
# 默认阈值: 0.5
```

## 集成到 Agent

声纹验证已集成到 LiveKit Agent 的 STT 流程中：

```python
# 在 agent.py 中
from voiceprint_manager import VoiceprintManager
from voiceprint_stt import VoiceprintSTT

# 初始化声纹管理器
voiceprint_manager = VoiceprintManager()

# 包装 STT
voiceprint_stt = VoiceprintSTT(
    base_stt=zhipu_stt,
    voiceprint_manager=voiceprint_manager,
    enable_verification=True
)

# 在 AgentSession 中使用
session = AgentSession(
    stt=voiceprint_stt,
    # ... 其他配置
)
```

**工作流程：**
1. 用户说话
2. VAD 检测到语音结束
3. 声纹验证模块提取声纹并与注册用户比对
4. 如果识别成功，音频被发送到 STT 进行转录
5. 如果识别失败，音频被丢弃，不进行转录

## 性能优化

### 1. 模型预加载

SpeechBrain 模型在首次使用时会自动下载并缓存：

```
pretrained_models/spkrec-ecapa-voxceleb/
```

### 2. 相似度阈值调整

可以根据实际需求调整相似度阈值：

```python
manager = VoiceprintManager(
    similarity_threshold=0.25,  # 默认值，越小要求越严格
)
```

### 3. 音频质量要求

```python
manager = VoiceprintManager(
    min_audio_duration=3.0,    # 最小音频时长（秒）
    quality_threshold=0.5,      # 质量评分阈值
)
```

## 多说话人场景

对于包含多个说话人的音频：

```python
# 检测音频中的多个说话人
speakers = manager.detect_speakers("multi_speaker.wav")

# 分别提取和注册每个说话人的声纹
for i, segment in enumerate(speakers):
    # 提取该片段的声纹
    # 让用户选择要注册哪个
    pass
```

**注意：** 多说话人检测和分离功能需要进一步开发。

## 故障排除

### 1. 声纹质量不足

**问题：** 注册时提示"声纹质量不足"

**解决方案：**
- 确保录音环境安静，减少背景噪音
- 使用更清晰的麦克风
- 录制时长 ≥ 5 秒
- 多录几次，选择质量最好的

### 2. 验证失败率高

**问题：** 经常无法识别注册用户

**解决方案：**
- 调高相似度阈值（降低要求）
- 使用更长的音频进行注册（≥ 10 秒）
- 确保注册和使用时的音频条件相似

### 3. 模型下载失败

**问题：** 首次运行时模型下载失败

**解决方案：**
- 检查网络连接
- 使用代理（如需要）
- 手动下载模型并放置在 `pretrained_models/spkrec-ecapa-voxceleb/` 目录

## 安全考虑

1. **声纹数据存储：** 声纹特征向量存储在本地文件系统，不包含原始音频
2. **隐私保护：** 不上传音频到外部服务
3. **访问控制：** 建议对 `voiceprints/` 目录设置适当的权限

## API 参考

### VoiceprintManager

```python
class VoiceprintManager:
    def __init__(
        self,
        data_dir: str = "voiceprints",
        similarity_threshold: float = 0.25,
        min_audio_duration: float = 3.0,
        quality_threshold: float = 0.5,
    )

    def register_voiceprint(
        self,
        user_id: str,
        name: str,
        audio_source,
        max_retries: int = 3
    ) -> dict

    def verify_speaker(self, audio_source) -> Optional[dict]

    def delete_voiceprint(self, user_id: str) -> bool

    def update_voiceprint(
        self,
        user_id: str,
        name: str = None,
        audio_source = None
    ) -> bool

    def list_voiceprints(self) -> list

    def extract_embedding(
        self,
        audio_source,
        sample_rate: int = 16000
    ) -> Optional[np.ndarray]

    def evaluate_quality(self, embedding: np.ndarray) -> float
```

### VoiceprintSTT

```python
class VoiceprintSTT(stt.STT):
    def __init__(
        self,
        base_stt: stt.STT,
        voiceprint_manager: VoiceprintManager,
        enable_verification: bool = True,
    )

    def get_current_speaker(self) -> Optional[dict]

    def enable_voiceprint_verification(self, enable: bool = True)
```

## 测试

运行测试：

```bash
uv run pytest tests/test_voiceprint.py -v
```

## 未来改进

1. **多说话人分离：** 实现更完善的多说话人检测和分离
2. **实时注册：** 支持通过麦克风实时录音注册
3. **增量学习：** 随着使用自动改进声纹模型
4. **GUI 工具：** 提供图形界面管理声纹
5. **云端同步：** 支持声纹数据的云端备份和同步

## 参考资源

- [SpeechBrain 官方文档](https://speechbrain.github.io/)
- [ECAPA-TDNN 论文](https://arxiv.org/abs/2005.07143)
- [VoxCeleb 数据集](https://www.robots.ox.ac.uk/~vgg/data/voxceleb/)
