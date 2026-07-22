from __future__ import annotations

from typing import Any

import government_role_permissions_v148 as strict_roles
import government_v127 as gov


VERSION = "Reality 174 · Голосование всех должностей"


def install_government_universal_voting_v174(core: Any) -> None:
    """Allow every active government office holder to vote on every bill type.

    Reality 168 changed the core vote handler, but the older strict-role middleware
    still rejected ``vote_bill`` unless the user was a Duma deputy. This final layer
    updates both the middleware gate and the state/handler used by the Mini App.
    """
    if getattr(core, "_government_universal_voting_v174_installed", False):
        return
    core._government_universal_voting_v174_installed = True
    core.GOVERNMENT_VERSION = VERSION
    gov.VERSION = VERSION

    previous_check_core_action = strict_roles._check_core_action

    async def check_core_action_with_universal_voting(
        core_arg: Any,
        chat_id: int,
        user_id: int,
        data: dict[str, Any],
    ) -> None:
        if str(data.get("action") or "") == "vote_bill":
            offices = await gov._user_offices(core_arg, int(chat_id), int(user_id))
            if not offices:
                raise PermissionError(
                    "Голосовать по законопроектам могут только действующие "
                    "государственные должностные лица."
                )
            if await gov._has_active_sanctions(core_arg, int(chat_id), int(user_id)):
                raise PermissionError(
                    "Должностное лицо с активными санкциями временно не участвует "
                    "в голосовании."
                )
            return
        await previous_check_core_action(
            core_arg,
            int(chat_id),
            int(user_id),
            data,
        )

    # The Reality 148 middleware resolves this module global at request time, so
    # replacing it removes the obsolete deputy-only gate without adding middleware.
    strict_roles._check_core_action = check_core_action_with_universal_voting

    async def vote_bill_for_any_official(
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
                "По законопроектам голосуют действующие государственные "
                "должностные лица."
            )
        if await gov._has_active_sanctions(core_arg, int(chat_id), int(voter_id)):
            raise PermissionError(
                "Должностное лицо с активными санкциями временно не участвует "
                "в голосовании."
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

    gov._vote_bill = vote_bill_for_any_official

    previous_state = gov._state

    async def state_with_universal_voting(
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

        payload.setdefault("permissions", {})["can_vote_bill"] = can_vote
        payload["universal_voting_v174"] = {
            "can_vote": can_vote,
            "my_offices": offices,
            "all_bill_types": True,
            "one_person_one_vote": True,
            "rule": (
                "Любое действующее государственное должностное лицо может "
                "голосовать за любой законопроект."
            ),
        }
        payload["version"] = VERSION
        return payload

    gov._state = state_with_universal_voting
