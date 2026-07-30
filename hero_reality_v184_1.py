from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from aiohttp import web
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats,
)
from aiogram.utils.web_app import safe_parse_webapp_init_data


LIVE_ROUTE = "/influence-shop-v184/api/live-v1841"


def _group_commands() -> list[BotCommand]:
    return [
        BotCommand(command="shop", description="Магазин влияния"),
        BotCommand(command="hero", description="Мой персонаж и главное меню"),
        BotCommand(command="games", description="Игры и развлечения"),
        BotCommand(command="stats", description="Живая статистика влияния"),
        BotCommand(command="story", description="Сюжет беседы"),
        BotCommand(command="achievements", description="Тайные достижения"),
        BotCommand(command="relationships", description="Отношения участников"),
        BotCommand(command="top", description="Рейтинг текущей беседы"),
        BotCommand(command="boss", description="Центр Вселенной"),
        BotCommand(command="secret", description="Получить тайное задание"),
        BotCommand(command="sabotage", description="Начать саботаж"),
        BotCommand(command="impeachment", description="Начать импичмент"),
        BotCommand(command="feedback", description="Сообщить об ошибке или предложить идею"),
        BotCommand(command="help", description="Все команды и механики"),
    ]


def _private_commands() -> list[BotCommand]:
    return [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="shop", description="Магазин влияния"),
        BotCommand(command="hero", description="Мой персонаж"),
        BotCommand(command="stats", description="Статистика влияния"),
        BotCommand(command="achievements", description="Тайные достижения"),
        BotCommand(command="help", description="Помощь и команды"),
    ]


def _chat_id_from_request(request: web.Request) -> int:
    raw = str(request.query.get("chat_id") or request.query.get("start_param") or "")
    if not raw:
        raise web.HTTPBadRequest(text="Не передана беседа.")
    match = re.search(r"-?\d+", raw.replace("shop_", ""))
    if not match:
        raise web.HTTPBadRequest(text="Некорректный ID беседы.")
    return int(match.group(0))


def _authorized_user(core: Any, request: web.Request) -> Any:
    init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
    if not init_data:
        init_data = str(request.query.get("init_data") or "").strip()
    if init_data:
        try:
            parsed = safe_parse_webapp_init_data(core.BOT_TOKEN, init_data)
            if parsed.user is not None:
                return parsed.user
        except Exception as error:
            raise web.HTTPUnauthorized(text="Telegram Mini App не прошла проверку.") from error
    if bool(getattr(core, "WEBAPP_DEV_MODE", False)):
        dev_id = int(request.query.get("user_id") or 0)
        if dev_id:
            return type("DevUser", (), {"id": dev_id})()
    raise web.HTTPUnauthorized(text="Открой приложение через Telegram.")


async def _table_columns(conn: Any, table: str) -> set[str]:
    cursor = await conn.execute(f"PRAGMA table_info({table})")
    return {str(row["name"]) for row in await cursor.fetchall()}


async def _load_operations(core: Any, chat_id: int, user_id: int, since: int) -> list[dict[str, Any]]:
    conn = core.db._require_connection()
    operations: list[dict[str, Any]] = []

    score_cursor = await conn.execute(
        """
        SELECT delta AS amount, reason, created_at
        FROM score_log
        WHERE chat_id = ? AND user_id = ? AND created_at >= ?
        ORDER BY created_at ASC, id ASC
        """,
        (chat_id, user_id, since),
    )
    for row in await score_cursor.fetchall():
        operations.append(
            {
                "amount": int(row["amount"] or 0),
                "reason": str(row["reason"] or "influence_change"),
                "created_at": int(row["created_at"] or 0),
                "operation_type": "score",
            }
        )

    tables_cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='influence_transactions'"
    )
    if await tables_cursor.fetchone():
        columns = await _table_columns(conn, "influence_transactions")
        amount_col = "amount" if "amount" in columns else "delta" if "delta" in columns else None
        if amount_col and {"chat_id", "user_id", "reason", "created_at"}.issubset(columns):
            type_expr = "operation_type" if "operation_type" in columns else "'transaction'"
            tx_cursor = await conn.execute(
                f"""
                SELECT {amount_col} AS amount, reason, created_at, {type_expr} AS operation_type
                FROM influence_transactions
                WHERE chat_id = ? AND user_id = ? AND created_at >= ?
                ORDER BY created_at ASC
                """,
                (chat_id, user_id, since),
            )
            for row in await tx_cursor.fetchall():
                operations.append(
                    {
                        "amount": int(row["amount"] or 0),
                        "reason": str(row["reason"] or "influence_change"),
                        "created_at": int(row["created_at"] or 0),
                        "operation_type": str(row["operation_type"] or "transaction"),
                    }
                )

    # Один и тот же новый платёж иногда присутствует и в score_log, и в
    # influence_transactions. Оставляем одну операцию с одинаковыми данными.
    unique: dict[tuple[int, str, int], dict[str, Any]] = {}
    for item in operations:
        key = (int(item["amount"]), str(item["reason"]), int(item["created_at"]))
        old = unique.get(key)
        if old is None or old.get("operation_type") == "score":
            unique[key] = item
    return sorted(unique.values(), key=lambda item: int(item["created_at"]))


