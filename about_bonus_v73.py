from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 73 · Видимый бонус древа"
SAFE_LIMIT = 3900


def install_about_bonus_v73(core: Any) -> None:
    if getattr(core, "_about_bonus_v73_installed", False):
        return
    core._about_bonus_v73_installed = True

    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        # Предыдущая компактная карточка уже безопасна по длине. Добавляем только
        # небольшую актуальную секцию, не возвращая длинную историю старых патчей.
        version_start = "Версия: <b>"
        if version_start in text:
            start = text.find(version_start)
            end = text.find("</b>", start)
            if end >= 0:
                text = text[:start] + f"Версия: <b>{core.BOT_VERSION}</b>" + text[end + 4:]

        section = (
            "🍀 <b>УДАЧА И ПРОЗРАЧНЫЕ НАГРАДЫ</b>\n"
            "• ветка «Награды» переименована в понятную ветку «Удача»;\n"
            "• после увеличения влияния, Шара судьбы, игр, заданий и других начислений "
            "бот показывает процент усиления от древа;\n"
            "• отдельно видны базовая награда, добавленные талантами очки и итог;\n"
            "• случайные редкие бонусы и особые таланты отмечаются отдельной строкой;\n"
            "• отображение не начисляет очки повторно, а объясняет уже применённый сервером результат.\n\n"
        )
        marker = "⚡ <b>СТАБИЛЬНАЯ ПРОКАЧКА ДРЕВА</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 72 — исправлен раздел «О боте»: карточка больше не превышает лимит Telegram.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 73 — бонусы древа теперь показываются под каждым подходящим начислением.\n" + history,
                1,
            )
        if len(text) <= SAFE_LIMIT:
            return text
        return (
            "👁 <b>О БОТЕ «ГЛАВНЫЙ ГЕРОЙ»</b> 👁\n"
            f"Версия: <b>{core.BOT_VERSION}</b>\n\n"
            "Социальная RPG про влияние, роли, задания, игры, рейды и древо знаний.\n\n"
            "🍀 Ветка наград теперь называется «Удача». После игровых и других "
            "положительных начислений бот показывает базовую награду, процент древа, "
            "добавленные талантами очки и итог.\n\n"
            "🚀 Идеи и ошибки можно отправлять через раздел <b>«Развить бота»</b>."
        )

    core.about_bot_text = about_bot_text
