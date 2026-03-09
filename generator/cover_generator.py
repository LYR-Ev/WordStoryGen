"""根据标题、单词、钩子文案生成与 bg1 同尺寸的封面图，随机背景、3 种排版模板。"""

import logging
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1440


def _find_font_path() -> Optional[Path]:
    """查找可用中文字体路径。"""
    candidates = [
        Path("assets/fonts/SourceHanSansSC-Regular.otf"),
        Path("assets/fonts/NotoSansSC-Regular.otf"),
        Path("fonts/SourceHanSansSC-Regular.otf"),
        Path("fonts/NotoSansSC-Regular.otf"),
    ]
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        candidates.extend([
            win_fonts / "msyh.ttc",
            win_fonts / "simhei.ttf",
            win_fonts / "simsun.ttc",
        ])
    for p in candidates:
        if p.exists():
            return p
    return None


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """获取指定大小的字体。"""
    font_path = _find_font_path()
    if font_path:
        try:
            return ImageFont.truetype(str(font_path), size)
        except OSError:
            pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _random_background_color() -> tuple[int, int, int]:
    """随机生成一种偏柔和的背景色（避免过亮或过暗）。"""
    r = random.randint(40, 200)
    g = random.randint(40, 200)
    b = random.randint(50, 220)
    return (r, g, b)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    y: int,
    width: int,
    fill: tuple[int, int, int] = (0, 0, 0),
) -> None:
    """在画布上居中绘制单行文字。"""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (width - tw) // 2
    draw.text((x, y), text, font=font, fill=fill)


def generate(
    title: str,
    word: str,
    hook: str,
    output_dir: str | Path = "output/images",
    output_filename: Optional[str] = None,
    template_index: Optional[int] = None,
) -> Path:
    """生成一张 1080x1440 的封面图并保存到 output/images。

    使用随机背景色，支持 3 种排版模板，文字均居中。

    Args:
        title: 标题文案。
        word: 英文单词。
        hook: 钩子文案。
        output_dir: 输出目录。
        output_filename: 输出文件名（含 .png），不传则自动生成。
        template_index: 0/1/2 指定模板，None 则随机。

    Returns:
        输出文件的 Path。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), _random_background_color())
    draw = ImageDraw.Draw(img)

    title = (title or "").strip() or "每日单词"
    word = (word or "").strip() or "word"
    hook = (hook or "").strip() or "每天一个单词故事"

    if template_index is None:
        template_index = random.randint(0, 2)

    font_title = _get_font(36)
    font_word = _get_font(80)
    font_hook = _get_font(28)

    # 三种排版：标题 / 单词 / 钩子 在上下位置的组合，均水平居中
    if template_index == 0:
        _draw_centered_text(draw, title, font_title, 280, OUTPUT_WIDTH)
        _draw_centered_text(draw, word, font_word, 580, OUTPUT_WIDTH)
        _draw_centered_text(draw, hook, font_hook, 1080, OUTPUT_WIDTH)
    elif template_index == 1:
        _draw_centered_text(draw, word, font_word, 320, OUTPUT_WIDTH)
        _draw_centered_text(draw, title, font_title, 720, OUTPUT_WIDTH)
        _draw_centered_text(draw, hook, font_hook, 1150, OUTPUT_WIDTH)
    else:
        _draw_centered_text(draw, title, font_title, 260, OUTPUT_WIDTH)
        _draw_centered_text(draw, hook, font_hook, 640, OUTPUT_WIDTH)
        _draw_centered_text(draw, word, font_word, 980, OUTPUT_WIDTH)

    if output_filename is None:
        import datetime
        output_filename = f"cover_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    if not output_filename.endswith(".png"):
        output_filename += ".png"
    out_path = output_dir / output_filename
    img.save(out_path, "PNG", quality=95)
    logger.info("封面图已保存: %s (模板 %d)", out_path, template_index)
    return out_path
