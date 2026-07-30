from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from aiohttp import web

import hero_reality_v184_1 as live1841
import hero_reality_v184_2 as reality1842


log = logging.getLogger(__name__)
MAX_OPERATIONS = 2500


async def _migrate_live_indexes(core: Any, db: Any) -> None:
    """Create the indexes used by the polling endpoint.

    The old live endpoint scanned the operation journals every few seconds.
    On a production database this could hold the request long enough for the
    WebView to remain in its initial loading state.
    """

    conn = db._require_connection()
    statements = (
        "CREATE INDEX IF NOT EXISTS idx_score_log_v1843_live "
        "ON score_log(chat_id, user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_influence_tx_v1843_live "
        "ON influence_transactions(chat_id, user_id, created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_v1842_cosmetics_live "
        "ON v1842_cosmetics(chat_id, user_id, equipped_at DESC)",
    )
    for statement in statements:
        try:
            await conn.execute(statement)
        except Exception:
            # An older installation may not have created one of the optional
            # tables yet. The endpoint remains usable without that index.
            log.exception("Reality 184.3 could not create live index")
    await conn.commit()


async def _load_operations_fast(
    core: Any,
    chat_id: int,
    user_id: int,
    since: int,
) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    operations: list[dict[str, Any]] = []

    try:
        cursor = await conn.execute(
            """
            SELECT delta AS amount, reason, created_at, 'score' AS operation_type
            FROM score_log
            WHERE chat_id = ? AND user_id = ? AND created_at >= ?
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (chat_id, user_id, since, MAX_OPERATIONS),
        )
        operations.extend(dict(row) for row in await cursor.fetchall())
    except Exception:
        log.exception("Reality 184.3 could not read score_log")

    try:
        columns = await live1841._table_columns(conn, "influence_transactions")
        amount_column = (
            "amount" if "amount" in columns else "delta" if "delta" in columns else None
        )
        if amount_column and {"chat_id", "user_id", "reason", "created_at"}.issubset(columns):
            type_expression = (
                "operation_type" if "operation_type" in columns else "'transaction'"
            )
            cursor = await conn.execute(
                f"""
                SELECT {amount_column} AS amount, reason, created_at,
                       {type_expression} AS operation_type
                FROM influence_transactions
                WHERE chat_id = ? AND user_id = ? AND created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (chat_id, user_id, since, MAX_OPERATIONS),
            )
            operations.extend(dict(row) for row in await cursor.fetchall())
    except Exception:
        log.exception("Reality 184.3 could not read influence_transactions")

    unique: dict[tuple[int, str, int], dict[str, Any]] = {}
    for raw in operations:
        item = {
            "amount": int(raw.get("amount") or 0),
            "reason": str(raw.get("reason") or "influence_change"),
            "created_at": int(raw.get("created_at") or 0),
            "operation_type": str(raw.get("operation_type") or "transaction"),
        }
        key = (item["amount"], item["reason"], item["created_at"])
        previous = unique.get(key)
        if previous is None or previous.get("operation_type") == "score":
            unique[key] = item
    return sorted(unique.values(), key=lambda item: int(item["created_at"]))


