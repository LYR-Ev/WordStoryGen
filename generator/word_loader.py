"""词库加载与已用单词持久化。"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Literal

logger = logging.getLogger(__name__)

WordBankType = Literal["cet4", "cet6", "kaoyan"]

# 词库文件名映射
BANK_FILES: dict[WordBankType, str] = {
    "cet4": "CET4.txt",
    "cet6": "CET6.txt",
    "kaoyan": "考研.txt",
}


class WordLoader:
    """从 data 目录加载词库，并维护 used_words.json 避免重复使用。"""

    def __init__(
        self,
        data_dir: str | Path = "data",
        used_words_path: str | Path = "used_words.json",
    ) -> None:
        """初始化。

        Args:
            data_dir: 词库所在目录。
            used_words_path: 已用单词记录文件路径。
        """
        self.data_dir = Path(data_dir)
        self.used_path = Path(used_words_path)
        self._ensure_dirs_and_file()

    def _backup_and_reinit(self) -> None:
        """将损坏的 used_words 文件复制为 used_words_时间戳.bak 后，写入新的空记录。"""
        if self.used_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"used_words_{timestamp}.bak"
            backup_path = self.used_path.parent / backup_name
            try:
                shutil.copy2(self.used_path, backup_path)
                logger.info("已备份损坏文件为: %s", backup_path)
            except OSError as e:
                logger.warning("备份失败，仍将重建 used_words: %s", e)
        self._save_used({k: [] for k in BANK_FILES})

    def _ensure_dirs_and_file(self) -> None:
        """确保 data 目录与 used_words.json 存在；JSON 损坏时先备份再重建。"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if not self.used_path.exists():
            self._save_used({k: [] for k in BANK_FILES})
            logger.info("已创建 used_words.json")
            return
        try:
            with open(self.used_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for key in BANK_FILES:
                if key not in data or not isinstance(data[key], list):
                    data[key] = []
            self._save_used(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("used_words.json 损坏，将备份后重建: %s", e)
            self._backup_and_reinit()

    def _load_used(self) -> dict[str, list[str]]:
        """读取已用单词记录。损坏时先备份为 .bak 再重建并返回空记录。"""
        if not self.used_path.exists():
            return {k: [] for k in BANK_FILES}
        try:
            with open(self.used_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                k: data.get(k, []) if isinstance(data.get(k), list) else []
                for k in BANK_FILES
            }
        except (json.JSONDecodeError, TypeError, OSError) as e:
            logger.warning("读取 used_words 失败，将备份后重建: %s", e)
            self._backup_and_reinit()
            return {k: [] for k in BANK_FILES}

    def _save_used(self, data: dict[str, list[str]]) -> None:
        """写入已用单词记录。"""
        self.used_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.used_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_words(self, bank: WordBankType) -> list[str]:
        """加载指定词库的所有单词（去重、小写）。"""
        fname = BANK_FILES.get(bank)
        if not fname:
            return []
        path = self.data_dir / fname
        if not path.exists():
            logger.warning("词库文件不存在: %s", path)
            return []
        words: list[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    w = line.strip().lower()
                    if w and w not in words:
                        words.append(w)
        except OSError as e:
            logger.error("读取词库失败 %s: %s", path, e)
        return words

    def get_next_word(self, bank: WordBankType) -> str | None:
        """获取下一个未使用的单词并标记为已用；若无则返回 None。"""
        words = self.load_words(bank)
        used = self._load_used()
        used_set = set(used.get(bank, []))
        for w in words:
            if w not in used_set:
                used.setdefault(bank, []).append(w)
                self._save_used(used)
                return w
        return None

    def mark_used(self, bank: WordBankType, word: str) -> None:
        """将单词标记为已用（若尚未记录）。"""
        used = self._load_used()
        lst = used.setdefault(bank, [])
        if word.lower() not in lst:
            lst.append(word.lower())
            self._save_used(used)
