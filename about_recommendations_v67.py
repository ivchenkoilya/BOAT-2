from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 67 · Настоящие сборки"


def install_about_recommendations_v67(core: Any) -> None:
    if getattr(core, "_about_recommendations_v67_installed", False):
        return
    core._about_recommendations_v67_installed = True

    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        section = (
            "🧭 <b>ИСПРАВЛЕННЫЕ РЕКОМЕНДУЕМЫЕ СБОРКИ</b>\n"
            "• вместо четырёх одинаковых левых маршрутов добавлено восемь настоящих сборок;\n"
            "• у каждой основной ветки теперь есть отдельный левый и правый путь;\n"
            "• карточка показывает точную последовательность талантов и следующий необходимый уровень;\n"
            "• готовые узлы подсвечиваются золотым, весь маршрут — синим, следующий шаг — зелёным;\n"
            "• система сообщает, если финал заблокирован уже выбранной несовместимой специализацией.\n\n"
        )
        marker = "🌳 <b>МАСТЕРСТВО ДРЕВА</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 66 — улучшено древо, добавлены сборки, специализации, титулы и мгновенное обновление кнопки.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 67 — исправлены рекомендации: добавлены реальные левые и правые оптимальные маршруты.\n" + history,
                1,
            )
        return text

    core.about_bot_text = about_bot_text