async def _load_cosmetics(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    try:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT cosmetic_type, cosmetic_key, source_item_key, equipped_at
            FROM v1842_cosmetics
            WHERE chat_id = ? AND user_id = ?
            ORDER BY equipped_at DESC
            """,
            (chat_id, user_id),
        )
        return {
            str(row["cosmetic_type"]): {
                "key": str(row["cosmetic_key"]),
                "source_item_key": str(row["source_item_key"]),
                "equipped_at": int(row["equipped_at"]),
            }
            for row in await cursor.fetchall()
        }
    except Exception:
        log.exception("Reality 184.3 could not read cosmetics")
        return {}


def _catalog() -> list[dict[str, Any]]:
    return [
        {
            "item_key": key,
            "title": item["title"],
            "description": item["description"],
            "price": int(item["price"]),
            "category": item["category"],
            "rarity": item["rarity"],
            "duration_seconds": 0,
        }
        for key, item in reality1842.COSMETIC_ITEMS.items()
    ]


async def _safe_live_state(core: Any, request: web.Request) -> web.Response:
    """Return a useful response even when one history source is unavailable."""

    user = live1841._authorized_user(core, request)
    chat_id = live1841._chat_id_from_request(request)
    user_id = int(user.id)
    player = await core.db.get_player(chat_id, user_id)
    if player is None:
        raise web.HTTPNotFound(text="Персонаж не найден в этой беседе.")

    now = int(time.time())
    try:
        operations = await asyncio.wait_for(
            _load_operations_fast(core, chat_id, user_id, now - 91 * 86400),
            timeout=3.5,
        )
        history_status = "ready"
    except asyncio.TimeoutError:
        operations = []
        history_status = "timeout"
        log.warning("Reality 184.3 history query timed out for chat=%s user=%s", chat_id, user_id)
    except Exception:
        operations = []
        history_status = "error"
        log.exception("Reality 184.3 history query failed")

    try:
        rank, total = await asyncio.wait_for(core.db.rank_of(chat_id, user_id), timeout=1.5)
    except Exception:
        rank, total = 1, 1

    role = core.role_by_points(int(player.points), int(rank) == 1)
    role_title, role_emoji = str(role.title), str(role.emoji)

    daily90 = live1841._series(
        operations,
        int(player.points),
        buckets=90,
        seconds_per_bucket=86400,
        now=now,
    )
    week_operations = [item for item in operations if int(item["created_at"]) >= now - 7 * 86400]
    earned_week = sum(max(0, int(item["amount"])) for item in week_operations)
    lost_week = sum(max(0, -int(item["amount"])) for item in week_operations)
    shop_spent = sum(
        max(0, -int(item["amount"]))
        for item in operations
        if str(item["reason"]).startswith("shop_")
    )
    interventions = sum(
        1 for item in operations if str(item["reason"]) == "intervention_cost"
    )
    max_balance = max(
        [int(player.points), *[int(item["balance"]) for item in daily90]],
        default=int(player.points),
    )

    try:
        cosmetics = await asyncio.wait_for(_load_cosmetics(core, chat_id, user_id), timeout=1.0)
    except Exception:
        cosmetics = {}

    payload = {
        "ok": True,
        "version": "184.3",
        "chat_id": chat_id,
        "updated_at": now,
        "history_status": history_status,
        "profile": {
            "balance": int(player.points),
            "role": role_title,
            "role_emoji": role_emoji,
            "rank": int(rank),
            "participants_total": int(total),
        },
        "series": {
            "24": live1841._series(
                operations,
                int(player.points),
                buckets=24,
                seconds_per_bucket=3600,
                now=now,
            ),
            "7": daily90[-7:],
            "30": daily90[-30:],
            "90": daily90,
        },
        "stats": {
            "current_balance": int(player.points),
            "rank": int(rank),
            "participants_total": int(total),
            "earned_week": int(earned_week),
            "lost_week": int(lost_week),
            "shop_spent": int(shop_spent),
            "interventions": int(interventions),
            "message_count": int(player.message_count),
            "max_balance": int(max_balance),
        },
        "transactions": [dict(item) for item in reversed(operations[-80:])],
        "cosmetics": cosmetics,
        "catalog_v1842": _catalog(),
    }
    return web.json_response(payload, headers={"Cache-Control": "no-store, max-age=0"})


def install_reality_v184_3(core: Any) -> None:
    if getattr(core, "_reality_v184_3_installed", False):
        return
    core._reality_v184_3_installed = True
    core.BOT_VERSION = "Reality 184.3 · Resilient Live Stats"

    original_connect = core.Database.connect

    async def connect_v184_3(self: Any) -> None:
        await original_connect(self)
        await _migrate_live_indexes(core, self)

    core.Database.connect = connect_v184_3

    # The Reality 184.2 route uses a lambda which resolves this module global
    # at request time, so replacing it here fixes the existing URL without
    # adding a duplicate aiohttp route.
    reality1842._live_state = lambda current_core, request: _safe_live_state(
        current_core, request
    )
