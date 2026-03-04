#!/usr/bin/env python3
"""
WordStoryGen 入口：根据词库生成小红书英语单词故事文案并生成封面。

用法：
    python main.py cet4
    python main.py cet6
    python main.py kaoyan
    python main.py cet4 --count 3
    python main.py cet4 --format json     # 仅输出 JSON
    python main.py cet4 --format txt      # 仅输出 TXT
    python main.py cet4 --format both     # JSON + TXT（默认）
    python main.py cet4 --only-story
    python main.py cet4 --only-cover
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# 加载 .env（若存在）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import os

from generator import CoverMaker, OllamaClient, StoryGenerator, WordLoader
from generator.exporters import write_txt
from generator.word_loader import WordBankType

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent
os.chdir(PROJECT_ROOT)

# 输出目录
OUTPUT_POSTS = PROJECT_ROOT / "output" / "posts"
OUTPUT_COVERS = PROJECT_ROOT / "output" / "covers"
LOGS_DIR = PROJECT_ROOT / "logs"

# 故事正文末尾固定追加：互动引导 + 标签（仅拼接到 content，不改变 title）
STORY_FOOTER_INTERACTION = """——
如果这个单词故事对你有帮助，记得点赞❤️和收藏⭐支持一下～
关注我，每天一个单词故事，轻松提升词汇量！
——"""
STORY_FOOTER_TAGS = "#英语学习 #每日单词 #单词积累 #词汇提升 #英语写作 #背单词 #学习打卡 #自律成长 #语言学习 #考研英语"


def setup_logging() -> None:
    """配置日志：同时输出到控制台与 logs 目录。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / f"run_{datetime.now().strftime('%Y%m%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )


def ensure_dirs() -> None:
    """确保 output/posts、output/covers、data、prompts 存在。"""
    OUTPUT_POSTS.mkdir(parents=True, exist_ok=True)
    OUTPUT_COVERS.mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    (PROJECT_ROOT / "prompts").mkdir(parents=True, exist_ok=True)


def parse_title_from_story(story: str) -> str:
    """从生成的故事中解析标题（第一行或「标题：」后一行）。"""
    lines = [ln.strip() for ln in story.splitlines() if ln.strip()]
    for i, line in enumerate(lines):
        if line.startswith("标题：") or line.startswith("标题:"):
            return line.split("：", 1)[-1].split(":", 1)[-1].strip() or (lines[i + 1] if i + 1 < len(lines) else lines[0])
        if i == 0:
            return line
    return "未命名标题"


def run_one(
    bank: WordBankType,
    word_loader: WordLoader,
    story_gen: StoryGenerator,
    cover_maker: CoverMaker,
    only_story: bool,
    only_cover: bool,
    cover_title: str | None = None,
    output_format: str = "both",
) -> bool:
    """生成一篇文案（可选封面），保存到 output。返回是否成功。

    当 only_cover 且 cover_title 非空时，不消耗词库单词，仅用给定标题生成封面。
    """
    if only_cover and cover_title:
        # 仅封面 + 指定标题：不消耗单词
        logger = logging.getLogger(__name__)
        post_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_cover"
        try:
            cover_maker.make(title=cover_title, output_filename=f"{post_id}.png")
            return True
        except Exception as e:
            logger.exception("生成封面失败: %s", e)
            return False

    word = word_loader.get_next_word(bank)
    if not word:
        logging.getLogger(__name__).error("词库 %s 中已无未使用单词，请添加词库或清空 used_words.json", bank)
        return False

    logger = logging.getLogger(__name__)
    post_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + word

    if only_cover:
        # 仅封面模式：无指定标题时用单词作为标题
        title = word
        story = ""
    else:
        try:
            story = story_gen.generate(word, bank)
        except Exception as e:
            logger.exception("生成文案失败: %s", e)
            word_loader.mark_used(bank, word)  # 不占用未成功生成的单词
            return False
        title = parse_title_from_story(story)
        # 正文末尾追加固定互动文案与标签（与正文空一行；不修改 title）
        story = story.rstrip() + "\n\n" + STORY_FOOTER_INTERACTION + "\n\n" + STORY_FOOTER_TAGS

    # 2. 保存文案（JSON = 主存储，TXT = 导出格式，由 --format 控制）
    if not only_cover:
        post_data = {
            "title": title,
            "word": word,
            "bank": bank,
            "content": story,
            "created_at": datetime.now().isoformat(),
        }
        if output_format in ("json", "both"):
            post_path = OUTPUT_POSTS / f"{post_id}.json"
            try:
                with open(post_path, "w", encoding="utf-8") as f:
                    json.dump(post_data, f, ensure_ascii=False, indent=2)
                logger.info("文案已保存: %s", post_path)
            except OSError as e:
                logger.warning("保存 JSON 失败: %s", e)
        if output_format in ("txt", "both"):
            txt_path = OUTPUT_POSTS / f"{post_id}.txt"
            try:
                write_txt(post_data, txt_path)
                logger.info("文案已导出 TXT: %s", txt_path)
            except OSError as e:
                logger.warning("导出 TXT 失败: %s", e)

    # 3. 生成封面（封面上只显示单词）
    if not only_story:
        try:
            cover_maker.make(title=word, output_filename=f"{post_id}.png")
        except Exception as e:
            logger.exception("生成封面失败: %s", e)

    return True


