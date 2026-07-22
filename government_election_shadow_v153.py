from __future__ import annotations

import html
import secrets
from pathlib import Path
from typing import Any, Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import government_crisis_v131 as crisis
import government_institutions_v128 as institutions
import government_mandate_luxury_v147 as luxury
import government_mandate_revocation_v152 as revocation
import government_mandates_v143 as mandates
import government_v127 as gov


VERSION = "Reality 153 · Теневая избирательная система"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "election-shadow-v153.js"
ASSET_CSS = APP_DIR / "election-shadow-v153.css"

OFFER_MIN = 1_000
OFFER_MAX = 500_000
OFFER_LIFETIME = 60 * 60
BRIBERY_EVIDENCE_REQUIRED = 7
THEFT_EVIDENCE_REQUIRED = 7
THEFT_ORGANS_REQUIRED = 3
INVESTIGATION_OFFICES = ("finance", "auditor", "oversight", "prosecutor")

BRIBERY_EVIDENCE = {
    "cec": (1, 2, "ЦИК подтвердил существование тайного предложения и связанный с ним голос."),
    "oversight": (1, 2, "Надзор обнаружил несоответствие между временем предложения и изменением голоса."),
    "auditor": (2, 3, "Счётная палата выявила совпадающий денежный перевод."),
    "prosecutor": (2, 3, "Прокуратура закрепила связь между заказчиком, переводом и голосом."),
}

THEFT_EVIDENCE = {
    "finance": (
        1,
        2,
        (
            "Минфин выявил движение средств вскоре после хищения.",
            "Минфин обнаружил дробление похищенной суммы на несколько операций.",
            "Минфин установил подозрительное изменение баланса одного из участников.",
        ),
    ),
    "auditor": (
        2,
        3,
        (
            "Счётная палата обнаружила совпадение части похищенной суммы.",
            "Счётная палата выявила нарушение контрольной суммы операции.",
            "Счётная палата нашла след изменения записи в журнале казны.",
        ),
    ),
    "oversight": (
        1,
        2,
        (
            "Надзор сузил круг подозреваемых по времени активности.",
            "Надзор установил, что подозреваемый имел доступ к государственному разделу.",
            "Надзор выявил попытку создать ложный след.",
        ),
    ),
    "prosecutor": (
        2,
        3,
        (
            "Прокуратура подтвердила связь финансового маршрута с подозреваемым.",
            "Прокуратура обнаружила попытку скрыть государственную операцию.",
            "Прокуратура закрепила собранные материалы как процессуальное доказательство.",
        ),
    ),
}


def _now() -> int:
    return gov._now()


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


def _offer_title(status: str) -> str:
    return {
        "pending": "Ожидает ответа",
        "accepted": "Голос продан",
        "declined": "Отклонено",
        "reported": "Передано в ЦИК",
        "expired": "Истекло",
        "cancelled": "Аннулировано",
        "convicted": "Подкуп доказан",
    }.get(status, status)


