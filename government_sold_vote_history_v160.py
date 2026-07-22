from __future__ import annotations

from pathlib import Path
from typing import Any

import government_election_shadow_v153 as shadow
import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 160 · Личная история проданных голосов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "sold-vote-history-v160.js"
ASSET_CSS = APP_DIR / "sold-vote-history-v160.css"


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


async def _my_sold_votes(core: Any, chat_id: int, user_id: int) -> list[dict[str, Any]]:
    """Return only votes sold by the authenticated participant."""
    await shadow._ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT
            b.offer_id,b.election_id,b.buyer_id,b.amount,b.status,
            b.created_at,b.responded_at,b.accepted_candidate_id,
            e.office_key,e.phase,e.resolved_at,e.voting_ends_at,
            p.username,p.full_name
        FROM government_vote_bribes_v153 b
        JOIN government_elections_v127 e ON e.election_id=b.election_id
        LEFT JOIN players p ON p.chat_id=b.chat_id AND p.user_id=b.buyer_id
        WHERE b.chat_id=? AND b.target_id=?
          AND b.status IN ('accepted','convicted')
          AND b.accepted_candidate_id=b.buyer_id
        ORDER BY CASE WHEN b.responded_at>0 THEN b.responded_at ELSE b.created_at END DESC
        LIMIT 100
        """,
        (int(chat_id), int(user_id)),
    )
    result: list[dict[str, Any]] = []
    for row in await cursor.fetchall():
        office_key = str(row["office_key"] or "")
        office = gov.OFFICES.get(office_key, {"title": office_key, "emoji": "🗳"})
        buyer_name = str(row["full_name"] or "").strip()
        username = str(row["username"] or "").strip()
        if not buyer_name:
            buyer_name = f"@{username}" if username else f"Telegram ID {int(row['buyer_id'])}"
        result.append(
            {
                "offer_id": str(row["offer_id"]),
                "election_id": str(row["election_id"]),
                "candidate_id": int(row["buyer_id"]),
                "candidate_name": buyer_name,
                "candidate_username": username,
                "amount": int(row["amount"]),
                "accepted_at": int(row["responded_at"] or row["created_at"]),
                "office_key": office_key,
                "office_title": str(office.get("title") or office_key),
                "office_emoji": str(office.get("emoji") or "🗳"),
                "election_phase": str(row["phase"] or ""),
                "election_resolved_at": int(row["resolved_at"] or 0),
                "status": str(row["status"]),
                "status_title": (
                    "Подкуп раскрыт"
                    if str(row["status"]) == "convicted"
                    else "Голос продан"
                ),
            }
        )
    return result


def install_government_sold_vote_history_v160(core: Any) -> None:
    if getattr(core, "_government_sold_vote_history_v160_installed", False):
        return
    core._government_sold_vote_history_v160_installed = True
    core.GOVERNMENT_VERSION = VERSION

    previous_shadow_state = shadow._shadow_state

    async def shadow_state_with_private_history(
        core_arg: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_shadow_state(core_arg, chat_id, user_id)
        payload["my_sold_vote_history"] = await _my_sold_votes(
            core_arg,
            int(chat_id),
            int(user_id),
        )
        payload["sold_vote_history_private"] = True
        payload["version"] = VERSION
        return payload

    shadow._shadow_state = shadow_state_with_private_history

    previous_inject = luxury._inject_assets

    def inject(source: str) -> str:
        source = previous_inject(source)
        if ASSET_CSS.name not in source:
            source = source.replace(
                "</head>",
                f'  <link rel="stylesheet" href="/government-v160/{ASSET_CSS.name}?v=160">\n</head>',
            )
        if ASSET_JS.name not in source:
            source = source.replace(
                "</body>",
                f'  <script src="/government-v160/{ASSET_JS.name}?v=160"></script>\n</body>',
            )
        return source

    luxury._inject_assets = inject
    original_start = core.start_webapp_server

    async def start(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Missing Reality 160 sold vote history assets")
        original_runner = core.web.AppRunner

        async def serve(request: Any):
            name = str(request.match_info.get("name") or "")
            if name == ASSET_JS.name:
                path = ASSET_JS
            elif name == ASSET_CSS.name:
                path = ASSET_CSS
            else:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                path,
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Sold-Vote-History": "160",
                },
            )

        def runner(app: Any, *args: Any, **kwargs: Any):
            path = "/government-v160/{name}"
            if ("GET", path) not in _route_keys(app):
                app.router.add_get(path, serve)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start
