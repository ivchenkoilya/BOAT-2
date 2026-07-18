import asyncio

import main as core
from talent_expansion import install_expansion
from talent_explanations import install_explanations
from talent_menu import install_menu
from talent_system import install
from talent_ux import install_ux
from today_types_expansion import install_today_types

install_today_types(core)
install_expansion(core)
install(core)
install_menu(core)
install_ux(core)
install_explanations(core)

# В main.py есть общий обработчик F.text, зарегистрированный раньше расширения.
# Переносим новые команды в начало списка, чтобы /talents, /buffs и
# /chat_buffs не поглощались общим обработчиком сообщений.
_priority_names = {"cmd_talents", "cmd_buffs", "cmd_chat_buffs"}
_handlers = core.router.message.handlers
_priority = [
    handler
    for handler in _handlers
    if getattr(handler.callback, "__name__", "") in _priority_names
]
_handlers[:] = _priority + [handler for handler in _handlers if handler not in _priority]

if __name__ == "__main__":
    asyncio.run(core.main())
