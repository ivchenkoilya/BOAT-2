from __future__ import annotations

import asyncio
import copy
import html
import json
import secrets
import time
from pathlib import Path
from typing import Any

import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 167 · Быстрое государство и редакции законов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
EARLY_JS = APP_DIR / "state-broker-v167.js"
LATE_JS = APP_DIR / "government-reliability-v167.js"
ASSET_CSS = APP_DIR / "government-reliability-v167.css"
STATE_CACHE_SECONDS = 2.0
CHAT_TITLE_CACHE_SECONDS = 10 * 60


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
    if getattr(core, "_government_reliability_laws_v167_schema_ready", False):
        return
    lock = getattr(core, "_government_reliability_laws_v167_schema_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        core._government_reliability_laws_v167_schema_lock = lock
    async with lock:
        if getattr(core, "_government_reliability_laws_v167_schema_ready", False):
            return
        conn = core.db._require_connection()
        async with core.db.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS government_law_revisions_v167(
                    revision_id TEXT PRIMARY KEY,
                    chat_id INTEGER NOT NULL,
                    law_id TEXT NOT NULL,
                    law_number INTEGER NOT NULL,
                    bill_id TEXT NOT NULL UNIQUE,
                    actor_id INTEGER NOT NULL,
                    old_title TEXT NOT NULL,
                    old_text TEXT NOT NULL,
                    new_title TEXT NOT NULL,
                    new_text TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_government_law_revisions_v167_chat_law
                    ON government_law_revisions_v167(chat_id,law_id,created_at DESC);
                """
            )
            await conn.commit()
        core._government_reliability_laws_v167_schema_ready = True


def install_government_reliability_laws_v167(core: Any) -> None:
    if getattr(core, "_government_reliability_laws_v167_installed", False):
        return
    core._government_reliability_laws_v167_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION
    gov.BILL_TYPES["law_amendment"] = {
        "emoji": "✍️",
        "title": "Новая редакция действующего закона",
    }

    state_cache: dict[tuple[int, int], tuple[float, dict[str, Any]]] = {}
    state_locks: dict[tuple[int, int], asyncio.Lock] = {}
    chat_title_cache: dict[int, tuple[float, str]] = {}

    def invalidate_chat(chat_id: int) -> None:
        target = int(chat_id)
        for key in [item for item in state_cache if item[0] == target]:
            state_cache.pop(key, None)

    previous_chat_title = gov._chat_title

    async def cached_chat_title(bot: Any, chat_id: int) -> str:
        key = int(chat_id)
        cached = chat_title_cache.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < CHAT_TITLE_CACHE_SECONDS:
            return cached[1]
        title = await previous_chat_title(bot, key)
        chat_title_cache[key] = (now, str(title))
        return str(title)

    gov._chat_title = cached_chat_title

    previous_create_bill = gov._create_bill

    async def create_bill_with_law_amendment(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        author_id: int,
        bill_type: str,
        title: str,
        description: str,
        payload: dict[str, Any],
    ) -> str:
        if str(bill_type) != "law_amendment":
            return await previous_create_bill(
                core_arg,
                bot,
                int(chat_id),
                int(author_id),
                str(bill_type),
                str(title),
                str(description),
                dict(payload or {}),
            )

        offices = await gov._user_offices(core_arg, int(chat_id), int(author_id))
        is_admin = int(author_id) == int(core_arg.DEVELOPER_ID)
        if not (is_admin or "president" in offices):
            raise PermissionError("Новую редакцию действующего закона предлагает Президент реальности.")

        await _ensure_schema(core_arg)
        law_id = str((payload or {}).get("law_id") or "").strip()
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM government_laws_v127 WHERE law_id=? AND chat_id=? AND active=1",
            (law_id, int(chat_id)),
        )
        law = await cursor.fetchone()
        if law is None:
            raise ValueError("Действующий закон для новой редакции не найден.")

        new_title = str((payload or {}).get("new_title") or "").strip()
        new_text = str((payload or {}).get("new_text") or "").strip()
        reason = str(description or "").strip()
        if len(new_title) < 5 or len(new_title) > 120:
            raise ValueError("Новое название закона должно содержать от 5 до 120 символов.")
        if len(new_text) < 10 or len(new_text) > 1200:
            raise ValueError("Новая редакция закона должна содержать от 10 до 1200 символов.")
        if len(reason) < 10 or len(reason) > 1200:
            raise ValueError("Обоснование поправки должно содержать от 10 до 1200 символов.")
        if new_title == str(law["title"]) and new_text == str(law["text"]):
            raise ValueError("Новая редакция полностью совпадает с действующим законом.")

        number = int(law["number"])
        normalized = {
            "law_id": law_id,
            "law_number": number,
            "new_title": new_title,
            "new_text": new_text,
        }
        bill_title = f"Новая редакция закона №{number}: {new_title}"[:120]
        bill_id = await previous_create_bill(
            core_arg,
            bot,
            int(chat_id),
            int(author_id),
            "law_amendment",
            bill_title,
            reason,
            normalized,
        )
        invalidate_chat(int(chat_id))
        return bill_id

    gov._create_bill = create_bill_with_law_amendment

    previous_enact_bill = gov._enact_bill

    async def enact_bill_with_law_amendment(
        core_arg: Any,
        bot: Any,
        bill: Any,
        actor_id: int,
    ) -> None:
        if str(bill["bill_type"]) != "law_amendment":
            await previous_enact_bill(core_arg, bot, bill, int(actor_id))
            invalidate_chat(int(bill["chat_id"]))
            return

        await _ensure_schema(core_arg)
        chat_id = int(bill["chat_id"])
        bill_id = str(bill["bill_id"])
        payload = gov._json(bill["payload_json"], {})
        law_id = str(payload.get("law_id") or "")
        new_title = str(payload.get("new_title") or "").strip()
        new_text = str(payload.get("new_text") or "").strip()
        conn = core_arg.db._require_connection()
        now = gov._now()

        async with core_arg.db.lock:
            cursor = await conn.execute(
                "SELECT * FROM government_laws_v127 WHERE law_id=? AND chat_id=? AND active=1",
                (law_id, chat_id),
            )
            law = await cursor.fetchone()
            if law is None:
                raise ValueError("Закон, для которого принята поправка, больше не действует.")
            cursor = await conn.execute(
                "SELECT 1 FROM government_law_revisions_v167 WHERE bill_id=? LIMIT 1",
                (bill_id,),
            )
            if await cursor.fetchone() is not None:
                raise ValueError("Эта редакция закона уже вступила в силу.")

            revision_id = secrets.token_urlsafe(12)
            await conn.execute(
                """
                INSERT INTO government_law_revisions_v167(
                    revision_id,chat_id,law_id,law_number,bill_id,actor_id,
                    old_title,old_text,new_title,new_text,reason,created_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    revision_id,
                    chat_id,
                    law_id,
                    int(law["number"]),
                    bill_id,
                    int(actor_id),
                    str(law["title"]),
                    str(law["text"]),
                    new_title,
                    new_text,
                    str(bill["description"]),
                    now,
                ),
            )
            await conn.execute(
                "UPDATE government_laws_v127 SET title=?,text=? WHERE law_id=? AND chat_id=? AND active=1",
                (new_title, new_text, law_id, chat_id),
            )
            await conn.execute(
                "UPDATE government_bills_v127 SET status='enacted',resolved_at=? WHERE bill_id=?",
                (now, bill_id),
            )
            await conn.commit()

        invalidate_chat(chat_id)
        await gov._publish(
            bot,
            chat_id,
            f"✍️ <b>ЗАКОН №{int(law['number'])} ИЗЛОЖЕН В НОВОЙ РЕДАКЦИИ</b>\n\n"
            f"<b>{html.escape(new_title)}</b>\n\n"
            f"{html.escape(new_text)}\n\n"
            f"Основание: {html.escape(str(bill['description']))}\n\n"
            "Редакция одобрена Госдумой и утверждена Президентом реальности.",
        )

    gov._enact_bill = enact_bill_with_law_amendment

    previous_state = gov._state

    async def state_with_reliability_and_revisions(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        key = (int(chat_id), int(user_id))
        now = time.monotonic()
        cached = state_cache.get(key)
        if cached and now - cached[0] < STATE_CACHE_SECONDS:
            return copy.deepcopy(cached[1])

        lock = state_locks.setdefault(key, asyncio.Lock())
        async with lock:
            now = time.monotonic()
            cached = state_cache.get(key)
            if cached and now - cached[0] < STATE_CACHE_SECONDS:
                return copy.deepcopy(cached[1])

            payload = await previous_state(core_arg, bot, int(chat_id), int(user_id))
            await _ensure_schema(core_arg)
            conn = core_arg.db._require_connection()
            cursor = await conn.execute(
                """
                SELECT law_id,COUNT(*) revision_count,MAX(created_at) last_revised_at
                FROM government_law_revisions_v167
                WHERE chat_id=? GROUP BY law_id
                """,
                (int(chat_id),),
            )
            revisions = {
                str(row["law_id"]): {
                    "revision_count": int(row["revision_count"] or 0),
                    "last_revised_at": int(row["last_revised_at"] or 0),
                }
                for row in await cursor.fetchall()
            }
            offices = set(str(value) for value in (payload.get("user") or {}).get("offices", []))
            is_admin = bool((payload.get("user") or {}).get("is_admin"))
            can_amend = bool(is_admin or "president" in offices)
            laws = payload.get("laws") or []
            for law in laws:
                if not isinstance(law, dict):
                    continue
                law_id = str(law.get("law_id") or "")
                law.update(revisions.get(law_id, {"revision_count": 0, "last_revised_at": 0}))
                law["can_amend"] = bool(can_amend and law.get("active", True))
            payload.setdefault("permissions", {})["can_amend_laws"] = can_amend
            payload["version"] = VERSION
            payload["law_revision_rules_v167"] = {
                "can_amend": can_amend,
                "requires_duma": True,
                "preserves_mechanics": True,
            }
            state_cache[key] = (time.monotonic(), copy.deepcopy(payload))
            return payload

    gov._state = state_with_reliability_and_revisions

    previous_inject = luxury._inject_assets

    def inject_reliability_assets(source: str) -> str:
        source = previous_inject(source)
        replacements = {
            "treasury-contributions-v150.css?v=150": "treasury-contributions-v150.css?v=167",
            "treasury-contributions-v150.js?v=150": "treasury-contributions-v150.js?v=167",
            "treasury-management-v164.css?v=166": "treasury-management-v164.css?v=167",
            "treasury-management-v164.js?v=166": "treasury-management-v164.js?v=167",
            "treasury-requests-v165.css?v=166": "treasury-requests-v165.css?v=167",
            "treasury-requests-v165.js?v=166": "treasury-requests-v165.js?v=167",
        }
        for old, new in replacements.items():
            source = source.replace(old, new)

        early_tag = f'  <script src="/government-v167/{EARLY_JS.name}?v=167"></script>\n'
        app_marker = '  <script src="/government-v127/app.js'
        if EARLY_JS.name not in source and app_marker in source:
            source = source.replace(app_marker, early_tag + app_marker, 1)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v167/{ASSET_CSS.name}?v=167">\n</head>',
            )
        if LATE_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v167/{LATE_JS.name}?v=167"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject_reliability_assets

    original_connect = core.Database.connect

    async def connect_with_reliability(self: Any) -> None:
        await original_connect(self)
        await _ensure_schema(core)

    core.Database.connect = connect_with_reliability

    original_start = core.start_webapp_server

    async def start_with_reliability(bot: Any):
        for path in (EARLY_JS, LATE_JS, ASSET_CSS):
            if not path.is_file():
                raise RuntimeError(f"Не найден ассет Reality 167: {path.name}")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            paths = {EARLY_JS.name: EARLY_JS, LATE_JS.name: LATE_JS, ASSET_CSS.name: ASSET_CSS}
            path = paths.get(name)
            if path is None:
                raise core.web.HTTPNotFound()
            content_type = "application/javascript" if path.suffix == ".js" else "text/css"
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "Content-Type": f"{content_type}; charset=utf-8",
                    "X-Government-Reliability": "167",
                },
            )

        def runner_with_reliability(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v167/{name}") not in keys:
                app.router.add_get("/government-v167/{name}", asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_reliability
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_reliability
