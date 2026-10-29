"""База знаний: принципы 12 шагов и техники самопомощи.

Сейчас поиск сделан простым способом — по ключевым словам (работает без интернета).
Следующий шаг развития — загрузить эти материалы и реальные истории выздоровления
(анонимизированные, с согласия авторов) в Yandex AI Search.
"""
import json
from pathlib import Path

from .safety import normalize

_PATH = Path(__file__).with_name("knowledge_base.json")
KNOWLEDGE: list[dict] = json.loads(_PATH.read_text(encoding="utf-8"))


def search(text: str, mode: str = "patient", limit: int = 2) -> list[dict]:
    query = f" {normalize(text)} "
    scored = []
    for item in KNOWLEDGE:
        if mode != "relative" and item["type"] == "relative":
            continue
        score = sum(1 for kw in item["keywords"] if normalize(kw) and f" {normalize(kw)}" in query)
        if mode == "relative" and item["type"] == "relative":
            score += 0.5
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: -x[0])
    return [item for _, item in scored[:limit]]


STEPS_OF_DAY = [
    ("Только сегодня", "Не нужно обещать себе «никогда». Достаточно пройти один этот день."),
    ("Честность", "Признать, что сам не справляешься, — это не слабость, а первый шаг."),
    ("Надежда", "Выздоровление возможно. Тысячи людей уже прошли этот путь."),
    ("Решение", "Сегодня можно выбрать доверие — группе, спонсору, людям рядом."),
    ("Взгляд внутрь", "Попробуй честно записать, что тебя сегодня тревожит."),
    ("Открытость", "Поделиться тем, что на душе, с другим человеком — облегчение."),
    ("Готовность меняться", "Заметь одну привычку, которая мешает тебе сегодня."),
    ("Смирение", "Можно попросить о помощи. Это делает тебя сильнее."),
    ("Ответственность", "Подумай, перед кем ты хотел бы когда-нибудь извиниться."),
    ("Исправление", "Маленький добрый поступок сегодня — тоже шаг."),
    ("Ежедневный самоанализ", "Вечером вспомни: что сегодня получилось хорошо?"),
    ("Тишина", "Пять минут спокойного дыхания помогают услышать себя."),
    ("Помощь другим", "Твой опыт однажды поможет кому-то, кто сейчас в начале пути."),
]


def step_of_day(day_of_year: int) -> dict:
    title, text = STEPS_OF_DAY[day_of_year % len(STEPS_OF_DAY)]
    return {"title": title, "text": text}
