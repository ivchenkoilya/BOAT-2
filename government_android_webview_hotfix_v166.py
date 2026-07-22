from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

import government_mandate_luxury_v147 as luxury
import government_treasury_management_v164 as treasury
import government_treasury_requests_v165 as requests
import government_v127 as gov


VERSION = "Reality 166 · Стабильная загрузка казны Android"


def _memoize_schema(
    original: Callable[[Any], Awaitable[None]],
) -> Callable[[Any], Awaitable[None]]:
    ready = False
    lock = asyncio.Lock()

    async def ensure_once(core: Any) -> None:
        nonlocal ready
        if ready:
            return
        async with lock:
            if ready:
                return
            await original(core)
            ready = True

    return ensure_once


def install_government_android_webview_hotfix_v166(core: Any) -> None:
    if getattr(core, "_government_android_webview_hotfix_v166_installed", False):
        return
    core._government_android_webview_hotfix_v166_installed = True

    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    # DDL больше не выполняется при каждом параллельном запросе состояния.
    # На Android это устраняет конкурирующие commit во время первого открытия Mini App.
    treasury._ensure_schema = _memoize_schema(treasury._ensure_schema)
    requests._ensure_schema = _memoize_schema(requests._ensure_schema)

    previous_inject = luxury._inject_assets

    def inject_android_hotfix(source: str) -> str:
        source = previous_inject(source)
        replacements = {
            "treasury-management-v164.css?v=164": "treasury-management-v164.css?v=166",
            "treasury-management-v164.js?v=164": "treasury-management-v164.js?v=166",
            "treasury-requests-v165.css?v=165": "treasury-requests-v165.css?v=166",
            "treasury-requests-v165.js?v=165": "treasury-requests-v165.js?v=166",
        }
        for old, new in replacements.items():
            source = source.replace(old, new)
        return source

    luxury._inject_assets = inject_android_hotfix
