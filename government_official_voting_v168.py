from __future__ import annotations

import html
import math
from typing import Any

import government_v127 as gov


VERSION = "Reality 168 · Голосование всех должностных лиц"


def install_government_official_voting_v168(core: Any) -> None:
    if getattr(core, "_government_official_voting_v168_installed", False):
        return
    core._government_official_voting_v168_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    async def official_voter_ids(core_arg: Any, chat_id: int) -> list[int]:
        """Все действующие и несанкционированные должностные лица беседы."""
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            """
            SELECT DISTINCT user_id
            FROM government_offices_v127
            WHERE chat_id=? AND ends_at>?
            ORDER BY user_id
            """,
            (int(chat_id), gov._now()),
        )
        result: list[int] = []
        for row in await cursor.fetchall():
            user_id = int(row["user_id"])
            if not await gov._has_active_sanctions(core_arg, int(chat_id), user_id):
                result.append(user_id)
        return result

    async def bill_votes_from_officials(
        core_arg: Any,
        bill_id: str,
    ) -> dict[str, int]:
        """Считает только голоса действующих должностных лиц."""
        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT chat_id FROM government_bills_v127 WHERE bill_id=? LIMIT 1",
            (str(bill_id),),
        )
        bill = await cursor.fetchone()
        result = {"yes": 0, "no": 0, "abstain": 0}
        if bill is None:
            return result

        voters = await official_voter_ids(core_arg, int(bill["chat_id"]))
        if not voters:
            return result
        placeholders = ",".join("?" for _ in voters)
        cursor = await conn.execute(
            f"""
            SELECT vote,COUNT(*) amount
            FROM government_bill_votes_v127
            WHERE bill_id=? AND voter_id IN ({placeholders})
            GROUP BY vote
            """,
            (str(bill_id), *voters),
        )
        for row in await cursor.fetchall():
            key = str(row["vote"])
            if key in result:
                result[key] = int(row["amount"] or 0)
        return result

    async def vote_bill_as_official(
        core_arg: Any,
        chat_id: int,
        voter_id: int,
        bill_id: str,
        vote: str,
    ) -> None:
        if vote not in {"yes", "no", "abstain"}:
            raise ValueError("Неизвестный вариант голосования.")

        offices = await gov._user_offices(core_arg, int(chat_id), int(voter_id))
        if not offices:
            raise PermissionError(
                "По законопроектам голосуют действующие государственные должностные лица."
            )
        if await gov._has_active_sanctions(core_arg, int(chat_id), int(voter_id)):
            raise PermissionError(
                "Должностное лицо с активными санкциями временно не участвует в голосовании."
            )

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
            INSERT INTO government_bill_votes_v127(
                bill_id,voter_id,vote,created_at
            ) VALUES(?,?,?,?)
            ON CONFLICT(bill_id,voter_id) DO UPDATE SET
                vote=excluded.vote,created_at=excluded.created_at
            """,
            (str(bill_id), int(voter_id), str(vote), gov._now()),
        )
        await conn.commit()

    async def process_bills_with_all_officials(core_arg: Any, bot: Any) -> None:
        conn = core_arg.db._require_connection()
        now = gov._now()
        cursor = await conn.execute(
            """
            SELECT * FROM government_bills_v127
            WHERE status='voting' AND voting_ends_at<=?
            ORDER BY voting_ends_at
            """,
            (now,),
        )
        for bill in await cursor.fetchall():
            chat_id = int(bill["chat_id"])
            votes = await gov._bill_votes(core_arg, str(bill["bill_id"]))
            voters = await official_voter_ids(core_arg, chat_id)
            quorum = max(1, math.ceil(len(voters) / 2))
            participation = votes["yes"] + votes["no"] + votes["abstain"]
            passed = participation >= quorum and votes["yes"] > votes["no"]

            if not passed:
                await conn.execute(
                    """
                    UPDATE government_bills_v127
                    SET status='rejected',resolved_at=? WHERE bill_id=?
                    """,
                    (now, str(bill["bill_id"])),
                )
                await conn.commit()
                await gov._publish(
                    bot,
                    chat_id,
                    f"❌ <b>ЗАКОНОПРОЕКТ №{int(bill['number'])} ОТКЛОНЁН</b>\n\n"
                    f"«{html.escape(str(bill['title']))}»\n\n"
                    f"За: <b>{votes['yes']}</b> · Против: <b>{votes['no']}</b> · "
                    f"Воздержались: <b>{votes['abstain']}</b>.\n"
                    f"Кворум должностных лиц: <b>{quorum}</b> из {len(voters)}.",
                )
                continue

            if str(bill["bill_type"]) == "appointment":
                try:
                    await gov._enact_bill(
                        core_arg,
                        bot,
                        bill,
                        int(bill["author_id"]),
                    )
                except Exception:
                    await conn.execute(
                        """
                        UPDATE government_bills_v127
                        SET status='rejected',resolved_at=? WHERE bill_id=?
                        """,
                        (now, str(bill["bill_id"])),
                    )
                    await conn.commit()
                continue

            review_ends = now + gov.PRESIDENT_REVIEW_SECONDS
            await conn.execute(
                """
                UPDATE government_bills_v127
                SET status='president_review',president_review_ends_at=?
                WHERE bill_id=?
                """,
                (review_ends, str(bill["bill_id"])),
            )
            await conn.commit()
            await gov._publish(
                bot,
                chat_id,
                f"✅ <b>ДОЛЖНОСТНЫЕ ЛИЦА ОДОБРИЛИ ЗАКОНОПРОЕКТ "
                f"№{int(bill['number'])}</b>\n\n"
                f"«{html.escape(str(bill['title']))}»\n\n"
                f"За: <b>{votes['yes']}</b> · Против: <b>{votes['no']}</b> · "
                f"Воздержались: <b>{votes['abstain']}</b>.\n\n"
                f"Документ передан Президенту. Срок решения: "
                f"<b>{gov._date_text(review_ends)}</b>.",
            )

        await conn.execute(
            """
            UPDATE government_bills_v127
            SET status='expired',resolved_at=?
            WHERE status='president_review' AND president_review_ends_at<=?
            """,
            (now, now),
        )
        await conn.commit()

    async def override_veto_by_official_votes(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        actor_id: int,
        bill_id: str,
    ) -> None:
        if not (
            int(actor_id) == int(core_arg.DEVELOPER_ID)
            or await gov._holds(core_arg, int(chat_id), int(actor_id), "chair")
        ):
            raise PermissionError(
                "Преодоление вето запускает Председатель Госдумы."
            )

        conn = core_arg.db._require_connection()
        cursor = await conn.execute(
            "SELECT * FROM government_bills_v127 WHERE bill_id=? AND chat_id=?",
            (str(bill_id), int(chat_id)),
        )
        bill = await cursor.fetchone()
        if bill is None or str(bill["status"]) != "vetoed":
            raise ValueError("Для этого законопроекта нет действующего вето.")

        voters = await official_voter_ids(core_arg, int(chat_id))
        votes = await gov._bill_votes(core_arg, str(bill_id))
        required = max(1, math.ceil(len(voters) * 2 / 3))
        if int(votes["yes"]) < required:
            raise ValueError(
                f"Для преодоления вето нужно минимум {required} голосов «за» "
                "от действующих должностных лиц."
            )
        await gov._enact_bill(core_arg, bot, bill, int(actor_id))

    previous_state = gov._state

    async def state_with_official_voting(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await previous_state(
            core_arg,
            bot,
            int(chat_id),
            int(user_id),
        )
        user = payload.get("user") or {}
        offices = [str(value) for value in user.get("offices", [])]
        sanctioned = bool(user.get("sanctioned"))
        can_vote = bool(offices) and not sanctioned
        voters = await official_voter_ids(core_arg, int(chat_id))

        payload.setdefault("permissions", {})["can_vote_bill"] = can_vote
        payload["official_voting_v168"] = {
            "can_vote": can_vote,
            "voter_count": len(voters),
            "my_offices": offices,
            "rule": "Один человек — один голос независимо от количества должностей.",
        }
        payload["version"] = VERSION
        return payload

    gov._bill_votes = bill_votes_from_officials
    gov._vote_bill = vote_bill_as_official
    gov._process_bills = process_bills_with_all_officials
    gov._override_veto = override_veto_by_official_votes
    gov._state = state_with_official_voting
