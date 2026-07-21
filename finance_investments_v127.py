from __future__ import annotations

import math
from typing import Any

from finance_investments_v127_core import (
    APP_DIR, MARKET_TICK_SECONDS, STOCKS, VERSION, _ensure_schema, _now, _route_keys, _safe_int,
)
from finance_investments_v127_market import _advance_market, _auth, _investment_payload, _news_dict
from finance_investments_v127_ops import _create_deposit, _trade, _withdraw_deposit
from finance_market_news_v128 import news_for_range


def install_finance_investments_v127(core: Any) -> None:
    if getattr(core, "_finance_investments_v127_installed", False):
        return
    core._finance_investments_v127_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_investments(self: Any) -> None:
        await original_connect(self)
        core._finance_investments_schema_v127_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_investments

    async def state_api(request: Any):
        try:
            user, chat_id, _, _ = await _auth(core, request)
            return core.web.json_response(
                await _investment_payload(core, chat_id, int(user.id))
            )
        except PermissionError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=403)
        except ValueError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=400)
        except Exception:
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось загрузить инвестиции."},
                status=500,
            )

    async def chart_api(request: Any):
        try:
            user, chat_id, _, _ = await _auth(core, request)
            await _ensure_schema(core)
            await _advance_market(core, chat_id)
            symbol = str(request.query.get("symbol") or "EGO").upper()
            if symbol not in STOCKS:
                raise ValueError("Акция не найдена.")
            allowed_periods = {3600, 86400, 7 * 86400, 30 * 86400}
            period = _safe_int(request.query.get("period"), 86400)
            if period not in allowed_periods:
                period = 86400
            now = _now()
            cutoff_bucket = (now - period) // MARKET_TICK_SECONDS
            conn = core.db._require_connection()
            cursor = await conn.execute(
                """
                SELECT bucket,price,volume FROM finance_stock_history_v127
                WHERE chat_id=? AND symbol=? AND bucket>=?
                ORDER BY bucket ASC
                """,
                (chat_id, symbol, cutoff_bucket),
            )
            rows = list(await cursor.fetchall())
            if len(rows) > 480:
                step = math.ceil(len(rows) / 480)
                sampled = rows[::step]
                if sampled[-1]["bucket"] != rows[-1]["bucket"]:
                    sampled.append(rows[-1])
                rows = sampled
            news = await news_for_range(conn, chat_id, symbol, now - period, now + MARKET_TICK_SECONDS)
            return core.web.json_response(
                {
                    "ok": True,
                    "symbol": symbol,
                    "period": period,
                    "history": [
                        {
                            "time": int(row["bucket"]) * MARKET_TICK_SECONDS,
                            "price": int(row["price"]),
                            "volume": int(row["volume"] or 0),
                        }
                        for row in rows
                    ],
                    "events": [_news_dict(item) for item in news],
                }
            )
        except PermissionError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=403)
        except ValueError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=400)
        except Exception:
            return core.web.json_response(
                {"ok": False, "reason": "Не удалось загрузить график."},
                status=500,
            )

    async def action_api(request: Any):
        try:
            user, chat_id, data, _ = await _auth(core, request)
            await _ensure_schema(core)
            action = str(data.get("action") or "")
            user_id = int(user.id)
            if action == "deposit_open":
                message = await _create_deposit(core, chat_id, user_id, data)
            elif action == "deposit_withdraw":
                message = await _withdraw_deposit(core, chat_id, user_id, data)
            elif action == "stock_buy":
                message = await _trade(core, chat_id, user_id, data, "buy")
            elif action == "stock_sell":
                message = await _trade(core, chat_id, user_id, data, "sell")
            else:
                raise ValueError("Неизвестная инвестиционная операция.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=403)
        except ValueError as error:
            return core.web.json_response({"ok": False, "reason": str(error)}, status=400)
        except Exception:
            return core.web.json_response(
                {"ok": False, "reason": "Операция не выполнена. Попробуй ещё раз."},
                status=500,
            )

    original_start_server = core.start_webapp_server

    async def start_server_with_investment_routes(bot: Any):
        original_app_runner = core.web.AppRunner

        def app_runner_factory(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)

            def add_get(path: str, handler: Any) -> None:
                if ("GET", path) not in keys and ("*", path) not in keys:
                    app.router.add_get(path, handler)
                    keys.add(("GET", path))

            def add_post(path: str, handler: Any) -> None:
                if ("POST", path) not in keys and ("*", path) not in keys:
                    app.router.add_post(path, handler)
                    keys.add(("POST", path))

            async def index(_: Any):
                return core.web.FileResponse(
                    APP_DIR / "index.html",
                    headers={
                        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                        "Pragma": "no-cache",
                        "Expires": "0",
                        "X-Finance-Center": VERSION,
                    },
                )

            async def style(_: Any):
                return core.web.FileResponse(
                    APP_DIR / "style.css",
                    headers={"Cache-Control": "no-store", "Content-Type": "text/css; charset=utf-8"},
                )

            async def script(_: Any):
                source = "\n".join(
                    (APP_DIR / f"app.part{index}.js").read_text(encoding="utf-8")
                    for index in range(1, 4)
                )
                return core.web.Response(
                    text=source,
                    content_type="application/javascript",
                    charset="utf-8",
                    headers={"Cache-Control": "no-store"},
                )

            for path in ("/finance-v127", "/finance-v127/", "/finance-v127/index.html"):
                add_get(path, index)
            add_get("/finance-v127/style.css", style)
            add_get("/finance-v127/app.js", script)
            add_get("/finance-v127/api/state", state_api)
            add_get("/finance-v127/api/chart", chart_api)
            add_post("/finance-v127/api/action", action_api)
            return original_app_runner(app, *args, **kwargs)

        core.web.AppRunner = app_runner_factory
        try:
            return await original_start_server(bot)
        finally:
            core.web.AppRunner = original_app_runner

    core.start_webapp_server = start_server_with_investment_routes
