from __future__ import annotations

import html
import json
import logging
import random
import time
from typing import Any

from aiohttp import web
from aiogram.filters import Command
from aiogram.types import BotCommand, Message

import talent_system as talents

LOGGER = logging.getLogger(__name__)
RESET_PRICE = 250
BUILD_SWITCH_COOLDOWN = 60 * 60

SPECIAL_SKILLS: dict[str, dict[str, Any]] = {
    "hybrid_retaliation": {
        "branch": "special", "name": "Ответная агрессия", "max": 1, "cost": 2,
        "parent": "damage2", "parents": ["damage2", "defense2"], "rarity": "epic",
        "kind": "hybrid", "icon": "counter", "effect": "После защиты следующий удар сильнее на 50%.",
    },
    "hybrid_popularity": {
        "branch": "special", "name": "Любимец публики", "max": 1, "cost": 2,
        "parent": "influence2", "parents": ["influence2", "rewards2"], "rarity": "epic",
        "kind": "hybrid", "icon": "crown", "effect": "+2% влияния и +3% наград мини-игр.",
    },
    "hybrid_loudcrit": {
        "branch": "special", "name": "Громкий выпад", "max": 1, "cost": 2,
        "parent": "damage2", "parents": ["damage2", "influence1"], "rarity": "epic",
        "kind": "hybrid", "icon": "bolt", "effect": "+2% шанса крита и +1% влияния.",
    },
    "hybrid_insurance": {
        "branch": "special", "name": "Страховка победителя", "max": 1, "cost": 2,
        "parent": "defense1", "parents": ["defense1", "rewards1"], "rarity": "epic",
        "kind": "hybrid", "icon": "shield", "effect": "+5% отмены проигрыша и −3% штрафов.",
    },
    "mechanic_combo": {
        "branch": "special", "name": "Серия из пяти", "max": 1, "cost": 3,
        "parent": "damage10", "parents": ["damage5", "damage10"], "rarity": "legendary",
        "kind": "mechanic", "icon": "sword", "effect": "Каждый пятый удар по боссу наносит двойной урон.",
    },
    "mechanic_break_shield": {
        "branch": "special", "name": "Разбить самолюбие", "max": 1, "cost": 3,
        "parent": "damage6", "parents": ["damage3", "damage6"], "rarity": "legendary",
        "kind": "mechanic", "icon": "break", "effect": "Критический удар полностью ломает щит босса.",
    },
    "mechanic_pity": {
        "branch": "special", "name": "Упрямство судьбы", "max": 1, "cost": 3,
        "parent": "rewards10", "parents": ["rewards3", "rewards10"], "rarity": "legendary",
        "kind": "mechanic", "icon": "repeat", "effect": "Каждый проигрыш усиливает следующую победу на 5%, максимум на 30%.",
    },
    "mechanic_taskflow": {
        "branch": "special", "name": "Поток достижений", "max": 1, "cost": 3,
        "parent": "influence10", "parents": ["influence3", "influence10"], "rarity": "legendary",
        "kind": "mechanic", "icon": "network", "effect": "Выполнение задания сокращает откат активных талантов на 30 минут.",
    },
    "hidden_sly": {
        "branch": "special", "name": "Подлый план", "max": 1, "cost": 2,
        "parent": None, "parents": [], "rarity": "mythic", "kind": "hidden",
        "icon": "mirror", "effect": "+4% влияния и усиленная защита от конфликтов.",
        "unlock": "sly", "clue": "Получи типаж 😈 Подлый.",
    },
    "hidden_raven": {
        "branch": "special", "name": "Вороний взгляд", "max": 1, "cost": 2,
        "parent": None, "parents": [], "rarity": "mythic", "kind": "hidden",
        "icon": "eye", "effect": "+5% к шансу редкой награды.",
        "unlock": "raven", "clue": "Получи типаж 🐦‍⬛ Вороний.",
    },
    "hidden_hero": {
        "branch": "special", "name": "Истинная корона", "max": 1, "cost": 3,
        "parent": None, "parents": [], "rarity": "mythic", "kind": "hidden",
        "icon": "crown", "effect": "+5% урона по боссу.",
        "unlock": "hero", "clue": "Достигни роли Главного героя.",
    },
    "hidden_saboteur": {
        "branch": "special", "name": "Корона без права", "max": 1, "cost": 3,
        "parent": None, "parents": [], "rarity": "mythic", "kind": "hidden",
        "icon": "bolt", "effect": "+4% наград за активность.",
        "unlock": "saboteur", "clue": "Стань Главным героем через саботаж.",
    },
    "hidden_veteran": {
        "branch": "special", "name": "Шрам Центра Вселенной", "max": 1, "cost": 3,
        "parent": None, "parents": [], "rarity": "mythic", "kind": "hidden",
        "icon": "flame", "effect": "+3% урона и +2% шанса крита по боссу.",
        "unlock": "veteran", "clue": "Совершив не меньше 25 атак по боссу.",
    },
    "active_last_word": {
        "branch": "special", "name": "Последнее слово", "max": 1, "cost": 3,
        "parent": "damage3", "parents": ["damage3", "damage6"], "rarity": "legendary",
        "kind": "active", "icon": "target", "effect": "Следующий удар гарантированно получает мощный крит.",
        "cooldown": 6 * 60 * 60, "effect_key": "guaranteed_crit",
    },
    "active_spotlight": {
        "branch": "special", "name": "Перетянуть внимание", "max": 1, "cost": 3,
        "parent": "influence3", "parents": ["influence3", "influence6"], "rarity": "legendary",
        "kind": "active", "icon": "aura", "effect": "Следующее положительное начисление влияния удваивается.",
        "cooldown": 8 * 60 * 60, "effect_key": "double_reward",
    },
    "active_mirror": {
        "branch": "special", "name": "Зеркало ЧСВ", "max": 1, "cost": 3,
        "parent": "defense3", "parents": ["defense3", "defense6"], "rarity": "legendary",
        "kind": "active", "icon": "mirror", "effect": "Следующий подходящий штраф полностью отменяется.",
        "cooldown": 12 * 60 * 60, "effect_key": "cancel_penalty",
    },
    "active_gamble": {
        "branch": "special", "name": "Азарт Главного героя", "max": 1, "cost": 3,
        "parent": "rewards3", "parents": ["rewards3", "rewards6"], "rarity": "legendary",
        "kind": "active", "icon": "jackpot", "effect": "Следующая игровая победа ×2, но проигрыш станет на 50% тяжелее.",
        "cooldown": 8 * 60 * 60, "effect_key": "gamble_reward",
    },
}

