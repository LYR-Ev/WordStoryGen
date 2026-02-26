"""封面图生成：在背景图上绘制标题，自适应字体与换行，导出高清图。"""

import logging
import re
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# 默认导出分辨率（竖版小红书）
OUTPUT_WIDTH = 1080
OUTPUT_HEIGHT = 1440

# 边距与安全区（像素）
PADDING = 60
MAX_LINE_RATIO = 0.85  # 单行最大宽度占画布比例

# 封面标题允许字符白名单：中文、英文、数字、常用中文标点
_TITLE_ALLOWED_PATTERN = re.compile(r"[^\u4e00-\u9fffa-zA-Z0-9，。！？：、]")


def sanitize_title(text: str) -> str:
    """清洗封面标题：去掉 emoji 与特殊符号，只保留中文、英文、数字及常用标点。

    允许字符：中文 \\u4e00-\\u9fff、英文 a-zA-Z、数字 0-9、标点 ，。！？：、
    不匹配的字符全部删除。若清洗后为空则返回「每日单词」。

    Args:
        text: 原始标题文本。

    Returns:
        清洗后的标题，或「每日单词」当结果为空时。
    """
    original = text if text is not None else ""
    if not original.strip():
        logger.info("封面标题清洗: '%s' -> '%s'", original, "每日单词")
        return "每日单词"
    cleaned = _TITLE_ALLOWED_PATTERN.sub("", original).strip()
    logger.info("封面标题清洗: '%s' -> '%s'", original, cleaned)
    if not cleaned:
        return "每日单词"
    return cleaned


def _find_font_path() -> Optional[Path]:
    """查找可用中文字体路径（fallback 机制）。"""
    candidates = [
        Path("assets/fonts/SourceHanSansSC-Regular.otf"),
        Path("assets/fonts/NotoSansSC-Regular.otf"),
        Path("fonts/SourceHanSansSC-Regular.otf"),
        Path("fonts/NotoSansSC-Regular.otf"),
    ]
    # Windows 系统字体
    win_fonts = Path("C:/Windows/Fonts")
    if win_fonts.exists():
        candidates.extend([
            win_fonts / "msyh.ttc",   # 微软雅黑
            win_fonts / "simhei.ttf", # 黑体
            win_fonts / "simsun.ttc", # 宋体
        ])
    for p in candidates:
        if p.exists():
            return p
    return None


def _get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """获取指定大小的字体；无中文字体时使用 PIL 默认（可能无中文）。"""
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


def _wrap_lines(
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> List[str]:
    """将标题按最大宽度自动换行，返回行列表。"""
    if not text or max_width <= 0:
        return [text] if text else []
    lines: List[str] = []
    # 逐字尝试，保证不溢出
    for char in text:
        if not lines:
            lines.append(char)
            continue
        test = lines[-1] + char
        bbox = font.getbbox(test)
        if bbox[2] - bbox[0] <= max_width:
            lines[-1] = test
        else:
            lines.append(char)
    return lines


def _fit_font_size(
    text: str,
    max_width: int,
    max_height: int,
    min_size: int = 24,
    max_size: int = 120,
) -> Tuple[int, List[str]]:
    """在给定区域内自适应字体大小与换行，返回 (字号, 行列表)。"""
    for size in range(max_size, min_size - 1, -4):
        font = _get_font(size)
        lines = _wrap_lines(text, font, max_width)
        line_height = size * 1.4
        total_h = len(lines) * line_height
        if total_h <= max_height:
            return size, lines
    font = _get_font(min_size)
    return min_size, _wrap_lines(text, font, max_width)


class CoverMaker:
    """使用背景图 + 标题文字生成封面图，导出高清 PNG。"""

    def __init__(
        self,
        background_path: str | Path = "bg1.jpg",
        output_dir: str | Path = "output/covers",
        width: int = OUTPUT_WIDTH,
        height: int = OUTPUT_HEIGHT,
    ) -> None:
        """初始化。

        Args:
            background_path: 背景图路径。
            output_dir: 封面输出目录。
            width: 输出宽度。
            height: 输出高度。
        """
        self.bg_path = Path(background_path)
        self.output_dir = Path(output_dir)
        self.width = width
        self.height = height
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _load_background(self) -> Image.Image:
        """加载背景图并缩放到目标尺寸；不存在则生成默认渐变背景。"""
        if self.bg_path.exists():
            try:
                img = Image.open(self.bg_path).convert("RGB")
                img = img.resize((self.width, self.height), Image.Resampling.LANCZOS)
                return img
            except Exception as e:
                logger.warning("加载背景图失败，使用默认背景: %s", e)
        # 默认渐变背景（深色到浅色）
        base = Image.new("RGB", (self.width, self.height), (30, 30, 50))
        draw = ImageDraw.Draw(base)
        for y in range(self.height):
            r = int(30 + (255 - 30) * (y / self.height) * 0.3)
            g = int(30 + (200 - 30) * (y / self.height) * 0.3)
            b = int(50 + (220 - 50) * (y / self.height) * 0.3)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))
        return base

    def make(
        self,
        title: str,
        output_filename: Optional[str] = None,
    ) -> Path:
        """在背景图上绘制标题并导出，保证标题不溢出、居中、高清。

        Args:
            title: 封面标题文字。
            output_filename: 可选输出文件名（不含路径）；默认按时间戳生成。

        Returns:
            输出文件的 Path。
        """
        if not title or not title.strip():
            title = "未命名标题"
        title = title.strip()

        # 绘制前清洗标题（仅影响封面图文字，不影响 JSON 存储）
        title = sanitize_title(title)

        img = self._load_background()
        draw = ImageDraw.Draw(img)

        max_text_width = int(self.width * MAX_LINE_RATIO) - 2 * PADDING
        max_text_height = self.height - 2 * PADDING

        font_size, lines = _fit_font_size(
            title,
            max_text_width,
            max_text_height,
            min_size=28,
            max_size=100,
        )
        font = _get_font(font_size)
        line_height = int(font_size * 1.4)
        total_h = len(lines) * line_height
        # 垂直居中
        y_start = (self.height - total_h) // 2

        for i, line in enumerate(lines):
            bbox = font.getbbox(line)
            line_w = bbox[2] - bbox[0]
            x = (self.width - line_w) // 2
            y = y_start + i * line_height
            # 抗锯齿：浅色描边 + 黑色字（适配浅色背景）
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((x + dx, y + dy), line, font=font, fill=(255, 255, 255))
            draw.text((x, y), line, font=font, fill=(0, 0, 0))

        if output_filename:
            out_name = output_filename if output_filename.endswith(".png") else output_filename + ".png"
        else:
            import datetime
            out_name = f"cover_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        out_path = self.output_dir / out_name
        img.save(out_path, "PNG", quality=95)
        logger.info("封面已保存: %s", out_path)
        return out_path
