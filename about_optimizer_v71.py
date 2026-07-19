from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 71 · Мгновенная прокачка"


def install_about_optimizer_v71(core: Any) -> None:
    if getattr(core, "_about_optimizer_v71_installed", False):
        return
    core._about_optimizer_v71_installed = True
    previous = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous()
        section = (
            "⚡ <b>МГНОВЕННАЯ ПРОКАЧКА ДРЕВА</b>\n"
            "• тяжёлый фоновый перебор полностью убран из рабочего процесса бота;\n"
            "• загрузка дерева и покупка таланта больше не запускают CPU-задачу;\n"
            "• персональные рекомендации рассчитываются быстрым ограниченным алгоритмом и кэшируются;\n"
            "• автоматический опрос сервера каждую секунду отключён;\n"
            "• при сетевой ошибке кнопка разблокируется и не остаётся в состоянии «Прокачиваем».\n\n"
        )
        marker = "🧠 <b>ПЕРСОНАЛЬНЫЙ ОПТИМИЗАТОР СБОРОК</b>\n"
        if marker in text:
            text = text.replace(marker, section + marker, 1)
        history = "Reality 70 — точный оптимизатор перенесён в фон, а загрузка и прокачка больше не ждут полный перебор.\n"
        if history in text:
            text = text.replace(
                history,
                "Reality 71 — фоновый перебор отключён полностью, прокачка и загрузка переведены на быстрый кэшируемый расчёт.\n" + history,
                1,
            )
        return text

    core.about_bot_text = about_bot_text