EXCLUSIVE_GROUPS: dict[str, tuple[str, ...]] = {
    "damage": ("damage4", "damage7", "damage9", "damage11"),
    "influence": ("influence4", "influence7", "influence9", "influence11"),
    "defense": ("defense4", "defense7", "defense9", "defense11"),
    "rewards": ("rewards4", "rewards7", "rewards9", "rewards11"),
}

SETS: dict[str, dict[str, Any]] = {
    "ego_breaker": {
        "title": "Разрушитель эго", "emoji": "⚔️", "skills": ["damage1", "damage2", "damage7"],
        "description": "+3% урона по боссу.",
    },
    "center_attention": {
        "title": "Центр внимания", "emoji": "👑", "skills": ["influence1", "influence8", "influence11"],
        "description": "+3% ко всем положительным начислениям.",
    },
    "iron_story": {
        "title": "Железный сюжет", "emoji": "🛡", "skills": ["defense1", "defense6", "defense11"],
        "description": "Ещё −3% обычных штрафов.",
    },
    "fortune_favorite": {
        "title": "Фаворит судьбы", "emoji": "🍀", "skills": ["rewards1", "rewards8", "rewards11"],
        "description": "+3% к наградам мини-игр.",
    },
}

COMMUNITY_SKILLS: dict[str, dict[str, Any]] = {
    "community_damage": {"title": "Общий натиск", "emoji": "⚔️", "max": 3, "cost": 1, "effect": "+2% урона всем"},
    "community_influence": {"title": "Громкая беседа", "emoji": "📈", "max": 3, "cost": 1, "effect": "+1% влияния всем"},
    "community_defense": {"title": "Круговая порука", "emoji": "🛡", "max": 3, "cost": 1, "effect": "−2% штрафов всем"},
    "community_luck": {"title": "Общая удача", "emoji": "🎁", "max": 3, "cost": 1, "effect": "+1,5% игровых наград всем"},
}

RARITY_LABELS = {
    "common": "Обычный", "rare": "Редкий", "epic": "Эпический",
    "legendary": "Легендарный", "mythic": "Мифический",
}

BUFF_LABELS = {
    "boss_damage": "Урон по боссу", "boss_crit_chance": "Шанс крита",
    "boss_crit_power": "Сила крита", "influence": "Общее влияние",
    "activity": "Награды за активность", "tasks": "Награды за задания",
    "penalty_reduction": "Снижение штрафов", "avoid_penalty": "Шанс отменить штраф",
    "sabotage_reduction": "Защита от конфликтов", "game_reward": "Награды мини-игр",
    "rare_reward": "Шанс редкой награды", "second_chance": "Шанс отменить проигрыш",
}


def _period_day() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def _cost_for_levels(levels: dict[str, int]) -> int:
    total = 0
    for skill_id, level in levels.items():
        spec = talents.SKILLS.get(skill_id)
        if spec:
            total += max(0, int(level)) * int(spec.get("cost", 1))
    return total


def _sets_for(levels: dict[str, int]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key, spec in SETS.items():
        active = all(levels.get(skill_id, 0) > 0 for skill_id in spec["skills"])
        result.append({"key": key, **spec, "active": active})
    return result


def _exclusive_group(skill_id: str) -> tuple[str, tuple[str, ...]] | None:
    for group, skill_ids in EXCLUSIVE_GROUPS.items():
        if skill_id in skill_ids:
            return group, skill_ids
    return None


async def _today_type_key(db: Any, chat_id: int, user_id: int) -> str:
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT type_key FROM today_type_assignments WHERE chat_id=? AND user_id=? AND expires_at>?",
        (chat_id, user_id, int(time.time())),
    )
    row = await cursor.fetchone()
    return str(row["type_key"]) if row else ""


async def _unlock_context(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    conn = talents._conn(db)
    player = await db.get_player(chat_id, user_id)
    type_key = await _today_type_key(db, chat_id, user_id)
    sabotage = await db.get_active_sabotage_for_usurper(chat_id, user_id)
    cursor = await conn.execute(
        """
        SELECT COALESCE(SUM(bf.attacks),0) AS attacks
        FROM boss_fighters bf
        JOIN boss_battles bb ON bb.boss_id=bf.boss_id
        WHERE bb.chat_id=? AND bf.user_id=?
        """,
        (chat_id, user_id),
    )
    row = await cursor.fetchone()
    return {
        "type_key": type_key,
        "hero": bool(player and int(player.points) >= 3000),
        "saboteur": sabotage is not None,
        "attacks": int(row["attacks"] if row else 0),
    }


def _hidden_unlocked(spec: dict[str, Any], context: dict[str, Any]) -> bool:
    unlock = spec.get("unlock")
    if unlock in {"sly", "raven"}:
        return context.get("type_key") == unlock
    if unlock == "hero":
        return bool(context.get("hero"))
    if unlock == "saboteur":
        return bool(context.get("saboteur"))
    if unlock == "veteran":
        return int(context.get("attacks", 0)) >= 25
    return True


async def _ensure_mastery_schema(db: Any) -> None:
    conn = talents._conn(db)
    async with db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS talent_meta (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                free_reset_used INTEGER NOT NULL DEFAULT 0,
                last_build_switch_at INTEGER NOT NULL DEFAULT 0,
                active_build_slot INTEGER,
                PRIMARY KEY(chat_id,user_id)
            );
            CREATE TABLE IF NOT EXISTS talent_builds (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                slot INTEGER NOT NULL,
                name TEXT NOT NULL,
                levels_json TEXT NOT NULL,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,slot)
            );
            CREATE TABLE IF NOT EXISTS talent_active_cooldowns (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                ability_key TEXT NOT NULL,
                ready_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,ability_key)
            );
            CREATE TABLE IF NOT EXISTS talent_active_effects (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                effect_key TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                charges INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY(chat_id,user_id,effect_key)
            );
            CREATE TABLE IF NOT EXISTS talent_counters (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                counter_key TEXT NOT NULL,
                period_key TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,user_id,counter_key,period_key)
            );
            CREATE TABLE IF NOT EXISTS community_talent_profiles (
                chat_id INTEGER PRIMARY KEY,
                total_points INTEGER NOT NULL DEFAULT 0,
                spent_points INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS community_talent_levels (
                chat_id INTEGER NOT NULL,
                skill_id TEXT NOT NULL,
                level INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,skill_id)
            );
            """
        )
        await conn.commit()


async def _community_state(db: Any, chat_id: int) -> dict[str, Any]:
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT COALESCE(SUM(spent_points),0) AS spent FROM talent_profiles WHERE chat_id=?",
        (chat_id,),
    )
    row = await cursor.fetchone()
    personal_spent = int(row["spent"] if row else 0)
    cursor = await conn.execute(
        "SELECT COUNT(*) AS wins FROM boss_battles WHERE chat_id=? AND status='victory'",
        (chat_id,),
    )
    row = await cursor.fetchone()
    wins = int(row["wins"] if row else 0)
    entitled = min(20, 1 + personal_spent // 15 + wins // 3)
    now = int(time.time())
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO community_talent_profiles(chat_id,total_points,spent_points,updated_at)
            VALUES(?,?,0,?)
            ON CONFLICT(chat_id) DO UPDATE SET
              total_points=MAX(community_talent_profiles.total_points,excluded.total_points),
              updated_at=excluded.updated_at
            """,
            (chat_id, entitled, now),
        )
        cursor = await conn.execute(
            "SELECT total_points,spent_points FROM community_talent_profiles WHERE chat_id=?",
            (chat_id,),
        )
        profile = await cursor.fetchone()
        cursor = await conn.execute(
            "SELECT skill_id,level FROM community_talent_levels WHERE chat_id=?",
            (chat_id,),
        )
        levels = {str(r["skill_id"]): int(r["level"]) for r in await cursor.fetchall()}
        await conn.commit()
    total = int(profile["total_points"] if profile else entitled)
    spent = int(profile["spent_points"] if profile else 0)
    return {
        "points": {"total": total, "spent": spent, "available": max(0, total - spent)},
        "levels": levels,
        "skills": [{"id": key, **spec, "level": levels.get(key, 0)} for key, spec in COMMUNITY_SKILLS.items()],
    }


