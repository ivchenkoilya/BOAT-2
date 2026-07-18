from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 68 · Свободный режим древа"


def install_about_recommendations_v68(core: Any) -> None:
    if getattr(core, "_about_recommendations_v68_installed", False):
        return
    core._about_recommendations_v68_installed = True

    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        section = (
            "👐 <b>СВОБОДНЫЙ РЕЖИМ ДРЕВА</b>\n"
            "• активную рекомендуемую сборку теперь можно убрать одной кнопкой;\n"
            "• после отмены маршруты и следующий шаг полностью перестают подсвечиваться;\n"
            "• пользователь снова выбирает таланты самостоятельно без подсказок;\n"
            "• следующий рекомендуемый узел больше не двигается и не дёргается — он только постоянно светится.\n\n"
        )
        marker = "🧭 <b>ИСПРАВЛЕННЫЕ РЕКОМЕНДУЕМЫЕ СБОРКИ</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 67 — исправлены рекомендации: добавлены реальные левые и правые оптимальные маршруты.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 68 — добавлена отмена сборки, свободный режим и спокойное свечение рекомендуемого узла.\n" + history,
                1,
            )
        return text

    core.about_bot_text = about_bot_text
