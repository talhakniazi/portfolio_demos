"""Language-model providers. All are called over plain HTTP, so there are no SDK dependencies.

Choose with CHATBOT_PROVIDER = openai | anthropic | ollama | extractive (default: extractive, which needs nothing).
"""
from __future__ import annotations

import os
import re

import requests

TIMEOUT = 60


class ProviderError(RuntimeError):
    pass


def openai_chat(system: str, messages: list[dict]) -> str:
    key = os.environ.get("OPENAI_API_KEY") or _missing("OPENAI_API_KEY")
    r = requests.post(os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1") + "/chat/completions", timeout=TIMEOUT,
                      headers={"Authorization": f"Bearer {key}"},
                      json={"model": os.environ.get("CHATBOT_MODEL", "gpt-4o-mini"), "temperature": 0.1,
                            "messages": [{"role": "system", "content": system}, *messages]})
    _check(r)
    return r.json()["choices"][0]["message"]["content"]


def anthropic_chat(system: str, messages: list[dict]) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY") or _missing("ANTHROPIC_API_KEY")
    r = requests.post("https://api.anthropic.com/v1/messages", timeout=TIMEOUT,
                      headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
                      json={"model": os.environ.get("CHATBOT_MODEL", "claude-haiku-5-5"), "max_tokens": 600, "temperature": 0.1,
                            "system": system, "messages": messages})
    _check(r)
    return "".join(b.get("text", "") for b in r.json()["content"])


def ollama_chat(system: str, messages: list[dict]) -> str:
    r = requests.post(os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434") + "/api/chat", timeout=180,
                      json={"model": os.environ.get("CHATBOT_MODEL", "qwen2.5:3b"), "stream": False,
                            "options": {"temperature": 0.1}, "messages": [{"role": "system", "content": system}, *messages]})
    _check(r)
    return r.json()["message"]["content"]


def _missing(name):
    raise ProviderError(f"{name} is not set")


def _check(r):
    if r.status_code >= 400:
        raise ProviderError(f"provider returned HTTP {r.status_code}: {r.text[:200]}")


PROVIDERS = {"openai": openai_chat, "anthropic": anthropic_chat, "ollama": ollama_chat}


def provider_name() -> str:
    return os.environ.get("CHATBOT_PROVIDER", "extractive").lower()


def strip_think(text: str) -> str:
    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