async def _community_upgrade(db: Any, chat_id: int, skill_id: str) -> dict[str, Any]:
    spec = COMMUNITY_SKILLS.get(skill_id)
    if not spec:
        raise ValueError("Неизвестное улучшение беседы.")
    await _community_state(db, chat_id)
    conn = talents._conn(db)
    now = int(time.time())
    async with db.lock:
        cursor = await conn.execute(
            "SELECT total_points,spent_points FROM community_talent_profiles WHERE chat_id=?",
            (chat_id,),
        )
        profile = await cursor.fetchone()
        cursor = await conn.execute(
            "SELECT level FROM community_talent_levels WHERE chat_id=? AND skill_id=?",
            (chat_id, skill_id),
        )
        row = await cursor.fetchone()
        level = int(row["level"] if row else 0)
        if level >= int(spec["max"]):
            raise ValueError("Улучшение беседы уже максимального уровня.")
        if int(profile["total_points"]) - int(profile["spent_points"]) < int(spec["cost"]):
            raise ValueError("Не хватает общих очков беседы.")
        await conn.execute(
            """
            INSERT INTO community_talent_levels(chat_id,skill_id,level,updated_at)
            VALUES(?,?,1,?)
            ON CONFLICT(chat_id,skill_id) DO UPDATE SET level=level+1,updated_at=excluded.updated_at
            """,
            (chat_id, skill_id, now),
        )
        await conn.execute(
            "UPDATE community_talent_profiles SET spent_points=spent_points+?,updated_at=? WHERE chat_id=?",
            (int(spec["cost"]), now, chat_id),
        )
        await conn.commit()
    return await _community_state(db, chat_id)


async def _context_buffs(db: Any, chat_id: int, user_id: int) -> dict[str, float]:
    result = {
        "boss_damage": 0.0, "boss_crit_chance": 0.0, "influence": 0.0,
        "activity": 0.0, "penalty_reduction": 0.0, "sabotage_reduction": 0.0,
        "game_reward": 0.0, "rare_reward": 0.0, "second_chance": 0.0,
    }
    type_key = await _today_type_key(db, chat_id, user_id)
    type_modifiers = {
        "chicken": {"penalty_reduction": 0.05},
        "eagle": {"influence": 0.05},
        "hawk": {"boss_crit_chance": 0.04},
        "pigeon": {"second_chance": 0.05},
        "bullfinch": {"rare_reward": 0.03},
        "salty": {"game_reward": 0.02},
        "nasty": {"activity": 0.03},
        "acidic": {"boss_damage": 0.05},
        "sly": {"influence": 0.02, "sabotage_reduction": 0.10},
        "raven": {"rare_reward": 0.06},
    }
    for key, value in type_modifiers.get(type_key, {}).items():
        result[key] += value
    community = await _community_state(db, chat_id)
    levels = community["levels"]
    result["boss_damage"] += levels.get("community_damage", 0) * 0.02
    result["influence"] += levels.get("community_influence", 0) * 0.01
    result["penalty_reduction"] += levels.get("community_defense", 0) * 0.02
    result["game_reward"] += levels.get("community_luck", 0) * 0.015
    return result


async def _effect_row(db: Any, chat_id: int, user_id: int, effect_key: str):
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT * FROM talent_active_effects WHERE chat_id=? AND user_id=? AND effect_key=? AND expires_at>? AND charges>0",
        (chat_id, user_id, effect_key, int(time.time())),
    )
    return await cursor.fetchone()


async def _consume_effect(db: Any, chat_id: int, user_id: int, effect_key: str) -> bool:
    row = await _effect_row(db, chat_id, user_id, effect_key)
    if row is None:
        return False
    conn = talents._conn(db)
    async with db.lock:
        if int(row["charges"]) <= 1:
            await conn.execute(
                "DELETE FROM talent_active_effects WHERE chat_id=? AND user_id=? AND effect_key=?",
                (chat_id, user_id, effect_key),
            )
        else:
            await conn.execute(
                "UPDATE talent_active_effects SET charges=charges-1 WHERE chat_id=? AND user_id=? AND effect_key=?",
                (chat_id, user_id, effect_key),
            )
        await conn.commit()
    return True


