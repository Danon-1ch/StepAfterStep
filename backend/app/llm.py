"""Работа с YandexGPT (Yandex AI Studio, OpenAI-совместимый API).

Если ключ не задан, используется демо-режим: бот собирает ответ из базы знаний
по шаблону. Так приложение можно показать без доступа к облаку.
"""
import json
import logging
import random

import httpx

from .config import settings
from .prompts import GUARD_PROMPT, KNOWLEDGE_HEADER, RELATIVE_ADDON, SYSTEM_PROMPT

log = logging.getLogger("llm")


class LLMError(Exception):
    pass


last_error: str | None = None  # текст последней ошибки YandexGPT, показывается в /api/health


def _model_uri() -> str:
    return f"gpt://{settings.yandex_folder_id}/{settings.yandex_model}"


async def _chat_completion(messages: list[dict], temperature: float = 0.5, max_tokens: int = 400, timeout: float = 20) -> str:
    global last_error
    headers = {
        "Authorization": f"Api-Key {settings.yandex_api_key}",
        "OpenAI-Project": settings.yandex_folder_id,
        "Content-Type": "application/json",
    }
    body = {
        "model": _model_uri(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{settings.yandex_base_url}/chat/completions", headers=headers, json=body)
            r.raise_for_status()
            reply = r.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:  # сеть, ключ, формат ответа
        log.warning("YandexGPT request failed: %s", exc)
        last_error = str(exc) or type(exc).__name__
        raise LLMError(last_error) from exc
    last_error = None
    return reply


def build_system_prompt(mode: str, knowledge: list[dict]) -> str:
    prompt = SYSTEM_PROMPT
    if mode == "relative":
        prompt += RELATIVE_ADDON
    if knowledge:
        prompt += KNOWLEDGE_HEADER + "\n".join(f"- {k['title']}: {k['text']}" for k in knowledge)
    return prompt


async def generate_reply(history: list[dict], mode: str, knowledge: list[dict]) -> str:
    """history — последние сообщения [{role: user|bot, text}], последнее — от пользователя."""
    if not settings.llm_enabled:
        return demo_reply(history[-1]["text"] if history else "", mode, knowledge)

    messages = [{"role": "system", "content": build_system_prompt(mode, knowledge)}]
    for m in history:
        messages.append({"role": "user" if m["role"] == "user" else "assistant", "content": m["text"]})
    return await _chat_completion(messages)


async def guard_check(text: str) -> dict:
    """ИИ-проверка сообщения: кризис и попытка атаки. Без ключа — ничего не находит."""
    if not settings.llm_enabled:
        return {"crisis": False, "attack": False}
    try:
        raw = await _chat_completion(
            [
                {"role": "system", "content": GUARD_PROMPT},
                {"role": "user", "content": f"<<<{text}>>>"},
            ],
            temperature=0,
            max_tokens=30,
            timeout=5,  # проверка не должна задерживать ответ, если облако тормозит
        )
        start, end = raw.find("{"), raw.rfind("}")
        data = json.loads(raw[start : end + 1])
        return {"crisis": bool(data.get("crisis")), "attack": bool(data.get("attack"))}
    except (LLMError, ValueError):
        return {"crisis": False, "attack": False}


# ---------- демо-режим ----------

_OPENERS = [
    "Спасибо, что написал, а не остался с этим один.",
    "Я тебя слышу. То, что ты сейчас пишешь, — уже шаг.",
    "Знакомое состояние — многие, кто прошёл этот путь, через него проходили.",
]
_OPENERS_RELATIVE = [
    "Спасибо, что пишете — близким зависимого тоже очень нужна поддержка.",
    "Понимаю, как это тяжело — переживать за близкого человека.",
]
_QUESTIONS = [
    "Что сейчас происходит вокруг тебя?",
    "Как ты себя чувствуешь прямо сейчас?",
    "Есть ли рядом кто-то, кому можно позвонить?",
    "Что обычно помогает тебе продержаться?",
]


def demo_reply(text: str, mode: str, knowledge: list[dict]) -> str:
    if mode == "relative":
        opener = random.choice(_OPENERS_RELATIVE)
        question = "Расскажите, что сейчас происходит?"
    else:
        opener = random.choice(_OPENERS)
        question = random.choice(_QUESTIONS)
    body = knowledge[0]["text"] if knowledge else (
        "Давай просто поговорим. Тяга и тяжёлые мысли проходят, особенно когда ими делишься."
    )
    return f"{opener} {body} {question}"
