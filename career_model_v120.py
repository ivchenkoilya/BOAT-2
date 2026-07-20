from __future__ import annotations

import hashlib
import time
from typing import Any

VERSION = "Reality 120 · Карьерное влияние"

CAREER_DUST = 50_000
CAREER_EXTRAS = 200_000
CAREER_SECONDARY = 500_000
CAREER_HERO = 900_000
CAREER_CENTER = 1_500_000

OLD_DUST = 1_000
OLD_EXTRAS = 3_000
OLD_SECONDARY = 6_000
OLD_HERO = 10_000


class CareerThreshold(int):
    def __new__(cls, wallet_value: int, career_value: int):
        obj = int.__new__(cls, int(wallet_value))
        obj.career_points = int(career_value)
        return obj


class CareerAwareInt(int):
    def __new__(cls, wallet_value: int, career_value: int):
        obj = int.__new__(cls, int(wallet_value))
        obj.career_points = max(0, int(career_value))
        return obj

    def _pair(self, other: Any) -> tuple[int, int] | None:
        if isinstance(other, CareerThreshold):
            return int(self.career_points), int(other.career_points)
        return None

    def __lt__(self, other: Any) -> bool:
        pair = self._pair(other)
        return pair[0] < pair[1] if pair else int.__lt__(self, other)

    def __le__(self, other: Any) -> bool:
        pair = self._pair(other)
        return pair[0] <= pair[1] if pair else int.__le__(self, other)

    def __gt__(self, other: Any) -> bool:
        pair = self._pair(other)
        return pair[0] > pair[1] if pair else int.__gt__(self, other)

    def __ge__(self, other: Any) -> bool:
        pair = self._pair(other)
        return pair[0] >= pair[1] if pair else int.__ge__(self, other)

    def __sub__(self, other: Any):
        pair = self._pair(other)
        return pair[0] - pair[1] if pair else int.__sub__(self, other)

    def __truediv__(self, other: Any):
        pair = self._pair(other)
        return pair[0] / pair[1] if pair and pair[1] else int.__truediv__(self, other)


def fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


def now() -> int:
    return int(time.time())


def deterministic_range(key: str, minimum: int, maximum: int) -> int:
    digest = hashlib.sha256(str(key).encode("utf-8")).digest()
    return int(minimum) + int.from_bytes(digest[:8], "big") % (int(maximum) - int(minimum) + 1)


def legacy_to_career(points: int) -> int:
    value = max(0, int(points))
    if value < OLD_DUST:
        return value * CAREER_DUST // OLD_DUST
    if value < OLD_EXTRAS:
        return CAREER_DUST + (value - OLD_DUST) * (CAREER_EXTRAS - CAREER_DUST) // (OLD_EXTRAS - OLD_DUST)
    if value < OLD_SECONDARY:
        return CAREER_EXTRAS + (value - OLD_EXTRAS) * (CAREER_SECONDARY - CAREER_EXTRAS) // (OLD_SECONDARY - OLD_EXTRAS)
    if value < OLD_HERO:
        return CAREER_SECONDARY + (value - OLD_SECONDARY) * (CAREER_HERO - CAREER_SECONDARY) // (OLD_HERO - OLD_SECONDARY)
    return CAREER_HERO


def career_value(points: Any) -> int:
    stored = getattr(points, "career_points", None)
    return max(0, int(stored)) if stored is not None else legacy_to_career(int(points or 0))


def progress(career: int) -> tuple[int, int, str]:
    value = max(0, int(career))
    if value < CAREER_DUST:
        return 0, CAREER_DUST, "Пыли"
    if value < CAREER_EXTRAS:
        return CAREER_DUST, CAREER_EXTRAS, "Массовки"
    if value < CAREER_SECONDARY:
        return CAREER_EXTRAS, CAREER_SECONDARY, "Второстепенной роли"
    if value < CAREER_HERO:
        return CAREER_SECONDARY, CAREER_HERO, "Главного героя"
    if value < CAREER_CENTER:
        return CAREER_HERO, CAREER_CENTER, "Центра Вселенной"
    return CAREER_CENTER, CAREER_CENTER, "вершины"


def progress_bar(career: int, width: int = 12) -> str:
    start, target, _ = progress(career)
    if target <= start:
        return "█" * width
    ratio = max(0.0, min(1.0, (int(career) - start) / (target - start)))
    filled = int(round(width * ratio))
    return "█" * filled + "░" * (width - filled)


async def table_exists(conn: Any, name: str) -> bool:
    cursor = await conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,))
    return await cursor.fetchone() is not None


async def meta_get(core: Any, key: str, default: int = 0) -> int:
    conn = core.db._require_connection()
    cursor = await conn.execute("SELECT value FROM career_meta_v120 WHERE key=?", (key,))
    row = await cursor.fetchone()
    try:
        return int(row["value"]) if row else int(default)
    except (TypeError, ValueError):
        return int(default)


async def meta_set(core: Any, key: str, value: int) -> None:
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            "INSERT INTO career_meta_v120(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(int(value))),
        )
        await conn.commit()


