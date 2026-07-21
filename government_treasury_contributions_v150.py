from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any, Callable

import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 150 · Государственные фонды"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "treasury-contributions-v150.js"
ASSET_CSS = APP_DIR / "treasury-contributions-v150.css"

MIN_CONTRIBUTION = 100
MAX_CONTRIBUTION = 1_000_000
FUND_SPECS: dict[str, dict[str, str]] = {
    "general": {"emoji": "🏛", "title": "Общий бюджет", "hint": "Повседневные государственные расходы"},
    "reserve": {"emoji": "🛡", "title": "Резервный фонд", "hint": "Кризисы и непредвиденные расходы"},
    "social": {"emoji": "🤝", "title": "Социальный фонд", "hint": "Помощь участникам по бюджетному закону"},
    "security": {"emoji": "🛡️", "title": "Фонд безопасности", "hint": "Государственная безопасность и расследования"},
    "elections": {"emoji": "🗳", "title": "Фонд выборов", "hint": "Избирательные кампании и работа ЦИК"},
    "development": {"emoji": "🚀", "title": "Фонд развития", "hint": "Новые государственные механики и проекты"},
}


def _now() -> int:
    return int(time.time())


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


async def _ensure_schema(core: Any) -> None:
    if getattr(core, "_government_treasury_contributions_v150_schema_ready", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_contributions_v150(
                contribution_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                fund_key TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_government_contributions_chat_v150
            ON government_contributions_v150(chat_id,created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_government_contributions_user_v150
            ON government_contributions_v150(chat_id,user_id,created_at DESC);

            CREATE TABLE IF NOT EXISTS government_fund_balances_v150(
                chat_id INTEGER NOT NULL,
                fund_key TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL,
                PRIMARY KEY(chat_id,fund_key)
            );
            """
        )
        await conn.commit()
    core._government_treasury_contributions_v150_schema_ready = True


async def _contribute(
    core: Any,
    chat_id: int,
    user_id: int,
    amount: int,
    fund_key: str,
    note: str,
) -> tuple[int, str]:
    await _ensure_schema(core)
    await gov._ensure_state(core, chat_id)

    value = int(amount)
    if value < MIN_CONTRIBUTION or value > MAX_CONTRIBUTION:
        raise ValueError(
            f"Размер вклада должен быть от {MIN_CONTRIBUTION:,} до {MAX_CONTRIBUTION:,} влияния."
            .replace(",", " ")
        )
    key = str(fund_key or "general")
    if key not in FUND_SPECS:
        raise ValueError("Выбран неизвестный государственный фонд.")
    clean_note = str(note or "").strip()
    if len(clean_note) > 200:
        raise ValueError("Комментарий к вкладу не может быть длиннее 200 символов.")

    player = await gov._player_dict(core, chat_id, user_id)
    if player is None:
        raise PermissionError("Сначала используй бота в этой беседе.")
    if int(player["points"]) < value:
        raise ValueError("На обычном балансе недостаточно влияния для такого вклада.")

    conn = core.db._require_connection()
    now = _now()
    contribution_id = secrets.token_urlsafe(12)
    title = FUND_SPECS[key]["title"]
    async with core.db.lock:
        cursor = await conn.execute(
            """
            UPDATE players SET points=points-?,updated_at=?
            WHERE chat_id=? AND user_id=? AND points>=?
            """,
            (value, now, int(chat_id), int(user_id), value),
        )
        if int(cursor.rowcount or 0) <= 0:
            await conn.rollback()
            raise ValueError("Баланс изменился. Обнови страницу и повтори вклад.")
        await conn.execute(
            "UPDATE government_state_v127 SET treasury=treasury+?,updated_at=? WHERE chat_id=?",
            (value, now, int(chat_id)),
        )
        await conn.execute(
            """
            INSERT INTO government_fund_balances_v150(chat_id,fund_key,amount,updated_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,fund_key) DO UPDATE SET
                amount=government_fund_balances_v150.amount+excluded.amount,
                updated_at=excluded.updated_at
            """,
            (int(chat_id), key, value, now),
        )
        await conn.execute(
            """
            INSERT INTO government_contributions_v150(
                contribution_id,chat_id,user_id,amount,fund_key,note,created_at
            ) VALUES(?,?,?,?,?,?,?)
            """,
            (contribution_id, int(chat_id), int(user_id), value, key, clean_note, now),
        )
        await conn.execute(
            "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
            (int(chat_id), int(user_id), -value, f"government_contribution_{key}_v150", now),
        )
        reason = f"Добровольный вклад: {title}"
        if clean_note:
            reason = f"{reason} — {clean_note}"
        await gov._treasury_log(
            core,
            chat_id,
            value,
            reason,
            "voluntary_contribution_v150",
            contribution_id,
            user_id,
        )
        await conn.commit()
    return value, title


async def _serialize_contributions(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    conn = core.db._require_connection()

    cursor = await conn.execute(
        "SELECT fund_key,amount FROM government_fund_balances_v150 WHERE chat_id=?",
        (int(chat_id),),
    )
    balances = {str(row["fund_key"]): int(row["amount"] or 0) for row in await cursor.fetchall()}

    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount),0) total FROM government_contributions_v150 WHERE chat_id=? AND user_id=?",
        (int(chat_id), int(user_id)),
    )
    my_row = await cursor.fetchone()

    cursor = await conn.execute(
        "SELECT COALESCE(SUM(amount),0) total FROM government_contributions_v150 WHERE chat_id=?",
        (int(chat_id),),
    )
    total_row = await cursor.fetchone()

    cursor = await conn.execute(
        """
        SELECT c.user_id,SUM(c.amount) total,p.full_name,p.username
        FROM government_contributions_v150 c
        LEFT JOIN players p ON p.chat_id=c.chat_id AND p.user_id=c.user_id
        WHERE c.chat_id=?
        GROUP BY c.user_id,p.full_name,p.username
        ORDER BY total DESC,c.user_id ASC
        LIMIT 10
        """,
        (int(chat_id),),
    )
    top = []
    for row in await cursor.fetchall():
        username = str(row["username"] or "").strip().lstrip("@")
        name = str(row["full_name"] or "").strip() or (f"@{username}" if username else f"ID {int(row['user_id'])}")
        top.append({"user_id": int(row["user_id"]), "name": name, "amount": int(row["total"] or 0)})

    cursor = await conn.execute(
        """
        SELECT c.*,p.full_name,p.username
        FROM government_contributions_v150 c
        LEFT JOIN players p ON p.chat_id=c.chat_id AND p.user_id=c.user_id
        WHERE c.chat_id=?
        ORDER BY c.created_at DESC
        LIMIT 12
        """,
        (int(chat_id),),
    )
    recent = []
    for row in await cursor.fetchall():
        username = str(row["username"] or "").strip().lstrip("@")
        name = str(row["full_name"] or "").strip() or (f"@{username}" if username else f"ID {int(row['user_id'])}")
        spec = FUND_SPECS.get(str(row["fund_key"]), FUND_SPECS["general"])
        recent.append(
            {
                "contribution_id": str(row["contribution_id"]),
                "user_id": int(row["user_id"]),
                "name": name,
                "amount": int(row["amount"]),
                "fund_key": str(row["fund_key"]),
                "fund_title": str(spec["title"]),
                "fund_emoji": str(spec["emoji"]),
                "note": str(row["note"] or ""),
                "created_at": int(row["created_at"]),
            }
        )

    player = await gov._player_dict(core, chat_id, user_id)
    return {
        "version": VERSION,
        "min_amount": MIN_CONTRIBUTION,
        "max_amount": MAX_CONTRIBUTION,
        "can_contribute": bool(player and int(player["points"]) >= MIN_CONTRIBUTION),
        "available_balance": int(player["points"] if player else 0),
        "my_total": int(my_row["total"] if my_row else 0),
        "total": int(total_row["total"] if total_row else 0),
        "funds": [
            {"key": key, **spec, "amount": int(balances.get(key, 0))}
            for key, spec in FUND_SPECS.items()
        ],
        "top": top,
        "recent": recent,
    }


def _with_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "treasury-contributions-v150.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v150/treasury-contributions-v150.css?v=150">\n</head>',
        )
    if "treasury-contributions-v150.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v150/treasury-contributions-v150.js?v=150"></script>\n</body>',
        )
    return source


def install_government_treasury_contributions_v150(core: Any) -> None:
    if getattr(core, "_government_treasury_contributions_v150_installed", False):
        return
    core._government_treasury_contributions_v150_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_inject = luxury._inject_assets

    def inject_with_contributions(source: str) -> str:
        return _with_assets(previous_inject, source)

    luxury._inject_assets = inject_with_contributions

    original_connect = core.Database.connect

    async def connect_with_contributions(self: Any) -> None:
        await original_connect(self)
        core._government_treasury_contributions_v150_schema_ready = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_contributions

    original_state = gov._state

    async def state_with_contributions(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        payload["treasury_contributions_v150"] = await _serialize_contributions(
            core_arg, chat_id, user_id
        )
        return payload

    gov._state = state_with_contributions

    async def contribute_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            amount, title = await _contribute(
                core,
                chat_id,
                int(user.id),
                int(data.get("amount") or 0),
                str(data.get("fund_key") or "general"),
                str(data.get("note") or ""),
            )
            return core.web.json_response(
                {
                    "ok": True,
                    "message": f"Вклад {gov._fmt(amount)} влияния зачислен в «{title}».",
                }
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    async def asset(request: Any):
        name = str(request.match_info.get("name") or "")
        if name == "treasury-contributions-v150.js":
            path = ASSET_JS
        elif name == "treasury-contributions-v150.css":
            path = ASSET_CSS
        else:
            raise core.web.HTTPNotFound()
        return core.web.FileResponse(
            path,
            headers={"Cache-Control": "no-store", "X-Government-Treasury": "150"},
        )

    original_start = core.start_webapp_server

    async def start_with_contributions(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты государственных фондов Reality 150")
        original_runner = core.web.AppRunner

        def runner_with_contributions(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("POST", "/government-v150/api/contribute") not in keys:
                app.router.add_post("/government-v150/api/contribute", contribute_api)
            if ("GET", "/government-v150/{name}") not in keys:
                app.router.add_get("/government-v150/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_contributions
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_contributions
