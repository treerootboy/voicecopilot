"""
声纹管理模块
提供声纹注册、识别、管理等功能
使用 SpeechBrain 进行声纹提取和比对
"""

import json
import logging
from pathlib import Path
from typing import Optional

import numpy as np
import torch
import torchaudio
from livekit.agents.utils import AudioBuffer
from speechbrain.inference.speaker import SpeakerRecognition

logger = logging.getLogger("voiceprint-manager")


class VoiceprintManager:
    """声纹管理器"""

    def __init__(
        self,
        data_dir: str = "voiceprints",
        similarity_threshold: float = 0.25,  # 余弦相似度阈值
        min_audio_duration: float = 3.0,  # 最小音频时长（秒）
        quality_threshold: float = 0.5,  # 声纹质量评分阈值
    ):
        """
        初始化声纹管理器

        Args:
            data_dir: 声纹数据存储目录
            similarity_threshold: 声纹匹配阈段（越小越相似）
            min_audio_duration: 最小音频时长要求
            quality_threshold: 声纹质量阈值
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.similarity_threshold = similarity_threshold
        self.min_audio_duration = min_audio_duration
        self.quality_threshold = quality_threshold

        # 声纹数据文件
        self.voiceprints_file = self.data_dir / "voiceprints.json"
        self.voiceprints = self._load_voiceprints()

        # 初始化 SpeechBrain 声纹识别模型
        # 使用预训练的 ECAPA-TDNN 模型
        logger.info("正在加载 SpeechBrain 声纹识别模型...")
        self.model = SpeakerRecognition.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="pretrained_models/spkrec-ecapa-voxceleb",
        )
        logger.info("声纹识别模型加载完成")

    def _load_voiceprints(self) -> dict:
        """加载已注册的声纹数据"""
        if self.voiceprints_file.exists():
            with open(self.voiceprints_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_voiceprints(self):
        """保存声纹数据到文件"""
        with open(self.voiceprints_file, "w", encoding="utf-8") as f:
            json.dump(self.voiceprints, f, ensure_ascii=False, indent=2)

    def _audio_buffer_to_tensor(self, buffer: AudioBuffer) -> torch.Tensor:
        """
        将 AudioBuffer 转换为 PyTorch tensor

        Args:
            buffer: 音频缓冲区

        Returns:
            torch.Tensor: 音频张量 (channels, samples)
        """
        # 将字节转换为 int16 数组
        audio_data = np.frombuffer(buffer.data, dtype=np.int16)

        # 转换为 float32 并归一化到 [-1, 1]
        audio_data = audio_data.astype(np.float32) / 32768.0

        # 如果是多声道，重塑数据
        if buffer.num_channels > 1:
            audio_data = audio_data.reshape(-1, buffer.num_channels).T
        else:
            audio_data = audio_data.reshape(1, -1)

        # 转换为 tensor
        audio_tensor = torch.from_numpy(audio_data)

        return audio_tensor

    def _file_to_tensor(self, file_path: str) -> tuple[torch.Tensor, int]:
        """
        从文件加载音频并转换为 tensor

        Args:
            file_path: 音频文件路径

        Returns:
            tuple: (音频张量, 采样率)
        """
        audio_tensor, sample_rate = torchaudio.load(file_path)
        return audio_tensor, sample_rate

    def extract_embedding(
        self, audio_source, sample_rate: int = 16000
    ) -> Optional[np.ndarray]:
        """
        提取声纹特征向量

        Args:
            audio_source: 音频数据源（AudioBuffer 或文件路径）
            sample_rate: 采样率

        Returns:
            声纹特征向量，如果提取失败返回 None
        """
        try:
            if isinstance(audio_source, AudioBuffer):
                # 从 AudioBuffer 提取
                audio_tensor = self._audio_buffer_to_tensor(audio_source)
                sr = audio_source.sample_rate
            elif isinstance(audio_source, (str, Path)):
                # 从文件提取
                audio_tensor, sr = self._file_to_tensor(str(audio_source))
            else:
                logger.error(f"不支持的音频源类型: {type(audio_source)}")
                return None

            # 检查音频时长
            duration = audio_tensor.shape[-1] / sr
            if duration < self.min_audio_duration:
                logger.warning(
                    f"音频时长 {duration:.2f}s 小于最小要求 {self.min_audio_duration}s"
                )
                return None

            # 重采样到 16kHz（SpeechBrain 模型要求）
            if sr != 16000:
                resampler = torchaudio.transforms.Resample(sr, 16000)
                audio_tensor = resampler(audio_tensor)

            # 提取声纹特征
            with torch.no_grad():
                embeddings = self.model.encode_batch(audio_tensor)
                embedding = embeddings.squeeze().cpu().numpy()

            return embedding

        except Exception as e:
            logger.error(f"提取声纹特征失败: {e}")
            return None

    def evaluate_quality(self, embedding: np.ndarray) -> float:
        """
        评估声纹质量

        Args:
            embedding: 声纹特征向量

        Returns:
            质量评分 (0-1)，越高越好
        """
        # 使用特征向量的范数和方差作为质量指标
        norm = np.linalg.norm(embedding)
        variance = np.var(embedding)

        # 归一化评分
        quality_score = min(1.0, (norm * variance) / 10.0)

        return quality_score

    def register_voiceprint(
        self, user_id: str, name: str, audio_source, max_retries: int = 3
    ) -> dict:
        """
        注册声纹

        Args:
            user_id: 用户ID
            name: 用户名称
            audio_source: 音频数据源
            max_retries: 最大重试次数

        Returns:
            注册结果字典
        """
        result = {"success": False, "message": "", "quality_score": 0.0}

        # 提取声纹
        embedding = self.extract_embedding(audio_source)
        if embedding is None:
            result["message"] = "提取声纹失败，请确保音频质量良好且时长足够"
            return result

        # 评估质量
        quality_score = self.evaluate_quality(embedding)
        result["quality_score"] = quality_score

        if quality_score < self.quality_threshold:
            result["message"] = (
                f"声纹质量不足（{quality_score:.2f} < {self.quality_threshold}），"
                f"请重新录制更清晰的音频"
            )
            return result

        # 保存声纹
        embedding_file = self.data_dir / f"{user_id}.npy"
        np.save(embedding_file, embedding)

        # 更新声纹数据库
        self.voiceprints[user_id] = {
            "name": name,
            "embedding_file": str(embedding_file),
            "quality_score": quality_score,
        }
        self._save_voiceprints()

        result["success"] = True
        result["message"] = "声纹注册成功"
        logger.info(
            f"用户 {name}({user_id}) 声纹注册成功，质量评分: {quality_score:.2f}"
        )

        return result

    def verify_speaker(self, audio_source) -> Optional[dict]:
        """
        验证说话人身份

        Args:
            audio_source: 音频数据源

        Returns:
            识别结果字典，包含 user_id, name, similarity
            如果未识别到注册用户，返回 None
        """
        if not self.voiceprints:
            logger.warning("没有注册的声纹数据")
            return None

        # 提取当前音频的声纹
        test_embedding = self.extract_embedding(audio_source)
        if test_embedding is None:
            return None

        # 与所有注册的声纹进行比对
        best_match = None
        best_similarity = float("inf")

        for user_id, data in self.voiceprints.items():
            # 加载注册的声纹
            registered_embedding = np.load(data["embedding_file"])

            # 计算余弦距离（越小越相似）
            similarity = self._compute_similarity(test_embedding, registered_embedding)

            if similarity < best_similarity:
                best_similarity = similarity
                best_match = {
                    "user_id": user_id,
                    "name": data["name"],
                    "similarity": similarity,
                }

        # 判断是否超过阈值
        if best_match and best_similarity < self.similarity_threshold:
            logger.info(
                f"识别到用户: {best_match['name']} (相似度: {best_similarity:.4f})"
            )
            return best_match
        else:
            logger.warning(f"未识别到注册用户 (最佳相似度: {best_similarity:.4f})")
            return None

    def _compute_similarity(
        self, embedding1: np.ndarray, embedding2: np.ndarray
    ) -> float:
        """
        计算两个声纹的相似度（余弦距离）

        Args:
            embedding1: 声纹1
            embedding2: 声纹2

        Returns:
            相似度（0-2，越小越相似）
        """
        # 归一化
        embedding1 = embedding1 / np.linalg.norm(embedding1)
        embedding2 = embedding2 / np.linalg.norm(embedding2)

        # 计算余弦相似度
        cosine_similarity = np.dot(embedding1, embedding2)

        # 转换为余弦距离
        cosine_distance = 1 - cosine_similarity

        return cosine_distance

    def delete_voiceprint(self, user_id: str) -> bool:
        """
        删除声纹

        Args:
            user_id: 用户ID

        Returns:
            是否删除成功
        """
        if user_id not in self.voiceprints:
            logger.warning(f"用户 {user_id} 不存在")
            return False

        # 删除声纹文件
        embedding_file = Path(self.voiceprints[user_id]["embedding_file"])
        if embedding_file.exists():
            embedding_file.unlink()

        # 从数据库中删除
        del self.voiceprints[user_id]
        self._save_voiceprints()

        logger.info(f"用户 {user_id} 声纹已删除")
        return True

    def update_voiceprint(
        self, user_id: str, name: Optional[str] = None, audio_source=None
    ) -> bool:
        """
        更新声纹

        Args:
            user_id: 用户ID
            name: 新名称（可选）
            audio_source: 新音频源（可选）

        Returns:
            是否更新成功
        """
        if user_id not in self.voiceprints:
            logger.warning(f"用户 {user_id} 不存在")
            return False

        # 更新名称
        if name:
            self.voiceprints[user_id]["name"] = name

        # 更新声纹
        if audio_source:
            embedding = self.extract_embedding(audio_source)
            if embedding is None:
                logger.error("提取新声纹失败")
                return False

            quality_score = self.evaluate_quality(embedding)
            if quality_score < self.quality_threshold:
                logger.error(f"新声纹质量不足: {quality_score:.2f}")
                return False

            # 保存新声纹
            embedding_file = Path(self.voiceprints[user_id]["embedding_file"])
            np.save(embedding_file, embedding)
            self.voiceprints[user_id]["quality_score"] = quality_score

        self._save_voiceprints()
        logger.info(f"用户 {user_id} 声纹已更新")
        return True

    def list_voiceprints(self) -> list:
        """
        列出所有注册的声纹

        Returns:
            声纹列表
        """
        return [
            {
                "user_id": user_id,
                "name": data["name"],
                "quality_score": data.get("quality_score", 0.0),
            }
            for user_id, data in self.voiceprints.items()
        ]

    def detect_speakers(self, audio_file: str) -> list:
        """
        检测音频中的多个说话人（简化版）

        Args:
            audio_file: 音频文件路径

        Returns:
            检测到的说话人数量和片段
        """
        # TODO: 实现更复杂的说话人分离
        # 这里简化处理，假设整个音频是一个说话人
        logger.info("多说话人检测功能待实现")
        return [{"start": 0, "end": -1, "speaker_id": 0}]
