from __future__ import annotations

from typing import Any

from aiogram.filters import Command
from aiogram.types import Message


def install_command_hub_compat_v121(core: Any) -> None:
    if getattr(core, "_command_hub_compat_v121_installed", False):
        return
    core._command_hub_compat_v121_installed = True

    @core.router.message(Command("abilities"))
    async def cmd_abilities_hidden_v121(message: Message) -> None:
        if not core.is_group(message):
            return
        await message.answer(core.role_ability_info_text())

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_abilities_hidden_v121"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