async def _ensure_schema(core: Any) -> None:
    if getattr(core.db, "_government_election_shadow_v153_schema", False):
        return
    await crisis._ensure_schema(core)
    await revocation._ensure_schema(core)
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_vote_bribes_v153(
                offer_id TEXT PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                election_id TEXT NOT NULL,
                buyer_id INTEGER NOT NULL,
                target_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                responded_at INTEGER NOT NULL DEFAULT 0,
                accepted_candidate_id INTEGER NOT NULL DEFAULT 0,
                UNIQUE(election_id,buyer_id,target_id)
            );
            CREATE INDEX IF NOT EXISTS idx_vote_bribes_target_v153
            ON government_vote_bribes_v153(chat_id,target_id,status,expires_at);
            CREATE INDEX IF NOT EXISTS idx_vote_bribes_election_v153
            ON government_vote_bribes_v153(election_id,status,created_at);

            CREATE TABLE IF NOT EXISTS government_vote_bribe_evidence_v153(
                offer_id TEXT NOT NULL,
                office_key TEXT NOT NULL,
                investigator_id INTEGER NOT NULL,
                points INTEGER NOT NULL,
                clue TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(offer_id,office_key)
            );

            CREATE TABLE IF NOT EXISTS government_theft_evidence_v153(
                theft_id TEXT NOT NULL,
                office_key TEXT NOT NULL,
                investigator_id INTEGER NOT NULL,
                points INTEGER NOT NULL,
                clue TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY(theft_id,office_key)
            );
            """
        )
        await conn.commit()
    core.db._government_election_shadow_v153_schema = True


async def _expire_offers(core: Any, chat_id: int = 0) -> None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    if chat_id:
        await conn.execute(
            """
            UPDATE government_vote_bribes_v153
            SET status='expired',responded_at=?
            WHERE chat_id=? AND status='pending' AND expires_at<=?
            """,
            (now, int(chat_id), now),
        )
    else:
        await conn.execute(
            """
            UPDATE government_vote_bribes_v153
            SET status='expired',responded_at=?
            WHERE status='pending' AND expires_at<=?
            """,
            (now, now),
        )
    await conn.commit()


async def _player(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    player = await gov._player_dict(core, int(chat_id), int(user_id))
    if player is None:
        raise ValueError("Участник не найден в этой беседе.")
    return player


async def _election(core: Any, chat_id: int, election_id: str) -> Any:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_elections_v127 WHERE election_id=? AND chat_id=?",
        (str(election_id), int(chat_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Выборы не найдены.")
    return row


async def _is_candidate(core: Any, election_id: str, user_id: int) -> bool:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT 1 FROM government_candidates_v127 WHERE election_id=? AND user_id=?",
        (str(election_id), int(user_id)),
    )
    return await cursor.fetchone() is not None


async def _send_secret_offer_notice(
    core: Any,
    bot: Any,
    chat_id: int,
    target_id: int,
    amount: int,
    office_title: str,
) -> None:
    try:
        link = gov._government_link(core, int(chat_id))
        markup = None
        if link:
            markup = InlineKeyboardMarkup(
                inline_keyboard=[[
                    InlineKeyboardButton(text="💵 Открыть тайное предложение", url=link)
                ]]
            )
        await bot.send_message(
            int(target_id),
            "💵 <b>ТАЙНОЕ ПРЕДЛОЖЕНИЕ</b>\n\n"
            f"Неизвестный кандидат предлагает <b>{gov._fmt(amount)}</b> влияния "
            f"за твой голос на выборах: <b>{html.escape(office_title)}</b>.\n\n"
            "Личность кандидата скрыта. Предложение действует <b>1 час</b>.",
            reply_markup=markup,
        )
    except Exception:
        pass


async def _create_bribe_offer(
    core: Any,
    bot: Any,
    chat_id: int,
    buyer_id: int,
    election_id: str,
    target_id: int,
    amount: int,
) -> str:
    await _ensure_schema(core)
    await _expire_offers(core, chat_id)
    election = await _election(core, chat_id, election_id)
    now = _now()
    if str(election["phase"]) != "voting" or int(election["voting_ends_at"]) <= now:
        raise ValueError("Покупать голоса можно только во время голосования.")
    if not await _is_candidate(core, election_id, buyer_id):
        raise PermissionError("Покупать голоса может только зарегистрированный кандидат.")
    if int(target_id) == int(buyer_id):
        raise ValueError("Нельзя купить собственный голос.")
    await _player(core, chat_id, target_id)
    amount = int(amount)
    if amount < OFFER_MIN or amount > OFFER_MAX:
        raise ValueError(
            f"Сумма предложения должна быть от {gov._fmt(OFFER_MIN)} до {gov._fmt(OFFER_MAX)}."
        )
    buyer = await _player(core, chat_id, buyer_id)
    if int(buyer["points"]) < amount:
        raise ValueError("На балансе кандидата недостаточно влияния.")
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_vote_bribes_v153
        WHERE election_id=? AND buyer_id=? AND target_id=?
        """,
        (str(election_id), int(buyer_id), int(target_id)),
    )
    existing = await cursor.fetchone()
    if existing is not None and str(existing["status"]) in {"accepted", "reported", "convicted"}:
        raise ValueError("Этому участнику уже нельзя отправить новое предложение от данного кандидата.")
    offer_id = str(existing["offer_id"]) if existing is not None else secrets.token_urlsafe(12)
    expires_at = min(now + OFFER_LIFETIME, int(election["voting_ends_at"]))
    await conn.execute(
        """
        INSERT INTO government_vote_bribes_v153(
            offer_id,chat_id,election_id,buyer_id,target_id,amount,status,
            created_at,expires_at,responded_at,accepted_candidate_id
        ) VALUES(?,?,?,?,?,?,'pending',?,?,0,0)
        ON CONFLICT(election_id,buyer_id,target_id) DO UPDATE SET
            offer_id=excluded.offer_id,amount=excluded.amount,status='pending',
            created_at=excluded.created_at,expires_at=excluded.expires_at,
            responded_at=0,accepted_candidate_id=0
        """,
        (
            offer_id,
            int(chat_id),
            str(election_id),
            int(buyer_id),
            int(target_id),
            amount,
            now,
            expires_at,
        ),
    )
    await conn.commit()
    spec = gov.OFFICES.get(str(election["office_key"]), {"title": str(election["office_key"])})
    await _send_secret_offer_notice(
        core,
        bot,
        chat_id,
        target_id,
        amount,
        str(spec["title"]),
    )
    return "Тайное предложение отправлено на один час."


