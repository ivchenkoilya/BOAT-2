from __future__ import annotations

from typing import Any


ABOUT_VERSION = "Reality 76 · Админ-центр"


def install_about_admin_v76(core: Any) -> None:
    if getattr(core, "_about_admin_v76_installed", False):
        return
    core._about_admin_v76_installed = True
    previous_about = core.about_bot_text
    core.BOT_VERSION = ABOUT_VERSION

    def about_bot_text() -> str:
        text = previous_about()
        latest = (
            "Reality 76 — новый админ-центр: исправлен выбор участников, "
            "подключена актуальная шкала ролей, добавлены игровые сессии, "
            "попытки, рекорды и аннулирование подозрительных результатов.\n"
        )
        marker = "📜 <b>ПОСЛЕДНИЕ ВЕРСИИ</b>\n"
        if latest not in text and marker in text:
            text = text.replace(marker, marker + latest, 1)
        return text

    core.about_bot_text = about_bot_text
