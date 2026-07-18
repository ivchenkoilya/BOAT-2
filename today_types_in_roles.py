from __future__ import annotations

import html
from typing import Any


def install_types_in_roles(core: Any) -> None:
    """Добавляет актуальный список типажей в конец раздела «Все роли и звания»."""
    if getattr(core, "_today_types_in_roles_installed", False):
        return
    core._today_types_in_roles_installed = True

    original_roles_text = core.roles_text

    def roles_text_with_today_types() -> str:
        lines = [
            original_roles_text(),
            "",
            "——————————",
            "",
            "🎭 <b>ТИПАЖИ ДНЯ</b> 🎭",
            "",
            "Типаж не зависит от роли и очков влияния. Он определяется в разделе «Кто ты сегодня?» и сохраняется на 24 часа.",
            "",
        ]
        for item in core.TODAY_TYPES:
            emoji = html.escape(str(item.get("emoji", "🎭")))
            title = html.escape(str(item.get("title", "Неизвестный")))
            description = html.escape(str(item.get("description", "")))
            lines.append(f"{emoji} <b>{title}</b>\n{description}")
        return "\n\n".join(lines)

    core.roles_text = roles_text_with_today_types
