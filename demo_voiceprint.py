#!/usr/bin/env python3
"""
声纹识别功能演示脚本

此脚本演示如何使用声纹管理功能，包括：
1. 创建测试音频
2. 注册声纹
3. 验证声纹
4. 列出和删除声纹
"""

import logging
import os
import sys
import wave
from pathlib import Path

import numpy as np

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from voiceprint_manager import VoiceprintManager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("voiceprint-demo")


def create_demo_audio(filename: str, duration: float = 5.0, frequency: float = 440.0):
    """创建演示用的音频文件"""
    sample_rate = 16000
    num_samples = int(duration * sample_rate)

    # 生成正弦波
    t = np.linspace(0, duration, num_samples)
    audio_data = (np.sin(2 * np.pi * frequency * t) * 32767).astype(np.int16)

    # 添加一些噪声使每个文件略有不同
    noise = (np.random.randn(num_samples) * 1000).astype(np.int16)
    audio_data = audio_data + noise

    # 保存为 WAV 文件
    with wave.open(filename, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data.tobytes())

    logger.info(f"创建演示音频: {filename}")


def demo_voiceprint_management():
    """演示声纹管理功能"""
    logger.info("=" * 60)
    logger.info("声纹识别功能演示")
    logger.info("=" * 60)

    # 创建演示目录
    demo_dir = Path("demo_voiceprints")
    demo_dir.mkdir(exist_ok=True)

    audio_dir = Path("demo_audio")
    audio_dir.mkdir(exist_ok=True)

    # 1. 创建测试音频文件
    logger.info("\n1. 创建测试音频文件...")
    user1_audio = audio_dir / "user1.wav"
    user2_audio = audio_dir / "user2.wav"
    test_audio = audio_dir / "test.wav"

    create_demo_audio(str(user1_audio), duration=5.0, frequency=440.0)
    create_demo_audio(str(user2_audio), duration=5.0, frequency=550.0)
    create_demo_audio(str(test_audio), duration=5.0, frequency=440.0)

    # 2. 初始化声纹管理器
    logger.info("\n2. 初始化声纹管理器...")
    manager = VoiceprintManager(
        data_dir=str(demo_dir),
        similarity_threshold=0.25,
        min_audio_duration=3.0,
        quality_threshold=0.0,  # 降低阈值用于演示
    )

    # 3. 注册声纹
    logger.info("\n3. 注册用户声纹...")
    logger.info("-" * 60)

    # 注册用户1
    result1 = manager.register_voiceprint(
        user_id="demo_user1", name="演示用户1", audio_source=str(user1_audio)
    )
    if result1["success"]:
        logger.info(
            f"✓ 用户1注册成功 - 质量评分: {result1['quality_score']:.3f}"
        )
    else:
        logger.error(f"✗ 用户1注册失败 - {result1['message']}")

    # 注册用户2
    result2 = manager.register_voiceprint(
        user_id="demo_user2", name="演示用户2", audio_source=str(user2_audio)
    )
    if result2["success"]:
        logger.info(
            f"✓ 用户2注册成功 - 质量评分: {result2['quality_score']:.3f}"
        )
    else:
        logger.error(f"✗ 用户2注册失败 - {result2['message']}")

    # 4. 列出已注册的声纹
    logger.info("\n4. 列出已注册的声纹...")
    logger.info("-" * 60)
    voiceprints = manager.list_voiceprints()
    for vp in voiceprints:
        logger.info(
            f"  用户ID: {vp['user_id']:<15} "
            f"姓名: {vp['name']:<15} "
            f"质量: {vp['quality_score']:.3f}"
        )

    # 5. 验证声纹
    logger.info("\n5. 验证测试音频...")
    logger.info("-" * 60)
    speaker = manager.verify_speaker(str(test_audio))

    if speaker:
        logger.info(
            f"✓ 识别成功!\n"
            f"  用户ID: {speaker['user_id']}\n"
            f"  姓名: {speaker['name']}\n"
            f"  相似度: {speaker['similarity']:.4f}"
        )
    else:
        logger.warning("✗ 未识别到注册用户")

    # 6. 更新声纹
    logger.info("\n6. 更新用户信息...")
    logger.info("-" * 60)
    if manager.update_voiceprint(user_id="demo_user1", name="演示用户1（已更新）"):
        logger.info("✓ 用户信息更新成功")
    else:
        logger.error("✗ 用户信息更新失败")

    # 7. 再次列出声纹
    logger.info("\n7. 查看更新后的声纹列表...")
    logger.info("-" * 60)
    voiceprints = manager.list_voiceprints()
    for vp in voiceprints:
        logger.info(
            f"  用户ID: {vp['user_id']:<15} "
            f"姓名: {vp['name']:<20} "
            f"质量: {vp['quality_score']:.3f}"
        )

    # 8. 删除声纹
    logger.info("\n8. 删除用户2的声纹...")
    logger.info("-" * 60)
    if manager.delete_voiceprint("demo_user2"):
        logger.info("✓ 声纹删除成功")
    else:
        logger.error("✗ 声纹删除失败")

    # 9. 最终声纹列表
    logger.info("\n9. 最终声纹列表...")
    logger.info("-" * 60)
    voiceprints = manager.list_voiceprints()
    if voiceprints:
        for vp in voiceprints:
            logger.info(
                f"  用户ID: {vp['user_id']:<15} "
                f"姓名: {vp['name']:<20} "
                f"质量: {vp['quality_score']:.3f}"
            )
    else:
        logger.info("  （无注册用户）")

    logger.info("\n" + "=" * 60)
    logger.info("演示完成!")
    logger.info("=" * 60)

    # 清理提示
    logger.info(
        f"\n演示文件保存在:\n"
        f"  - 音频文件: {audio_dir}/\n"
        f"  - 声纹数据: {demo_dir}/\n"
        f"可以手动删除这些目录"
    )


if __name__ == "__main__":
    try:
        demo_voiceprint_management()
    except KeyboardInterrupt:
        logger.info("\n演示被用户中断")
        sys.exit(0)
    except Exception as e:
        logger.error(f"演示过程中出错: {e}", exc_info=True)
        sys.exit(1)
