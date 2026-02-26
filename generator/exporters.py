"""导出器：将文案数据（JSON 结构）导出为多种展示格式。"""

from pathlib import Path
from typing import Any


def export_to_txt(post_data: dict[str, Any]) -> str:
    """将单篇文案导出为纯文本（适合直接复制到小红书等）。

    Args:
        post_data: 含 title, word, bank, content, created_at 的字典。

    Returns:
        格式化后的 TXT 字符串。
    """
    title = post_data.get("title", "").strip() or "未命名标题"
    content = post_data.get("content", "").strip()
    parts = [title, "", content]
    return "\n".join(parts).strip() + "\n"


def write_txt(post_data: dict[str, Any], path: Path) -> None:
    """将文案导出为 TXT 并写入指定路径。

    Args:
        post_data: 文案数据字典。
        path: 输出文件路径（通常以 .txt 结尾）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    txt = export_to_txt(post_data)
    path.write_text(txt, encoding="utf-8")
