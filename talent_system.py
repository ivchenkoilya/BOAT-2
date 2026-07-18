from __future__ import annotations

import contextvars
import html
import logging
import random
import time
from pathlib import Path
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

LOGGER = logging.getLogger(__name__)
TALENT_DIR = Path(__file__).resolve().parent / "talent_app"
TALENT_PREFIX = "talent_"

SKILLS: dict[str, dict[str, Any]] = {
    "damage1": {"branch": "damage", "name": "Острый язык", "max": 3, "cost": 1, "parent": None},
    "damage2": {"branch": "damage", "name": "Больное место", "max": 3, "cost": 1, "parent": "damage1"},
    "damage3": {"branch": "damage", "name": "Безжалостный выпад", "max": 2, "cost": 2, "parent": "damage2"},
    "damage4": {"branch": "damage", "name": "Крушение эго", "max": 1, "cost": 4, "parent": "damage3"},
    "influence1": {"branch": "influence", "name": "Заметная личность", "max": 3, "cost": 1, "parent": None},
    "influence2": {"branch": "influence", "name": "Центр внимания", "max": 3, "cost": 1, "parent": "influence1"},
    "influence3": {"branch": "influence", "name": "Восходящая звезда", "max": 2, "cost": 2, "parent": "influence2"},
    "influence4": {"branch": "influence", "name": "Культ личности", "max": 1, "cost": 4, "parent": "influence3"},
    "defense1": {"branch": "defense", "name": "Толстая кожа", "max": 3, "cost": 1, "parent": None},
    "defense2": {"branch": "defense", "name": "Железные нервы", "max": 3, "cost": 1, "parent": "defense1"},
    "defense3": {"branch": "defense", "name": "Ответный удар", "max": 2, "cost": 2, "parent": "defense2"},
    "defense4": {"branch": "defense", "name": "Сюжетная броня", "max": 1, "cost": 4, "parent": "defense3"},
    "rewards1": {"branch": "rewards", "name": "Богатая добыча", "max": 3, "cost": 1, "parent": None},
    "rewards2": {"branch": "rewards", "name": "Любимчик судьбы", "max": 3, "cost": 1, "parent": "rewards1"},
    "rewards3": {"branch": "rewards", "name": "Второй шанс", "max": 2, "cost": 2, "parent": "rewards2"},
    "rewards4": {"branch": "rewards", "name": "Переписать судьбу", "max": 1, "cost": 4, "parent": "rewards3"},
}

_adjusting_points: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "talent_adjusting_points", default=False
)


def _conn(db: Any):
    if db.connection is None:
        raise RuntimeError("Database is not connected")
    return db.connection


