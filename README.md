# hh-cover-letter-skill

[![Claude Code](https://img.shields.io/badge/Claude_Code-skill-D97757?style=flat-square)](https://github.com/anthropics/claude-code)
[![Codex](https://img.shields.io/badge/Codex-skill-111111?style=flat-square)](https://github.com/openai/codex)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

Навык для Claude Code и Codex: пишет короткие честные сопроводительные письма к откликам на hh.ru и учится на ответах рекрутеров.

## Что делает

1. Вы даёте ссылку на вакансию. Навык пишет три варианта письма по 3–7 предложений, проверяет каждый и показывает его оценку.
2. В письмо попадают только факты из вашего профиля. О требованиях, которых в профиле нет, навык спросит, а ловушки для нейросетей в тексте вакансии покажет.
3. Вы говорите, какой вариант отправили и что ответил рекрутер. Навык ведёт журнал и со временем закрепляет в письмах то, что рекрутеры берут в воронку.

## Установка

Claude Code:
```bash
git clone https://github.com/Kesh113/hh-cover-letter-skill
cp -r hh-cover-letter-skill/skills/hh-cover-letter ~/.claude/skills/
```

Codex:
```bash
git clone https://github.com/Kesh113/hh-cover-letter-skill
cp -r hh-cover-letter-skill/skills/hh-cover-letter ~/.codex/skills/
```

Нужен Python 3.9+, без сторонних библиотек: журнал и статистику ведёт `scripts/journal.py`, механику письма проверяет `scripts/check.py`. Подсчёты делает код, а не модель.

Обновление: удалите старую папку навыка и скопируйте новую. Профиль и журнал лежат отдельно и не пострадают.

## Первый запуск

Напишите агенту «напиши сопроводительное к <ссылка на вакансию>» и приложите резюме. Навык соберёт профиль в `~/.hh-cover-letter/profile.md`. Туда стоит дописать то, чего нет в резюме: проекты, детали, цифры. Резюме короткое, а письму нужны факты.

Папка `~/.hh-cover-letter/` хранит профиль, журнал и образец стиля. Она лежит вне навыка, поэтому обновление навыка её не трогает. Другое место можно задать переменной окружения `HH_LETTER_DATA`.

## Благодарности

Правила собраны из открытых проектов: [hh-applicant-tool](https://github.com/s3rgeym/hh-applicant-tool), [hh-ai-agent](https://github.com/fikstt2/hh-ai-agent), [n8n-hh.ru](https://github.com/jointime1/n8n-hh.ru), [hh-ru-apply](https://github.com/Steev193/hh-ru-apply), [hh.ru-clicker](https://github.com/Vlad9572324/hh.ru-clicker), [hhru](https://github.com/axisrow/hhru), [hh-ai-responder](https://github.com/s3rgeym/hh-ai-responder), [career-ops](https://github.com/career-ops-hq/career-ops), [proficiently-claude-skills](https://github.com/proficientlyjobs/proficiently-claude-skills), [stop-slop](https://github.com/hardikpandya/stop-slop), [infostyle-skill](https://github.com/artgas1/infostyle-skill), [plain-prose](https://github.com/dripips/plain-prose). Код из них не копировался.

Проект не связан с hh.ru (HeadHunter). Лицензия — [MIT](LICENSE).
