from __future__ import annotations

import asyncio
import html
import json
import re
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

import talent_system


GAME_DIR = Path(__file__).resolve().parent / "games"
GAME_PREFIX = "games_"
GAME_MARKER = re.compile(r"#INFLUENCE_GAMES_(\d+)")
GAME_ATTEMPTS_PER_DAY = 3
GAME_INFO = {
    "rooftop": {
        "title": "Бег по крышам",
        "emoji": "🌃",
        "duration": 60,
        "max_reward": 100,
    },
    "heist": {
        "title": "Ограбление хранилища",
        "emoji": "🏛",
        "duration": 90,
        "max_reward": 120,
    },
}
_FINISH_LOCK = asyncio.Lock()


def _date_key() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _int(value: Any, default: int = 0, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _base_reward(game_key: str, score: int) -> int:
    value = max(0, int(score))
    if game_key == "rooftop":
        if value <= 0:
            return 0
        if value < 30:
            return 15
        if value < 70:
            return 30
        if value < 120:
            return 50
        if value < 180:
            return 75
        return 100
    if value <= 0:
        return 0
    if value < 25:
        return 15
    if value < 60:
        return 35
    if value < 110:
        return 60
    if value < 170:
        return 90
    return 120


def _game_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp={GAME_PREFIX}{chat_id}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/games/?chat_id={chat_id}"
    return ""


def install_game_center_v75(core: Any) -> None:
    if getattr(core, "_game_center_v75_installed", False):
        return
    core._game_center_v75_installed = True

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

    async def _payload(request: web.Request) -> dict[str, Any]:
        try:
            value = await request.json()
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}

    def _parse_chat_id(start_param: str | None, payload: dict[str, Any], request: web.Request) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(GAME_PREFIX):
            raw = raw[len(GAME_PREFIX):]
        else:
            raw = str(payload.get("chat_id") or request.query.get("chat_id") or "")
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    async def _auth(request: web.Request) -> tuple[Any, int, dict[str, Any]]:
        user, reason = core._webapp_auth(request)
        if user is None:
            raise PermissionError(reason or "Нет авторизации Telegram.")
        payload = await _payload(request)
        chat_id = _parse_chat_id(reason, payload, request)
        if chat_id is None:
            # Во втором элементе _webapp_auth возвращается start_param при успехе.
            _, start_param = core._webapp_auth(request)
            chat_id = _parse_chat_id(start_param, payload, request)
        if chat_id is None:
            raise ValueError("Не найдена беседа для начисления влияния.")
        player = await core.db.get_player(chat_id, user.id)
        if player is None:
            raise PermissionError(
                "Сначала открой игру из меню бота в нужной беседе."
            )
        return user, chat_id, payload

    def _error(error: Exception) -> web.Response:
        status = 403 if isinstance(error, PermissionError) else 400
        return core.web.json_response(
            {"ok": False, "reason": str(error)}, status=status
        )

    async def _daily_rows(chat_id: int, user_id: int) -> dict[str, dict[str, int]]:
        conn = core.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT game_key, attempts, best_score, best_base_reward, total_paid
            FROM game_daily_v75
            WHERE chat_id = ? AND user_id = ? AND date_key = ?
            """,
            (chat_id, user_id, _date_key()),
        )
        result: dict[str, dict[str, int]] = {}
        for row in await cursor.fetchall():
            result[str(row["game_key"])] = {
                "attempts": int(row["attempts"]),
                "best_score": int(row["best_score"]),
                "best_base_reward": int(row["best_base_reward"]),
                "total_paid": int(row["total_paid"]),
            }
        return result

    async def game_state(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await _auth(request)
            player = await core.db.get_player(chat_id, user.id)
            daily = await _daily_rows(chat_id, user.id)
            buffs = await talent_system.buffs_for(core.db, chat_id, user.id)
            games = {}
            for key, info in GAME_INFO.items():
                row = daily.get(key, {})
                attempts = int(row.get("attempts", 0))
                games[key] = {
                    **info,
                    "attempts": attempts,
                    "attempts_left": max(0, GAME_ATTEMPTS_PER_DAY - attempts),
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
                        "Три попытки на каждую игру. Влияние начисляется только "
                        "за улучшение лучшей награды за текущий день."
                    ),
                }
            )
        except (PermissionError, ValueError) as error:
            return _error(error)

    async def game_start(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await _auth(request)
            game_key = str(payload.get("game") or "")
            info = GAME_INFO.get(game_key)
            if info is None:
                raise ValueError("Неизвестная игра.")
            now = int(time.time())
            date_key = _date_key()
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
                    (chat_id, user.id, game_key, date_key, now),
                )
                cursor = await conn.execute(
                    """
                    SELECT attempts FROM game_daily_v75
                    WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                    """,
                    (chat_id, user.id, game_key, date_key),
                )
                row = await cursor.fetchone()
                attempts = int(row["attempts"]) if row else 0
                if attempts >= GAME_ATTEMPTS_PER_DAY:
                    await conn.commit()
                    raise ValueError("Все три попытки этой игры на сегодня использованы.")
                await conn.execute(
                    """
                    UPDATE game_daily_v75
                    SET attempts = attempts + 1, updated_at = ?
                    WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                    """,
                    (now, chat_id, user.id, game_key, date_key),
                )
                await conn.execute(
                    """
                    UPDATE game_runs_v75 SET status = 'expired'
                    WHERE status = 'active' AND started_at < ?
                    """,
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
                    "attempts_left": GAME_ATTEMPTS_PER_DAY - attempts - 1,
                }
            )
        except (PermissionError, ValueError) as error:
            return _error(error)

    async def game_finish(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await _auth(request)
            session_id = str(payload.get("session_id") or "")
            if not session_id:
                raise ValueError("Потеряна игровая сессия.")
            reported_score = _int(payload.get("score"), 0, 0, 1_000_000)
            meta = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
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
                                "base_reward": int(run["base_reward"]),
                                "actual_reward": int(run["actual_reward"]),
                                "balance": int(player.points) if player else 0,
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
                    if game_key not in GAME_INFO:
                        raise ValueError("Повреждён тип игры.")
                    elapsed_cap = (
                        min(300, elapsed * 8 + 40)
                        if game_key == "rooftop"
                        else min(300, elapsed * 5 + 50)
                    )
                    score = min(reported_score, elapsed_cap, 300)
                    base_reward = _base_reward(game_key, score)
                    cursor = await conn.execute(
                        """
                        SELECT best_score, best_base_reward FROM game_daily_v75
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (chat_id, user.id, game_key, _date_key()),
                    )
                    daily = await cursor.fetchone()
                    previous_best_score = int(daily["best_score"]) if daily else 0
                    previous_best_reward = int(daily["best_base_reward"]) if daily else 0
                    payable_base = max(0, base_reward - previous_best_reward)
                    await conn.execute(
                        "UPDATE game_runs_v75 SET status = 'resolving' WHERE session_id = ?",
                        (session_id,),
                    )
                    await conn.commit()

                actual_reward = 0
                tree_bonus = 0
                player = await core.db.get_player(chat_id, user.id)
                if payable_base > 0:
                    before, player = await core.db.add_points_with_balance(
                        chat_id,
                        user.id,
                        payable_base,
                        f"game_influence_hunt_{game_key}",
                    )
                    actual_reward = int(player.points) - int(before)
                    tree_bonus = max(0, actual_reward - payable_base)

                async with core.db.lock:
                    await conn.execute(
                        """
                        UPDATE game_daily_v75
                        SET best_score = MAX(best_score, ?),
                            best_base_reward = MAX(best_base_reward, ?),
                            total_paid = total_paid + ?,
                            updated_at = ?
                        WHERE chat_id = ? AND user_id = ? AND game_key = ? AND date_key = ?
                        """,
                        (
                            score,
                            base_reward,
                            actual_reward,
                            now,
                            chat_id,
                            user.id,
                            game_key,
                            _date_key(),
                        ),
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
                            base_reward,
                            actual_reward,
                            json.dumps(meta, ensure_ascii=False)[:4000],
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
                        "previous_best_score": previous_best_score,
                        "base_run_reward": base_reward,
                        "previous_best_reward": previous_best_reward,
                        "payable_base": payable_base,
                        "tree_bonus": tree_bonus,
                        "actual_reward": actual_reward,
                        "balance": int(player.points) if player else 0,
                        "new_best": score > previous_best_score,
                        "message": (
                            "Новый лучший результат и влияние начислены."
                            if payable_base > 0
                            else "Результат не превысил лучшую награду дня, поэтому влияние не начислено повторно."
                        ),
                    }
                )
        except (PermissionError, ValueError) as error:
            return _error(error)
        except Exception:
            # Возвращаем resolving-сессию в активное состояние для безопасного повтора.
            try:
                conn = core.db._require_connection()
                async with core.db.lock:
                    await conn.execute(
                        "UPDATE game_runs_v75 SET status = 'active' WHERE session_id = ? AND status = 'resolving'",
                        (str(locals().get("session_id") or ""),),
                    )
                    await conn.commit()
            except Exception:
                pass
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось сохранить результат. Попробуй отправить его ещё раз."},
                status=500,
            )

    def _file(path: Path) -> web.FileResponse:
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
        return _file(GAME_DIR / "index.html")

    async def rooftop_index(_: web.Request) -> web.StreamResponse:
        return _file(GAME_DIR / "rooftop" / "index.html")

    async def heist_index(_: web.Request) -> web.StreamResponse:
        return _file(GAME_DIR / "heist" / "index.html")

    original_start_server = core.start_webapp_server
    original_application = core.web.Application

    async def start_server_with_games(bot: Any):
        def application_factory(*args: Any, **kwargs: Any):
            app = original_application(*args, **kwargs)
            app.router.add_get("/games", games_index)
            app.router.add_get("/games/", games_index)
            app.router.add_get("/games/index.html", games_index)
            app.router.add_get("/games/rooftop", rooftop_index)
            app.router.add_get("/games/rooftop/", rooftop_index)
            app.router.add_get("/games/rooftop/index.html", rooftop_index)
            app.router.add_get("/games/heist", heist_index)
            app.router.add_get("/games/heist/", heist_index)
            app.router.add_get("/games/heist/index.html", heist_index)
            app.router.add_post("/games/api/state", game_state)
            app.router.add_post("/games/api/start", game_start)
            app.router.add_post("/games/api/finish", game_finish)
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = original_application

    core.start_webapp_server = start_server_with_games

    original_group_commands = core.group_bot_commands

    def group_commands_with_games() -> list[BotCommand]:
        commands = original_group_commands()
        if any(command.command == "games" for command in commands):
            return commands
        insert_at = next(
            (
                index + 1
                for index, command in enumerate(commands)
                if command.command == "talents"
            ),
            len(commands),
        )
        commands.insert(
            insert_at,
            BotCommand(command="games", description="Охота за влиянием"),
        )
        return commands

    core.group_bot_commands = group_commands_with_games

    async def _send_game_card(message: Message) -> None:
        if not message.from_user:
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        link = _game_link(core, int(message.chat.id))
        if not link:
            await message.answer("⚠️ Адрес Mini App не настроен.")
            return
        await message.answer(
            "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
            "🌃 Беги по крышам, собирай внимание и уклоняйся от препятствий.\n"
            "🏛 Проникай в хранилище, вскрывай сейфы и уходи с добычей.\n\n"
            "У каждой игры по <b>3 попытки в сутки</b>. Сервер начисляет влияние "
            "за улучшение лучшего результата дня и применяет бонусы древа знаний.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="🎮 ОТКРЫТЬ ИГРОВОЙ ЦЕНТР", url=link)]
                ]
            ),
        )

    @core.router.message(Command("games", "hunt"))
    async def cmd_games(message: Message) -> None:
        if (
            not await core.require_group_command(message, "Охота за влиянием")
            or not message.from_user
        ):
            return
        await _send_game_card(message)

    original_inline_specs = core.inline_menu_specs

    def inline_specs_with_games(user: Any) -> list[dict[str, Any]]:
        specs = original_inline_specs(user)
        if any(str(spec.get("result_id", "")).startswith("games_menu:") for spec in specs):
            return specs
        card = {
            "kind": "static",
            "result_id": f"games_menu:{user.id}:{secrets.token_hex(3)}",
            "title": "🎮 Охота за влиянием 🎮",
            "description": "Бег по крышам и ограбление хранилища",
            "message_text": (
                "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
                "Две игровые Mini App готовят персональный вход для этой беседы…\n"
                f"<tg-spoiler>#INFLUENCE_GAMES_{user.id}</tg-spoiler>"
            ),
        }
        insert_at = next(
            (
                index
                for index, spec in enumerate(specs)
                if str(spec.get("action", "")) == "about"
            ),
            len(specs),
        )
        specs.insert(insert_at, card)
        return specs

    core.inline_menu_specs = inline_specs_with_games

    original_dispatch = core.maybe_handle_inline_dispatch

    async def dispatch_with_games(message: Any, bot: Any) -> bool:
        body = message.text or message.caption or ""
        match = GAME_MARKER.search(body)
        if match is None:
            return await original_dispatch(message, bot)
        owner_id = int(match.group(1))
        if message.from_user is None or int(message.from_user.id) != owner_id:
            return False
        chat_id = int(message.chat.id)
        await core.db.upsert_player(chat_id, message.from_user)
        link = _game_link(core, chat_id)
        result_text = (
            "🎮 <b>ОХОТА ЗА ВЛИЯНИЕМ</b> 🎮\n\n"
            "🌃 <b>Бег по крышам</b> — свайпы, прыжки, подкаты и сбор влияния.\n"
            "🏛 <b>Ограбление хранилища</b> — свободное движение, сейфы, охрана и тревога.\n\n"
            "Добыча связана с балансом этой беседы. Награду рассчитывает сервер, "
            "после чего применяются игровые бонусы древа знаний."
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
                text=result_text,
                reply_markup=markup,
            )
        except Exception:
            await message.answer(result_text, reply_markup=markup)
        return True

    core.maybe_handle_inline_dispatch = dispatch_with_games