async def _counter_change(db: Any, chat_id: int, user_id: int, key: str, delta: int, period: str = "all") -> int:
    conn = talents._conn(db)
    now = int(time.time())
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO talent_counters(chat_id,user_id,counter_key,period_key,value,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(chat_id,user_id,counter_key,period_key)
            DO UPDATE SET value=MAX(0,talent_counters.value+excluded.value),updated_at=excluded.updated_at
            """,
            (chat_id, user_id, key, period, delta, now),
        )
        cursor = await conn.execute(
            "SELECT value FROM talent_counters WHERE chat_id=? AND user_id=? AND counter_key=? AND period_key=?",
            (chat_id, user_id, key, period),
        )
        row = await cursor.fetchone()
        await conn.commit()
    return int(row["value"] if row else 0)


async def _counter_reset(db: Any, chat_id: int, user_id: int, key: str, period: str = "all") -> None:
    conn = talents._conn(db)
    async with db.lock:
        await conn.execute(
            "DELETE FROM talent_counters WHERE chat_id=? AND user_id=? AND counter_key=? AND period_key=?",
            (chat_id, user_id, key, period),
        )
        await conn.commit()


async def _activate_ability(db: Any, chat_id: int, user_id: int, ability_id: str) -> dict[str, Any]:
    spec = SPECIAL_SKILLS.get(ability_id)
    if not spec or spec.get("kind") != "active":
        raise ValueError("Неизвестная активная способность.")
    levels = await talents.levels_for(db, chat_id, user_id)
    if levels.get(ability_id, 0) <= 0:
        raise ValueError("Сначала открой эту способность в древе.")
    conn = talents._conn(db)
    now = int(time.time())
    cursor = await conn.execute(
        "SELECT ready_at FROM talent_active_cooldowns WHERE chat_id=? AND user_id=? AND ability_key=?",
        (chat_id, user_id, ability_id),
    )
    row = await cursor.fetchone()
    if row and int(row["ready_at"]) > now:
        raise ValueError(f"Способность восстановится через {talents.core_human_duration(int(row['ready_at'])-now)}.")
    buffs = talents.calculate_buffs(levels)
    reduction = min(0.40, float(buffs.get("active_cooldown_reduction", 0.0)))
    ready_at = now + int(int(spec["cooldown"]) * (1.0 - reduction))
    effect_key = str(spec["effect_key"])
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO talent_active_cooldowns(chat_id,user_id,ability_key,ready_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,user_id,ability_key) DO UPDATE SET ready_at=excluded.ready_at
            """,
            (chat_id, user_id, ability_id, ready_at),
        )
        await conn.execute(
            """
            INSERT INTO talent_active_effects(chat_id,user_id,effect_key,expires_at,charges)
            VALUES(?,?,?,?,1)
            ON CONFLICT(chat_id,user_id,effect_key) DO UPDATE SET expires_at=excluded.expires_at,charges=1
            """,
            (chat_id, user_id, effect_key, now + 24 * 60 * 60),
        )
        await conn.commit()
    return {"ok": True, "ability_id": ability_id, "effect_key": effect_key, "ready_at": ready_at}


def _rarity_for(skill_id: str, spec: dict[str, Any]) -> str:
    if skill_id in SPECIAL_SKILLS:
        return str(spec.get("rarity", "epic"))
    if skill_id in {item for group in EXCLUSIVE_GROUPS.values() for item in group}:
        return "legendary"
    cost = int(spec.get("cost", 1))
    return "rare" if cost >= 2 else "common"


def _preview_for(levels: dict[str, int], skill_id: str) -> dict[str, Any]:
    spec = talents.SKILLS[skill_id]
    current = levels.get(skill_id, 0)
    if current >= int(spec.get("max", 1)):
        return {"lines": ["Навык уже прокачан до максимума."], "current": current, "next": current}
    before = talents.calculate_buffs(levels)
    after_levels = dict(levels)
    after_levels[skill_id] = current + 1
    after = talents.calculate_buffs(after_levels)
    lines: list[str] = []
    for key, label in BUFF_LABELS.items():
        old = float(before.get(key, 0.0))
        new = float(after.get(key, 0.0))
        if abs(new - old) > 0.00001:
            lines.append(f"{label}: {old*100:.1f}% → {new*100:.1f}%")
    if not lines:
        lines.append(str(spec.get("effect", "Открывает новую механику или активную способность.")))
    return {"lines": lines, "current": current, "next": current + 1}


