from __future__ import annotations

import json
import time
from typing import Any

import government_institutions_v128 as institutions


VERSION = "Reality 137 · Лимит ставок ЦБ до миллиона"
MAX_WAGER = 1_000_000


async def _force_million_policy(core: Any, chat_id: int) -> None:
    conn = core.db._require_connection()
    now = int(time.time())
    async with core.db.lock:
        await conn.execute(
            """
            INSERT OR IGNORE INTO government_policy_v128(
                chat_id, transfer_fee_bps, max_wager, loan_limit,
                economic_mode, mode_ends_at, emergency_until, updated_at
            ) VALUES(?, 0, ?, 1000000, 'stability', 0, 0, ?)
            """,
            (int(chat_id), MAX_WAGER, now),
        )
        await conn.execute(
            """
            UPDATE government_policy_v128
            SET max_wager = ?, updated_at = ?
            WHERE chat_id = ? AND max_wager <> ?
            """,
            (MAX_WAGER, now, int(chat_id), MAX_WAGER),
        )
        await conn.commit()


def install_central_bank_wager_limit_v137(core: Any) -> None:
    if getattr(core, "_central_bank_wager_limit_v137_installed", False):
        return
    core._central_bank_wager_limit_v137_installed = True
    core.CENTRAL_BANK_WAGER_VERSION = VERSION
    core.BOT_GAME_MAX_STAKE = MAX_WAGER
    institutions.VERSION = VERSION

    for action in institutions.OFFICE_ACTIONS.get("central_bank", []):
        if action.get("key") == "economic_policy":
            action["hint"] = "Комиссия, ставки до 1 000 000 и лимиты займов"

    original_connect = core.Database.connect

    async def connect_with_million_wager(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                """
                UPDATE government_policy_v128
                SET max_wager = ?, updated_at = ?
                WHERE max_wager <> ?
                """,
                (MAX_WAGER, int(time.time()), MAX_WAGER),
            )
            await conn.commit()

    core.Database.connect = connect_with_million_wager

    original_policy = institutions._policy

    async def policy_with_million_wager(
        core_value: Any,
        chat_id: int,
    ) -> dict[str, Any]:
        await _force_million_policy(core_value, int(chat_id))
        policy = dict(await original_policy(core_value, int(chat_id)))
        if (
            not bool(policy.get("emergency"))
            and str(policy.get("economic_mode") or "stability")
            in {"stability", "growth", "inflation"}
        ):
            policy["max_wager"] = MAX_WAGER
        return policy

    institutions._policy = policy_with_million_wager

    @core.web.middleware
    async def force_million_in_policy_action(request: Any, handler: Any):
        if (
            request.method.upper() == "POST"
            and str(request.path or "").rstrip("/")
            == "/government-v128/api/action"
        ):
            try:
                data = await request.json()
            except Exception:
                data = None
            if isinstance(data, dict) and str(data.get("action") or "") == "economic_policy":
                data["max_wager"] = MAX_WAGER
                request._read_bytes = json.dumps(
                    data,
                    ensure_ascii=False,
                ).encode("utf-8")
        return await handler(request)

    previous_application = core.web.Application

    def application_with_million_wager(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, force_million_in_policy_action)
        return application

    core.web.Application = application_with_million_wager
