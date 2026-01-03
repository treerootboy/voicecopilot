"""
声纹管理命令行工具
提供声纹的注册、删除、查询等功能
"""

import argparse
import logging
import sys
from pathlib import Path

from voiceprint_manager import VoiceprintManager

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("voiceprint-cli")


def register_voiceprint(args):
    """注册声纹"""
    manager = VoiceprintManager(data_dir=args.data_dir)

    if not Path(args.audio_file).exists():
        logger.error(f"音频文件不存在: {args.audio_file}")
        return 1

    logger.info(f"正在为用户 {args.name}({args.user_id}) 注册声纹...")
    result = manager.register_voiceprint(
        user_id=args.user_id, name=args.name, audio_source=args.audio_file
    )

    if result["success"]:
        logger.info(f"✓ {result['message']}")
        logger.info(f"  质量评分: {result['quality_score']:.2f}")
        return 0
    else:
        logger.error(f"✗ {result['message']}")
        if result.get("quality_score", 0) > 0:
            logger.info(f"  质量评分: {result['quality_score']:.2f}")
        return 1


def delete_voiceprint(args):
    """删除声纹"""
    manager = VoiceprintManager(data_dir=args.data_dir)

    logger.info(f"正在删除用户 {args.user_id} 的声纹...")
    if manager.delete_voiceprint(args.user_id):
        logger.info("✓ 声纹删除成功")
        return 0
    else:
        logger.error("✗ 声纹删除失败")
        return 1


def list_voiceprints(args):
    """列出所有声纹"""
    manager = VoiceprintManager(data_dir=args.data_dir)

    voiceprints = manager.list_voiceprints()

    if not voiceprints:
        logger.info("暂无注册的声纹")
        return 0

    logger.info(f"共有 {len(voiceprints)} 个注册用户:")
    logger.info("-" * 60)
    for vp in voiceprints:
        logger.info(
            f"  用户ID: {vp['user_id']:<20} "
            f"姓名: {vp['name']:<15} "
            f"质量: {vp['quality_score']:.2f}"
        )
    logger.info("-" * 60)
    return 0


def verify_voiceprint(args):
    """验证声纹"""
    manager = VoiceprintManager(data_dir=args.data_dir)

    if not Path(args.audio_file).exists():
        logger.error(f"音频文件不存在: {args.audio_file}")
        return 1

    logger.info(f"正在验证音频文件: {args.audio_file}")
    result = manager.verify_speaker(args.audio_file)

    if result:
        logger.info("✓ 识别成功!")
        logger.info(f"  用户ID: {result['user_id']}")
        logger.info(f"  姓名: {result['name']}")
        logger.info(f"  相似度: {result['similarity']:.4f}")
        return 0
    else:
        logger.warning("✗ 未识别到注册用户")
        return 1


def update_voiceprint(args):
    """更新声纹"""
    manager = VoiceprintManager(data_dir=args.data_dir)

    audio_file = args.audio_file if args.audio_file else None
    if audio_file and not Path(audio_file).exists():
        logger.error(f"音频文件不存在: {audio_file}")
        return 1

    logger.info(f"正在更新用户 {args.user_id} 的声纹...")
    if manager.update_voiceprint(
        user_id=args.user_id, name=args.name, audio_source=audio_file
    ):
        logger.info("✓ 声纹更新成功")
        return 0
    else:
        logger.error("✗ 声纹更新失败")
        return 1


def main():
    parser = argparse.ArgumentParser(description="声纹管理工具")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="voiceprints",
        help="声纹数据存储目录 (默认: voiceprints)",
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 注册声纹
    register_parser = subparsers.add_parser("register", help="注册新声纹")
    register_parser.add_argument("user_id", help="用户ID")
    register_parser.add_argument("name", help="用户名称")
    register_parser.add_argument("audio_file", help="音频文件路径")

    # 删除声纹
    delete_parser = subparsers.add_parser("delete", help="删除声纹")
    delete_parser.add_argument("user_id", help="用户ID")

    # 列出声纹
    subparsers.add_parser("list", help="列出所有声纹")

    # 验证声纹
    verify_parser = subparsers.add_parser("verify", help="验证音频中的说话人")
    verify_parser.add_argument("audio_file", help="音频文件路径")

    # 更新声纹
    update_parser = subparsers.add_parser("update", help="更新声纹")
    update_parser.add_argument("user_id", help="用户ID")
    update_parser.add_argument("--name", help="新的用户名称")
    update_parser.add_argument("--audio-file", help="新的音频文件路径")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # 执行对应命令
    commands = {
        "register": register_voiceprint,
        "delete": delete_voiceprint,
        "list": list_voiceprints,
        "verify": verify_voiceprint,
        "update": update_voiceprint,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
