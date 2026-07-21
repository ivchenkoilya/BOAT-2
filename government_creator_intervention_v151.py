from __future__ import annotations

from typing import Any

import government_v127 as gov


VERSION = "Reality 151 · Системное вмешательство создателя"


def install_government_creator_intervention_v151(core: Any) -> None:
    if getattr(core, "_government_creator_intervention_v151_installed", False):
        return
    core._government_creator_intervention_v151_installed = True

    original_vote_bill = gov._vote_bill
    original_vote_election = gov._vote_election

    async def vote_bill_with_creator(
        core_arg: Any,
        chat_id: int,
        voter_id: int,
        bill_id: str,
        vote: str,
    ) -> None:
        if int(voter_id) != int(core_arg.DEVELOPER_ID):
            await original_vote_bill(core_arg, chat_id, voter_id, bill_id, vote)
            return
        if vote not in {"yes", "no", "abstain"}:
            raise ValueError("Неизвестный вариант голосования.")
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM government_bills_v127 WHERE bill_id=? AND chat_id=?",
            (str(bill_id), int(chat_id)),
        )
        bill = await cursor.fetchone()
        if (
            bill is None
            or str(bill["status"]) != "voting"
            or int(bill["voting_ends_at"]) <= gov._now()
        ):
            raise ValueError("Голосование по законопроекту завершено.")
        await conn.execute(
            """
            INSERT INTO government_bill_votes_v127(bill_id,voter_id,vote,created_at)
            VALUES(?,?,?,?)
            ON CONFLICT(bill_id,voter_id) DO UPDATE SET
                vote=excluded.vote,created_at=excluded.created_at
            """,
            (str(bill_id), int(voter_id), str(vote), gov._now()),
        )
        await conn.commit()

    async def vote_election_with_creator(
        core_arg: Any,
        chat_id: int,
        voter_id: int,
        election_id: str,
        candidate_id: int,
    ) -> None:
        if int(voter_id) != int(core_arg.DEVELOPER_ID):
            await original_vote_election(
                core_arg,
                chat_id,
                voter_id,
                election_id,
                candidate_id,
            )
            return
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM government_elections_v127 WHERE election_id=? AND chat_id=?",
            (str(election_id), int(chat_id)),
        )
        election = await cursor.fetchone()
        if (
            election is None
            or str(election["phase"]) != "voting"
            or int(election["voting_ends_at"]) <= gov._now()
        ):
            raise ValueError("Голосование уже завершено.")
        cursor = await conn.execute(
            "SELECT 1 FROM government_candidates_v127 WHERE election_id=? AND user_id=?",
            (str(election_id), int(candidate_id)),
        )
        if await cursor.fetchone() is None:
            raise ValueError("Кандидат не найден.")
        await conn.execute(
            """
            INSERT INTO government_election_votes_v127(
                election_id,voter_id,candidate_id,created_at
            ) VALUES(?,?,?,?)
            ON CONFLICT(election_id,voter_id) DO UPDATE SET
                candidate_id=excluded.candidate_id,created_at=excluded.created_at
            """,
            (str(election_id), int(voter_id), int(candidate_id), gov._now()),
        )
        await conn.commit()

    gov._vote_bill = vote_bill_with_creator
    gov._vote_election = vote_election_with_creator
