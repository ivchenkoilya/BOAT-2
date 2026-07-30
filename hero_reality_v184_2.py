from __future__ import annotations

import json
import time
from typing import Any

from aiohttp import web

import hero_expansion_v184 as expansion
import hero_reality_v184_1 as live1841


LIVE_ROUTE = "/influence-shop-v184/api/live-v1842"

HALF_PRICE_MAP: dict[str, int] = {
    "custom_title": 75_000,
    "roast_member": 40_000,
    "extended_stats": 50_000,
    "profile_frame": 150_000,
    "sabotage_shield": 100_000,
    "mission_boost": 50_000,
    "chat_event": 250_000,
    "hide_losses": 125_000,
    "reroll_today_type": 60_000,
    "story_insurance": 200_000,
}

COSMETIC_ITEMS: dict[str, dict[str, Any]] = {
    "badge_fire": {
        "title": "Знак пламени",
        "description": "Добавляет огненный знак рядом с именем и сразу экипирует его.",
        "price": 12_500,
        "category": "appearance",
        "rarity": "common",
        "cosmetic_type": "badge",
        "cosmetic_key": "fire",
    },
    "badge_lightning": {
        "title": "Знак молнии",
        "description": "Электрический знак для профиля человека, который всегда вмешивается вовремя.",
        "price": 12_500,
        "category": "appearance",
        "rarity": "common",
        "cosmetic_type": "badge",
        "cosmetic_key": "lightning",
    },
    "badge_star": {
        "title": "Звезда сцены",
        "description": "Коллекционный знак звезды рядом с именем персонажа.",
        "price": 17_500,
        "category": "status",
        "rarity": "rare",
        "cosmetic_type": "badge",
        "cosmetic_key": "star",
    },
    "badge_crown": {
        "title": "Малая корона",
        "description": "Золотая корона возле имени. Не даёт власть, но выглядит убедительно.",
        "price": 20_000,
        "category": "status",
        "rarity": "rare",
        "cosmetic_type": "badge",
        "cosmetic_key": "crown",
    },
    "name_gold": {
        "title": "Золотое имя",
        "description": "Переливающееся золотое имя в карточке персонажа.",
        "price": 22_500,
        "category": "appearance",
        "rarity": "rare",
        "cosmetic_type": "name_style",
        "cosmetic_key": "gold",
    },
    "name_neon": {
        "title": "Неоновое имя",
        "description": "Фиолетово-голубое неоновое свечение имени.",
        "price": 22_500,
        "category": "appearance",
        "rarity": "rare",
        "cosmetic_type": "name_style",
        "cosmetic_key": "neon",
    },
    "profile_glow": {
        "title": "Аура профиля",
        "description": "Добавляет мягкое живое сияние вокруг карточки персонажа.",
        "price": 27_500,
        "category": "appearance",
        "rarity": "epic",
        "cosmetic_type": "glow",
        "cosmetic_key": "royal",
    },
    "background_noir": {
        "title": "Фон «Нуар»",
        "description": "Глубокий графитовый фон с кинематографичной засветкой.",
        "price": 30_000,
        "category": "appearance",
        "rarity": "rare",
        "cosmetic_type": "background",
        "cosmetic_key": "noir",
    },
    "background_crimson": {
        "title": "Фон «Багровая сцена»",
        "description": "Тёмно-красный фон для персонажа, который любит конфликты.",
        "price": 37_500,
        "category": "chaos",
        "rarity": "epic",
        "cosmetic_type": "background",
        "cosmetic_key": "crimson",
    },
    "background_cosmos": {
        "title": "Фон «Космос»",
        "description": "Живой космический фон с частицами и глубиной.",
        "price": 45_000,
        "category": "appearance",
        "rarity": "epic",
        "cosmetic_type": "background",
        "cosmetic_key": "cosmos",
    },
    "frame_ice": {
        "title": "Рамка «Ледяной герой»",
        "description": "Холодный голубой кант, блики льда и мягкое свечение.",
        "price": 35_000,
        "category": "appearance",
        "rarity": "rare",
        "cosmetic_type": "frame",
        "cosmetic_key": "ice",
    },
    "frame_crimson": {
        "title": "Рамка «Багровый герой»",
        "description": "Красный энергетический контур с пульсирующей искрой.",
        "price": 42_500,
        "category": "chaos",
        "rarity": "epic",
        "cosmetic_type": "frame",
        "cosmetic_key": "crimson",
    },
    "frame_cosmos": {
        "title": "Рамка «Центр галактики»",
        "description": "Фиолетово-синий космический портал вокруг аватара.",
        "price": 55_000,
        "category": "appearance",
        "rarity": "epic",
        "cosmetic_type": "frame",
        "cosmetic_key": "cosmos",
    },
    "frame_crown": {
        "title": "Рамка «Корона реальности»",
        "description": "Легендарная золотая рамка с вращающимся световым венцом.",
        "price": 62_500,
        "category": "status",
        "rarity": "legendary",
        "cosmetic_type": "frame",
        "cosmetic_key": "crown",
    },
}


