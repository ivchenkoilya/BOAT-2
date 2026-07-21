from __future__ import annotations

from typing import Any

import government_mandates_v143 as mandates
import government_v127 as gov


VERSION = "Reality 143 · Мандаты и основные законы"


async def _ensure_numbering(core: Any, chat_id: int) -> None:
    await mandates._ensure_schema(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS government_law_numbering_v143(
                chat_id INTEGER PRIMARY KEY,
                migrated_at INTEGER NOT NULL
            )
            """
        )
        cursor = await conn.execute(
            "SELECT 1 FROM government_law_numbering_v143 WHERE chat_id=?",
            (int(chat_id),),
        )
        if await cursor.fetchone() is not None:
            return
        await conn.execute(
            "UPDATE government_laws_v127 SET number=number+10 WHERE chat_id=?",
            (int(chat_id),),
        )
        await conn.execute(
            """
            UPDATE government_state_v127
            SET law_seq=CASE WHEN law_seq<0 THEN 10 ELSE law_seq+10 END,
                updated_at=?
            WHERE chat_id=?
            """,
            (mandates._now(), int(chat_id)),
        )
        await conn.execute(
            "INSERT INTO government_law_numbering_v143(chat_id,migrated_at) VALUES(?,?)",
            (int(chat_id), mandates._now()),
        )
        await conn.commit()


async def _enrich_laws_fixed(core: Any, chat_id: int, laws: list[dict[str, Any]]) -> None:
    await _ensure_numbering(core, chat_id)
    conn = core.db._require_connection()
    for law in laws:
        law_id = str(law.get("law_id") or "")
        cursor = await conn.execute(
            """
            SELECT l.number current_number,l.bill_id,b.author_id,m.signed_by,
                   COALESCE(SUM(CASE WHEN v.vote='yes' THEN 1 ELSE 0 END),0) yes_votes,
                   COALESCE(SUM(CASE WHEN v.vote='no' THEN 1 ELSE 0 END),0) no_votes,
                   COALESCE(SUM(CASE WHEN v.vote='abstain' THEN 1 ELSE 0 END),0) abstain_votes
            FROM government_laws_v127 l
            LEFT JOIN government_bills_v127 b ON b.bill_id=l.bill_id AND b.chat_id=l.chat_id
            LEFT JOIN government_bill_votes_v127 v ON v.bill_id=l.bill_id
            LEFT JOIN government_law_meta_v143 m ON m.law_id=l.law_id
            WHERE l.law_id=? AND l.chat_id=?
            GROUP BY l.number,l.bill_id,b.author_id,m.signed_by
            """,
            (law_id, int(chat_id)),
        )
        row = await cursor.fetchone()
        if row is not None:
            law["number"] = int(row["current_number"])
        law["author_id"] = int(row["author_id"] if row and row["author_id"] is not None else 0)
        law["signed_by"] = int(row["signed_by"] if row and row["signed_by"] is not None else 0)
        law["votes"] = {
            "yes": int(row["yes_votes"] if row else 0),
            "no": int(row["no_votes"] if row else 0),
            "abstain": int(row["abstain_votes"] if row else 0),
        }


def install_government_mandates_integrity_v143(core: Any) -> None:
    if getattr(core, "_government_mandates_integrity_v143_installed", False):
        return
    core._government_mandates_integrity_v143_installed = True
    core.GOVERNMENT_VERSION = VERSION
    mandates.VERSION = VERSION
    mandates._enrich_laws = _enrich_laws_fixed

    original_next_number = gov._next_number

    async def next_number_with_foundation(core_arg: Any, chat_id: int, field: str) -> int:
        if field == "law_seq":
            await _ensure_numbering(core_arg, chat_id)
        return await original_next_number(core_arg, chat_id, field)

    gov._next_number = next_number_with_foundation
