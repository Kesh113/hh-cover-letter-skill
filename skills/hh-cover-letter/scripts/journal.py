#!/usr/bin/env python3
"""Журнал откликов и статистика объектов стиля сопроводительных писем.

Модель не считает сама: все подсчёты делает этот скрипт, чтобы цифры были точными.
Только стандартная библиотека Python 3.9+.

Данные лежат вне навыка, чтобы переустановка их не стирала: в $HH_LETTER_DATA,
а если переменная не задана — в ~/.hh-cover-letter/. Путь печатает команда where.
  journal.jsonl — по строке на отправленное письмо: объекты стиля и исход;
  style.md      — образец стиля, пересобирается после каждого исхода.

Команды:
  where    напечатать путь к папке данных (и создать её)
  add      записать отправленное письмо и его объекты стиля (повтор не создаёт дубль)
  outcome  отметить ответ рекрутера: funnel (воронка) или reject (отказ)
  stats    таблица по объектам стиля
  style    пересобрать style.md
  list     последние письма в журнале
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Объекты стиля и их допустимые значения. Термины вакансии (term) — свободный список.
OBJECTS: dict[str, tuple[str, ...]] = {
    "opening": ("опыт", "результат", "компания", "просьба"),
    "number": ("да", "нет"),
    "story": ("да", "нет"),
    "company": ("да", "нет"),
    "length": ("3-4", "5-7"),
    "tone": ("сдержанный", "тёплый"),
}
OBJECT_TITLES = {
    "opening": "Начало письма",
    "number": "Цифра в письме",
    "story": "История «было → сделал → стало»",
    "company": "Смысл из деятельности компании",
    "length": "Длина, предложений",
    "tone": "Тон",
    "term": "Термин вакансии",
}
OUTCOMES = {"funnel": "воронка", "reject": "отказ"}

MIN_OUTCOMES = 15  # до стольких исходов только копим статистику
FIX_MIN_POSITIVE = 3  # закрепить: положительных не меньше и больше, чем отказов
REMOVE_STREAK = 3  # убрать: столько отказов подряд и ни одного положительного
STYLE_EXAMPLES = 3  # сколько писем из воронки показывать как образец


def data_dir() -> Path:
    return Path(os.environ.get("HH_LETTER_DATA") or Path.home() / ".hh-cover-letter").expanduser()


def journal_path() -> Path:
    return data_dir() / "journal.jsonl"


def load() -> list[dict]:
    path = journal_path()
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def save(rows: list[dict]) -> None:
    path = journal_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    tmp.replace(path)


def now() -> str:
    return datetime.now().isoformat()  # микросекунды: порядок исходов важен для серий отказов


def parse_objects(pairs: list[str]) -> dict[str, str]:
    objects: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        key, value = key.strip(), value.strip()
        if not sep or key not in OBJECTS:
            raise SystemExit(f"неизвестный объект стиля {pair!r}; допустимы: {', '.join(OBJECTS)}")
        if value not in OBJECTS[key]:
            raise SystemExit(f"{key}: значение {value!r} не из списка {OBJECTS[key]}")
        objects[key] = value
    missing = [k for k in OBJECTS if k not in objects]
    if missing:
        raise SystemExit(f"не заданы объекты стиля: {', '.join(missing)}")
    return objects


def features(row: dict) -> list[tuple[str, str]]:
    """Все объекты стиля письма в виде пар (объект, значение)."""
    items = list(row["objects"].items())
    items += [("term", t.lower()) for t in row.get("terms", [])]
    return items


@dataclass
class Stat:
    positive: int = 0
    negative: int = 0
    streak: int = 0  # отказов подряд по последним исходам

    def status(self, total_outcomes: int) -> str:
        if total_outcomes < MIN_OUTCOMES:
            return "копим"
        if self.positive >= FIX_MIN_POSITIVE and self.positive > self.negative:
            return "закрепить"
        if self.positive == 0 and self.streak >= REMOVE_STREAK:
            return "убрать"
        return "тест"


def compute(rows: list[dict]) -> tuple[dict[tuple[str, str], Stat], int]:
    done = sorted((r for r in rows if r.get("outcome") in OUTCOMES), key=lambda r: r["outcome_at"])
    stats: dict[tuple[str, str], Stat] = {}
    for row in done:
        for feature in features(row):
            s = stats.setdefault(feature, Stat())
            if row["outcome"] == "funnel":
                s.positive += 1
                s.streak = 0
            else:
                s.negative += 1
                s.streak += 1
    return stats, len(done)


def find(rows: list[dict], key: str) -> dict:
    exact = [r for r in rows if r["id"] == key]
    if exact:
        return exact[0]
    key_l = key.lower()
    hits = [r for r in rows if key_l in r.get("company", "").lower() or key_l in r.get("title", "").lower()]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise SystemExit(f"в журнале нет письма {key!r}")
    listing = "\n".join(f"  {r['id']}: {r.get('company', '')} — {r.get('title', '')}" for r in hits)
    raise SystemExit(f"{key!r} подходит к нескольким письмам, укажи id:\n{listing}")


def cmd_add(args: argparse.Namespace) -> None:
    rows = load()
    letter = Path(args.letter_file).read_text(encoding="utf-8").strip() if args.letter_file else args.letter
    if not letter:
        raise SystemExit("нужен текст письма: --letter или --letter-file")
    for r in rows:  # повтор той же команды не создаёт дубль
        if (r.get("company"), r.get("title"), r.get("url", ""), r["letter"]) == (args.company, args.title, args.url or "", letter):
            print(f"уже записано: {r['id']}")
            return
    base = args.id or datetime.now().strftime("%Y%m%d-%H%M")
    ids = {r["id"] for r in rows}
    entry_id, n = base, 2
    while entry_id in ids:
        entry_id, n = f"{base}-{n}", n + 1
    rows.append({
        "id": entry_id,
        "sent_at": now(),
        "company": args.company,
        "title": args.title,
        "url": args.url or "",
        "objects": parse_objects(args.obj),
        "terms": [t.strip() for t in args.term if t.strip()],
        "letter": letter,
        "outcome": None,
        "outcome_at": None,
    })
    save(rows)
    print(f"записано: {entry_id}")


def cmd_outcome(args: argparse.Namespace) -> None:
    rows = load()
    row = find(rows, args.key)
    if args.result not in OUTCOMES:
        raise SystemExit("исход: funnel (воронка) или reject (отказ); молчание не записываем")
    row["outcome"], row["outcome_at"] = args.result, now()
    save(rows)
    write_style(rows)
    print(f"{row['id']} ({row.get('company', '')}): {OUTCOMES[args.result]}; style.md обновлён")


def stats_table(rows: list[dict]) -> str:
    stats, total = compute(rows)
    lines = [f"Исходов: {total} (статусы включаются с {MIN_OUTCOMES})", ""]
    lines.append("| Объект | Значение | Воронка | Отказ | Отказов подряд | Статус |")
    lines.append("|---|---|---|---|---|---|")
    for (obj, value), s in sorted(stats.items(), key=lambda kv: (list(OBJECT_TITLES).index(kv[0][0]), kv[0][1])):
        lines.append(f"| {OBJECT_TITLES[obj]} | {value} | {s.positive} | {s.negative} | {s.streak} | {s.status(total)} |")
    return "\n".join(lines)


def write_style(rows: list[dict]) -> Path:
    stats, total = compute(rows)
    fixed = [k for k, s in stats.items() if s.status(total) == "закрепить"]
    removed = [k for k, s in stats.items() if s.status(total) == "убрать"]

    def fmt(keys: list[tuple[str, str]]) -> str:
        return "\n".join(f"- {OBJECT_TITLES[o]}: {v}" for o, v in sorted(keys)) or "- пока нет"

    funnel = sorted((r for r in rows if r.get("outcome") == "funnel"), key=lambda r: r["outcome_at"], reverse=True)
    examples = "\n\n".join(
        f"### {r.get('title', '')}\n\n{r['letter']}" for r in funnel[:STYLE_EXAMPLES]
    ) or "Пока нет писем, дошедших до воронки."
    note = (
        f"Исходов {total} из {MIN_OUTCOMES}: пока только копим статистику, стиль не меняем."
        if total < MIN_OUTCOMES else f"Исходов {total}: правила ниже действуют."
    )
    text = (
        "# Образец стиля\n\n"
        f"_Собрано scripts/journal.py {now()}. Не править вручную._\n\n{note}\n\n"
        f"## Закрепить — использовать во всех вариантах\n\n{fmt(fixed)}\n\n"
        f"## Убрать — не использовать\n\n{fmt(removed)}\n\n"
        "## Письма, дошедшие до воронки (образец тона и ритма, факты не переносить)\n\n"
        f"{examples}\n\n## Статистика\n\n{stats_table(rows)}\n"
    )
    path = data_dir() / "style.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def cmd_list(args: argparse.Namespace) -> None:
    for r in load()[-args.n:]:
        outcome = OUTCOMES.get(r.get("outcome") or "", "ждём ответа")
        print(f"{r['id']}\t{r['sent_at'][:10]}\t{r.get('company', '')} — {r.get('title', '')}\t{outcome}")


def cmd_where(_args: argparse.Namespace) -> None:
    path = data_dir()
    path.mkdir(parents=True, exist_ok=True)
    print(path)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="записать отправленное письмо")
    a.add_argument("--company", required=True)
    a.add_argument("--title", required=True, help="название вакансии")
    a.add_argument("--url", default="")
    a.add_argument("--id", default="", help="по умолчанию — дата и время")
    a.add_argument("--letter", default="")
    a.add_argument("--letter-file", default="")
    a.add_argument("--obj", action="append", default=[], help="объект=значение, например opening=опыт")
    a.add_argument("--term", action="append", default=[], help="термин вакансии, использованный в письме")
    a.set_defaults(func=cmd_add)

    o = sub.add_parser("outcome", help="отметить ответ рекрутера")
    o.add_argument("key", help="id письма или часть названия компании/вакансии")
    o.add_argument("result", choices=sorted(OUTCOMES))
    o.set_defaults(func=cmd_outcome)

    w = sub.add_parser("where", help="путь к папке данных")
    w.set_defaults(func=cmd_where)

    s = sub.add_parser("stats", help="статистика по объектам стиля")
    s.set_defaults(func=lambda _a: print(stats_table(load())))

    st = sub.add_parser("style", help="пересобрать style.md")
    st.set_defaults(func=lambda _a: print(write_style(load())))

    ls = sub.add_parser("list", help="последние письма")
    ls.add_argument("-n", type=int, default=20)
    ls.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    sys.exit(main())
