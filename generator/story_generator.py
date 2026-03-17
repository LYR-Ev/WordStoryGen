"""故事文案生成：读取 Prompt、调用 Ollama、解析并返回结构化内容。"""

import logging
from pathlib import Path
from typing import Optional

from generator.ollama_client import OllamaClient
from generator.word_loader import WordBankType

logger = logging.getLogger(__name__)


class StoryGenerator:
    """根据词库单词与 Prompt 模板，调用 Ollama 生成小红书风格故事文案。"""

    def __init__(
        self,
        ollama_client: OllamaClient,
        prompt_path: str | Path = "prompts/story_prompt.txt",
    ) -> None:
        """初始化。

        Args:
            ollama_client: Ollama 客户端实例。
            prompt_path: 故事 Prompt 模板文件路径。
        """
        self.client = ollama_client
        self.prompt_path = Path(prompt_path)

    def load_prompt_template(self) -> str:
        """从 prompts/story_prompt.txt 读取模板；文件不存在则返回默认模板。"""
        if self.prompt_path.exists():
            try:
                return self.prompt_path.read_text(encoding="utf-8").strip()
            except OSError as e:
                logger.warning("读取 Prompt 文件失败，使用默认: %s", e)
        return self._default_prompt()

    def _default_prompt(self) -> str:
        """默认故事生成 Prompt（当文件缺失时使用）。"""
        return """你是一位擅长写爆款情感故事的小红书博主。请根据下面给出的英文单词，写一篇符合以下结构的小红书文案。

【必须遵守的结构】
1. 吸睛标题：仅一句爆款风格标题（可带情绪、悬念）。不要用斜杠、换行或并列写多个标题；不要直接输出“吸睛标题”字样。
2. 正文故事：一个有趣、生动、不寻常的小故事，优先爱情题材，有情绪张力，节奏快，200字左右。（不要直接输出“正文故事”字样）
3. 反转结尾：故事结尾自然反转，引出的英文单词就是给定的单词（在文中用该英文单词收尾）。（注意在生成的文案中不要直接输出“反转结尾”四个字）
4. 单词解释：最后一段写「单词解释：」+ 单词 + 中文释义；再写「记忆：」+ 简短记忆技巧（如词根/联想）。

【要求】
- 风格：情绪张力强、反转明显、节奏快。
- 字数：标题一句话；正文约200字；单词解释与记忆各一两句。
- 禁止：不要输出任何关于「作为AI」、「模型」、「根据要求」等元说明，只输出纯文案。

【本次要用的英文单词】
{word}
"""

    def generate(self, word: str, bank: WordBankType) -> str:
        """根据单词生成完整故事文案（含标题、正文、反转、单词解释）。

        Args:
            word: 本次要用的英文单词。
            bank: 词库类型（仅用于日志）。

        Returns:
            模型生成的完整文案文本。
        """
        template = self.load_prompt_template()
        # 支持 {word} 占位符
        if "{word}" in template:
            user_prompt = template.replace("{word}", word.strip().lower())
        else:
            user_prompt = template + "\n\n【本次要用的英文单词】\n" + word

        logger.info("生成故事文案: word=%s, bank=%s", word, bank)
        raw = self.client.generate(user_prompt)
        if not raw or len(raw) < 50:
            raise ValueError("模型返回内容过短或为空，请检查 Prompt 或重试")
        return raw