def _apply_price_constants() -> None:
    items = getattr(expansion, "SHOP_ITEMS", [])
    for item in items:
        key = str(item.get("key") or item.get("item_key") or "")
        if key in HALF_PRICE_MAP:
            item["price"] = HALF_PRICE_MAP[key]


async def _table_columns(conn: Any, table: str) -> set[str]:
    cursor = await conn.execute(f"PRAGMA table_info({table})")
    return {str(row["name"]) for row in await cursor.fetchall()}


async def _migrate(core: Any, db: Any) -> None:
    conn = db._require_connection()
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS v1842_cosmetics (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            cosmetic_type TEXT NOT NULL,
            cosmetic_key TEXT NOT NULL,
            source_item_key TEXT NOT NULL,
            equipped_at INTEGER NOT NULL,
            PRIMARY KEY (chat_id, user_id, cosmetic_type)
        )
        """
    )

    table_cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='shop_items'"
    )
    if await table_cursor.fetchone():
        columns = await _table_columns(conn, "shop_items")
        key_col = "item_key" if "item_key" in columns else "key" if "key" in columns else None
        if key_col and "price" in columns:
            for key, price in HALF_PRICE_MAP.items():
                await conn.execute(
                    f"UPDATE shop_items SET price = ? WHERE {key_col} = ?",
                    (price, key),
                )
    await conn.commit()


async def _equip_cosmetic(
    core: Any,
    *,
    chat_id: int,
    user_id: int,
    item_key: str,
    cosmetic_type: str,
    cosmetic_key: str,
) -> None:
    conn = core.db._require_connection()
    now = int(time.time())
    await conn.execute(
        """
        INSERT INTO v1842_cosmetics (
            chat_id, user_id, cosmetic_type, cosmetic_key, source_item_key, equipped_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id, user_id, cosmetic_type) DO UPDATE SET
            cosmetic_key = excluded.cosmetic_key,
            source_item_key = excluded.source_item_key,
            equipped_at = excluded.equipped_at
        """,
        (chat_id, user_id, cosmetic_type, cosmetic_key, item_key, now),
    )
    await conn.commit()


async def _purchase_custom(
    core: Any,
    bot: Any,
    user: Any,
    chat_id: int,
    data: dict[str, Any],
) -> dict[str, Any]:
    item_key = str(data.get("item_key") or "")
    item = COSMETIC_ITEMS.get(item_key)
    if item is None:
        raise ValueError("Неизвестный предмет Reality 184.2")
    request_id = str(data.get("request_id") or "").strip()
    if len(request_id) < 8:
        raise ValueError("Некорректный идентификатор покупки")

    operation_id = f"shop-v1842:{request_id}"
    result = await expansion.change_influence(
        core,
        chat_id=chat_id,
        user_id=int(user.id),
        amount=-int(item["price"]),
        reason=f"shop_{item_key}",
        operation_id=operation_id,
        check_achievements=True,
    )

    try:
        await _equip_cosmetic(
            core,
            chat_id=chat_id,
            user_id=int(user.id),
            item_key=item_key,
            cosmetic_type=str(item["cosmetic_type"]),
            cosmetic_key=str(item["cosmetic_key"]),
        )
    except Exception:
        if not bool(result.get("duplicate")):
            await expansion.change_influence(
                core,
                chat_id=chat_id,
                user_id=int(user.id),
                amount=int(item["price"]),
                reason=f"shop_refund_{item_key}",
                operation_id=f"refund:{operation_id}",
                check_achievements=False,
            )
        raise

    message = (
        f"Покупка совершена. Списано {int(item['price']):,} влияния. "
        f"Предмет «{item['title']}» экипирован."
    ).replace(",", " ")
    if not bool(result.get("duplicate")):
        try:
            await bot.send_message(int(user.id), message)
        except Exception:
            pass
        record_story = getattr(expansion, "_record_story", None)
        if record_story is not None:
            try:
                await record_story(
                    core=core,
                    chat_id=chat_id,
                    event_type="shop_purchase",
                    title="Новый образ персонажа",
                    description=f"Куплен и экипирован предмет «{item['title']}».",
                    participants=[int(user.id)],
                    importance=2 if item["rarity"] in {"epic", "legendary"} else 1,
                    operation_id=f"story:{operation_id}",
                )
            except Exception:
                pass
    return {
        "ok": True,
        "duplicate": bool(result.get("duplicate")),
        "balance": int(result.get("balance") or 0),
        "message": message,
        "item_key": item_key,
    }


async def _live_state(core: Any, request: web.Request) -> web.Response:
    response = await live1841._live_state(core, request)
    payload = json.loads(response.body.decode("utf-8"))
    user = live1841._authorized_user(core, request)
    chat_id = live1841._chat_id_from_request(request)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT cosmetic_type, cosmetic_key, source_item_key, equipped_at
        FROM v1842_cosmetics
        WHERE chat_id = ? AND user_id = ?
        ORDER BY equipped_at DESC
        """,
        (chat_id, int(user.id)),
    )
    payload["cosmetics"] = {
        str(row["cosmetic_type"]): {
            "key": str(row["cosmetic_key"]),
            "source_item_key": str(row["source_item_key"]),
            "equipped_at": int(row["equipped_at"]),
        }
        for row in await cursor.fetchall()
    }
    payload["catalog_v1842"] = [
        {
            "item_key": key,
            "title": item["title"],
            "description": item["description"],
            "price": item["price"],
            "category": item["category"],
            "rarity": item["rarity"],
            "duration_seconds": 0,
        }
        for key, item in COSMETIC_ITEMS.items()
    ]
    payload["version"] = "184.2"
    payload["updated_at"] = int(time.time())
    return web.json_response(payload, headers={"Cache-Control": "no-store"})


def install_reality_v184_2(core: Any) -> None:
    if getattr(core, "_reality_v184_2_installed", False):
        return
    core._reality_v184_2_installed = True
    core.BOT_VERSION = "Reality 184.2 · Shop Polish"
    _apply_price_constants()

    original_connect = core.Database.connect

    async def connect_v184_2(self: Any) -> None:
        await original_connect(self)
        await _migrate(core, self)

    core.Database.connect = connect_v184_2

    original_purchase = expansion._purchase

    async def purchase_v184_2(
        current_core: Any,
        bot: Any,
        user: Any,
        chat_id: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        if str(data.get("item_key") or "") in COSMETIC_ITEMS:
            return await _purchase_custom(current_core, bot, user, chat_id, data)
        return await original_purchase(current_core, bot, user, chat_id, data)

    expansion._purchase = purchase_v184_2

    original_application = core.web.Application

    def application_v184_2(*args: Any, **kwargs: Any) -> web.Application:
        app = original_application(*args, **kwargs)
        app.router.add_get(LIVE_ROUTE, lambda request: _live_state(core, request))
        return app

    core.web.Application = application_v184_2
