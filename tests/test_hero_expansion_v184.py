from __future__ import annotations

import asyncio
import importlib.util
import sqlite3
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


# Локальный CI-smoke может запускаться без установленных Telegram-зависимостей.
# В рабочем окружении проекта используются настоящие aiogram-классы.
try:
    import aiogram  # noqa: F401
except ModuleNotFoundError:
    aiogram = types.ModuleType("aiogram")
    aiogram.F = SimpleNamespace(data=SimpleNamespace(startswith=lambda *_: None, __eq__=lambda *_: None))
    dispatcher = types.ModuleType("aiogram.dispatcher")
    event = types.ModuleType("aiogram.dispatcher.event")
    bases = types.ModuleType("aiogram.dispatcher.event.bases")
    class SkipHandler(Exception):
        pass
    bases.SkipHandler = SkipHandler
    filters = types.ModuleType("aiogram.filters")
    class Command:
        def __init__(self, *args, **kwargs):
            self.args = args
    filters.Command = Command
    types_mod = types.ModuleType("aiogram.types")
    for name in ("CallbackQuery", "InlineKeyboardButton", "InlineKeyboardMarkup", "Message", "MessageReactionUpdated"):
        setattr(types_mod, name, type(name, (), {}))
    sys.modules.update({
        "aiogram": aiogram,
        "aiogram.dispatcher": dispatcher,
        "aiogram.dispatcher.event": event,
        "aiogram.dispatcher.event.bases": bases,
        "aiogram.filters": filters,
        "aiogram.types": types_mod,
    })

MODULE_PATH = Path(__file__).resolve().parents[1] / "hero_expansion_v184.py"
spec = importlib.util.spec_from_file_location("hero_expansion_v184", MODULE_PATH)
hero = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(hero)


class AsyncCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor
        self.rowcount = cursor.rowcount

    async def fetchone(self):
        return self.cursor.fetchone()

    async def fetchall(self):
        return self.cursor.fetchall()


class AsyncConnection:
    def __init__(self):
        self.raw = sqlite3.connect(":memory:", isolation_level=None)
        self.raw.row_factory = sqlite3.Row
        self.raw.execute("PRAGMA foreign_keys=ON")

    async def execute(self, sql, params=()):
        return AsyncCursor(self.raw.execute(sql, params))

    async def executescript(self, script):
        self.raw.executescript(script)

    async def commit(self):
        self.raw.commit()

    async def rollback(self):
        self.raw.rollback()


class FakeDB:
    def __init__(self):
        self.connection = AsyncConnection()
        self.lock = asyncio.Lock()

    def _require_connection(self):
        return self.connection

    async def get_player(self, chat_id, user_id):
        cur = await self.connection.execute(
            "SELECT * FROM players WHERE chat_id=? AND user_id=?", (chat_id, user_id)
        )
        row = await cur.fetchone()
        if row is None:
            return None
        return SimpleNamespace(
            chat_id=row["chat_id"], user_id=row["user_id"], username=row["username"],
            full_name=row["full_name"], points=row["points"], message_count=row["message_count"],
        )

    async def rank_of(self, chat_id, user_id):
        cur = await self.connection.execute(
            "SELECT user_id FROM players WHERE chat_id=? ORDER BY points DESC", (chat_id,)
        )
        ids = [row["user_id"] for row in await cur.fetchall()]
        return (ids.index(user_id) + 1 if user_id in ids else len(ids) + 1, len(ids))


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text, **kwargs):
        self.messages.append((chat_id, text))
        return SimpleNamespace(message_id=len(self.messages))


class HeroExpansionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = FakeDB()
        self.core = SimpleNamespace(db=self.db)
        conn = self.db.connection
        await conn.executescript(
            """
            CREATE TABLE players(
              chat_id INTEGER NOT NULL,user_id INTEGER NOT NULL,username TEXT,full_name TEXT NOT NULL,
              points INTEGER NOT NULL DEFAULT 0,message_count INTEGER NOT NULL DEFAULT 0,
              created_at INTEGER NOT NULL DEFAULT 0,updated_at INTEGER NOT NULL DEFAULT 0,
              PRIMARY KEY(chat_id,user_id)
            );
            CREATE TABLE score_log(
              id INTEGER PRIMARY KEY AUTOINCREMENT,chat_id INTEGER,user_id INTEGER,
              delta INTEGER,reason TEXT,created_at INTEGER
            );
            CREATE TABLE today_type_assignments(
              chat_id INTEGER,user_id INTEGER,type_key TEXT,assigned_at INTEGER,expires_at INTEGER,
              PRIMARY KEY(chat_id,user_id)
            );
            """
        )
        await hero._migrate(self.core, self.db)
        now = hero._now()
        for user_id, points, name in ((1, 4_000_000, "Илья"), (2, 500_000, "Нара"), (3, 50_000, "Максим")):
            await conn.execute(
                "INSERT INTO players(chat_id,user_id,username,full_name,points,message_count,created_at,updated_at) VALUES(-100,?,?,?,?,20,?,?)",
                (user_id, name.lower(), name, points, now, now),
            )
        await conn.commit()

    async def asyncTearDown(self):
        self.db.connection.raw.close()

    async def test_01_shop_prices_are_scaled(self):
        self.assertEqual(next(x for x in hero.SHOP_ITEMS if x["key"] == "custom_title")["price"], 150_000)
        self.assertEqual(next(x for x in hero.SHOP_ITEMS if x["key"] == "chat_event")["price"], 500_000)

    async def test_02_at_least_25_achievements(self):
        self.assertGreaterEqual(len(hero.ACHIEVEMENTS), 25)

    async def test_03_all_required_tables_created(self):
        cur = await self.db.connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        names = {row["name"] for row in await cur.fetchall()}
        required = {
            "influence_transactions", "shop_items", "shop_purchases", "user_inventory",
            "user_effects", "story_events", "weekly_story_reports", "user_relationships",
            "achievement_definitions", "user_achievements", "achievement_progress",
            "inactive_return_events", "user_daily_statistics", "user_chat_statistics",
            "chat_statistics", "profile_frames", "user_profile_customization",
        }
        self.assertTrue(required.issubset(names))

    async def test_04_successful_change(self):
        result = await hero.change_influence(
            self.core, chat_id=-100, user_id=1, amount=25_000, reason="test_win",
            operation_id="test:change:1", check_achievements=False,
        )
        self.assertEqual(result["balance"], 4_025_000)

    async def test_05_duplicate_operation_is_idempotent(self):
        first = await hero.change_influence(
            self.core, chat_id=-100, user_id=1, amount=10_000, reason="test",
            operation_id="test:duplicate", check_achievements=False,
        )
        second = await hero.change_influence(
            self.core, chat_id=-100, user_id=1, amount=10_000, reason="test",
            operation_id="test:duplicate", check_achievements=False,
        )
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual((await self.db.get_player(-100, 1)).points, 4_010_000)

    async def test_06_insufficient_balance(self):
        with self.assertRaises(hero.InsufficientInfluence):
            await hero.change_influence(
                self.core, chat_id=-100, user_id=3, amount=-100_000, reason="too_much",
                operation_id="test:insufficient", check_achievements=False,
            )

    async def test_07_concurrent_operations_are_serialized(self):
        await asyncio.gather(*[
            hero.change_influence(
                self.core, chat_id=-100, user_id=2, amount=1000, reason="parallel",
                operation_id=f"parallel:{i}", check_achievements=False,
            ) for i in range(10)
        ])
        self.assertEqual((await self.db.get_player(-100, 2)).points, 510_000)

    async def test_08_intervention_cost_range(self):
        values = [hero._intervention_cost() for _ in range(1000)]
        self.assertGreaterEqual(min(values), 1000)
        self.assertLessEqual(max(values), 5000)

    async def test_09_safe_title(self):
        self.assertEqual(hero._safe_title("  Орлиный режиссёр  "), "Орлиный режиссёр")

    async def test_10_title_rejects_link(self):
        with self.assertRaises(hero.InfluenceError):
            hero._safe_title("https://example.com")

    async def test_11_title_rejects_mass_mention(self):
        with self.assertRaises(hero.InfluenceError):
            hero._safe_title("@everyone сюда")

    async def test_12_relationship_statuses(self):
        self.assertEqual(hero._relationship_status(800, 0, 700, 0), "Верные союзники")
        self.assertEqual(hero._relationship_status(0, 800, 0, 0), "Заклятые соперники")
        self.assertEqual(hero._relationship_status(400, 0, 0, 800), "Хаотичный союз")

    async def test_13_relationship_daily_limit(self):
        await hero._update_relationship(self.core, -100, 1, 2, closeness=100)
        await hero._update_relationship(self.core, -100, 1, 2, closeness=100)
        cur = await self.db.connection.execute(
            "SELECT closeness FROM user_relationships WHERE chat_id=-100 AND user_low=1 AND user_high=2"
        )
        self.assertEqual((await cur.fetchone())["closeness"], 60)

    async def test_14_successful_purchase(self):
        bot = FakeBot()
        result = await hero._purchase(
            self.core, bot, SimpleNamespace(id=1), -100,
            {"item_key":"custom_title", "request_id":"purchase-test-0001", "payload":{"title":"Режиссёр хаоса"}},
        )
        self.assertEqual(result["balance"], 3_855_000)
        cur = await self.db.connection.execute("SELECT custom_title FROM user_profile_customization WHERE chat_id=-100 AND user_id=1")
        self.assertEqual((await cur.fetchone())["custom_title"], "Режиссёр хаоса")

    async def test_15_purchase_is_idempotent(self):
        bot = FakeBot()
        data = {"item_key":"extended_stats", "request_id":"purchase-test-0002", "payload":{}}
        first = await hero._purchase(self.core, bot, SimpleNamespace(id=1), -100, data)
        second = await hero._purchase(self.core, bot, SimpleNamespace(id=1), -100, data)
        self.assertFalse(first["duplicate"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(first["balance"], second["balance"])

    async def test_16_purchase_insufficient_balance(self):
        with self.assertRaises(hero.InsufficientInfluence):
            await hero._purchase(
                self.core, FakeBot(), SimpleNamespace(id=3), -100,
                {"item_key":"chat_event", "request_id":"purchase-test-0003", "payload":{}},
            )

    async def test_17_purchase_creates_story_event(self):
        await hero._purchase(
            self.core, FakeBot(), SimpleNamespace(id=1), -100,
            {"item_key":"reroll_today_type", "request_id":"purchase-test-0004", "payload":{}},
        )
        cur = await self.db.connection.execute("SELECT COUNT(*) n FROM story_events WHERE chat_id=-100 AND event_type='shop_purchase'")
        self.assertEqual((await cur.fetchone())["n"], 1)

    async def test_18_achievement_cannot_be_awarded_twice(self):
        first = await hero._award_achievement(self.core, -100, 1, "first_purchase")
        second = await hero._award_achievement(self.core, -100, 1, "first_purchase")
        self.assertTrue(first)
        self.assertFalse(second)

    async def test_19_data_is_separated_by_chat(self):
        now = hero._now()
        await self.db.connection.execute(
            "INSERT INTO players(chat_id,user_id,username,full_name,points,message_count,created_at,updated_at) VALUES(-200,1,'ilia','Илья',100,1,?,?)",
            (now, now),
        )
        await hero.change_influence(
            self.core, chat_id=-200, user_id=1, amount=50, reason="other_chat",
            operation_id="other-chat-op", check_achievements=False,
        )
        self.assertEqual((await self.db.get_player(-200, 1)).points, 150)
        self.assertEqual((await self.db.get_player(-100, 1)).points, 4_000_000)

    async def test_20_story_operation_is_idempotent(self):
        kwargs = dict(
            core=self.core, chat_id=-100, event_type="test", title="Событие",
            description="Описание", participants=[1], operation_id="story:idempotent",
        )
        await hero._record_story(**kwargs)
        await hero._record_story(**kwargs)
        cur = await self.db.connection.execute("SELECT COUNT(*) n FROM story_events WHERE operation_id='story:idempotent'")
        self.assertEqual((await cur.fetchone())["n"], 1)


if __name__ == "__main__":
    unittest.main()