def main() -> int:
    """命令行入口。"""
    parser = argparse.ArgumentParser(
        description="小红书英语单词故事文案 + 封面生成（Ollama 本地模型）",
    )
    parser.add_argument(
        "bank",
        choices=["cet4", "cet6", "kaoyan"],
        help="词库：cet4 / cet6 / kaoyan",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=1,
        metavar="N",
        help="批量生成数量，默认 1",
    )
    parser.add_argument(
        "--only-story",
        action="store_true",
        help="仅生成文案，不生成封面",
    )
    parser.add_argument(
        "--only-cover",
        action="store_true",
        help="仅生成封面（使用单词作为标题，需先有文案时可手动指定标题逻辑）",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        metavar="TEXT",
        help="与 --only-cover 合用：指定封面标题，不消耗词库单词",
    )
    parser.add_argument(
        "--format",
        choices=["json", "txt", "both"],
        default="both",
        dest="output_format",
        help="文案输出格式：json=仅JSON，txt=仅TXT，both=JSON+TXT（默认）",
    )
    args = parser.parse_args()
    bank: WordBankType = args.bank

    setup_logging()
    ensure_dirs()
    log = logging.getLogger(__name__)

    # 仅封面模式与仅文案不能同时
    if args.only_story and args.only_cover:
        log.error("不能同时使用 --only-story 与 --only-cover")
        return 2

    # 环境变量
    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5")
    try:
        temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.8"))
    except ValueError:
        temperature = 0.8
    try:
        timeout = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    except ValueError:
        timeout = 120

    word_loader = WordLoader(
        data_dir=PROJECT_ROOT / "data",
        used_words_path=PROJECT_ROOT / "used_words.json",
    )
    ollama = OllamaClient(
        base_url=ollama_url,
        model=model,
        temperature=temperature,
        timeout_seconds=timeout,
    )
    story_gen = StoryGenerator(
        ollama_client=ollama,
        prompt_path=PROJECT_ROOT / "prompts" / "story_prompt.txt",
    )
    cover_maker = CoverMaker(
        background_path=PROJECT_ROOT / "bg1.jpg",
        output_dir=OUTPUT_COVERS,
        width=1080,
        height=1440,
    )

    success = 0
    effective_count = args.count
    if args.only_cover and args.title:
        effective_count = 1
    for i in range(effective_count):
        if effective_count > 1:
            log.info("--- 第 %d/%d 篇 ---", i + 1, effective_count)
        if run_one(bank, word_loader, story_gen, cover_maker, args.only_story, args.only_cover, getattr(args, "title", None), args.output_format):
            success += 1

    if success == 0 and effective_count > 0:
        return 1
    log.info("完成：成功 %d 篇", success)
    return 0


if __name__ == "__main__":
    sys.exit(main())
