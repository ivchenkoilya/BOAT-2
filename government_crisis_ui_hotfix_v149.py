from __future__ import annotations

from typing import Any, Callable

import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 149 · Теневая казна"


def _with_crisis_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "crisis-v131.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v131/crisis-v131.css?v=149">\n</head>',
        )
    if "crisis-v131.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v131/crisis-v131.js?v=149"></script>\n</body>',
        )
    return source


def install_government_crisis_ui_hotfix_v149(core: Any) -> None:
    if getattr(core, "_government_crisis_ui_hotfix_v149_installed", False):
        return
    core._government_crisis_ui_hotfix_v149_installed = True
    core.GOVERNMENT_VERSION = VERSION

    # Capture the injector at installation time. At this point the mandate and
    # strict-role layers are already installed, so their assets remain present.
    previous_inject = luxury._inject_assets

    def inject_with_crisis(source: str) -> str:
        return _with_crisis_assets(previous_inject, source)

    luxury._inject_assets = inject_with_crisis

    original_state = gov._state

    async def state_with_visible_theft_controls(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION

        crisis_state = payload.get("crisis_v131")
        treasury = payload.get("treasury")
        balance = int(treasury.get("balance", 0)) if isinstance(treasury, dict) else 0

        if isinstance(crisis_state, dict):
            theft = crisis_state.get("theft")
            if isinstance(theft, dict):
                theft["treasury_balance"] = balance
                if balance < 10:
                    theft["can_attempt"] = False
                    theft["remaining"] = (
                        "в казне недостаточно средств — нужно минимум 10 влияния"
                    )

        return payload

    gov._state = state_with_visible_theft_controls
