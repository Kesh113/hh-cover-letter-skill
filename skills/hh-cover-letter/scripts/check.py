#!/usr/bin/env python3
"""Механическая проверка сопроводительного письма.

Считает то, в чём модель ошибается: предложения, абзацы, длинное тире, разметку,
стоп-фразы, усилители, слова-связки, повторы. Смысл письма проверяет модель.
Списки фраз совпадают с references/style.md — при правке меняй оба места.

Запуск:
  python3 scripts/check.py письмо.txt [--length 3-4|5-7] [--company "Название"] [--max-chars N] [--metrics]
Код выхода 1, если есть ошибки. Предупреждения не меняют код выхода.
--metrics добавляет измеримую часть для оценки: длину предложений, длинные подряд,
долю пустых слов и фразы-анонсы.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from pathlib import Path

# Разделы references/style.md. Фразы в нижнем регистре.
STOP_PHRASES = [
    # служебный текст
    "вот ваше письмо", "вот сопроводительное письмо", "ниже сопроводительное письмо", "конечно",
    "исходя из предоставленной информации", "с уважением", "надеюсь на ответ",
    # пустые вступления
    "хочу предложить свою кандидатуру", "уважаемые рекрутеры", "меня зовут", "я пишу вам, чтобы",
    "с большим интересом", "рад возможности", "я пишу, чтобы выразить",
    # самооценки и обещания
    "я лучший специалист в своей области", "у меня огромный опыт", "обширный опыт",
    "результат-ориентированный", "я увлечён", "идеально подхожу", "уникальный опыт",
    "глубокие знания", "уверен, что", "внести вклад", "буду рад",
    # компания
    "динамичная компания", "динамичной компании",
    # канцелярит и пустые слова
    "задействовал", "возглавил", "обеспечил взаимодействие", "синергия", "комплексный",
    "инновационный", "в современном быстро меняющемся мире",
    # повторы и концовки-выводы
    "так что", "таким образом", "получается",
]
INTENSIFIERS = [
    "очень", "максимально", "самый", "самая", "самое", "самые", "наиболее", "крайне", "абсолютно",
    "весьма", "чрезвычайно", "невероятно", "исключительный", "предельно", "сильно",
    "сам", "сама", "лично", "ещё и", "еще и", "даже", "как раз", "именно",
]
CONNECTORS = [
    "таким образом", "более того", "кроме того", "при этом", "в свою очередь",
    "следует отметить", "в связи с этим",
]
# Анонсы: фраза обещает содержание вместо самого содержания (аналоги throat-clearing из stop-slop).
ANNOUNCEMENTS = [
    "хочу рассказать", "хотел бы рассказать", "расскажу о", "хочу отметить", "стоит отметить",
    "важно отметить", "обратите внимание", "позвольте", "это говорит о том", "это показывает",
]
LONG_SENTENCE = 20  # слов
GREETINGS = ["здравствуйте", "добрый день", "добрый вечер", "доброе утро", "приветствую", "привет"]
LENGTHS = {"3-4": (3, 4, 1, 2), "5-7": (5, 7, 2, 3)}  # предложения от/до, абзацы от/до

WORD = r"[\w-]+"


def find_phrase(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![\w-]){re.escape(phrase)}(?![\w-])", text, re.IGNORECASE) is not None


def sentences(text: str) -> list[str]:
    flat = re.sub(r"\s+", " ", text).strip()
    parts = re.split(r"(?<=[.!?…])\s+(?=[«\"(A-ZА-ЯЁ0-9])", flat)
    return [p for p in parts if p]


def paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]


def check(text: str, length: str | None = None, company: str = "", max_chars: int = 0) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    low = text.lower()
    sents = sentences(text)
    paras = paragraphs(text)

    lo, hi, plo, phi = LENGTHS.get(length or "", (3, 7, 1, 3))
    if not lo <= len(sents) <= hi:
        errors.append(f"предложений {len(sents)}, нужно {lo}–{hi}")
    if length is None:
        plo, phi = (1, 2) if len(sents) <= 4 else (2, 3)
    if not plo <= len(paras) <= phi:
        errors.append(f"абзацев {len(paras)}, при {len(sents)} предложениях нужно {plo}–{phi}")
    if max_chars and len(text.strip()) > max_chars:
        errors.append(f"знаков {len(text.strip())}, лимит формы {max_chars}")

    if "—" in text:
        errors.append(f"длинное тире: {text.count('—')} шт.")
    if re.search(r"\*|`|^\s*#|^\s*[-•]\s|^\s*\d+[.)]\s", text, re.M):
        errors.append("разметка: звёздочки, решётки, маркеры или нумерация списка")
    if re.search(r"\[[^\]]*\]|\{[^}]*\}|<[^>]*>", text):
        errors.append("заглушка в квадратных, фигурных или угловых скобках")
    first = low.lstrip()
    for g in GREETINGS:
        if first.startswith(g):
            errors.append(f"приветствие в начале: «{g}»")
            break
    if company and company.lower() in low:
        errors.append(f"название компании: «{company}»")

    for phrase in STOP_PHRASES:
        if find_phrase(text, phrase):
            errors.append(f"стоп-фраза: «{phrase}»")
    for phrase in ANNOUNCEMENTS:
        if find_phrase(text, phrase):
            errors.append(f"анонс вместо факта: «{phrase}»")
    for word in INTENSIFIERS:
        if find_phrase(text, word):
            errors.append(f"усилитель или подчёркивание: «{word}»")
    for i, para in enumerate(paras, 1):
        used = [c for c in CONNECTORS if find_phrase(para, c)]
        if len(used) > 1:
            errors.append(f"абзац {i}: больше одной связки ({', '.join(used)})")

    starts = [re.findall(WORD, s.lower())[:1] for s in sents]
    for a, b in zip(starts, starts[1:]):
        if a and a == b:
            warnings.append(f"два предложения подряд начинаются с «{a[0]}»")
    ya = re.findall(WORD, low).count("я")
    if ya:
        warnings.append(f"«я» в письме: {ya} — глагол и так показывает, кто делал; убери, если фраза не теряет смысл")
    words = [w for w in re.findall(WORD, low) if len(w) >= 5]
    for word, n in Counter(words).items():
        if n >= 3:
            warnings.append(f"слово «{word}» повторяется {n} раза — проверь, не повтор ли мысли")
    return errors, warnings


def metrics(text: str) -> list[str]:
    sents = sentences(text)
    lens = [len(re.findall(WORD, x)) for x in sents]
    words = sum(lens) or 1
    mean = sum(lens) / len(lens) if lens else 0
    spread = (sum((n - mean) ** 2 for n in lens) / len(lens)) ** 0.5 if lens else 0
    long_pairs = sum(1 for a, b in zip(lens, lens[1:]) if a > LONG_SENTENCE and b > LONG_SENTENCE)
    empty = [w for w in STOP_PHRASES + INTENSIFIERS + CONNECTORS if find_phrase(text, w)]
    ann = [w for w in ANNOUNCEMENTS if find_phrase(text, w)]
    return [
        f"длина предложений в словах: {lens}; среднее {mean:.1f}; разброс {spread:.1f}",
        f"длинных (больше {LONG_SENTENCE} слов) подряд: {long_pairs}",
        f"пустые слова и связки: {len(empty)} на {words} слов" + (f" ({', '.join(empty)})" if empty else ""),
        f"фразы-анонсы: {len(ann)}" + (f" ({', '.join(ann)})" if ann else ""),
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("file")
    p.add_argument("--length", choices=sorted(LENGTHS))
    p.add_argument("--company", default="")
    p.add_argument("--max-chars", type=int, default=0)
    p.add_argument("--metrics", action="store_true", help="напечатать измеримую часть для оценки")
    a = p.parse_args(argv)
    text = Path(a.file).read_text(encoding="utf-8")
    errors, warnings = check(text, a.length, a.company, a.max_chars)
    for e in errors:
        print(f"ОШИБКА: {e}")
    for w in warnings:
        print(f"проверь: {w}")
    if not errors and not warnings:
        print("ok")
    if a.metrics:
        for m in metrics(text):
            print(f"метрика: {m}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
