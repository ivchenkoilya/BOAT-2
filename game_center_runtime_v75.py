from __future__ import annotations

import asyncio
import json
import secrets
import time
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

import game_center_v75 as base
import talent_system


_FINISH_LOCK = asyncio.Lock()


def install_game_center_runtime_v75(core: Any) -> None:
    if getattr(core, "_game_center_runtime_v75_installed", False):
        return
    core._game_center_runtime_v75_installed = True

    original_connect = core.Database.connect

    async def connect_with_games(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_daily_v75 (
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    game_key TEXT NOT NULL,
                    date_key TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    best_score INTEGER NOT NULL DEFAULT 0,
                    best_base_reward INTEGER NOT NULL DEFAULT 0,
                    total_paid INTEGER NOT NULL DEFAULT 0,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, user_id, game_key, date_key)
                );
                CREATE TABLE IF NOT EXISTS game_runs_v75 (
                    session_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    game_key TEXT NOT NULL,
                    seed INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    started_at INTEGER NOT NULL,
                    finished_at INTEGER,
                    score INTEGER NOT NULL DEFAULT 0,
                    base_reward INTEGER NOT NULL DEFAULT 0,
                    actual_reward INTEGER NOT NULL DEFAULT 0,
                    meta_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE INDEX IF NOT EXISTS idx_game_runs_v75_owner
                ON game_runs_v75 (chat_id, user_id, game_key, started_at DESC);
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_games

    async def payload(request: web.Request) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def parse_chat_id(start_param: str | None, data: dict[str, Any], request: web.Request) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(base.GAME_PREFIX):
            raw = raw[len(base.GAME_PREFIX):]
        else:
            raw = str(data.get("chat_id") or request.query.get("chat_id") or "")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    async def auth(request: web.Request) -> tuple[Any, int, dict[str, Any]]:
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации Telegram.")
        data = await payload(request)
        chat_id = parse_chat_id(start_param, data, request)
        if chat_id is None:
            raise ValueError("Не найдена беседа для начисления влияния.")
        if await core.db.get_player(chat_id, user.id) is None:
            raise PermissionError("Сначала открой игру из меню бота в нужной беседе.")
        return user, chat_id, data

    def error_response(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core.web.json_response({"ok": False, "reason": str(error)}, status=status)

    async def daily_rows(chat_id: int, user_id: int) -> dict[str, dict[str, int]]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT game_key, attempts, best_score, best_base_reward, total_paid
            FROM game_daily_v75
            WHERE chat_id = ? AND user_id = ? AND date_key = ?
            """,
            (chat_id, user_id, base._date_key()),
        )
        return {
            str(row["game_key"]): {
                "attempts": int(row["attempts"]),
                "best_score": int(row["best_score"]),
                "best_base_reward": int(row["best_base_reward"]),
                "total_paid": int(row["total_paid"]),
            }
            for row in await cursor.fetchall()
        }

    async def state_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await auth(request)
            player = await core.db.get_player(chat_id, user.id)
            rows = await daily_rows(chat_id, user.id)
            buffs = await talent_system.buffs_for(core.db, chat_id, user.id)
            games = {}
            for key, info in base.GAME_INFO.items():
                row = rows.get(key, {})
                attempts = int(row.get("attempts", 0))
                games[key] = {
                    **info,
                    "attempts": attempts,
                    "attempts_left": max(0, base.GAME_ATTEMPTS_PER_DAY - attempts),
                    "best_score": int(row.get("best_score", 0)),
                    "best_base_reward": int(row.get("best_base_reward", 0)),
                    "total_paid": int(row.get("total_paid", 0)),
                }
            return core.web.json_response(
                {
                    "ok": True,
                    "chat_id": chat_id,
                    "player": {
                        "user_id": user.id,
                        "name": user.full_name,
                        "points": int(player.points) if player else 0,
                    },
                    "games": games,
                    "buffs": buffs,
                    "daily_rule": (
                        "На каждую игру даётся три попытки в сутки. Влияние "
                        "начисляется только за улучшение лучшей награды дня."
                    ),
                }
            )
        except (PermissionError, ValueError) as error:
            return error_response(error)

    async def start_api(request: web.Request) -> web.Response:
        try:
            user, chat_id, data = await auth(request)
            game_key = str(data.get("game") or "")
            info = base.GAME_INFO.get(game_key)
            if info is None:
                raise ValueError("Неизвестная игра.")
            now = int(time.time())
            day = base._date_key()
            session_id = secrets.token_urlsafe(18)
            seed = secrets.randbelow(2_000_000_000) + 1
            conn = core.db._require_connection()
            async with core.db.lock:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO game_daily_v75 (
                        chat_id, user_id, game_key, date_key, attempts, updated_at
                    ) VALUES (?, ?, ?, ?, 0, ?)
                    """,
                    (chat_id, user.id, game_key, day, now),
                )
                cursor = await conn.execute(
                    """
                    SELECT attempts FROM game_daily_v75
                    WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                    """,
                    (chat_id, user.id, game_key, day),
                )
                row = await cursor.fetchone()
                attempts = int(row["attempts"]) if row else 0
                if attempts >= base.GAME_ATTEMPTS_PER_DAY:
                    await conn.commit()
                    raise ValueError("Все три попытки этой игры на сегодня использованы.")
                await conn.execute(
                    """
                    UPDATE game_daily_v75 SET attempts = attempts + 1, updated_at = ?
                    WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                    """,
                    (now, chat_id, user.id, game_key, day),
                )
                await conn.execute(
                    "UPDATE game_runs_v75 SET status = 'expired' WHERE status = 'active' AND started_at < ?",
                    (now - 600,),
                )
                await conn.execute(
                    """
                    INSERT INTO game_runs_v75 (
                        session_id, chat_id, user_id, game_key, seed, status, started_at
                    ) VALUES (?, ?, ?, ?, ?, 'active', ?)
                    """,
                    (session_id, chat_id, user.id, game_key, seed, now),
                )
                await conn.commit()
            return core.web.json_response(
                {
                    "ok": True,
                    "session_id": session_id,
                    "seed": seed,
                    "game": game_key,
                    "duration": int(info["duration"]),
                    "attempts_left": base.GAME_ATTEMPTS_PER_DAY - attempts - 1,
                }
            )
        except (PermissionError, ValueError) as error:
            return error_response(error)

    async def finish_api(request: web.Request) -> web.Response:
        session_id = ""
        reward_applied = False
        try:
            user, chat_id, data = await auth(request)
            session_id = str(data.get("session_id") or "")
            if not session_id:
                raise ValueError("Потеряна игровая сессия.")
            reported_score = base._int(data.get("score"), 0, 0, 1_000_000)
            stats = data.get("stats") if isinstance(data.get("stats"), dict) else {}
            now = int(time.time())
            conn = core.db._require_connection()

            async with _FINISH_LOCK:
                async with core.db.lock:
                    cursor = await conn.execute(
                        "SELECT * FROM game_runs_v75 WHERE session_id = ? LIMIT 1",
                        (session_id,),
                    )
                    run = await cursor.fetchone()
                    if run is None:
                        raise ValueError("Игровая сессия не найдена.")
                    if int(run["chat_id"]) != chat_id or int(run["user_id"]) != user.id:
                        raise PermissionError("Эта игровая сессия принадлежит другому игроку.")
                    if str(run["status"]) == "finished":
                        player = await core.db.get_player(chat_id, user.id)
                        return core.web.json_response(
                            {
                                "ok": True,
                                "already_finished": True,
                                "score": int(run["score"]),
                                "base_run_reward": int(run["base_reward"]),
                                "payable_base": int(run["base_reward"]),
                                "tree_bonus": max(0, int(run["actual_reward"]) - int(run["base_reward"])),
                                "actual_reward": int(run["actual_reward"]),
                                "balance": int(player.points) if player else 0,
                                "message": "Этот результат уже был сохранён.",
                            }
                        )
                    if str(run["status"]) != "active":
                        raise ValueError("Эта игровая сессия уже закрыта.")
                    elapsed = now - int(run["started_at"])
                    if elapsed < 8:
                        raise ValueError("Забег завершён слишком быстро и не засчитан.")
                    if elapsed > 300:
                        raise ValueError("Игровая сессия устарела.")
                    game_key = str(run["game_key"])
                    if game_key not in base.GAME_INFO:
                        raise ValueError("Повреждён тип игры.")
                    limit = min(300, elapsed * (8 if game_key == "rooftop" else 5) + (40 if game_key == "rooftop" else 50))
                    score = min(reported_score, limit, 300)
                    run_reward = base._base_reward(game_key, score)
                    cursor = await conn.execute(
                        """
                        SELECT best_score, best_base_reward FROM game_daily_v75
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (chat_id, user.id, game_key, base._date_key()),
                    )
                    daily = await cursor.fetchone()
                    previous_score = int(daily["best_score"]) if daily else 0
                    previous_reward = int(daily["best_base_reward"]) if daily else 0
                    payable = max(0, run_reward - previous_reward)
                    await conn.execute(
                        "UPDATE game_runs_v75 SET status = 'resolving' WHERE session_id = ?",
                        (session_id,),
                    )
                    await conn.commit()

                actual = 0
                tree_bonus = 0
                player = await core.db.get_player(chat_id, user.id)
                if payable > 0:
                    before, player = await core.db.add_points_with_balance(
                        chat_id,
                        user.id,
                        payable,
                        f"game_influence_hunt_{game_key}",
                    )
                    actual = int(player.points) - int(before)
                    tree_bonus = max(0, actual - payable)
                    reward_applied = True

                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE game_daily_v75
                        SET best_score = MAX(best_score, ?),
                            best_base_reward = MAX(best_base_reward, ?),
                            total_paid = total_paid + ?, updated_at = ?
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (score, run_reward, actual, now, chat_id, user.id, game_key, base._date_key()),
                    )
                    await conn.execute(
                        """
                        UPDATE game_runs_v75
                        SET status = 'finished', finished_at = ?, score = ?,
                            base_reward = ?, actual_reward = ?, meta_json = ?
                        WHERE session_id = ?
                        """,
                        (
                            now,
                            score,
                            payable,
                            actual,
                            json.dumps(stats, ensure_ascii=False)[:4000],
                            session_id,
                        ),
                    )
                    await conn.commit()

                if player is None:
                    player = await core.db.get_player(chat_id, user.id)
                return core.web.json_response(
                    {
                        "ok": True,
                        "game": game_key,
                        "score": score,
                        "previous_best_score": previous_score,
                        "base_run_reward": run_reward,
                        "previous_best_reward": previous_reward,
                        "payable_base": payable,
                        "tree_bonus": tree_bonus,
                        "actual_reward": actual,
                        "balance": int(player.points) if player else 0,
                        "new_best": score > previous_score,
                        "message": (
                            "Новый лучший результат и влияние начислены."
                            if payable > 0
                            else "Награда дня не улучшилась, поэтому влияние повторно не начислено."
                        ),
                    }
                )
        except (PermissionError, ValueError) as error:
            return error_response(error)
        except Exception:
            if session_id and not reward_applied:
                try:
                    conn = core.db._require_connection()
                    async with core.db.lock:
                        await conn.execute(
                            "UPDATE game_runs_v75 SET status = 'active' WHERE session_id = ? AND status = 'resolving'",
                            (session_id,),
                        )
                        await conn.commit()
                except Exception:
                    pass
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось сохранить результат. Попробуй ещё раз."},
                status=500,
            )

    def file_response(path: Any) -> web.FileResponse:
        return core.web.FileResponse(
            path,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                "Pragma": "no-cache",
                "Expires": "0",
                "X-Game-Center": "reality-75",
            },
        )

    async def games_index(_: web.Request) -> web.StreamResponse:
        return file_response(base.GAME_DIR / "index.html")

    async def rooftop_index(_: web.Request) -> web.StreamResponse:
        return file_response(base.GAME_DIR / "rooftop" / "index.html")

    async def heist_index(_: web.Request) -> web.StreamResponse:
        return file_response(base.GAME_DIR / "heist" / "index.html")

    original_start_server = core.start_webapp_server

    async def start_server_with_games(bot: Any):
        previous_application = core.web.Application

        def application_factory(*args: Any, **kwargs: Any):
            app = previous_application(*args, **kwargs)
            app.router.add_get("/games", games_index)
            app.router.add_get("/games/", games_index)
            app.router.add_get("/games/index.html", games_index)
            app.router.add_get("/games/rooftop", rooftop_index)
            app.router.add_get("/games/rooftop/", rooftop_index)
            app.router.add_get("/games/rooftop/index.html", rooftop_index)
            app.router.add_get("/games/heist", heist_index)
            app.router.add_get("/games/heist/", heist_index)
            app.router.add_get("/games/heist/index.html", heist_index)
            app.router.add_post("/games/api/state", state_api)
            app.router.add_post("/games/api/start", start_api)
            app.router.add_post("/games/api/finish", finish_api)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = previous_application

    core.start_webapp_server = start_server_with_games

    original_commands = core.group_bot_commands

    def group_commands_with_games() -> list[BotCommand]:
        commands = original_commands()
        if any(item.command == "games" for item in commands):
            return commands
        index = next(
            (i + 1 for i, item in enumerate(commands) if item.command == "talents"),
            len(commands),
        )
        commands.insert(index, BotCommand(command="games", description="Охота за влиянием"))
        return commands

    core.group_bot_commands = group_commands_with_games

    def game_link(chat_id: int) -> str:
        return base._game_link(core, chat_id)

    async def send_card(message: Message) -> None:
        if not message.from_user:
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        link = game_link(int(message.chat.id))
        if not link:
            await message.answer("⚠️ Адрес Mini App не настроен.")
            return
        await message.answer(
            "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
            "🌃 Бег по крышам — свайпы, прыжки и сбор влияния.\n"
            "🏛 Ограбление хранилища — сейфы, охрана, тревога и побег.\n\n"
            "У каждой игры по <b>3 попытки в сутки</b>. Добыча начисляется "
            "в баланс этой беседы с учётом древа знаний.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎮 ОТКРЫТЬ ИГРОВОЙ ЦЕНТР", url=link)]
                ]
            ),
        )

    @core.router.message(Command("games", "hunt"))
    async def cmd_games(message: Message) -> None:
        if not await core.require_group_command(message, "Охота за влиянием"):
            return
        await send_card(message)

    original_specs = core.inline_menu_specs

    def specs_with_games(user: Any) -> list[dict[str, Any]]:
        specs = original_specs(user)
        if any(str(item.get("result_id", "")).startswith("games_menu:") for item in specs):
            return specs
        card = {
            "kind": "static",
            "result_id": f"games_menu:{user.id}:{secrets.token_hex(3)}",
            "title": "🎮 Охота за влиянием 🎮",
            "description": "Бег по крышам и ограбление хранилища",
            "message_text": (
                "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
                "Игровой центр готовит вход для этой беседы…\n"
                f"<tg-spoiler>#INFLUENCE_GAMES_{user.id}</tg-spoiler>"
            ),
        }
        index = next(
            (i for i, item in enumerate(specs) if str(item.get("action", "")) == "about"),
            len(specs),
        )
        specs.insert(index, card)
        return specs

    core.inline_menu_specs = specs_with_games

    original_dispatch = core.maybe_handle_inline_dispatch

    async def dispatch_with_games(message: Any, bot: Any) -> bool:
        body = message.text or message.caption or ""
        match = base.GAME_MARKER.search(body)
        if match is None:
            return await original_dispatch(message, bot)
        owner_id = int(match.group(1))
        if message.from_user is None or int(message.from_user.id) != owner_id:
            return False
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = game_link(chat_id)
        text = (
            "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
            "🌃 <b>Бег по крышам</b> — автоматический бег, свайпы, препятствия и серии.\n"
            "🏛 <b>Ограбление хранилища</b> — свободное движение, сейфы и охрана.\n\n"
            "Собранная добыча связана с влиянием именно этой беседы."
        )
        markup = (
            InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎮 ОТКРЫТЬ ИГРОВОЙ ЦЕНТР", url=link)]
                ]
            )
            if link
            else None
        )
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.message_id,
                text=text,
                reply_markup=markup,
            )
        except Exception:
            await message.answer(text, reply_markup=markup)
        return True

    core.maybe_handle_inline_dispatch = dispatch_with_games