async def _builds_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    conn = talents._conn(db)
    await conn.execute(
        "INSERT OR IGNORE INTO talent_meta(chat_id,user_id) VALUES(?,?)",
        (chat_id, user_id),
    )
    await conn.commit()
    cursor = await conn.execute(
        "SELECT free_reset_used,last_build_switch_at,active_build_slot FROM talent_meta WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    meta = await cursor.fetchone()
    cursor = await conn.execute(
        "SELECT slot,name,updated_at FROM talent_builds WHERE chat_id=? AND user_id=? ORDER BY slot",
        (chat_id, user_id),
    )
    saved = {int(r["slot"]): {"slot": int(r["slot"]), "name": str(r["name"]), "updated_at": int(r["updated_at"])} for r in await cursor.fetchall()}
    return {
        "free_reset": not bool(meta and int(meta["free_reset_used"])),
        "reset_price": RESET_PRICE,
        "switch_ready_in": max(0, int(meta["last_build_switch_at"] if meta else 0) + BUILD_SWITCH_COOLDOWN - int(time.time())),
        "active_slot": int(meta["active_build_slot"]) if meta and meta["active_build_slot"] is not None else None,
        "slots": [saved.get(i, {"slot": i, "name": f"Билд {i}", "empty": True}) for i in range(1, 4)],
    }


async def _save_build(db: Any, chat_id: int, user_id: int, slot: int, name: str) -> dict[str, Any]:
    if slot not in (1, 2, 3):
        raise ValueError("Можно сохранить только три билда.")
    levels = await talents.levels_for(db, chat_id, user_id)
    clean_name = (name or f"Билд {slot}").strip()[:32]
    conn = talents._conn(db)
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO talent_builds(chat_id,user_id,slot,name,levels_json,updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(chat_id,user_id,slot) DO UPDATE SET name=excluded.name,levels_json=excluded.levels_json,updated_at=excluded.updated_at
            """,
            (chat_id, user_id, slot, clean_name, json.dumps(levels, ensure_ascii=False), int(time.time())),
        )
        await conn.commit()
    return await _builds_state(db, chat_id, user_id)


def _validate_build(levels: dict[str, int], total_points: int) -> int:
    for skill_id, level in levels.items():
        spec = talents.SKILLS.get(skill_id)
        if spec is None or int(level) < 0 or int(level) > int(spec.get("max", 1)):
            raise ValueError("Сохранённый билд содержит недоступный навык.")
    for skill_id, level in levels.items():
        if level <= 0:
            continue
        spec = talents.SKILLS[skill_id]
        parents = list(spec.get("parents") or ([] if not spec.get("parent") else [spec.get("parent")]))
        if any(levels.get(str(parent), 0) <= 0 for parent in parents):
            raise ValueError("В сохранённом билде нарушены связи между навыками.")
    for skill_ids in EXCLUSIVE_GROUPS.values():
        if sum(1 for sid in skill_ids if levels.get(sid, 0) > 0) > 1:
            raise ValueError("В сохранённом билде выбрано несколько взаимоисключающих специализаций.")
    spent = _cost_for_levels(levels)
    if spent > total_points:
        raise ValueError("Для этого билда пока не хватает заработанных очков таланта.")
    return spent


async def _load_build(db: Any, chat_id: int, user_id: int, slot: int) -> dict[str, Any]:
    conn = talents._conn(db)
    builds = await _builds_state(db, chat_id, user_id)
    if builds["switch_ready_in"] > 0:
        raise ValueError(f"Переключить билд можно через {builds['switch_ready_in']} сек.")
    cursor = await conn.execute(
        "SELECT levels_json FROM talent_builds WHERE chat_id=? AND user_id=? AND slot=?",
        (chat_id, user_id, slot),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Этот слот ещё пуст.")
    levels = {str(k): int(v) for k, v in json.loads(str(row["levels_json"])).items()}
    profile = await talents.sync_profile(db, chat_id, user_id)
    spent = _validate_build(levels, int(profile["total"]))
    context = await _unlock_context(db, chat_id, user_id)
    for skill_id, level in levels.items():
        spec = SPECIAL_SKILLS.get(skill_id)
        if level > 0 and spec and spec.get("kind") == "hidden" and not _hidden_unlocked(spec, context):
            raise ValueError(f"Скрытый навык «{spec['name']}» сейчас недоступен.")
    now = int(time.time())
    async with db.lock:
        await conn.execute("DELETE FROM talent_levels WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        for skill_id, level in levels.items():
            if level > 0:
                await conn.execute(
                    "INSERT INTO talent_levels(chat_id,user_id,skill_id,level,updated_at) VALUES(?,?,?,?,?)",
                    (chat_id, user_id, skill_id, level, now),
                )
        await conn.execute(
            "UPDATE talent_profiles SET spent_points=?,updated_at=? WHERE chat_id=? AND user_id=?",
            (spent, now, chat_id, user_id),
        )
        await conn.execute(
            "UPDATE talent_meta SET last_build_switch_at=?,active_build_slot=? WHERE chat_id=? AND user_id=?",
            (now, slot, chat_id, user_id),
        )
        await conn.commit()
    return await talents.talent_state(db, chat_id, user_id)


async def _reset_build(core: Any, db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    builds = await _builds_state(db, chat_id, user_id)
    player = await db.get_player(chat_id, user_id)
    if player is None:
        raise ValueError("Игрок не найден.")
    if not builds["free_reset"]:
        if int(player.points) < RESET_PRICE:
            raise ValueError(f"Для сброса нужно {RESET_PRICE} очков влияния.")
        await db.add_points_with_balance(chat_id, user_id, -RESET_PRICE, "admin_talent_reset")
    conn = talents._conn(db)
    async with db.lock:
        await conn.execute("DELETE FROM talent_levels WHERE chat_id=? AND user_id=?", (chat_id, user_id))
        await conn.execute(
            "UPDATE talent_profiles SET spent_points=0,updated_at=? WHERE chat_id=? AND user_id=?",
            (int(time.time()), chat_id, user_id),
        )
        await conn.execute(
            "UPDATE talent_meta SET free_reset_used=1,active_build_slot=NULL WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        await conn.commit()
    return await talents.talent_state(db, chat_id, user_id)


def _human_duration(core: Any, seconds: int) -> str:
    try:
        return core.human_duration(max(0, int(seconds)))
    except Exception:
        return f"{max(0, int(seconds))} сек."


def install_mastery(core: Any) -> None:
    if getattr(talents, "_mastery_installed", False):
        return
    talents._mastery_installed = True
    talents.SKILLS.update(SPECIAL_SKILLS)
    talents.core_human_duration = core.human_duration

    original_entitled = talents._entitled_points
    talents._entitled_points = lambda influence: max(original_entitled(influence), min(45, 5 + max(0, int(influence)) // 300))

    original_ensure = talents.ensure_schema
    async def ensure_schema(db: Any) -> None:
        await original_ensure(db)
        await _ensure_mastery_schema(db)
    talents.ensure_schema = ensure_schema

    original_calculate = talents.calculate_buffs
    def calculate_buffs(levels: dict[str, int]) -> dict[str, float]:
        buffs = original_calculate(levels)
        buffs.setdefault("active_cooldown_reduction", 0.0)
        buffs.setdefault("combo_double", 0.0)
        buffs.setdefault("crit_break_shield", 0.0)
        buffs.setdefault("loss_pity", 0.0)
        if levels.get("hybrid_popularity", 0):
            buffs["influence"] += 0.02; buffs["game_reward"] += 0.03
        if levels.get("hybrid_loudcrit", 0):
            buffs["boss_crit_chance"] += 0.02; buffs["influence"] += 0.01
        if levels.get("hybrid_insurance", 0):
            buffs["second_chance"] += 0.05; buffs["penalty_reduction"] += 0.03
        buffs["combo_double"] = float(levels.get("mechanic_combo", 0) > 0)
        buffs["crit_break_shield"] = float(levels.get("mechanic_break_shield", 0) > 0)
        buffs["loss_pity"] = float(levels.get("mechanic_pity", 0) > 0)
        buffs["active_cooldown_reduction"] += levels.get("mechanic_taskflow", 0) * 0.15
        if levels.get("hidden_sly", 0):
            buffs["influence"] += 0.04; buffs["sabotage_reduction"] += 0.05
        if levels.get("hidden_raven", 0): buffs["rare_reward"] += 0.05
        if levels.get("hidden_hero", 0): buffs["boss_damage"] += 0.05
        if levels.get("hidden_saboteur", 0): buffs["activity"] += 0.04
        if levels.get("hidden_veteran", 0):
            buffs["boss_damage"] += 0.03; buffs["boss_crit_chance"] += 0.02
        active_sets = {item["key"] for item in _sets_for(levels) if item["active"]}
        if "ego_breaker" in active_sets: buffs["boss_damage"] += 0.03
        if "center_attention" in active_sets: buffs["influence"] += 0.03
        if "iron_story" in active_sets: buffs["penalty_reduction"] += 0.03
        if "fortune_favorite" in active_sets: buffs["game_reward"] += 0.03
        return buffs
    talents.calculate_buffs = calculate_buffs

    async def buffs_for(db: Any, chat_id: int, user_id: int) -> dict[str, float]:
        buffs = calculate_buffs(await talents.levels_for(db, chat_id, user_id))
        for key, value in (await _context_buffs(db, chat_id, user_id)).items():
            buffs[key] = float(buffs.get(key, 0.0)) + float(value)
        return buffs
    talents.buffs_for = buffs_for

    original_upgrade = talents.upgrade_skill
    async def upgrade_skill(db: Any, chat_id: int, user_id: int, skill_id: str) -> dict[str, Any]:
        spec = talents.SKILLS.get(skill_id)
        if spec is None:
            raise ValueError("Неизвестный навык.")
        levels = await talents.levels_for(db, chat_id, user_id)
        parents = list(spec.get("parents") or ([] if not spec.get("parent") else [spec.get("parent")]))
        if any(levels.get(str(parent), 0) <= 0 for parent in parents):
            raise ValueError("Сначала открой все связанные предыдущие навыки.")
        group = _exclusive_group(skill_id)
        if group and levels.get(skill_id, 0) <= 0:
            chosen = [sid for sid in group[1] if sid != skill_id and levels.get(sid, 0) > 0]
            if chosen:
                chosen_name = talents.SKILLS[chosen[0]]["name"]
                raise ValueError(f"Уже выбрана специализация «{chosen_name}». Сначала сбрось билд.")
        if spec.get("kind") == "hidden":
            context = await _unlock_context(db, chat_id, user_id)
            if not _hidden_unlocked(spec, context):
                raise ValueError(str(spec.get("clue", "Условие скрытого таланта ещё не выполнено.")))
        return await original_upgrade(db, chat_id, user_id, skill_id)
    talents.upgrade_skill = upgrade_skill

    original_adjusted = talents.adjusted_delta
    async def adjusted_delta(db: Any, chat_id: int, user_id: int, delta: int, reason: str) -> int:
        result = await original_adjusted(db, chat_id, user_id, delta, reason)
        reason_text = str(reason or "").casefold()
        protected = any(word in reason_text for word in ("admin", "transfer", "restore", "hero_day", "stake"))
        game = any(word in reason_text for word in ("coin", "dice", "roulette", "game", "fate", "boss"))
        task = any(word in reason_text for word in ("task", "mission", "action"))
        levels = await talents.levels_for(db, chat_id, user_id)
        if not protected and result > 0:
            if await _consume_effect(db, chat_id, user_id, "double_reward"):
                result *= 2
            gamble = await _effect_row(db, chat_id, user_id, "gamble_reward") if game else None
            if gamble is not None:
                await _consume_effect(db, chat_id, user_id, "gamble_reward")
                result *= 2
            if game and levels.get("mechanic_pity", 0):
                conn = talents._conn(db)
                cursor = await conn.execute(
                    "SELECT value FROM talent_counters WHERE chat_id=? AND user_id=? AND counter_key='game_losses' AND period_key='all'",
                    (chat_id, user_id),
                )
                row = await cursor.fetchone()
                losses = int(row["value"] if row else 0)
                if losses:
                    result = int(round(result * (1.0 + min(0.30, losses * 0.05))))
                    await _counter_reset(db, chat_id, user_id, "game_losses")
            if task and levels.get("mechanic_taskflow", 0):
                conn = talents._conn(db)
                async with db.lock:
                    await conn.execute(
                        "UPDATE talent_active_cooldowns SET ready_at=MAX(?,ready_at-1800) WHERE chat_id=? AND user_id=?",
                        (int(time.time()), chat_id, user_id),
                    )
                    await conn.commit()
        elif not protected and result < 0:
            if await _consume_effect(db, chat_id, user_id, "cancel_penalty"):
                return 0
            gamble = await _effect_row(db, chat_id, user_id, "gamble_reward") if game else None
            if gamble is not None:
                await _consume_effect(db, chat_id, user_id, "gamble_reward")
                result = -max(1, int(round(abs(result) * 1.5)))
            if game and levels.get("mechanic_pity", 0):
                await _counter_change(db, chat_id, user_id, "game_losses", 1)
        return result
    talents.adjusted_delta = adjusted_delta

    original_boss_extra = talents.apply_extra_boss_damage
    async def apply_extra_boss_damage(core_obj: Any, db: Any, boss_id: str, chat_id: int, user_id: int, result: dict[str, Any], *, ability: bool) -> dict[str, Any]:
        updated = await original_boss_extra(core_obj, db, boss_id, chat_id, user_id, result, ability=ability)
        if not updated.get("ok") or int(updated.get("damage", 0)) <= 0 or updated.get("defeated"):
            return updated
        levels = await talents.levels_for(db, chat_id, user_id)
        base = int(updated.get("damage", 0))
        extra = 0
        labels: list[str] = []
        if not ability and levels.get("mechanic_combo", 0):
            count = await _counter_change(db, chat_id, user_id, "boss_combo", 1, _period_day())
            if count % 5 == 0:
                extra += base; labels.append("пятый удар")
        if not ability and await _consume_effect(db, chat_id, user_id, "guaranteed_crit"):
            buffs = await talents.buffs_for(db, chat_id, user_id)
            extra += int(round(base * (1.0 + float(buffs.get("boss_crit_power", 0.0)))))
            labels.append("Последнее слово")
        if not ability and levels.get("hybrid_retaliation", 0):
            conn = talents._conn(db)
            cursor = await conn.execute(
                "SELECT protected FROM boss_fighters WHERE boss_id=? AND user_id=?",
                (boss_id, user_id),
            )
            fighter = await cursor.fetchone()
            if fighter and int(fighter["protected"]):
                extra += int(round(base * 0.5)); labels.append("ответная агрессия")
        conn = talents._conn(db)
        if levels.get("mechanic_break_shield", 0) and (updated.get("critical") or updated.get("talent_critical")):
            async with db.lock:
                await conn.execute("UPDATE boss_battles SET shield_hits=0 WHERE boss_id=?", (boss_id,))
                await conn.commit()
            labels.append("щит разбит")
        if extra <= 0:
            if labels:
                result2 = dict(updated); result2["mastery_labels"] = labels; return result2
            return updated
        now = int(time.time())
        async with db.lock:
            cursor = await conn.execute("SELECT hp,max_hp,phase FROM boss_battles WHERE boss_id=?", (boss_id,))
            battle = await cursor.fetchone()
            if battle is None:
                return updated
            actual = min(int(battle["hp"]), extra)
            hp_after = max(0, int(battle["hp"]) - actual)
            phase_after = core_obj.boss_phase_for_hp(hp_after, int(battle["max_hp"]))
            await conn.execute(
                "UPDATE boss_battles SET hp=?,phase=?,last_attacker_id=? WHERE boss_id=?",
                (hp_after, phase_after, user_id, boss_id),
            )
            await conn.execute(
                "UPDATE boss_fighters SET damage_done=damage_done+? WHERE boss_id=? AND user_id=?",
                (actual, boss_id, user_id),
            )
            await conn.execute(
                "INSERT INTO boss_logs(boss_id,log_text,created_at) VALUES(?,?,?)",
                (boss_id, f"✨ Мастерство талантов ({', '.join(labels)}): −{actual} HP.", now),
            )
            await conn.commit()
        result2 = dict(updated)
        result2.update({"damage": base + actual, "hp": hp_after, "phase": phase_after,
                        "phase_changed": bool(updated.get("phase_changed")) or phase_after != int(battle["phase"]),
                        "defeated": hp_after <= 0, "mastery_bonus_damage": actual, "mastery_labels": labels})
        return result2
    talents.apply_extra_boss_damage = apply_extra_boss_damage

    original_state = talents.talent_state
    async def talent_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_state(db, chat_id, user_id)
        levels = await talents.levels_for(db, chat_id, user_id)
        context = await _unlock_context(db, chat_id, user_id)
        data["buffs"] = await talents.buffs_for(db, chat_id, user_id)
        data["sets"] = _sets_for(levels)
        data["community"] = await _community_state(db, chat_id)
        data["builds"] = await _builds_state(db, chat_id, user_id)
        data["today_type_key"] = context.get("type_key", "")
        meta: dict[str, Any] = {}
        for skill_id, spec in talents.SKILLS.items():
            rarity = _rarity_for(skill_id, spec)
            hidden = spec.get("kind") == "hidden"
            visible = not hidden or levels.get(skill_id, 0) > 0 or _hidden_unlocked(spec, context)
            parents = list(spec.get("parents") or ([] if not spec.get("parent") else [spec.get("parent")]))
            unlocked = all(levels.get(str(parent), 0) > 0 for parent in parents)
            if hidden:
                unlocked = unlocked and _hidden_unlocked(spec, context)
            group = _exclusive_group(skill_id)
            blocked_by = None
            if group and levels.get(skill_id, 0) <= 0:
                blocked = [sid for sid in group[1] if sid != skill_id and levels.get(sid, 0) > 0]
                blocked_by = talents.SKILLS[blocked[0]]["name"] if blocked else None
                if blocked_by:
                    unlocked = False
            display_name = str(spec.get("name", skill_id)) if visible else "Неизвестный талант"
            meta[skill_id] = {
                "id": skill_id, "name": display_name, "real_name": str(spec.get("name", skill_id)),
                "branch": spec.get("branch"), "kind": spec.get("kind", "passive"),
                "rarity": rarity, "rarity_title": RARITY_LABELS.get(rarity, rarity),
                "level": levels.get(skill_id, 0), "max": int(spec.get("max", 1)), "cost": int(spec.get("cost", 1)),
                "parents": parents, "unlocked": unlocked, "visible": visible, "hidden": hidden,
                "clue": spec.get("clue"), "effect": spec.get("effect"), "icon": spec.get("icon"),
                "blocked_by": blocked_by, "preview": _preview_for(levels, skill_id),
            }
        data["skill_meta"] = meta
        data["special_skills"] = [meta[sid] for sid in SPECIAL_SKILLS]
        data["specializations"] = {
            group: next((talents.SKILLS[sid]["name"] for sid in ids if levels.get(sid, 0) > 0), None)
            for group, ids in EXCLUSIVE_GROUPS.items()
        }
        data["branch_completion"] = {
            branch_name: {
                "learned": sum(1 for sid, spec in talents.SKILLS.items() if spec.get("branch") == branch_name and levels.get(sid, 0) > 0),
                "total": sum(1 for spec in talents.SKILLS.values() if spec.get("branch") == branch_name),
            }
            for branch_name in ("damage", "influence", "defense", "rewards", "special")
        }
        conn = talents._conn(db)
        now = int(time.time())
        cursor = await conn.execute(
            "SELECT ability_key,ready_at FROM talent_active_cooldowns WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        cooldowns = {str(r["ability_key"]): max(0, int(r["ready_at"]) - now) for r in await cursor.fetchall()}
        cursor = await conn.execute(
            "SELECT effect_key,expires_at,charges FROM talent_active_effects WHERE chat_id=? AND user_id=? AND expires_at>? AND charges>0",
            (chat_id, user_id, now),
        )
        effects = {str(r["effect_key"]): {"expires_in": int(r["expires_at"]) - now, "charges": int(r["charges"])} for r in await cursor.fetchall()}
        data["active_abilities"] = [
            {**meta[sid], "ready_in": cooldowns.get(sid, 0), "active_effect": effects.get(str(SPECIAL_SKILLS[sid]["effect_key"]))}
            for sid in SPECIAL_SKILLS if SPECIAL_SKILLS[sid].get("kind") == "active"
        ]
        return data
    talents.talent_state = talent_state

    original_commands = core.group_bot_commands
    def group_commands() -> list[BotCommand]:
        commands = original_commands()
        known = {item.command for item in commands}
        additions = [
            BotCommand(command="builds", description="Сохранённые билды талантов"),
            BotCommand(command="active_talents", description="Активные способности талантов"),
            BotCommand(command="community_tree", description="Общее древо беседы"),
        ]
        commands.extend(item for item in additions if item.command not in known)
        return commands
    core.group_bot_commands = group_commands

    @core.router.message(Command("builds"))
    async def cmd_builds(message: Message) -> None:
        if not message.from_user or not await core.require_group_command(message, "Билды талантов"):
            return
        await core.prepare_command_player(message)
        builds = await _builds_state(core.db, message.chat.id, message.from_user.id)
        lines = ["🧩 <b>БИЛДЫ ТАЛАНТОВ</b>"]
        for item in builds["slots"]:
            lines.append(f"{item['slot']}. <b>{html.escape(str(item['name']))}</b>" + (" — пусто" if item.get("empty") else ""))
        lines.append("\nОткрывай /talents, чтобы сохранять, переключать и сбрасывать билды.")
        await message.answer("\n".join(lines))

    @core.router.message(Command("active_talents"))
    async def cmd_active_talents(message: Message) -> None:
        if not message.from_user or not await core.require_group_command(message, "Активные таланты"):
            return
        await core.prepare_command_player(message)
        state = await talents.talent_state(core.db, message.chat.id, message.from_user.id)
        lines = ["✨ <b>АКТИВНЫЕ СПОСОБНОСТИ</b>"]
        for item in state["active_abilities"]:
            status = "не открыт" if item["level"] <= 0 else (f"откат: {_human_duration(core, item['ready_in'])}" if item["ready_in"] else "готово")
            lines.append(f"• <b>{html.escape(item['real_name'])}</b> — {status}")
        lines.append("\nАктивировать их можно внутри /talents.")
        await message.answer("\n".join(lines))

    @core.router.message(Command("community_tree"))
    async def cmd_community_tree(message: Message) -> None:
        if not await core.require_group_command(message, "Общее древо беседы"):
            return
        state = await _community_state(core.db, message.chat.id)
        lines = ["🏛 <b>ОБЩЕЕ ДРЕВО БЕСЕДЫ</b>", f"Свободно общих очков: <b>{state['points']['available']}</b>"]
        for item in state["skills"]:
            lines.append(f"{item['emoji']} <b>{item['title']}</b> {item['level']}/{item['max']} — {item['effect']}")
        lines.append("\nОбщие очки появляются за личную прокачку участников и победы над боссом.")
        await message.answer("\n".join(lines))

    def parse_chat_id(start_param: str | None, payload: dict[str, Any], request: web.Request) -> int | None:
        raw = str(start_param or "")
        if raw.startswith(talents.TALENT_PREFIX):
            raw = raw[len(talents.TALENT_PREFIX):]
        else:
            raw = str(payload.get("chat_id") or request.query.get("chat_id") or "")
        try:
            return int(raw)
        except ValueError:
            return None

    async def auth_payload(request: web.Request):
        user, start_param = core._webapp_auth(request)
        if user is None:
            raise PermissionError(start_param or "Нет авторизации.")
        payload = await core._webapp_json(request)
        chat_id = parse_chat_id(start_param, payload, request)
        if chat_id is None:
            raise ValueError("Не найдена беседа.")
        if await core.db.get_player(chat_id, user.id) is None:
            raise PermissionError("Игрок не найден в этой беседе.")
        return user, chat_id, payload

    async def api_activate(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            result = await _activate_ability(core.db, chat_id, user.id, str(payload.get("ability_id") or ""))
            result["state"] = await talents.talent_state(core.db, chat_id, user.id)
            return web.json_response(result)
        except PermissionError as exc:
            return core._webapp_error(str(exc), 403)
        except ValueError as exc:
            return core._webapp_error(str(exc))

    async def api_save_build(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            result = await _save_build(core.db, chat_id, user.id, int(payload.get("slot") or 0), str(payload.get("name") or ""))
            return web.json_response({"ok": True, "builds": result})
        except (PermissionError, ValueError) as exc:
            return core._webapp_error(str(exc), 403 if isinstance(exc, PermissionError) else 400)

    async def api_load_build(request: web.Request) -> web.Response:
        try:
            user, chat_id, payload = await auth_payload(request)
            state = await _load_build(core.db, chat_id, user.id, int(payload.get("slot") or 0))
            return web.json_response(state)
        except (PermissionError, ValueError) as exc:
            return core._webapp_error(str(exc), 403 if isinstance(exc, PermissionError) else 400)

    async def api_reset(request: web.Request) -> web.Response:
        try:
            user, chat_id, _ = await auth_payload(request)
            return web.json_response(await _reset_build(core, core.db, chat_id, user.id))
        except (PermissionError, ValueError) as exc:
            return core._webapp_error(str(exc), 403 if isinstance(exc, PermissionError) else 400)

    async def api_community_upgrade(request: web.Request) -> web.Response:
        try:
            _, chat_id, payload = await auth_payload(request)
            result = await _community_upgrade(core.db, chat_id, str(payload.get("skill_id") or ""))
            return web.json_response({"ok": True, "community": result})
        except (PermissionError, ValueError) as exc:
            return core._webapp_error(str(exc), 403 if isinstance(exc, PermissionError) else 400)

    original_start = core.start_webapp_server
    async def start_with_mastery(bot: Any):
        original_application = core.web.Application
        def application_factory(*args: Any, **kwargs: Any):
            app = original_application(*args, **kwargs)
            app.router.add_post("/talents/api/activate", api_activate)
            app.router.add_post("/talents/api/save-build", api_save_build)
            app.router.add_post("/talents/api/load-build", api_load_build)
            app.router.add_post("/talents/api/reset", api_reset)
            app.router.add_post("/talents/api/community-upgrade", api_community_upgrade)
            return app
        core.web.Application = application_factory
        try:
            return await original_start(bot)
        finally:
            core.web.Application = original_application
    core.start_webapp_server = start_with_mastery