async def ensure_schema(db: Any) -> None:
    conn = _conn(db)
    async with db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS talent_profiles (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                total_points INTEGER NOT NULL DEFAULT 0,
                spent_points INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS talent_levels (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                skill_id TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id, skill_id)
            );
            CREATE INDEX IF NOT EXISTS idx_talent_levels_chat
            ON talent_levels (chat_id, user_id);
            CREATE TABLE IF NOT EXISTS talent_usage (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                usage_key TEXT NOT NULL,
                period_key TEXT NOT NULL,
                used_at INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id, usage_key, period_key)
            );
            """
        )
        await conn.commit()


def _entitled_points(influence: int) -> int:
    return min(15, 3 + max(0, influence) // 500)


async def sync_profile(db: Any, chat_id: int, user_id: int) -> dict[str, int]:
    conn = _conn(db)
    player = await db.get_player(chat_id, user_id)
    if player is None:
        raise ValueError("Сначала используй бота в этой беседе.")
    entitlement = _entitled_points(int(player.points))
    now = int(time.time())
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO talent_profiles (
                chat_id, user_id, total_points, spent_points, updated_at
            ) VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(chat_id, user_id) DO UPDATE SET
                total_points = MAX(talent_profiles.total_points, excluded.total_points),
                updated_at = excluded.updated_at
            """,
            (chat_id, user_id, entitlement, now),
        )
        cursor = await conn.execute(
            """
            SELECT total_points, spent_points
            FROM talent_profiles
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        await conn.commit()
    total = int(row["total_points"]) if row else entitlement
    spent = int(row["spent_points"]) if row else 0
    return {"total": total, "spent": spent, "available": max(0, total - spent)}


async def levels_for(db: Any, chat_id: int, user_id: int) -> dict[str, int]:
    conn = _conn(db)
    cursor = await conn.execute(
        """
        SELECT skill_id, level
        FROM talent_levels
        WHERE chat_id = ? AND user_id = ?
        """,
        (chat_id, user_id),
    )
    return {
        str(row["skill_id"]): int(row["level"])
        for row in await cursor.fetchall()
    }


def calculate_buffs(levels: dict[str, int]) -> dict[str, float]:
    return {
        "boss_damage": levels.get("damage1", 0) * 0.03,
        "boss_crit_chance": levels.get("damage2", 0) * 0.02,
        "boss_crit_power": levels.get("damage3", 0) * 0.15,
        "first_hit_x3": float(levels.get("damage4", 0) > 0),
        "influence": levels.get("influence1", 0) * 0.02,
        "activity": levels.get("influence2", 0) * 0.03,
        "tasks": levels.get("influence3", 0) * 0.05,
        "daily_double": float(levels.get("influence4", 0) > 0),
        "penalty_reduction": levels.get("defense1", 0) * 0.04,
        "avoid_penalty": levels.get("defense2", 0) * 0.05,
        "sabotage_reduction": levels.get("defense3", 0) * 0.10,
        "weekly_armor": float(levels.get("defense4", 0) > 0),
        "game_reward": levels.get("rewards1", 0) * 0.05,
        "rare_reward": levels.get("rewards2", 0) * 0.03,
        "second_chance": levels.get("rewards3", 0) * 0.05,
        "daily_reroll": float(levels.get("rewards4", 0) > 0),
    }


async def buffs_for(db: Any, chat_id: int, user_id: int) -> dict[str, float]:
    return calculate_buffs(await levels_for(db, chat_id, user_id))


async def consume_period(
    db: Any,
    chat_id: int,
    user_id: int,
    key: str,
    period: str,
) -> bool:
    conn = _conn(db)
    async with db.lock:
        cursor = await conn.execute(
            """
            INSERT OR IGNORE INTO talent_usage (
                chat_id, user_id, usage_key, period_key, used_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, key, period, int(time.time())),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def upgrade_skill(
    db: Any,
    chat_id: int,
    user_id: int,
    skill_id: str,
) -> dict[str, Any]:
    spec = SKILLS.get(skill_id)
    if spec is None:
        raise ValueError("Неизвестный навык.")
    await sync_profile(db, chat_id, user_id)
    conn = _conn(db)
    now = int(time.time())
    async with db.lock:
        cursor = await conn.execute(
            """
            SELECT total_points, spent_points
            FROM talent_profiles
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )
        profile = await cursor.fetchone()
        cursor = await conn.execute(
            """
            SELECT skill_id, level
            FROM talent_levels
            WHERE chat_id = ? AND user_id = ?
            """,
            (chat_id, user_id),
        )
        current_levels = {
            str(row["skill_id"]): int(row["level"])
            for row in await cursor.fetchall()
        }
        current = current_levels.get(skill_id, 0)
        if current >= int(spec["max"]):
            raise ValueError("Навык уже прокачан до максимума.")
        parent = spec.get("parent")
        if parent and current_levels.get(str(parent), 0) <= 0:
            raise ValueError("Сначала открой предыдущий навык этой ветки.")
        cost = int(spec["cost"])
        available = int(profile["total_points"]) - int(profile["spent_points"])
        if available < cost:
            raise ValueError("Не хватает очков таланта.")
        await conn.execute(
            """
            INSERT INTO talent_levels (
                chat_id, user_id, skill_id, level, updated_at
            ) VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(chat_id, user_id, skill_id) DO UPDATE SET
                level = talent_levels.level + 1,
                updated_at = excluded.updated_at
            """,
            (chat_id, user_id, skill_id, now),
        )
        await conn.execute(
            """
            UPDATE talent_profiles
            SET spent_points = spent_points + ?, updated_at = ?
            WHERE chat_id = ? AND user_id = ?
            """,
            (cost, now, chat_id, user_id),
        )
        await conn.commit()
    return await talent_state(db, chat_id, user_id)


async def talent_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    profile = await sync_profile(db, chat_id, user_id)
    levels = await levels_for(db, chat_id, user_id)
    return {
        "ok": True,
        "chat_id": chat_id,
        "points": profile,
        "levels": levels,
        "buffs": calculate_buffs(levels),
    }


def _reason_has(reason: str, words: tuple[str, ...]) -> bool:
    value = reason.casefold()
    return any(word in value for word in words)


async def adjusted_delta(
    db: Any,
    chat_id: int,
    user_id: int,
    delta: int,
    reason: str,
) -> int:
    if delta == 0:
        return 0
    await sync_profile(db, chat_id, user_id)
    buffs = await buffs_for(db, chat_id, user_id)
    result = int(delta)
    reason_text = str(reason or "")
    game = _reason_has(
        reason_text,
        ("coin", "dice", "roulette", "game", "fate", "boss"),
    )
    activity = _reason_has(
        reason_text,
        ("message", "reaction", "voice", "reply", "activity"),
    )
    task = _reason_has(reason_text, ("task", "mission", "action"))
    protected_reason = _reason_has(
        reason_text,
        ("admin", "transfer", "restore", "hero_day", "stake"),
    )

    if result > 0 and not protected_reason:
        multiplier = 1.0 + buffs["influence"]
        if activity:
            multiplier += buffs["activity"]
        if task:
            multiplier += buffs["tasks"]
        if game:
            multiplier += buffs["game_reward"]
        result = max(result, int(round(result * multiplier)))
        if (
            game
            and buffs["rare_reward"] > 0
            and random.random() < buffs["rare_reward"]
        ):
            result += max(1, int(round(result * 0.5)))
        if (
            buffs["daily_double"]
            and await consume_period(
                db,
                chat_id,
                user_id,
                "influence4",
                time.strftime("%Y-%m-%d"),
            )
        ):
            result *= 2
    elif result < 0 and not protected_reason:
        if game:
            if (
                buffs["daily_reroll"]
                and await consume_period(
                    db,
                    chat_id,
                    user_id,
                    "rewards4",
                    time.strftime("%Y-%m-%d"),
                )
            ):
                return 0
            if (
                buffs["second_chance"] > 0
                and random.random() < buffs["second_chance"]
            ):
                return 0
        if buffs["weekly_armor"]:
            week = time.strftime("%Y-W%W")
            if await consume_period(
                db,
                chat_id,
                user_id,
                "defense4",
                week,
            ):
                return 0
        if (
            buffs["avoid_penalty"] > 0
            and random.random() < buffs["avoid_penalty"]
        ):
            return 0
        reduction = buffs["penalty_reduction"]
        if _reason_has(
            reason_text,
            ("sabotage", "impeachment", "rebellion"),
        ):
            reduction += buffs["sabotage_reduction"]
        result = -max(
            1,
            int(round(abs(result) * max(0.0, 1.0 - min(0.8, reduction)))),
        )
    return result


def _extract_score_args(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> tuple[int, int, int, str] | None:
    try:
        chat_id = int(kwargs["chat_id"] if "chat_id" in kwargs else args[0])
        user_id = int(kwargs["user_id"] if "user_id" in kwargs else args[1])
        delta = int(kwargs["delta"] if "delta" in kwargs else args[2])
        reason = str(kwargs["reason"] if "reason" in kwargs else args[3])
        return chat_id, user_id, delta, reason
    except (IndexError, KeyError, TypeError, ValueError):
        return None


def _replace_delta(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    delta: int,
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if "delta" in kwargs:
        updated = dict(kwargs)
        updated["delta"] = delta
        return args, updated
    values = list(args)
    if len(values) >= 3:
        values[2] = delta
    return tuple(values), kwargs


async def apply_extra_boss_damage(
    core: Any,
    db: Any,
    boss_id: str,
    chat_id: int,
    user_id: int,
    result: dict[str, Any],
    *,
    ability: bool,
) -> dict[str, Any]:
    if not result.get("ok") or int(result.get("damage", 0)) <= 0:
        return result
    buffs = await buffs_for(db, chat_id, user_id)
    base = int(result["damage"])
    bonus = int(round(base * buffs["boss_damage"]))
    talent_crit = False
    if (
        not ability
        and buffs["boss_crit_chance"] > 0
        and random.random() < buffs["boss_crit_chance"]
    ):
        bonus += int(round(base * (0.75 + buffs["boss_crit_power"])))
        talent_crit = True
    if not ability and buffs["first_hit_x3"]:
        if await consume_period(
            db,
            chat_id,
            user_id,
            "damage4",
            time.strftime("%Y-%m-%d"),
        ):
            bonus += base * 2
    if bonus <= 0:
        return result

    conn = _conn(db)
    now = int(time.time())
    async with db.lock:
        cursor = await conn.execute(
            "SELECT hp, max_hp, phase FROM boss_battles WHERE boss_id = ?",
            (boss_id,),
        )
        battle = await cursor.fetchone()
        if battle is None:
            return result
        hp_before = int(battle["hp"])
        actual = min(hp_before, bonus)
        hp_after = max(0, hp_before - actual)
        phase_after = core.boss_phase_for_hp(
            hp_after,
            int(battle["max_hp"]),
        )
        await conn.execute(
            """
            UPDATE boss_battles
            SET hp = ?, phase = ?, last_attacker_id = ?
            WHERE boss_id = ?
            """,
            (hp_after, phase_after, user_id, boss_id),
        )
        await conn.execute(
            """
            UPDATE boss_fighters
            SET damage_done = damage_done + ?,
                critical_hits = critical_hits + ?
            WHERE boss_id = ? AND user_id = ?
            """,
            (actual, 1 if talent_crit else 0, boss_id, user_id),
        )
        if actual:
            label = "крит таланта" if talent_crit else "усиление талантов"
            await conn.execute(
                """
                INSERT INTO boss_logs (boss_id, log_text, created_at)
                VALUES (?, ?, ?)
                """,
                (
                    boss_id,
                    f"🌳 {label}: дополнительный урон −{actual} HP.",
                    now,
                ),
            )
        await conn.commit()
    updated = dict(result)
    updated["damage"] = base + actual
    updated["talent_bonus_damage"] = actual
    updated["talent_critical"] = talent_crit
    updated["hp"] = hp_after
    updated["phase"] = phase_after
    updated["phase_changed"] = (
        bool(result.get("phase_changed"))
        or phase_after != int(battle["phase"])
    )
    updated["defeated"] = hp_after <= 0
    return updated


def format_buffs(
    name: str,
    profile: dict[str, int],
    buffs: dict[str, float],
) -> str:
    return (
        f"✨ <b>УСИЛЕНИЯ {html.escape(name.upper())}</b>\n\n"
        f"⚔ Урон по боссу: <b>+{round(buffs['boss_damage'] * 100)}%</b>\n"
        f"🎯 Шанс крита таланта: <b>+{round(buffs['boss_crit_chance'] * 100)}%</b>\n"
        f"📈 Получение влияния: <b>+{round(buffs['influence'] * 100)}%</b>\n"
        f"🛡 Снижение штрафов: <b>{round(buffs['penalty_reduction'] * 100)}%</b>\n"
        f"🎁 Награды мини-игр: <b>+{round(buffs['game_reward'] * 100)}%</b>\n"
        f"🍀 Шанс редкого бонуса: <b>+{round(buffs['rare_reward'] * 100)}%</b>\n\n"
        f"💠 Свободно очков: <b>{profile['available']}</b>\n"
        f"🌳 Потрачено: <b>{profile['spent']}</b>"
    )


def install(core: Any) -> None:
    if getattr(core, "_talent_system_installed", False):
        return
    core._talent_system_installed = True

    original_connect = core.Database.connect

    async def connect_with_talents(self: Any) -> None:
        await original_connect(self)
        await ensure_schema(self)

    core.Database.connect = connect_with_talents

    for method_name in ("add_points", "add_points_with_balance"):
        original = getattr(core.Database, method_name, None)
        if original is None:
            continue

        async def score_wrapper(
            self: Any,
            *args: Any,
            __original=original,
            **kwargs: Any,
        ):
            if _adjusting_points.get():
                return await __original(self, *args, **kwargs)
            extracted = _extract_score_args(args, kwargs)
            if extracted is None:
                return await __original(self, *args, **kwargs)
            chat_id, user_id, delta, reason = extracted
            try:
                new_delta = await adjusted_delta(
                    self,
                    chat_id,
                    user_id,
                    delta,
                    reason,
                )
            except Exception:
                LOGGER.exception("Не удалось применить таланты к начислению")
                new_delta = delta
            new_args, new_kwargs = _replace_delta(args, kwargs, new_delta)
            token = _adjusting_points.set(True)
            try:
                return await __original(self, *new_args, **new_kwargs)
            finally:
                _adjusting_points.reset(token)

        setattr(core.Database, method_name, score_wrapper)

    original_hit = getattr(core.Database, "boss_apply_hit", None)
    if original_hit is not None:

        async def boss_hit_wrapper(
            self: Any,
            boss_id: str,
            chat_id: int,
            user_id: int,
            *args: Any,
            **kwargs: Any,
        ):
            result = await original_hit(
                self,
                boss_id,
                chat_id,
                user_id,
                *args,
                **kwargs,
            )
            return await apply_extra_boss_damage(
                core,
                self,
                boss_id,
                chat_id,
                user_id,
                result,
                ability=False,
            )

        core.Database.boss_apply_hit = boss_hit_wrapper

    original_ability = getattr(core.Database, "boss_apply_ability", None)
    if original_ability is not None:

        async def boss_ability_wrapper(
            self: Any,
            boss_id: str,
            chat_id: int,
            user_id: int,
            *args: Any,
            **kwargs: Any,
        ):
            result = await original_ability(
                self,
                boss_id,
                chat_id,
                user_id,
                *args,
                **kwargs,
            )
            return await apply_extra_boss_damage(
                core,
                self,
                boss_id,
                chat_id,
                user_id,
                result,
                ability=True,
            )

        core.Database.boss_apply_ability = boss_ability_wrapper

    original_group_commands = core.group_bot_commands

    def group_commands_with_talents() -> list[BotCommand]:
        commands = original_group_commands()
        insert_at = next(
            (
                index + 1
                for index, command in enumerate(commands)
                if command.command == "boss"
            ),
            len(commands),
        )
        commands[insert_at:insert_at] = [
            BotCommand(
                command="talents",
                description="Открыть древо развития",
            ),
            BotCommand(
                command="buffs",
                description="Мои активные усиления",
            ),
            BotCommand(
                command="chat_buffs",
                description="Развитие участников беседы",
            ),
        ]
        return commands

    core.group_bot_commands = group_commands_with_talents

    def talent_link(chat_id: int) -> str:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/"
            f"{core.WEBAPP_SHORT_NAME}?startapp={TALENT_PREFIX}{chat_id}"
        )

    @core.router.message(Command("talents", "tree"))
    async def cmd_talents(message: Message) -> None:
        if (
            not await core.require_group_command(message, "Древо развития")
            or not message.from_user
        ):
            return
        await core.prepare_command_player(message)
        await sync_profile(core.db, message.chat.id, message.from_user.id)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🌳 ОТКРЫТЬ ДРЕВО РАЗВИТИЯ",
                        url=talent_link(message.chat.id),
                    )
                ]
            ]
        )
        await message.answer(
            "🌳 <b>ДРЕВО РАЗВИТИЯ</b>\n\n"
            "Прокачивай урон, влияние, защиту и награды. "
            "Все выбранные навыки сохраняются в этой беседе "
            "и сразу применяются ботом.",
            reply_markup=keyboard,
        )

    @core.router.message(Command("buffs"))
    async def cmd_buffs(message: Message) -> None:
        if (
            not await core.require_group_command(message, "Усиления")
            or not message.from_user
        ):
            return
        player = await core.prepare_command_player(message)
        if player is None:
            return
        profile = await sync_profile(
            core.db,
            message.chat.id,
            message.from_user.id,
        )
        buffs = await buffs_for(
            core.db,
            message.chat.id,
            message.from_user.id,
        )
        await message.answer(format_buffs(player.full_name, profile, buffs))

    @core.router.message(Command("chat_buffs"))
    async def cmd_chat_buffs(message: Message) -> None:
        if not await core.require_group_command(message, "Баффы беседы"):
            return
        conn = _conn(core.db)
        cursor = await conn.execute(
            """
            SELECT p.user_id, p.full_name,
                   COALESCE(t.spent_points, 0) AS spent
            FROM players p
            LEFT JOIN talent_profiles t
              ON t.chat_id = p.chat_id AND t.user_id = p.user_id
            WHERE p.chat_id = ?
            ORDER BY spent DESC, p.points DESC
            LIMIT 10
            """,
            (message.chat.id,),
        )
        rows = await cursor.fetchall()
        lines = ["👥 <b>РАЗВИТИЕ УЧАСТНИКОВ</b>"]
        for index, row in enumerate(rows, 1):
            levels = await levels_for(
                core.db,
                message.chat.id,
                int(row["user_id"]),
            )
            buffs = calculate_buffs(levels)
            lines.append(
                f"{index}. <b>{html.escape(str(row['full_name']))}</b> — "
                f"{int(row['spent'])} очк.\n"
                f"   ⚔ +{round(buffs['boss_damage'] * 100)}% · "
                f"📈 +{round(buffs['influence'] * 100)}% · "
                f"🛡 {round(buffs['penalty_reduction'] * 100)}% · "
                f"🎁 +{round(buffs['game_reward'] * 100)}%"
            )
        await message.answer(
            "\n\n".join(lines)
            if len(lines) > 1
            else "Пока никто не открыл древо развития."
        )

    async def talent_index(request: web.Request) -> web.StreamResponse:
        return web.FileResponse(TALENT_DIR / "index.html")

    def parse_chat_id(
        start_param: str | None,
        payload: dict[str, Any],
        request: web.Request,
    ) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(TALENT_PREFIX):
            raw = raw[len(TALENT_PREFIX):]
        else:
            raw = str(
                payload.get("chat_id")
                or request.query.get("chat_id")
                or ""
            )
        try:
            return int(raw)
        except ValueError:
            return None

    async def talent_session(request: web.Request) -> web.Response:
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core._webapp_error(
                start_param or "Нет авторизации.",
                401,
            )
        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            return core._webapp_error("Не найдена беседа.")
        player = await core.db.get_player(chat_id, user.id)
        if player is None:
            return core._webapp_error(
                "Сначала открой древо командой /talents в нужной беседе.",
                403,
            )
        return web.json_response(
            await talent_state(core.db, chat_id, user.id)
        )

    async def talent_upgrade(request: web.Request) -> web.Response:
        user, start_param = core._webapp_auth(request)
        if user is None:
            return core._webapp_error(
                start_param or "Нет авторизации.",
                401,
            )
        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            return core._webapp_error("Не найдена беседа.")
        if await core.db.get_player(chat_id, user.id) is None:
            return core._webapp_error(
                "Игрок не найден в этой беседе.",
                403,
            )
        try:
            state = await upgrade_skill(
                core.db,
                chat_id,
                user.id,
                str(payload.get("skill_id") or ""),
            )
        except ValueError as error:
            return core._webapp_error(str(error))
        return web.json_response(state)

    original_start_server = core.start_webapp_server
    original_application = core.web.Application

    async def start_server_with_talents(bot: Any):
        def application_factory(*args: Any, **kwargs: Any):
            app = original_application(*args, **kwargs)
            app.router.add_get("/talents", talent_index)
            app.router.add_get("/talents/", talent_index)
            app.router.add_get("/talents/index.html", talent_index)
            app.router.add_post(
                "/talents/api/session",
                talent_session,
            )
            app.router.add_post(
                "/talents/api/upgrade",
                talent_upgrade,
            )
            return app

        core.web.Application = application_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.Application = original_application

    core.start_webapp_server = start_server_with_talents
