from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 69 · Персональный оптимизатор"


def install_about_optimizer_v69(core: Any) -> None:
    if getattr(core, "_about_optimizer_v69_installed", False):
        return
    core._about_optimizer_v69_installed = True
    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        section = (
            "🧠 <b>ПЕРСОНАЛЬНЫЙ ОПТИМИЗАТОР СБОРОК</b>\n"
            "• заранее записанные оптимальные маршруты заменены серверным расчётом;\n"
            "• отдельно для каждой ветки перебираются все допустимые комбинации уровней;\n"
            "• учитываются текущие таланты, свободные очки, родители узлов, заблокированные финалы и специализация;\n"
            "• урон рассчитывается по последним рейдам, количеству атак и среднему урону;\n"
            "• влияние — по начислениям, сообщениям, реакциям, голосовым и заданиям;\n"
            "• защита — по обычным штрафам и потерям в конфликтах;\n"
            "• награды — по выигрышам, проигрышам и частоте игр;\n"
            "• показываются лучший маршрут без сброса и абсолютный максимум после полного сброса;\n"
            "• при недостатке статистики рекомендация помечается как предварительная.\n\n"
        )
        marker = "👐 <b>СВОБОДНЫЙ РЕЖИМ ДРЕВА</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 68 — добавлена отмена сборки, свободный режим и спокойное свечение рекомендуемого узла.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 69 — добавлен персональный перебор всех допустимых сборок по статистике каждого игрока.\n" + history,
                1,
            )
        return text

    core.about_bot_text = about_bot_text