def install_career_model_v120(core: Any) -> None:
    if getattr(core, "_career_model_v120_installed", False):
        return
    core._career_model_v120_installed = True
    core.CAREER_SYSTEM_VERSION = VERSION
    core.DUST_MIN_POINTS = CareerThreshold(OLD_DUST, CAREER_DUST)
    core.EXTRAS_MIN_POINTS = CareerThreshold(OLD_EXTRAS, CAREER_EXTRAS)
    core.SECONDARY_MIN_POINTS = CareerThreshold(OLD_SECONDARY, CAREER_SECONDARY)
    core.HERO_MIN_POINTS = CareerThreshold(OLD_HERO, CAREER_HERO)
    core.CAREER_DUST_MIN = CAREER_DUST
    core.CAREER_EXTRAS_MIN = CAREER_EXTRAS
    core.CAREER_SECONDARY_MIN = CAREER_SECONDARY
    core.CAREER_HERO_MIN = CAREER_HERO
    core.CAREER_CENTER_MIN = CAREER_CENTER
    core.CENTER_UNIVERSE_ROLE = core.Role("hero", "🌌", "Центр Вселенной")

    original_connect = core.Database.connect

    async def connect_with_career(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            columns_cursor = await conn.execute("PRAGMA table_info(players)")
            columns = {str(row["name"]) for row in await columns_cursor.fetchall()}
            if "career_points" not in columns:
                await conn.execute("ALTER TABLE players ADD COLUMN career_points INTEGER NOT NULL DEFAULT 0")
            if "career_initialized" not in columns:
                await conn.execute("ALTER TABLE players ADD COLUMN career_initialized INTEGER NOT NULL DEFAULT 0")
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS career_meta_v120(key TEXT PRIMARY KEY,value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS career_sources_v120(
                    source_type TEXT NOT NULL,source_id TEXT NOT NULL,chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,amount INTEGER NOT NULL,created_at INTEGER NOT NULL,
                    PRIMARY KEY(source_type,source_id,user_id));
                CREATE TABLE IF NOT EXISTS career_log_v120(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,
                    delta INTEGER NOT NULL,reason TEXT NOT NULL,source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,created_at INTEGER NOT NULL);
                CREATE INDEX IF NOT EXISTS idx_career_log_player_v120 ON career_log_v120(chat_id,user_id,id DESC);
                CREATE INDEX IF NOT EXISTS idx_career_rank_v120 ON players(chat_id,career_points DESC);
                """
            )
            cursor = await conn.execute("SELECT value FROM career_meta_v120 WHERE key='migration_done'")
            migrated = await cursor.fetchone()
            if migrated is None:
                await conn.execute(
                    """UPDATE players SET career_points=CASE
                    WHEN points<=0 THEN 0
                    WHEN points<1000 THEN CAST(points*50000/1000 AS INTEGER)
                    WHEN points<3000 THEN 50000+CAST((points-1000)*150000/2000 AS INTEGER)
                    WHEN points<6000 THEN 200000+CAST((points-3000)*300000/3000 AS INTEGER)
                    WHEN points<10000 THEN 500000+CAST((points-6000)*400000/4000 AS INTEGER)
                    ELSE 900000 END,career_initialized=1"""
                )
                cursor = await conn.execute("SELECT COALESCE(MAX(id),0) maximum FROM score_log")
                row = await cursor.fetchone()
                await conn.executemany(
                    "INSERT OR REPLACE INTO career_meta_v120(key,value) VALUES(?,?)",
                    [("migration_done", "1"), ("career_started_at", str(now())), ("score_cursor", str(int(row["maximum"] or 0)))],
                )
            await conn.commit()

    core.Database.connect = connect_with_career

    def row_to_player_v120(row: Any):
        keys = set(row.keys()) if hasattr(row, "keys") else set()
        wallet = int(row["points"] or 0)
        career = int(row["career_points"] or 0) if "career_points" in keys else legacy_to_career(wallet)
        return core.Player(
            chat_id=row["chat_id"], user_id=row["user_id"], username=row["username"],
            full_name=row["full_name"], points=CareerAwareInt(wallet, career),
            message_count=row["message_count"], last_reward_at=row["last_reward_at"],
            last_fate_date=row["last_fate_date"],
        )

    core.Database._row_to_player = staticmethod(row_to_player_v120)
    original_upsert = core.Database.upsert_player

    async def upsert_player_with_career(self: Any, *args: Any, **kwargs: Any):
        player = await original_upsert(self, *args, **kwargs)
        conn = self._require_connection()
        async with self.lock:
            await conn.execute(
                "UPDATE players SET career_initialized=1 WHERE chat_id=? AND user_id=? AND career_initialized=0",
                (int(player.chat_id), int(player.user_id)),
            )
            await conn.commit()
        return await self.get_player(int(player.chat_id), int(player.user_id)) or player

    core.Database.upsert_player = upsert_player_with_career

    def role_by_points_v120(points: int, is_leader: bool):
        career = career_value(points)
        if career >= CAREER_CENTER:
            return core.CENTER_UNIVERSE_ROLE
        if career >= CAREER_HERO:
            return core.HERO
        if career >= CAREER_SECONDARY:
            return core.SECONDARY
        if career >= CAREER_EXTRAS:
            return core.EXTRAS
        if career >= CAREER_DUST:
            return core.DUST
        return core.DECORATION

    def next_role_text_v120(points: int, is_leader: bool) -> str:
        career = career_value(points)
        if career >= CAREER_CENTER:
            return f"⭐ Карьерное влияние: <b>{fmt(career)}</b>. Ты достиг роли Центра Вселенной."
        _, target, title = progress(career)
        return f"⭐ Карьерное влияние: <b>{fmt(career)}</b>. До {title}: <b>{fmt(target-career)}</b>."

    core.role_by_points = role_by_points_v120
    core.next_role_text = next_role_text_v120
    core.career_value = career_value
