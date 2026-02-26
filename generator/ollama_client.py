"""Ollama HTTP 客户端：调用本地模型生成文案，支持重试与超时。"""

import json
import logging
import time
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    """通过 Ollama HTTP API 调用本地大模型。"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5",
        temperature: float = 0.8,
        timeout_seconds: int = 120,
        max_retries: int = 3,
        retry_delay_seconds: float = 2.0,
    ) -> None:
        """初始化 Ollama 客户端。

        Args:
            base_url: Ollama 服务地址。
            model: 模型名称。
            temperature: 采样温度，越高越随机。
            timeout_seconds: 单次请求超时时间（秒）。
            max_retries: 失败后最大重试次数。
            retry_delay_seconds: 重试间隔（秒）。
        """
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay = retry_delay_seconds
        self._session = requests.Session()

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """发送生成请求，支持自动重试与超时。

        Args:
            prompt: 用户提示词。
            system_prompt: 可选系统提示词。
            temperature: 可选覆盖实例默认温度。

        Returns:
            模型生成的文本。

        Raises:
            RuntimeError: 所有重试均失败或响应异常。
        """
        temp = temperature if temperature is not None else self.temperature
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temp},
        }
        if system_prompt:
            payload["system"] = system_prompt

        url = f"{self.base_url}/api/generate"
        last_error: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "Ollama 请求 (attempt %d/%d): model=%s",
                    attempt,
                    self.max_retries,
                    self.model,
                )
                resp = self._session.post(
                    url,
                    json=payload,
                    timeout=self.timeout,
                )
                resp.raise_for_status()
                data = resp.json()
                text = self._extract_text(data)
                if not text or not text.strip():
                    raise ValueError("模型返回内容为空")
                return text.strip()
            except requests.exceptions.Timeout as e:
                last_error = e
                logger.warning("Ollama 请求超时 (attempt %d): %s", attempt, e)
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning("Ollama 请求失败 (attempt %d): %s", attempt, e)
            except (KeyError, ValueError, TypeError) as e:
                last_error = e
                logger.warning("Ollama 响应解析异常 (attempt %d): %s", attempt, e)

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        raise RuntimeError(
            f"Ollama 调用失败，已重试 {self.max_retries} 次: {last_error}"
        ) from last_error

    @staticmethod
    def _extract_text(data: dict[str, Any]) -> str:
        """从 API 响应中提取文本。"""
        if "response" in data:
            return data["response"]
        if "message" in data and isinstance(data["message"], dict):
            return data["message"].get("content", "")
        return ""