async def _get_offer(core: Any, chat_id: int, offer_id: str) -> Any:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_vote_bribes_v153 WHERE offer_id=? AND chat_id=?",
        (str(offer_id), int(chat_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Тайное предложение не найдено.")
    return row


async def _accept_offer(core: Any, chat_id: int, user_id: int, offer_id: str) -> str:
    await _expire_offers(core, chat_id)
    offer = await _get_offer(core, chat_id, offer_id)
    now = _now()
    if int(offer["target_id"]) != int(user_id):
        raise PermissionError("Это предложение предназначено другому участнику.")
    if str(offer["status"]) != "pending" or int(offer["expires_at"]) <= now:
        raise ValueError("Предложение уже недействительно.")
    election = await _election(core, chat_id, str(offer["election_id"]))
    if str(election["phase"]) != "voting" or int(election["voting_ends_at"]) <= now:
        raise ValueError("Голосование уже завершено.")
    buyer_id = int(offer["buyer_id"])
    if not await _is_candidate(core, str(offer["election_id"]), buyer_id):
        raise ValueError("Заказчик больше не участвует в этих выборах.")
    amount = int(offer["amount"])
    conn = core.db._require_connection()
    async with core.db.lock:
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
        await conn.execute(
            """
            UPDATE government_vote_bribes_v153
            SET status='accepted',responded_at=?,accepted_candidate_id=?
            WHERE offer_id=? AND status='pending'
            """,
            (now, buyer_id, str(offer_id)),
        )
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


async def _decline_offer(core: Any, chat_id: int, user_id: int, offer_id: str) -> str:
    offer = await _get_offer(core, chat_id, offer_id)
    if int(offer["target_id"]) != int(user_id):
        raise PermissionError("Это предложение предназначено другому участнику.")
    if str(offer["status"]) != "pending":
        raise ValueError("Предложение уже закрыто.")
    conn = core.db._require_connection()
    await conn.execute(
        "UPDATE government_vote_bribes_v153 SET status='declined',responded_at=? WHERE offer_id=?",
        (_now(), str(offer_id)),
    )
    await conn.commit()
    return "Тайное предложение отклонено."


async def _report_offer(core: Any, bot: Any, chat_id: int, user_id: int, offer_id: str) -> str:
    offer = await _get_offer(core, chat_id, offer_id)
    if int(offer["target_id"]) != int(user_id):
        raise PermissionError("Передать в ЦИК можно только собственное предложение.")
    if str(offer["status"]) != "pending":
        raise ValueError("Предложение уже закрыто.")
    conn = core.db._require_connection()
    now = _now()
    await conn.execute(
        "UPDATE government_vote_bribes_v153 SET status='reported',responded_at=? WHERE offer_id=?",
        (now, str(offer_id)),
    )
    await conn.execute(
        """
        INSERT OR IGNORE INTO government_vote_bribe_evidence_v153(
            offer_id,office_key,investigator_id,points,clue,created_at
        ) VALUES(?,'citizen_report',?,2,?,?)
        """,
        (
            str(offer_id),
            int(user_id),
            "Получатель добровольно передал тайное предложение в ЦИК.",
            now,
        ),
    )
    await conn.commit()
    await gov._publish(
        bot,
        int(chat_id),
        "🚨 <b>В ЦИК ПЕРЕДАНО ТАЙНОЕ ПРЕДЛОЖЕНИЕ</b>\n\n"
        f"Сумма предложения: <b>{gov._fmt(int(offer['amount']))}</b> влияния.\n"
        "Личность кандидата пока не установлена.\n"
        "Доказательства: <b>2/7</b>.",
    )
    return "Предложение передано в ЦИК как доказательство. Голос не изменён."


async def _bribery_case_points(core: Any, offer_id: str) -> tuple[int, int, list[dict[str, Any]]]:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT office_key,investigator_id,points,clue,created_at
        FROM government_vote_bribe_evidence_v153
        WHERE offer_id=? ORDER BY created_at
        """,
        (str(offer_id),),
    )
    evidence = [
        {
            "office_key": str(row["office_key"]),
            "investigator_id": int(row["investigator_id"]),
            "points": int(row["points"]),
            "clue": str(row["clue"]),
            "created_at": int(row["created_at"]),
        }
        for row in await cursor.fetchall()
    ]
    points = sum(int(item["points"]) for item in evidence)
    organs = len({item["office_key"] for item in evidence if item["office_key"] in BRIBERY_EVIDENCE})
    return points, organs, evidence


async def _annul_for_vote_buying(
    core: Any,
    chat_id: int,
    buyer_id: int,
    reference: str,
    actor_id: int,
) -> list[int]:
    await revocation._ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        """
        SELECT mandate_no FROM government_mandates_v143
        WHERE chat_id=? AND user_id=? AND office_starts_at<=? AND office_ends_at>?
        """,
        (int(chat_id), int(buyer_id), now, now),
    )
    mandate_nos = [int(row["mandate_no"]) for row in await cursor.fetchall()]
    reason = (
        "Покупка голоса избирателя и вмешательство в свободное волеизъявление. "
        "Дополнительно установлены признаки коррупции по Закону №10 "
        "«О коррупции и злоупотреблении полномочиями»."
    )
    for mandate_no in mandate_nos:
        await revocation._annotate_mandate(
            core,
            mandate_no,
            revoked_at=now,
            source="law_violation",
            reason=reason,
            law_number=2,
            law_title="О свободных выборах",
            reference=reference,
            revoked_by=int(actor_id),
        )
    await conn.commit()
    return mandate_nos


async def _convict_bribery(core: Any, bot: Any, offer: Any, actor_id: int) -> None:
    chat_id = int(offer["chat_id"])
    election_id = str(offer["election_id"])
    buyer_id = int(offer["buyer_id"])
    offer_id = str(offer["offer_id"])
    conn = core.db._require_connection()
    buyer = await _player(core, chat_id, buyer_id)
    await _annul_for_vote_buying(core, chat_id, buyer_id, f"vote_bribe:{offer_id}", actor_id)
    async with core.db.lock:
        await conn.execute(
            "DELETE FROM government_election_votes_v127 WHERE election_id=? AND candidate_id=?",
            (election_id, buyer_id),
        )
        await conn.execute(
            "DELETE FROM government_candidates_v127 WHERE election_id=? AND user_id=?",
            (election_id, buyer_id),
        )
        await conn.execute(
            """
            UPDATE government_vote_bribes_v153
            SET status='convicted',responded_at=CASE WHEN responded_at=0 THEN ? ELSE responded_at END
            WHERE election_id=? AND buyer_id=? AND status IN ('pending','accepted','reported')
            """,
            (_now(), election_id, buyer_id),
        )
        await conn.execute(
            "DELETE FROM government_offices_v127 WHERE chat_id=? AND user_id=? AND ends_at>?",
            (chat_id, buyer_id, _now()),
        )
        await conn.commit()
    await crisis._set_ban(
        core,
        "government_election_bans_v131",
        chat_id,
        buyer_id,
        48 * 60 * 60,
        "Покупка голосов избирателей",
    )
    await gov._publish(
        bot,
        chat_id,
        "🚫 <b>ПОДКУП ИЗБИРАТЕЛЯ ДОКАЗАН</b>\n\n"
        f"Кандидат: <b>{html.escape(str(buyer['name']))}</b>\n"
        "Купленные голоса аннулированы, кандидат снят с выборов.\n"
        "Действующие должности прекращены, мандаты аннулированы.\n\n"
        "Правовое основание: Закон №2 «О свободных выборах» и "
        "Закон №10 «О коррупции и злоупотреблении полномочиями».",
    )


async def _investigate_bribery(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    offer_id: str,
    requested_office: str = "",
) -> str:
    offer = await _get_offer(core, chat_id, offer_id)
    if str(offer["status"]) not in {"reported", "accepted"}:
        raise ValueError("Для этого предложения нет открытого расследования.")
    offices = await gov._user_offices(core, chat_id, user_id)
    allowed = [key for key in BRIBERY_EVIDENCE if key in offices]
    if int(user_id) == int(core.DEVELOPER_ID):
        allowed = list(BRIBERY_EVIDENCE)
    office = str(requested_office or "")
    if office not in allowed:
        office = next((key for key in allowed), "")
    if not office:
        raise PermissionError("Расследование доступно ЦИК, Надзору, Счётной палате и прокуратуре.")
    _, _, evidence_before = await _bribery_case_points(core, offer_id)
    if any(item["office_key"] == office for item in evidence_before):
        raise ValueError("Эта структура уже исследовала предложение.")
    low, high, clue = BRIBERY_EVIDENCE[office]
    points = low + secrets.randbelow(high - low + 1)
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_vote_bribe_evidence_v153(
            offer_id,office_key,investigator_id,points,clue,created_at
        ) VALUES(?,?,?,?,?,?)
        """,
        (str(offer_id), office, int(user_id), points, clue, _now()),
    )
    await conn.commit()
    total, organs, _ = await _bribery_case_points(core, offer_id)
    if total >= BRIBERY_EVIDENCE_REQUIRED and organs >= 3:
        await _convict_bribery(core, bot, offer, user_id)
        return "Доказательств достаточно. Заказчик раскрыт и снят с выборов."
    return (
        f"Получено доказательств: +{points}. Всего {total}/{BRIBERY_EVIDENCE_REQUIRED}. "
        f"Участвовало структур: {organs}/3."
    )


async def _locked_bribe(core: Any, election_id: str, voter_id: int) -> Any | None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_vote_bribes_v153
        WHERE election_id=? AND target_id=? AND status='accepted'
        ORDER BY responded_at DESC LIMIT 1
        """,
        (str(election_id), int(voter_id)),
    )
    return await cursor.fetchone()


async def _universal_start_election(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    office_key: str,
) -> str:
    if office_key not in gov.OFFICES:
        raise ValueError("Неизвестная государственная должность.")
    offices = await gov._user_offices(core, chat_id, actor_id)
    if int(actor_id) != int(core.DEVELOPER_ID) and "cec" not in offices:
        raise PermissionError("Выборы на произвольную должность открывает ЦИК.")
    if await gov._active_election(core, chat_id, office_key):
        raise ValueError("Выборы на эту должность уже идут.")
    now = _now()
    election_id = secrets.token_urlsafe(12)
    spec = gov.OFFICES[office_key]
    conn = core.db._require_connection()
    await conn.execute(
        """
        INSERT INTO government_elections_v127(
            election_id,chat_id,office_key,seats,phase,nomination_ends_at,
            voting_ends_at,term_seconds,created_by,created_at,resolved_at
        ) VALUES(?,?,?,?, 'nomination', ?,0,?,?,?,0)
        """,
        (
            election_id,
            int(chat_id),
            office_key,
            int(spec.get("seats") or 1),
            now + gov.NOMINATION_SECONDS,
            gov.TERM_SECONDS,
            int(actor_id),
            now,
        ),
    )
    await conn.commit()
    await gov._publish(
        bot,
        chat_id,
        f"{spec['emoji']} <b>ОТКРЫТЫ ВЫБОРЫ</b>\n\n"
        f"Должность: <b>{html.escape(str(spec['title']))}</b>\n"
        "Выдвижение кандидатов длится 24 часа.",
    )
    return f"Выборы открыты: {election_id}."


async def _presidential_appoint(
    core: Any,
    bot: Any,
    chat_id: int,
    actor_id: int,
    office_key: str,
    target_id: int,
    seat_no: int,
    reason: str,
) -> str:
    offices = await gov._user_offices(core, chat_id, actor_id)
    if int(actor_id) != int(core.DEVELOPER_ID) and "president" not in offices:
        raise PermissionError("Назначать на должности может Президент реальности.")
    if office_key not in gov.OFFICES:
        raise ValueError("Неизвестная государственная должность.")
    person = await _player(core, chat_id, target_id)
    spec = gov.OFFICES[office_key]
    seats = max(1, int(spec.get("seats") or 1))
    seat_no = max(1, min(seats, int(seat_no or 1)))
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_offices_v127
        WHERE chat_id=? AND office_key=? AND seat_no=? AND ends_at>?
        """,
        (int(chat_id), office_key, seat_no, _now()),
    )
    previous = await cursor.fetchone()
    if previous is not None and int(previous["user_id"]) != int(target_id):
        cursor = await conn.execute(
            """
            SELECT mandate_no FROM government_mandates_v143
            WHERE chat_id=? AND user_id=? AND office_key=? AND seat_no=?
              AND office_starts_at=? AND office_ends_at>?
            """,
            (
                int(chat_id),
                int(previous["user_id"]),
                office_key,
                seat_no,
                int(previous["starts_at"]),
                _now(),
            ),
        )
        mandate = await cursor.fetchone()
        if mandate is not None:
            await revocation._annotate_mandate(
                core,
                int(mandate["mandate_no"]),
                revoked_at=_now(),
                source="system",
                reason=(
                    "Досрочная замена должностного лица прямым назначением Президента реальности. "
                    f"Основание назначения: {reason or 'кадровое решение президента'}."
                ),
                law_number=1,
                law_title="О честной государственной власти",
                reference=f"presidential_appointment:{office_key}:{seat_no}:{_now()}",
                revoked_by=int(actor_id),
            )
            await conn.commit()
    await gov._assign_office(
        core,
        chat_id,
        office_key,
        target_id,
        seat_no,
        actor_id,
        gov.TERM_SECONDS,
    )
    await institutions._log(
        core,
        chat_id,
        actor_id,
        "president",
        "direct_appointment_v153",
        "Прямое президентское назначение",
        reason,
        target_id,
        {"office_key": office_key, "seat_no": seat_no},
    )
    await gov._publish(
        bot,
        chat_id,
        "🎖 <b>ПРЯМОЕ НАЗНАЧЕНИЕ ПРЕЗИДЕНТА</b>\n\n"
        f"Участник: <b>{html.escape(str(person['name']))}</b>\n"
        f"Должность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>"
        + (f" · место {seat_no}" if seats > 1 else "")
        + f"\nОснование: {html.escape(reason or 'решение Президента реальности')}.\n\n"
        "Полномочия назначены на 7 дней и внесены в государственный реестр.",
    )
    return "Президентское назначение исполнено."


