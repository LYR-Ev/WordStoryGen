"""根据单词生成与 bg1 同尺寸的封面图，封面上只显示英文单词。"""

import logging
import random
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1440

# 背景图目录：assets/backgrounds/ 下放置 bg1.jpg, bg2.jpg, bg3.jpg
BACKGROUND_DIR = Path("assets/backgrounds")
BACKGROUND_NAMES = ["bg1.jpg", "bg2.jpg", "bg3.jpg"]

# 轮流使用背景图时的当前索引（每生成一次 +1，对 3 取模）
current_bg_index = 0


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
    """随机生成一种偏柔和的背景色（避免过亮或过暗）。保留用于回退逻辑。"""
    r = random.randint(40, 200)
    g = random.randint(40, 200)
    b = random.randint(50, 220)
    return (r, g, b)


def _load_background_image() -> Image.Image:
    """按 current_bg_index 轮流加载 assets/backgrounds/bg1.jpg、bg2.jpg、bg3.jpg。

    若对应背景图不存在，则回退为纯白背景，避免程序崩溃。
    返回的图片尺寸为 OUTPUT_WIDTH x OUTPUT_HEIGHT。
    """
    global current_bg_index
    idx = current_bg_index % len(BACKGROUND_NAMES)
    bg_path = BACKGROUND_DIR / BACKGROUND_NAMES[idx]
    if bg_path.exists():
        try:
            img = Image.open(bg_path).convert("RGB")
            img = img.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
            logger.debug("使用背景图: %s", bg_path)
            return img
        except Exception as e:
            logger.warning("加载背景图失败，使用纯白背景: %s", e)
    # 背景图不存在或加载失败：纯白背景
    return Image.new("RGB", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (255, 255, 255))


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

    封面上只显示英文单词，垂直居中；背景轮流使用 bg1.jpg → bg2.jpg → bg3.jpg。
    template_index: 0/1/2 仅微调单词垂直位置，None 则随机。

    Args:
        title: 未使用（保留参数兼容调用方）。
        word: 英文单词，封面上唯一内容。
        hook: 未使用（保留参数兼容调用方）。
        output_dir: 输出目录。
        output_filename: 输出文件名（含 .png），不传则自动生成。
        template_index: 0/1/2 指定垂直位置，None 则随机。

    Returns:
        输出文件的 Path。
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    img = _load_background_image()
    draw = ImageDraw.Draw(img)

    word = (word or "").strip() or "word"

    if template_index is None:
        template_index = random.randint(0, 2)

    font_word = _get_font(80)

    # 封面上只有单词，垂直位置三种微调
    y_positions = (620, 580, 600)  # 居中偏上/正中/略下
    y = y_positions[template_index]
    _draw_centered_text(draw, word, font_word, y, OUTPUT_WIDTH)

    global current_bg_index
    current_bg_index = (current_bg_index + 1) % len(BACKGROUND_NAMES)

    if output_filename is None:
        import datetime
        output_filename = f"cover_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    if not output_filename.endswith(".png"):
        output_filename += ".png"
    out_path = output_dir / output_filename
    img.save(out_path, "PNG", quality=95)
    logger.info("封面图已保存: %s (模板 %d)", out_path, template_index)
    return out_path
