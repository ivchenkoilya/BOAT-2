from __future__ import annotations

from typing import Any

import government_election_shadow_v153 as shadow
import government_v127 as gov


async def _accepted_sale(core: Any, election_id: str, target_id: int) -> Any | None:
    await shadow._ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_vote_bribes_v153
        WHERE election_id=? AND target_id=? AND status='accepted'
        ORDER BY responded_at DESC LIMIT 1
        """,
        (str(election_id), int(target_id)),
    )
    return await cursor.fetchone()


def install_government_election_shadow_safety_v153(core: Any) -> None:
    if getattr(core, "_government_election_shadow_safety_v153_installed", False):
        return
    core._government_election_shadow_safety_v153_installed = True

    original_create = shadow._create_bribe_offer

    async def create_without_resale(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        buyer_id: int,
        election_id: str,
        target_id: int,
        amount: int,
    ) -> str:
        if await _accepted_sale(core_arg, election_id, target_id) is not None:
            raise ValueError("Этот участник уже продал голос на данных выборах.")
        return await original_create(
            core_arg,
            bot,
            chat_id,
            buyer_id,
            election_id,
            target_id,
            amount,
        )

    async def accept_once(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        offer_id: str,
    ) -> str:
        await shadow._expire_offers(core_arg, chat_id)
        offer = await shadow._get_offer(core_arg, chat_id, offer_id)
        now = shadow._now()
        if int(offer["target_id"]) != int(user_id):
            raise PermissionError("Это предложение предназначено другому участнику.")
        if str(offer["status"]) != "pending" or int(offer["expires_at"]) <= now:
            raise ValueError("Предложение уже недействительно.")
        election = await shadow._election(core_arg, chat_id, str(offer["election_id"]))
        if str(election["phase"]) != "voting" or int(election["voting_ends_at"]) <= now:
            raise ValueError("Голосование уже завершено.")
        buyer_id = int(offer["buyer_id"])
        if not await shadow._is_candidate(core_arg, str(offer["election_id"]), buyer_id):
            raise ValueError("Заказчик больше не участвует в этих выборах.")
        amount = int(offer["amount"])
        conn = core_arg.db._require_connection()
        async with core_arg.db.lock:
            cursor = await conn.execute(
                """
                SELECT 1 FROM government_vote_bribes_v153
                WHERE election_id=? AND target_id=? AND status='accepted'
                LIMIT 1
                """,
                (str(offer["election_id"]), int(user_id)),
            )
            if await cursor.fetchone() is not None:
                await conn.rollback()
                raise ValueError("Ты уже продал голос на этих выборах.")
            cursor = await conn.execute(
                """
                UPDATE players SET points=points-?,updated_at=?
                WHERE chat_id=? AND user_id=? AND points>=?
                """,
                (amount, now, int(chat_id), buyer_id, amount),
            )
            if int(cursor.rowcount or 0) <= 0:
                await conn.rollback()
                raise ValueError("У кандидата больше нет денег для исполнения предложения.")
            await conn.execute(
                "UPDATE players SET points=points+?,updated_at=? WHERE chat_id=? AND user_id=?",
                (amount, now, int(chat_id), int(user_id)),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (int(chat_id), buyer_id, -amount, "secret_vote_purchase_v153", now),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (int(chat_id), int(user_id), amount, "secret_vote_sale_v153", now),
            )
            await conn.execute(
                """
                INSERT INTO government_election_votes_v127(election_id,voter_id,candidate_id,created_at)
                VALUES(?,?,?,?) ON CONFLICT(election_id,voter_id) DO UPDATE SET
                candidate_id=excluded.candidate_id,created_at=excluded.created_at
                """,
                (str(offer["election_id"]), int(user_id), buyer_id, now),
            )
            cursor = await conn.execute(
                """
                UPDATE government_vote_bribes_v153
                SET status='accepted',responded_at=?,accepted_candidate_id=?
                WHERE offer_id=? AND status='pending'
                """,
                (now, buyer_id, str(offer_id)),
            )
            if int(cursor.rowcount or 0) <= 0:
                await conn.rollback()
                raise ValueError("Предложение уже обработано.")
            await conn.execute(
                """
                UPDATE government_vote_bribes_v153
                SET status='cancelled',responded_at=?
                WHERE election_id=? AND target_id=? AND offer_id<>? AND status='pending'
                """,
                (now, str(offer["election_id"]), int(user_id), str(offer_id)),
            )
            await conn.commit()
        return (
            f"Ты получил {gov._fmt(amount)} влияния. Голос автоматически отдан "
            "тайному кандидату и заблокирован до конца выборов."
        )

    shadow._create_bribe_offer = create_without_resale
    shadow._accept_offer = accept_once
