from __future__ import annotations

import html
import json
import secrets
import time
from pathlib import Path
from typing import Any

import admin_full_v124 as admin_full
import finance_investments_v127 as investments_app
import finance_investments_v127_core as invest_core
import finance_investments_v127_market as invest_market
import finance_investments_v127_ops as invest_ops
import government_crisis_v131 as crisis
import government_v127 as gov


VERSION = "Reality 132 · Админ власти и биржи"
BASE_DIR = Path(__file__).resolve().parent
ASSET_JS = BASE_DIR / "adminapp_v132" / "government-market.js"


def _route_keys(app: Any) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for route in app.router.routes():
        resource = getattr(route, "resource", None)
        result.add(
            (
                str(getattr(route, "method", "") or "").upper(),
                str(getattr(resource, "canonical", "") or ""),
            )
        )
    return result


def _as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fmt(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


async def _payload(request: Any) -> dict[str, Any]:
    try:
        value = await request.json()
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _auth(core: Any, request: Any) -> Any:
    user, reason = core._webapp_auth(request)
    if user is None:
        raise PermissionError(reason or "Нет авторизации Telegram.")
    if int(user.id) != int(core.DEVELOPER_ID):
        raise PermissionError("Админ-центр доступен только владельцу бота.")
    return user


async def _table_exists(conn: Any, name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (str(name),),
    )
    return await cursor.fetchone() is not None


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_admin_government_market_v132_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS finance_stock_admin_v132(
                chat_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                trading_paused INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,symbol)
            );
            """
        )
        await conn.commit()
    core._admin_government_market_v132_schema_ready = True


async def _log_admin(
    core: Any,
    admin_id: int,
    chat_id: int,
    user_id: int,
    action: str,
    detail: str,
    payload: dict[str, Any],
) -> None:
    conn = core.db._require_connection()
    if not await _table_exists(conn, "admin_action_log_v62"):
        return
    await conn.execute(
        """
        INSERT INTO admin_action_log_v62(
            admin_id,chat_id,target_user_id,action,detail,payload_json,reversible,created_at
        ) VALUES(?,?,?,?,?,?,0,?)
        """,
        (
            int(admin_id),
            int(chat_id),
            int(user_id) if int(user_id) else None,
            str(action),
            str(detail),
            json.dumps(payload or {}, ensure_ascii=False),
            int(time.time()),
        ),
    )
    await conn.commit()


async def _selected_player(core: Any, chat_id: int, user_id: int) -> dict[str, Any] | None:
    if not user_id:
        return None
    return await gov._player_dict(core, int(chat_id), int(user_id))


async def _office_state(core: Any, chat_id: int, target_id: int) -> dict[str, Any]:
    conn = core.db._require_connection()
    now = int(time.time())
    cursor = await conn.execute(
        """
        SELECT o.office_key,o.seat_no,o.user_id,o.starts_at,o.ends_at,o.trust,o.appointed_by,
               p.full_name,p.username,p.career_points
        FROM government_offices_v127 o
        LEFT JOIN players p ON p.chat_id=o.chat_id AND p.user_id=o.user_id
        WHERE o.chat_id=? AND o.ends_at>?
        ORDER BY CASE o.office_key
          WHEN 'president' THEN 0 WHEN 'chair' THEN 1 WHEN 'deputy' THEN 2
          WHEN 'finance' THEN 3 WHEN 'oversight' THEN 4 ELSE 5 END,o.seat_no
        """,
        (int(chat_id), now),
    )
    offices: list[dict[str, Any]] = []
    target_offices: list[dict[str, Any]] = []
    for row in await cursor.fetchall():
        key = str(row["office_key"])
        spec = gov.OFFICES.get(key, {"emoji": "🏛", "title": key, "seats": 1})
        item = {
            "office_key": key,
            "seat_no": int(row["seat_no"]),
            "user_id": int(row["user_id"]),
            "name": str(row["full_name"] or f"ID {row['user_id']}"),
            "username": str(row["username"] or ""),
            "career_points": int(row["career_points"] or 0),
            "emoji": str(spec.get("emoji", "🏛")),
            "title": str(spec.get("title", key)),
            "starts_at": int(row["starts_at"]),
            "ends_at": int(row["ends_at"]),
            "remaining": gov._remaining(int(row["ends_at"])),
            "trust": int(row["trust"] or 50),
        }
        offices.append(item)
        if int(row["user_id"]) == int(target_id):
            target_offices.append(item)

    specs = []
    for key, spec in gov.OFFICES.items():
        specs.append(
            {
                "key": key,
                "emoji": str(spec.get("emoji", "🏛")),
                "title": str(spec.get("title", key)),
                "seats": 7 if key == "deputy" else int(spec.get("seats", 1)),
                "threshold": int(spec.get("threshold", 0)),
            }
        )

    state = await gov._ensure_state(core, int(chat_id))
    election_ban = 0
    conflict_ban = 0
    if target_id and await _table_exists(conn, "government_election_bans_v131"):
        cursor = await conn.execute(
            "SELECT until_at FROM government_election_bans_v131 WHERE chat_id=? AND user_id=? AND until_at>?",
            (int(chat_id), int(target_id), now),
        )
        row = await cursor.fetchone()
        election_ban = int(row["until_at"] or 0) if row else 0
    if target_id and await _table_exists(conn, "government_conflict_bans_v131"):
        cursor = await conn.execute(
            "SELECT until_at FROM government_conflict_bans_v131 WHERE chat_id=? AND user_id=? AND until_at>?",
            (int(chat_id), int(target_id), now),
        )
        row = await cursor.fetchone()
        conflict_ban = int(row["until_at"] or 0) if row else 0

    return {
        "specs": specs,
        "offices": offices,
        "target_offices": target_offices,
        "treasury": int(state["treasury"] or 0),
        "election_ban_until": election_ban,
        "conflict_ban_until": conflict_ban,
    }


async def _market_state(core: Any, chat_id: int) -> list[dict[str, Any]]:
    await invest_core._ensure_schema(core)
    await _ensure_schema(core)
    await invest_market._advance_market(core, int(chat_id))
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM finance_market_v127 WHERE chat_id=? ORDER BY symbol",
        (int(chat_id),),
    )
    market = {str(row["symbol"]): row for row in await cursor.fetchall()}
    cursor = await conn.execute(
        "SELECT symbol,trading_paused FROM finance_stock_admin_v132 WHERE chat_id=?",
        (int(chat_id),),
    )
    controls = {str(row["symbol"]): bool(int(row["trading_paused"] or 0)) for row in await cursor.fetchall()}
    cursor = await conn.execute(
        """
        SELECT symbol,COUNT(DISTINCT user_id) holders,COALESCE(SUM(quantity),0) quantity
        FROM finance_stock_positions_v127 WHERE chat_id=? GROUP BY symbol
        """,
        (int(chat_id),),
    )
    holders = {
        str(row["symbol"]): {
            "holders": int(row["holders"] or 0),
            "quantity": int(row["quantity"] or 0),
        }
        for row in await cursor.fetchall()
    }
    result: list[dict[str, Any]] = []
    for symbol, spec in invest_core.STOCKS.items():
        row = market.get(symbol)
        if row is None:
            continue
        stats = holders.get(symbol, {"holders": 0, "quantity": 0})
        result.append(
            {
                "symbol": symbol,
                "name": str(spec["name"]),
                "icon": str(spec["icon"]),
                "risk": str(spec["risk"]),
                "base_price": int(spec["base_price"]),
                "price": int(row["price"]),
                "previous_price": int(row["previous_price"]),
                "high": int(row["high_price"]),
                "low": int(row["low_price"]),
                "volume": int(row["volume"] or 0),
                "last_event": str(row["last_event"] or ""),
                "updated_at": int(row["updated_at"] or 0),
                "trading_paused": bool(controls.get(symbol, False)),
                "holders": int(stats["holders"]),
                "quantity": int(stats["quantity"]),
            }
        )
    return result


async def _set_market_price(core: Any, chat_id: int, symbol: str, new_price: int, event: str) -> int:
    await invest_core._ensure_schema(core)
    await invest_market._initialize_market(core, int(chat_id))
    symbol = str(symbol).upper()
    if symbol not in invest_core.STOCKS:
        raise ValueError("Акция не найдена.")
    price = max(5, min(100_000_000, int(new_price)))
    conn = core.db._require_connection()
    now = int(time.time())
    bucket = now // invest_core.MARKET_TICK_SECONDS
    async with core.db.lock:
        cursor = await conn.execute(
            "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
            (int(chat_id), symbol),
        )
        row = await cursor.fetchone()
        if row is None:
            raise ValueError("Курс акции не найден.")
        previous = int(row["price"])
        await conn.execute(
            """
            UPDATE finance_market_v127
            SET previous_price=?,price=?,high_price=MAX(high_price,?),low_price=MIN(low_price,?),
                updated_at=?,last_event=?,last_event_at=?
            WHERE chat_id=? AND symbol=?
            """,
            (previous, price, price, price, now, str(event), now, int(chat_id), symbol),
        )
        await conn.execute(
            """
            INSERT INTO finance_stock_history_v127(chat_id,symbol,bucket,price,volume)
            VALUES(?,?,?,?,0)
            ON CONFLICT(chat_id,symbol,bucket) DO UPDATE SET price=excluded.price
            """,
            (int(chat_id), symbol, bucket, price),
        )
        await conn.commit()
    return price


def install_admin_government_market_v132(core: Any) -> None:
    if getattr(core, "_admin_government_market_v132_installed", False):
        return
    core._admin_government_market_v132_installed = True
    core.ADMIN_CENTER_VERSION = VERSION

    previous_connect = core.Database.connect

    async def connect_with_admin_v132(self: Any) -> None:
        await previous_connect(self)
        core._admin_government_market_v132_schema_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_admin_v132

    original_trade = invest_ops._trade

    async def trade_with_admin_pause(
        core_value: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
        side: str,
    ) -> str:
        await _ensure_schema(core_value)
        symbol = str(data.get("symbol") or "").upper()
        conn = core_value.db._require_connection()
        cursor = await conn.execute(
            "SELECT trading_paused FROM finance_stock_admin_v132 WHERE chat_id=? AND symbol=?",
            (int(chat_id), symbol),
        )
        row = await cursor.fetchone()
        if row is not None and bool(int(row["trading_paused"] or 0)):
            raise PermissionError("Торги этой акцией временно остановлены администратором.")
        return await original_trade(core_value, chat_id, user_id, data, side)

    invest_ops._trade = trade_with_admin_pause
    investments_app._trade = trade_with_admin_pause

    async def state_api(request: Any):
        try:
            admin = _auth(core, request)
            chat_id = _as_int(request.query.get("chat_id"))
            user_id = _as_int(request.query.get("user_id"))
            if chat_id >= 0:
                raise ValueError("Выбери групповую беседу.")
            await crisis._ensure_schema(core)
            target = await _selected_player(core, chat_id, user_id)
            return core.web.json_response(
                {
                    "ok": True,
                    "version": VERSION,
                    "admin_id": int(admin.id),
                    "chat_id": int(chat_id),
                    "target": target,
                    "government": await _office_state(core, chat_id, user_id),
                    "stocks": await _market_state(core, chat_id),
                }
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка загрузки админ-разделов Reality 132")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def action_api(request: Any):
        try:
            admin = _auth(core, request)
            data = await _payload(request)
            action = str(data.get("action") or "")
            chat_id = _as_int(data.get("chat_id"))
            user_id = _as_int(data.get("user_id"))
            if chat_id >= 0:
                raise ValueError("Выбери групповую беседу.")
            await crisis._ensure_schema(core)
            await _ensure_schema(core)
            conn = core.db._require_connection()
            bot = request.app["bot"]
            message = "Готово."

            if action == "office_assign":
                office_key = str(data.get("office_key") or "")
                if office_key not in gov.OFFICES:
                    raise ValueError("Неизвестная государственная должность.")
                target = await _selected_player(core, chat_id, user_id)
                if target is None:
                    raise ValueError("Сначала выбери участника.")
                seat_no = 1 if office_key != "deputy" else max(1, min(7, _as_int(data.get("seat_no"), 1)))
                term_days = max(1, min(30, _as_int(data.get("term_days"), 7)))
                now = int(time.time())
                ends_at = now + term_days * 86400
                async with core.db.lock:
                    await conn.execute(
                        "DELETE FROM government_offices_v127 WHERE chat_id=? AND office_key=? AND user_id=?",
                        (chat_id, office_key, user_id),
                    )
                    await conn.execute(
                        """
                        INSERT INTO government_offices_v127(
                            chat_id,office_key,seat_no,user_id,starts_at,ends_at,trust,appointed_by
                        ) VALUES(?,?,?,?,?,?,50,?)
                        ON CONFLICT(chat_id,office_key,seat_no) DO UPDATE SET
                            user_id=excluded.user_id,starts_at=excluded.starts_at,
                            ends_at=excluded.ends_at,trust=50,appointed_by=excluded.appointed_by
                        """,
                        (chat_id, office_key, seat_no, user_id, now, ends_at, int(admin.id)),
                    )
                    await conn.commit()
                spec = gov.OFFICES[office_key]
                message = f"{target['name']} назначен: {spec['title']} на {term_days} дн."
                if bool(data.get("announce", True)):
                    await gov._publish(
                        bot,
                        chat_id,
                        "🛠 <b>АДМИНИСТРАТИВНОЕ НАЗНАЧЕНИЕ</b>\n\n"
                        f"Участник: <b>{html.escape(str(target['name']))}</b>\n"
                        f"Должность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>\n"
                        f"Срок: <b>{term_days} дн.</b>",
                    )

            elif action == "office_remove":
                office_key = str(data.get("office_key") or "")
                seat_no = max(1, _as_int(data.get("seat_no"), 1))
                cursor = await conn.execute(
                    "SELECT user_id FROM government_offices_v127 WHERE chat_id=? AND office_key=? AND seat_no=?",
                    (chat_id, office_key, seat_no),
                )
                row = await cursor.fetchone()
                await conn.execute(
                    "DELETE FROM government_offices_v127 WHERE chat_id=? AND office_key=? AND seat_no=?",
                    (chat_id, office_key, seat_no),
                )
                await conn.commit()
                removed_id = int(row["user_id"] or 0) if row else 0
                message = "Должность освобождена."
                user_id = removed_id or user_id

            elif action == "office_remove_all":
                if not user_id:
                    raise ValueError("Сначала выбери участника.")
                cursor = await conn.execute(
                    "DELETE FROM government_offices_v127 WHERE chat_id=? AND user_id=?",
                    (chat_id, user_id),
                )
                await conn.commit()
                message = f"Снято государственных должностей: {int(cursor.rowcount or 0)}."

            elif action == "office_extend":
                office_key = str(data.get("office_key") or "")
                seat_no = max(1, _as_int(data.get("seat_no"), 1))
                days = max(1, min(30, _as_int(data.get("days"), 7)))
                cursor = await conn.execute(
                    "UPDATE government_offices_v127 SET ends_at=MAX(ends_at,?)+? WHERE chat_id=? AND office_key=? AND seat_no=?",
                    (int(time.time()), days * 86400, chat_id, office_key, seat_no),
                )
                await conn.commit()
                if int(cursor.rowcount or 0) <= 0:
                    raise ValueError("Действующая должность не найдена.")
                message = f"Срок полномочий продлён на {days} дн."

            elif action in {"treasury_set", "treasury_delta"}:
                state = await gov._ensure_state(core, chat_id)
                current = int(state["treasury"] or 0)
                value = _as_int(data.get("value"))
                updated = value if action == "treasury_set" else current + value
                updated = max(0, min(1_000_000_000, updated))
                await conn.execute(
                    "UPDATE government_state_v127 SET treasury=?,updated_at=? WHERE chat_id=?",
                    (updated, int(time.time()), chat_id),
                )
                await gov._treasury_log(
                    core,
                    chat_id,
                    updated - current,
                    "Изменение казны администратором",
                    "admin_v132",
                    str(time.time_ns()),
                    int(admin.id),
                )
                await conn.commit()
                message = f"Казна: {_fmt(current)} → {_fmt(updated)}."
                user_id = 0

            elif action == "political_bans_clear":
                if not user_id:
                    raise ValueError("Сначала выбери участника.")
                total = 0
                for table in ("government_election_bans_v131", "government_conflict_bans_v131"):
                    if await _table_exists(conn, table):
                        cursor = await conn.execute(
                            f"DELETE FROM {table} WHERE chat_id=? AND user_id=?",
                            (chat_id, user_id),
                        )
                        total += int(cursor.rowcount or 0)
                await conn.commit()
                message = f"Снято политических запретов: {total}."

            elif action in {"stock_set_price", "stock_move", "stock_reset"}:
                symbol = str(data.get("symbol") or "").upper()
                if symbol not in invest_core.STOCKS:
                    raise ValueError("Акция не найдена.")
                if action == "stock_reset":
                    new_price = int(invest_core.STOCKS[symbol]["base_price"])
                    label = "Сброс цены к базовой"
                else:
                    cursor = await conn.execute(
                        "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                        (chat_id, symbol),
                    )
                    row = await cursor.fetchone()
                    if row is None:
                        await invest_market._initialize_market(core, chat_id)
                        cursor = await conn.execute(
                            "SELECT price FROM finance_market_v127 WHERE chat_id=? AND symbol=?",
                            (chat_id, symbol),
                        )
                        row = await cursor.fetchone()
                    current = int(row["price"])
                    if action == "stock_set_price":
                        new_price = _as_int(data.get("value"))
                        label = "Ручная установка курса"
                    else:
                        percent = max(-90.0, min(500.0, float(data.get("percent") or 0)))
                        new_price = round(current * (1 + percent / 100))
                        label = f"Административное движение курса {percent:+g}%"
                price = await _set_market_price(core, chat_id, symbol, new_price, label)
                message = f"{symbol}: курс установлен на {_fmt(price)}."
                user_id = 0

            elif action == "stock_pause":
                symbol = str(data.get("symbol") or "").upper()
                if symbol not in invest_core.STOCKS:
                    raise ValueError("Акция не найдена.")
                paused = 1 if bool(data.get("paused")) else 0
                await conn.execute(
                    """
                    INSERT INTO finance_stock_admin_v132(chat_id,symbol,trading_paused,updated_at)
                    VALUES(?,?,?,?) ON CONFLICT(chat_id,symbol) DO UPDATE SET
                        trading_paused=excluded.trading_paused,updated_at=excluded.updated_at
                    """,
                    (chat_id, symbol, paused, int(time.time())),
                )
                await conn.commit()
                message = f"Торги {symbol} {'остановлены' if paused else 'возобновлены'}."
                user_id = 0

            elif action == "stock_event":
                symbol = str(data.get("symbol") or "").upper()
                if symbol not in invest_core.STOCKS:
                    raise ValueError("Акция не найдена.")
                title = str(data.get("title") or "").strip()
                if len(title) < 5 or len(title) > 120:
                    raise ValueError("Название события должно содержать от 5 до 120 символов.")
                effect_percent = max(-50.0, min(50.0, float(data.get("effect_percent") or 0)))
                effect_bp = round(effect_percent * 100)
                await invest_market._ensure_news_applied_column(core)
                news_id = secrets.token_urlsafe(10)
                now = int(time.time())
                await conn.execute(
                    """
                    INSERT INTO finance_market_news_v128(
                        news_id,chat_id,symbol,source_key,source_type,category,title,summary,body,
                        effect_bp,event_at,source_at,created_at,applied
                    ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)
                    """,
                    (
                        news_id,
                        chat_id,
                        symbol,
                        f"admin:{symbol}:{time.time_ns()}",
                        "admin_event",
                        "Решение администратора",
                        title,
                        title,
                        title,
                        effect_bp,
                        now,
                        now,
                        now,
                    ),
                )
                await conn.commit()
                await invest_market._advance_market(core, chat_id)
                message = f"Событие {symbol} создано: {effect_percent:+g}%."
                user_id = 0

            else:
                raise ValueError("Неизвестное действие админ-центра.")

            await _log_admin(core, int(admin.id), chat_id, user_id, action, message, data)
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка действия админ-центра Reality 132")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def asset(_: Any):
        if not ASSET_JS.is_file():
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            ASSET_JS,
            headers={"Cache-Control": "no-store", "X-Admin-Center": "reality-132"},
        )

    @core.web.middleware
    async def admin_v132_index(request: Any, handler: Any):
        if request.method.upper() == "GET" and str(request.path or "") in {
            "/admin-v124",
            "/admin-v124/",
            "/admin-v126",
            "/admin-v126/",
        }:
            source = admin_full._full_html()
            source = source.replace("Reality 126", "Reality 132")
            if "/admin-v132/government-market.js" not in source:
                source = source.replace(
                    "</body>",
                    '  <script src="/admin-v132/government-market.js?v=132"></script>\n</body>',
                )
            return core.web.Response(
                text=source,
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": "reality-132",
                },
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_admin_v132(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, admin_v132_index)
        return application

    core.web.Application = application_with_admin_v132
    original_start = core.start_webapp_server

    async def start_with_admin_v132(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс админ-центра Reality 132")
        original_runner = core.web.AppRunner

        def runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/admin-v132/government-market.js") not in keys:
                app.router.add_get("/admin-v132/government-market.js", asset)
            if ("GET", "/admin-v132/api/state") not in keys:
                app.router.add_get("/admin-v132/api/state", state_api)
            if ("POST", "/admin-v132/api/action") not in keys:
                app.router.add_post("/admin-v132/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_factory
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_admin_v132