def _series(
    operations: list[dict[str, Any]],
    current_balance: int,
    *,
    buckets: int,
    seconds_per_bucket: int,
    now: int,
) -> list[dict[str, Any]]:
    end = (now // seconds_per_bucket + 1) * seconds_per_bucket
    start = end - buckets * seconds_per_bucket
    relevant = [item for item in operations if int(item["created_at"]) >= start]
    balance = current_balance - sum(int(item["amount"]) for item in relevant)
    result: list[dict[str, Any]] = []
    index = 0
    for bucket in range(buckets):
        bucket_start = start + bucket * seconds_per_bucket
        bucket_end = bucket_start + seconds_per_bucket
        delta = earned = lost = 0
        while index < len(relevant) and int(relevant[index]["created_at"]) < bucket_end:
            amount = int(relevant[index]["amount"])
            delta += amount
            if amount >= 0:
                earned += amount
            else:
                lost += abs(amount)
            index += 1
        balance += delta
        dt = datetime.fromtimestamp(bucket_start, tz=timezone.utc)
        label = dt.strftime("%H:%M") if seconds_per_bucket < 86400 else dt.strftime("%d.%m")
        result.append(
            {
                "ts": bucket_start,
                "label": label,
                "balance": balance,
                "delta": delta,
                "earned": earned,
                "lost": lost,
            }
        )
    if result:
        result[-1]["balance"] = current_balance
    return result


async def _live_state(core: Any, request: web.Request) -> web.Response:
    user = _authorized_user(core, request)
    chat_id = _chat_id_from_request(request)
    player = await core.db.get_player(chat_id, int(user.id))
    if player is None:
        raise web.HTTPNotFound(text="Персонаж не найден в этой беседе.")

    now = int(time.time())
    since = now - 91 * 86400
    operations = await _load_operations(core, chat_id, int(user.id), since)
    rank, total = await core.db.rank_of(chat_id, int(user.id))
    role = core.role_by_points(int(player.points), rank == 1)
    role_title = str(role.title)
    role_emoji = str(role.emoji)

    temporary_fn = getattr(core, "temporary_hero_day_user_id", None)
    if temporary_fn is not None:
        try:
            if int(await temporary_fn(chat_id) or 0) == int(user.id):
                role_title, role_emoji = "Временный Главный герой", "🌟👑"
        except Exception:
            pass
    sabotage_fn = getattr(core.db, "active_sabotage_usurper_ids", None)
    if sabotage_fn is not None:
        try:
            if int(user.id) in set(await sabotage_fn(chat_id)):
                role_title, role_emoji = "Саботажный Главный герой", "💣👑"
        except Exception:
            pass

    week_start = now - 7 * 86400
    week_ops = [item for item in operations if int(item["created_at"]) >= week_start]
    earned_week = sum(max(0, int(item["amount"])) for item in week_ops)
    lost_week = sum(max(0, -int(item["amount"])) for item in week_ops)
    shop_spent = sum(
        max(0, -int(item["amount"]))
        for item in operations
        if str(item["reason"]).startswith("shop_")
    )
    interventions = sum(1 for item in operations if str(item["reason"]) == "intervention_cost")

    daily90 = _series(operations, int(player.points), buckets=90, seconds_per_bucket=86400, now=now)
    max_balance = max([int(player.points), *[int(item["balance"]) for item in daily90]])
    transactions = [dict(item) for item in reversed(operations[-80:])]

    payload = {
        "ok": True,
        "chat_id": chat_id,
        "updated_at": now,
        "profile": {
            "balance": int(player.points),
            "role": role_title,
            "role_emoji": role_emoji,
            "rank": int(rank),
            "participants_total": int(total),
        },
        "series": {
            "24": _series(operations, int(player.points), buckets=24, seconds_per_bucket=3600, now=now),
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
        "transactions": transactions,
    }
    return web.json_response(payload, headers={"Cache-Control": "no-store"})


def install_reality_v184_1(core: Any) -> None:
    if getattr(core, "_reality_v184_1_installed", False):
        return
    core._reality_v184_1_installed = True
    core.BOT_VERSION = "Reality 184.1 · Live Influence"

    core.group_bot_commands = _group_commands
    core.private_bot_commands = _private_commands

    original_set_commands = core.set_commands

    async def set_commands_v184_1(bot: Any) -> None:
        # Telegram кэширует slash-список. Явно очищаем все scope перед новой
        # регистрацией, чтобы старые команды не оставались в клиенте.
        for scope in (None, BotCommandScopeAllGroupChats(), BotCommandScopeAllPrivateChats()):
            try:
                if scope is None:
                    await bot.delete_my_commands()
                else:
                    await bot.delete_my_commands(scope=scope)
            except Exception:
                pass
        await original_set_commands(bot)

    core.set_commands = set_commands_v184_1

    original_application = core.web.Application

    def application_v184_1(*args: Any, **kwargs: Any) -> web.Application:
        app = original_application(*args, **kwargs)
        app.router.add_get(LIVE_ROUTE, lambda request: _live_state(core, request))
        return app

    core.web.Application = application_v184_1
