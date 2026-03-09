"""从预设标签池中随机生成 N 个小红书标签，避免每次相同。"""

import random
from typing import List

# 预设标签池（不含 #，主流程拼接时加 #）
TAG_POOL: List[str] = [
    "英语学习",
    "每日单词",
    "单词积累",
    "背单词",
    "英语笔记",
    "词汇学习",
    "学习打卡",
    "英语提升",
    "自律成长",
    "语言学习",
    "英语分享",
    "考研英语",
    "英语口语",
]


def get_random_tags(n: int = 10) -> List[str]:
    """从标签池中随机抽取 n 个不重复标签。

    Args:
        n: 需要返回的标签数量，默认 10。不得超过标签池大小。

    Returns:
        标签字符串列表（不含 #），如 ["英语学习", "每日单词", ...]。
    """
    k = min(n, len(TAG_POOL))
    return random.sample(TAG_POOL, k)


def get_random_tags_string(n: int = 10) -> str:
    """返回可直接拼接到文案的标签行，如 "#英语学习 #每日单词 ..." """
    tags = get_random_tags(n)
    return " ".join("#" + t for t in tags)