async def _theft_case(core: Any, theft_id: str) -> tuple[int, int, list[dict[str, Any]]]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT office_key,investigator_id,points,clue,created_at
        FROM government_theft_evidence_v153
        WHERE theft_id=? ORDER BY created_at
        """,
        (str(theft_id),),
    )
    evidence = [
        {
            "office_key": str(row["office_key"]),
            "investigator_id": int(row["investigator_id"]),
            "points": int(row["points"]),
            "clue": str(row["clue"]),
            "created_at": int(row["created_at"]),
        }
        for row in await cursor.fetchall()
    ]
    return (
        sum(int(item["points"]) for item in evidence),
        len({item["office_key"] for item in evidence}),
        evidence,
    )


async def _investigate_theft_v153(
    core: Any,
    bot: Any,
    chat_id: int,
    user_id: int,
    theft_id: str,
    requested_office: str = "",
) -> str:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT * FROM government_thefts_v131 WHERE theft_id=? AND chat_id=?",
        (str(theft_id), int(chat_id)),
    )
    theft = await cursor.fetchone()
    if theft is None or str(theft["status"]) != "pending" or int(theft["resolve_at"]) <= _now():
        raise ValueError("Эта операция уже закрыта.")
    offices = await gov._user_offices(core, chat_id, user_id)
    allowed = [key for key in INVESTIGATION_OFFICES if key in offices]
    if int(user_id) == int(core.DEVELOPER_ID):
        allowed = list(INVESTIGATION_OFFICES)
    _, _, existing = await _theft_case(core, theft_id)
    used = {item["office_key"] for item in existing}
    office = str(requested_office or "")
    if office not in allowed or office in used:
        office = next((key for key in allowed if key not in used), "")
    if not office:
        if set(allowed) & used:
            raise ValueError("Все доступные тебе структуры уже провели проверку.")
        raise PermissionError(
            "Расследование доступно Минфину, Счётной палате, Надзору и прокуратуре."
        )
    low, high, clues = THEFT_EVIDENCE[office]
    points = low + secrets.randbelow(high - low + 1)
    clue = clues[secrets.randbelow(len(clues))]
    await conn.execute(
        """
        INSERT INTO government_theft_evidence_v153(
            theft_id,office_key,investigator_id,points,clue,created_at
        ) VALUES(?,?,?,?,?,?)
        """,
        (str(theft_id), office, int(user_id), points, clue, _now()),
    )
    await conn.commit()
    total, organs, _ = await _theft_case(core, theft_id)
    if total >= THEFT_EVIDENCE_REQUIRED and organs >= THEFT_ORGANS_REQUIRED:
        await crisis._catch_theft(core, bot, theft, user_id)
        return "Собрано достаточно доказательств. Личность казнокрада установлена."
    return (
        f"{clue} Получено +{points}. Доказательства: {total}/{THEFT_EVIDENCE_REQUIRED}. "
        f"Структуры: {organs}/{THEFT_ORGANS_REQUIRED}."
    )


async def _shadow_state(core: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    await _ensure_schema(core)
    await _expire_offers(core, chat_id)
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        """
        SELECT b.*,e.office_key,e.phase,e.voting_ends_at
        FROM government_vote_bribes_v153 b
        JOIN government_elections_v127 e ON e.election_id=b.election_id
        WHERE b.chat_id=? AND (b.target_id=? OR b.buyer_id=?)
        ORDER BY b.created_at DESC LIMIT 80
        """,
        (int(chat_id), int(user_id), int(user_id)),
    )
    rows = list(await cursor.fetchall())
    incoming = []
    campaigns: dict[str, dict[str, Any]] = {}
    for row in rows:
        status = str(row["status"])
        item = {
            "offer_id": str(row["offer_id"]),
            "election_id": str(row["election_id"]),
            "office_key": str(row["office_key"]),
            "office_title": str(
                gov.OFFICES.get(str(row["office_key"]), {"title": row["office_key"]})["title"]
            ),
            "amount": int(row["amount"]),
            "status": status,
            "status_title": _offer_title(status),
            "created_at": int(row["created_at"]),
            "expires_at": int(row["expires_at"]),
            "remaining": gov._remaining(int(row["expires_at"])),
            "can_accept": (
                int(row["target_id"]) == int(user_id)
                and status == "pending"
                and int(row["expires_at"]) > now
                and str(row["phase"]) == "voting"
            ),
            "buyer_revealed": (
                int(row["buyer_id"])
                if str(row["phase"]) in {"resolved", "cancelled"} or status == "convicted"
                else 0
            ),
        }
        if int(row["target_id"]) == int(user_id):
            incoming.append(item)
        if int(row["buyer_id"]) == int(user_id):
            campaign = campaigns.setdefault(
                str(row["election_id"]),
                {
                    "election_id": str(row["election_id"]),
                    "office_key": str(row["office_key"]),
                    "office_title": item["office_title"],
                    "offers": 0,
                    "pending": 0,
                    "accepted": 0,
                    "reported": 0,
                    "spent": 0,
                },
            )
            campaign["offers"] += 1
            campaign[status] = int(campaign.get(status) or 0) + 1
            if status == "accepted":
                campaign["spent"] += int(row["amount"])

    cursor = await conn.execute(
        """
        SELECT b.* FROM government_vote_bribes_v153 b
        WHERE b.chat_id=? AND b.status IN ('reported','accepted')
        ORDER BY b.created_at DESC LIMIT 30
        """,
        (int(chat_id),),
    )
    investigations = []
    offices = await gov._user_offices(core, chat_id, user_id)
    for row in await cursor.fetchall():
        points, organs, evidence = await _bribery_case_points(core, str(row["offer_id"]))
        can_offices = [
            key
            for key in BRIBERY_EVIDENCE
            if (key in offices or int(user_id) == int(core.DEVELOPER_ID))
            and key not in {item["office_key"] for item in evidence}
        ]
        investigations.append(
            {
                "offer_id": str(row["offer_id"]),
                "election_id": str(row["election_id"]),
                "amount": int(row["amount"]),
                "points": points,
                "required": BRIBERY_EVIDENCE_REQUIRED,
                "organs": organs,
                "organs_required": 3,
                "evidence": evidence,
                "can_investigate_offices": can_offices,
            }
        )

    cursor = await conn.execute(
        """
        SELECT * FROM government_thefts_v131
        WHERE chat_id=? AND status='pending'
        ORDER BY started_at DESC
        """,
        (int(chat_id),),
    )
    theft_cases = []
    for row in await cursor.fetchall():
        points, organs, evidence = await _theft_case(core, str(row["theft_id"]))
        can_offices = [
            key
            for key in INVESTIGATION_OFFICES
            if (key in offices or int(user_id) == int(core.DEVELOPER_ID))
            and key not in {item["office_key"] for item in evidence}
        ]
        theft_cases.append(
            {
                "theft_id": str(row["theft_id"]),
                "amount": int(row["amount"]),
                "percent": int(row["percent"]),
                "resolve_at": int(row["resolve_at"]),
                "remaining": gov._remaining(int(row["resolve_at"])),
                "points": points,
                "required": THEFT_EVIDENCE_REQUIRED,
                "organs": organs,
                "organs_required": THEFT_ORGANS_REQUIRED,
                "evidence": evidence,
                "can_investigate_offices": can_offices,
            }
        )

    return {
        "offer_min": OFFER_MIN,
        "offer_max": OFFER_MAX,
        "offer_lifetime": OFFER_LIFETIME,
        "incoming_offers": incoming,
        "campaigns": list(campaigns.values()),
        "bribery_investigations": investigations,
        "theft_cases": theft_cases,
        "can_presidential_appoint": (
            int(user_id) == int(core.DEVELOPER_ID) or "president" in offices
        ),
        "can_start_any_election": (
            int(user_id) == int(core.DEVELOPER_ID) or "cec" in offices
        ),
        "office_options": [
            {
                "office_key": key,
                "title": str(spec["title"]),
                "emoji": str(spec["emoji"]),
                "seats": int(spec.get("seats") or 1),
            }
            for key, spec in gov.OFFICES.items()
        ],
    }


def _inject_assets(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "election-shadow-v153.css" not in source:
        source = source.replace(
            "</head>",
            '  <link rel="stylesheet" href="/government-v153/election-shadow-v153.css?v=153">\n</head>',
        )
    if "election-shadow-v153.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v153/election-shadow-v153.js?v=153"></script>\n</body>',
        )
    return source


def _extend_laws() -> None:
    for law in mandates.FOUNDATION_LAWS:
        number = int(law.get("number") or 0)
        text = str(law.get("text") or "")
        if number == 2 and "тайное предложение" not in text:
            law["text"] = (
                text
                + "\n\nТайное предложение денег за автоматическую передачу голоса признаётся "
                "покупкой голоса. При доказанном подкупе купленные голоса аннулируются, "
                "кандидат снимается с выборов и лишается государственных полномочий."
            )
        if number == 6 and "прямо назначать" not in text:
            law["text"] = (
                text
                + "\n\nПрезидент вправе прямо назначать любого участника на любую государственную "
                "должность. Такое назначение фиксируется в государственном реестре и может досрочно "
                "прекратить полномочия прежнего владельца должности."
            )


def install_government_election_shadow_v153(core: Any) -> None:
    if getattr(core, "_government_election_shadow_v153_installed", False):
        return
    core._government_election_shadow_v153_installed = True
    core.GOVERNMENT_VERSION = VERSION
    _extend_laws()

    original_connect = core.Database.connect

    async def connect_with_shadow_schema(self: Any) -> None:
        await original_connect(self)
        core.db._government_election_shadow_v153_schema = False
        await _ensure_schema(core)

    core.Database.connect = connect_with_shadow_schema

    original_state = gov._state

    async def state_with_shadow(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        payload["election_shadow_v153"] = await _shadow_state(core_arg, chat_id, user_id)
        for election in payload.get("elections", []):
            locked = await _locked_bribe(core_arg, str(election.get("election_id") or ""), user_id)
            if locked is not None and str(election.get("phase") or "") == "voting":
                election["my_vote"] = 0
                election["secret_vote_locked"] = True
        return payload

    gov._state = state_with_shadow

    previous_vote_election = gov._vote_election

    async def vote_election_with_lock(
        core_arg: Any,
        chat_id: int,
        voter_id: int,
        election_id: str,
        candidate_id: int,
    ) -> None:
        locked = await _locked_bribe(core_arg, election_id, voter_id)
        if locked is not None:
            raise PermissionError(
                "Этот голос продан тайному кандидату и заблокирован до завершения выборов."
            )
        await previous_vote_election(
            core_arg,
            chat_id,
            voter_id,
            election_id,
            candidate_id,
        )

    gov._vote_election = vote_election_with_lock
    crisis._investigate_theft = _investigate_theft_v153

    previous_inject = luxury._inject_assets

    def inject_with_shadow(source: str) -> str:
        return _inject_assets(previous_inject, source)

    luxury._inject_assets = inject_with_shadow

    async def action_api(request: Any):
        try:
            user, chat_id, data = await gov._auth(core, request)
            user_id = int(user.id)
            action = str(data.get("action") or "")
            bot = request.app["bot"]
            if action == "bribe_create":
                message = await _create_bribe_offer(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("election_id") or ""),
                    int(data.get("target_user_id") or 0),
                    int(data.get("amount") or 0),
                )
            elif action == "bribe_accept":
                message = await _accept_offer(
                    core, chat_id, user_id, str(data.get("offer_id") or "")
                )
            elif action == "bribe_decline":
                message = await _decline_offer(
                    core, chat_id, user_id, str(data.get("offer_id") or "")
                )
            elif action == "bribe_report":
                message = await _report_offer(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("offer_id") or ""),
                )
            elif action == "bribe_investigate":
                message = await _investigate_bribery(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("offer_id") or ""),
                    str(data.get("office_key") or ""),
                )
            elif action == "theft_investigate_v153":
                message = await _investigate_theft_v153(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("theft_id") or ""),
                    str(data.get("office_key") or ""),
                )
            elif action == "presidential_appoint":
                message = await _presidential_appoint(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("office_key") or ""),
                    int(data.get("target_user_id") or 0),
                    int(data.get("seat_no") or 1),
                    str(data.get("reason") or ""),
                )
            elif action == "start_any_election":
                message = await _universal_start_election(
                    core,
                    bot,
                    chat_id,
                    user_id,
                    str(data.get("office_key") or ""),
                )
            else:
                raise ValueError("Неизвестное действие Reality 153.")
            return core.web.json_response({"ok": True, "message": message})
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    original_start = core.start_webapp_server

    async def start_with_shadow(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены ассеты теневых выборов Reality 153")
        original_runner = core.web.AppRunner

        async def asset(request: Any):
            name = str(request.match_info.get("name") or "")
            path = ASSET_JS if name == ASSET_JS.name else ASSET_CSS if name == ASSET_CSS.name else None
            if path is None:
                raise core.web.HTTPNotFound()
            return core.web.FileResponse(
                path,
                headers={"Cache-Control": "no-store", "X-Government-Election-Shadow": "153"},
            )

        def runner_with_shadow(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            if ("GET", "/government-v153/{name}") not in keys:
                app.router.add_get("/government-v153/{name}", asset)
            if ("POST", "/government-v153/api/action") not in keys:
                app.router.add_post("/government-v153/api/action", action_api)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_shadow
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_shadow
