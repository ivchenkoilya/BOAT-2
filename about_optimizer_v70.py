from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 70 · Быстрый оптимизатор"


def install_about_optimizer_v70(core: Any) -> None:
    if getattr(core, "_about_optimizer_v70_installed", False):
        return
    core._about_optimizer_v70_installed = True
    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        section = (
            "⚡ <b>БЫСТРЫЙ ОПТИМИЗАТОР</b>\n"
            "• загрузка древа и прокачка больше не ждут полного перебора сборок;\n"
            "• сервер сразу возвращает рабочее древо и предварительный персональный маршрут;\n"
            "• точный перебор всех допустимых комбинаций выполняется в фоне;\n"
            "• готовый точный результат автоматически подставляется без закрытия Mini App;\n"
            "• одновременно выполняется только один тяжёлый расчёт, чтобы бот не зависал под нагрузкой;\n"
            "• добавлен предел ожидания ответа, поэтому кнопка не останется навечно в состоянии «Прокачиваем».\n\n"
        )
        marker = "🧠 <b>ПЕРСОНАЛЬНЫЙ ОПТИМИЗАТОР СБОРОК</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 69 — добавлен персональный перебор всех допустимых сборок по статистике каждого игрока.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 70 — точный оптимизатор перенесён в фон, исправлены зависание загрузки и кнопки прокачки.\n" + history,
                1,
            )
        return text

    core.about_bot_text = about_bot_text
