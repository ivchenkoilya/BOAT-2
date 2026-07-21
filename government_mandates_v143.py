from __future__ import annotations

import base64
import html
import secrets
import time
from pathlib import Path
from typing import Any

from aiogram.filters import Command
from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Message

import government_v127 as gov


VERSION = "Reality 143 · Мандаты и основной свод законов"
ASSET_JS = Path(__file__).resolve().parent / "governmentapp_v127" / "mandates-v143.js"
ASSET_CSS = Path(__file__).resolve().parent / "governmentapp_v127" / "mandates-v143.css"
MAX_SIGNATURE_LENGTH = 260_000

MANDATE_POWERS: dict[str, list[str]] = {
    "president": [
        "вносить обычные, налоговые и бюджетные законопроекты",
        "предлагать министра финансов и главу Надзора",
        "подписывать принятые законы или накладывать президентское вето",
        "управлять налоговым циклом государства",
        "представлять исполнительную власть Государства реальности",
    ],
    "chair": [
        "вносить государственные законопроекты",
        "представлять и организовывать работу Государственной Думы",
        "участвовать в депутатском голосовании",
        "запускать процедуру преодоления президентского вето",
    ],
    "deputy": [
        "вносить обычные, налоговые, бюджетные и санкционные предложения",
        "голосовать за принятие или отклонение законопроектов",
        "участвовать в формировании решений Государственной Думы",
        "осуществлять парламентский контроль в пределах системы",
    ],
    "finance": [
        "вносить обычные, налоговые и бюджетные законопроекты",
        "управлять налоговым циклом совместно с президентом",
        "участвовать в подготовке решений по казне и бюджету",
        "представлять финансовую власть Государства реальности",
    ],
    "oversight": [
        "вносить обычные и санкционные предложения",
        "предлагать меры государственного надзора",
        "участвовать в проверке нарушений и злоупотреблений",
        "представлять надзорную власть Государства реальности",
    ],
}

FOUNDATION_LAWS: list[dict[str, Any]] = [
    {
        "number": 1,
        "title": "О честной государственной власти",
        "summary": "Законность выборов, назначений, мандатов и государственных полномочий.",
        "text": (
            "Государственные полномочия могут быть получены только через установленные выборы, "
            "законное назначение или иной предусмотренный системой порядок.\n\n"
            "Все полномочия действуют исключительно в рамках занимаемой должности и прекращаются "
            "после окончания срока, отставки, импичмента, досрочного снятия или аннулирования мандата.\n\n"
            "Передача, подделка и незаконное использование мандата запрещены. Подлинность полномочий "
            "подтверждается государственным реестром."
        ),
    },
    {
        "number": 2,
        "title": "О свободных выборах",
        "summary": "Один участник — один голос, без подкупа, угроз и вмешательства.",
        "text": (
            "Каждый допущенный участник вправе участвовать в выборах и отдавать один голос за выбранного кандидата.\n\n"
            "Запрещаются покупка голосов, угрозы избирателям, саботаж для устранения кандидатов, выдача себя "
            "за другого участника и вмешательство в подсчёт голосов.\n\n"
            "Победителем признаётся кандидат, набравший наибольшее количество подтверждённых системой голосов."
        ),
    },
    {
        "number": 3,
        "title": "О государственных должностях",
        "summary": "Перечень должностей, сроки и несовместимость полномочий.",
        "text": (
            "Государственными должностями признаются Президент реальности, Председатель Государственной Думы, "
            "депутат Государственной Думы, министр финансов и глава Надзора.\n\n"
            "Каждая должность имеет установленный срок и собственный перечень полномочий. Один участник не может "
            "занимать несколько несовместимых должностей, кроме прямо предусмотренных системой случаев."
        ),
    },
    {
        "number": 4,
        "title": "О государственном мандате",
        "summary": "Номер, Telegram ID, подпись, срок, статус и проверка подлинности.",
        "text": (
            "После избрания или назначения должностное лицо вправе оформить персональный государственный мандат.\n\n"
            "Мандат содержит уникальный номер, Telegram ID владельца, должность, даты начала и окончания полномочий, "
            "электронную подпись, код проверки и перечень разрешённых действий.\n\n"
            "Неподписанный, просроченный или аннулированный мандат не подтверждает действующие полномочия."
        ),
    },
    {
        "number": 5,
        "title": "О Государственной Думе",
        "summary": "Законодательная власть, депутатское голосование и парламентский контроль.",
        "text": (
            "Государственная Дума является законодательным органом Государства реальности.\n\n"
            "Депутаты вправе предлагать законопроекты, голосовать, вносить налоговые, бюджетные и санкционные "
            "инициативы, а также контролировать действия исполнительной власти.\n\n"
            "Каждый депутат имеет один голос. Решения принимаются большинством участвующих депутатов при наличии кворума."
        ),
    },
    {
        "number": 6,
        "title": "О Президенте реальности",
        "summary": "Полномочия главы государства, назначения, подпись законов и вето.",
        "text": (
            "Президент является главой государства и представляет исполнительную власть.\n\n"
            "Президент вправе предлагать законопроекты, налоговые и бюджетные инициативы, кандидатов на должности "
            "министра финансов и главы Надзора, подписывать законы и накладывать вето.\n\n"
            "Президент не вправе единолично присваивать средства казны или отменять результаты законных выборов."
        ),
    },
    {
        "number": 7,
        "title": "О государственной казне и бюджете",
        "summary": "Учёт доходов, расходов и обязательная прозрачность каждой операции.",
        "text": (
            "Государственные доходы, налоги, штрафы и иные поступления зачисляются в казну.\n\n"
            "Каждая операция должна содержать сумму, основание, Telegram ID инициатора, дату и связь с законом или "
            "государственным решением. Расходование средств без законного основания запрещено.\n\n"
            "История операций казны должна быть доступна для государственной проверки."
        ),
    },
    {
        "number": 8,
        "title": "О налогах и защите граждан",
        "summary": "Налоги вводятся только законом с открытыми ставками и пределами.",
        "text": (
            "Налоги вводятся только на основании принятого налогового закона.\n\n"
            "Закон обязан указывать ставки, категории участников, пороги влияния, максимальный размер налога и дату "
            "вступления в силу.\n\n"
            "Налог не может превышать установленный системой предел, кроме прямо предусмотренного чрезвычайного режима."
        ),
    },
    {
        "number": 9,
        "title": "О санкциях и справедливом наказании",
        "summary": "Причина, срок, инициатор и автоматическое прекращение санкций.",
        "text": (
            "Санкции применяются только при наличии указанной причины, срока действия и инициатора.\n\n"
            "Участник вправе знать обвинение, автора предложения, срок и перечень временно ограниченных возможностей.\n\n"
            "После окончания установленного срока санкция автоматически прекращает действие."
        ),
    },
    {
        "number": 10,
        "title": "О коррупции и злоупотреблении полномочиями",
        "summary": "Запрет личной выгоды, подделок, покупки голосов и политической мести.",
        "text": (
            "Должностным лицам запрещается использовать власть ради личной выгоды, мести, давления на соперников или "
            "незаконного обогащения.\n\n"
            "Коррупцией признаются присвоение казны, покупка голосов, незаконная выдача должностей, сокрытие операций, "
            "политическое использование санкций и подделка мандатов или результатов голосования.\n\n"
            "При подтверждённом нарушении полномочия могут быть приостановлены или прекращены в установленном порядке."
        ),
    },
]


def _now() -> int:
    return int(time.time())


def _status_title(status: str) -> str:
    return {
        "available": "доступен к оформлению",
        "active": "действующий",
        "expired": "срок завершён",
        "annulled": "аннулирован",
    }.get(status, status)


async def _ensure_schema(core: Any) -> None:
    if getattr(core.db, "_government_mandates_v143_schema", False):
        return
    conn = core.db._require_connection()
    async with core.db.lock:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS government_mandates_v143(
                mandate_no INTEGER PRIMARY KEY AUTOINCREMENT,
                mandate_id TEXT NOT NULL UNIQUE,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                office_key TEXT NOT NULL,
                seat_no INTEGER NOT NULL,
                office_starts_at INTEGER NOT NULL,
                office_ends_at INTEGER NOT NULL,
                signature_data TEXT NOT NULL,
                verification_code TEXT NOT NULL UNIQUE,
                issued_at INTEGER NOT NULL,
                signed_at INTEGER NOT NULL,
                revoked_at INTEGER NOT NULL DEFAULT 0,
                UNIQUE(chat_id,user_id,office_key,seat_no,office_starts_at)
            );
            CREATE INDEX IF NOT EXISTS idx_mandates_v143_owner
            ON government_mandates_v143(chat_id,user_id,issued_at DESC);

            CREATE TABLE IF NOT EXISTS government_law_meta_v143(
                law_id TEXT PRIMARY KEY,
                signed_by INTEGER NOT NULL DEFAULT 0,
                recorded_at INTEGER NOT NULL
            );
            """
        )
        await conn.commit()
    core.db._government_mandates_v143_schema = True


def _office_spec(office_key: str) -> dict[str, Any]:
    return gov.OFFICES.get(office_key, {"emoji": "🏛", "title": office_key, "seats": 1})


def _base_mandate_dict(row: Any, status: str) -> dict[str, Any]:
    office_key = str(row["office_key"])
    spec = _office_spec(office_key)
    return {
        "mandate_no": int(row["mandate_no"]),
        "mandate_id": str(row["mandate_id"]),
        "verification_code": str(row["verification_code"]),
        "user_id": int(row["user_id"]),
        "office_key": office_key,
        "office_title": str(spec["title"]),
        "emoji": str(spec["emoji"]),
        "seat_no": int(row["seat_no"]),
        "starts_at": int(row["office_starts_at"]),
        "ends_at": int(row["office_ends_at"]),
        "issued_at": int(row["issued_at"]),
        "signed_at": int(row["signed_at"]),
        "signature_data": str(row["signature_data"] or ""),
        "status": status,
        "status_title": _status_title(status),
        "powers": list(MANDATE_POWERS.get(office_key, [])),
        "can_claim": False,
    }


async def _current_mandates(core: Any, chat_id: int, user_id: int) -> list[dict[str, Any]]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        """
        SELECT * FROM government_offices_v127
        WHERE chat_id=? AND user_id=? AND ends_at>?
        ORDER BY CASE office_key WHEN 'president' THEN 0 WHEN 'chair' THEN 1
          WHEN 'deputy' THEN 2 WHEN 'finance' THEN 3 ELSE 4 END,seat_no
        """,
        (int(chat_id), int(user_id), now),
    )
    offices = list(await cursor.fetchall())
    cursor = await conn.execute(
        """
        SELECT * FROM government_mandates_v143
        WHERE chat_id=? AND user_id=?
        ORDER BY issued_at DESC,mandate_no DESC
        """,
        (int(chat_id), int(user_id)),
    )
    rows = list(await cursor.fetchall())
    by_period = {
        (str(row["office_key"]), int(row["seat_no"]), int(row["office_starts_at"])): row
        for row in rows
    }
    active_keys: set[tuple[str, int, int]] = set()
    result: list[dict[str, Any]] = []
    for office in offices:
        key = (str(office["office_key"]), int(office["seat_no"]), int(office["starts_at"]))
        active_keys.add(key)
        mandate = by_period.get(key)
        if mandate is not None:
            result.append(_base_mandate_dict(mandate, "active"))
            continue
        spec = _office_spec(str(office["office_key"]))
        result.append(
            {
                "mandate_no": 0,
                "mandate_id": "",
                "verification_code": "",
                "user_id": int(user_id),
                "office_key": str(office["office_key"]),
                "office_title": str(spec["title"]),
                "emoji": str(spec["emoji"]),
                "seat_no": int(office["seat_no"]),
                "starts_at": int(office["starts_at"]),
                "ends_at": int(office["ends_at"]),
                "issued_at": 0,
                "signed_at": 0,
                "signature_data": "",
                "status": "available",
                "status_title": _status_title("available"),
                "powers": list(MANDATE_POWERS.get(str(office["office_key"]), [])),
                "can_claim": True,
            }
        )
    for row in rows:
        key = (str(row["office_key"]), int(row["seat_no"]), int(row["office_starts_at"]))
        if key in active_keys:
            continue
        status = "annulled" if int(row["revoked_at"] or 0) > 0 or int(row["office_ends_at"]) > now else "expired"
        result.append(_base_mandate_dict(row, status))
    return result


async def _enrich_laws(core: Any, chat_id: int, laws: list[dict[str, Any]]) -> None:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    for law in laws:
        law_id = str(law.get("law_id") or "")
        bill_id = str(law.get("bill_id") or "")
        cursor = await conn.execute(
            """
            SELECT b.author_id,m.signed_by,
                   COALESCE(SUM(CASE WHEN v.vote='yes' THEN 1 ELSE 0 END),0) yes_votes,
                   COALESCE(SUM(CASE WHEN v.vote='no' THEN 1 ELSE 0 END),0) no_votes,
                   COALESCE(SUM(CASE WHEN v.vote='abstain' THEN 1 ELSE 0 END),0) abstain_votes
            FROM government_bills_v127 b
            LEFT JOIN government_bill_votes_v127 v ON v.bill_id=b.bill_id
            LEFT JOIN government_law_meta_v143 m ON m.law_id=?
            WHERE b.bill_id=? AND b.chat_id=?
            GROUP BY b.author_id,m.signed_by
            """,
            (law_id, bill_id, int(chat_id)),
        )
        row = await cursor.fetchone()
        law["author_id"] = int(row["author_id"] if row else 0)
        law["signed_by"] = int(row["signed_by"] if row else 0)
        law["votes"] = {
            "yes": int(row["yes_votes"] if row else 0),
            "no": int(row["no_votes"] if row else 0),
            "abstain": int(row["abstain_votes"] if row else 0),
        }


async def _sign_mandate(
    core: Any,
    chat_id: int,
    user_id: int,
    office_key: str,
    seat_no: int,
    signature_data: str,
) -> dict[str, Any]:
    await _ensure_schema(core)
    office_key = str(office_key or "").strip().casefold()
    if office_key not in MANDATE_POWERS:
        raise ValueError("Для этой должности мандат не предусмотрен.")
    seat_no = max(1, int(seat_no or 1))
    signature_data = str(signature_data or "").strip()
    if not signature_data.startswith("data:image/png;base64,"):
        raise ValueError("Поставь подпись в специальном поле.")
    if len(signature_data) > MAX_SIGNATURE_LENGTH:
        raise ValueError("Подпись получилась слишком большой. Очисти поле и подпиши короче.")
    try:
        raw = base64.b64decode(signature_data.split(",", 1)[1], validate=True)
    except Exception as exc:
        raise ValueError("Подпись повреждена. Поставь её ещё раз.") from exc
    if len(raw) < 120:
        raise ValueError("Подпись слишком короткая.")

    conn = core.db._require_connection()
    now = _now()
    cursor = await conn.execute(
        """
        SELECT * FROM government_offices_v127
        WHERE chat_id=? AND user_id=? AND office_key=? AND seat_no=? AND ends_at>?
        LIMIT 1
        """,
        (int(chat_id), int(user_id), office_key, seat_no, now),
    )
    office = await cursor.fetchone()
    if office is None:
        raise PermissionError("Эта государственная должность больше не принадлежит тебе.")
    cursor = await conn.execute(
        """
        SELECT * FROM government_mandates_v143
        WHERE chat_id=? AND user_id=? AND office_key=? AND seat_no=? AND office_starts_at=?
        LIMIT 1
        """,
        (int(chat_id), int(user_id), office_key, seat_no, int(office["starts_at"])),
    )
    existing = await cursor.fetchone()
    if existing is not None:
        raise ValueError("Мандат на этот срок полномочий уже оформлен.")

    mandate_id = secrets.token_urlsafe(12)
    pending_code = f"PENDING-{secrets.token_hex(8).upper()}"
    async with core.db.lock:
        cursor = await conn.execute(
            """
            INSERT INTO government_mandates_v143(
                mandate_id,chat_id,user_id,office_key,seat_no,office_starts_at,office_ends_at,
                signature_data,verification_code,issued_at,signed_at,revoked_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,0)
            """,
            (
                mandate_id,
                int(chat_id),
                int(user_id),
                office_key,
                seat_no,
                int(office["starts_at"]),
                int(office["ends_at"]),
                signature_data,
                pending_code,
                now,
                now,
            ),
        )
        mandate_no = int(cursor.lastrowid)
        verification_code = f"GOV-{mandate_no:06d}-{secrets.token_hex(2).upper()}"
        await conn.execute(
            "UPDATE government_mandates_v143 SET verification_code=? WHERE mandate_no=?",
            (verification_code, mandate_no),
        )
        await conn.commit()
    cursor = await conn.execute(
        "SELECT * FROM government_mandates_v143 WHERE mandate_no=?",
        (mandate_no,),
    )
    row = await cursor.fetchone()
    return _base_mandate_dict(row, "active")


async def _resolve_target(core: Any, message: Message) -> int:
    if message.reply_to_message and message.reply_to_message.from_user:
        return int(message.reply_to_message.from_user.id)
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        return int(message.from_user.id)
    query = parts[1].strip()
    if query.lstrip("@").isdigit():
        return int(query.lstrip("@"))
    username = query.lstrip("@").casefold()
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT user_id FROM players
        WHERE chat_id=? AND (
            LOWER(COALESCE(username,''))=? OR LOWER(COALESCE(full_name,''))=?
            OR LOWER(COALESCE(full_name,'')) LIKE ?
        )
        ORDER BY CASE WHEN LOWER(COALESCE(username,''))=? THEN 0 ELSE 1 END,message_count DESC
        LIMIT 1
        """,
        (int(message.chat.id), username, query.casefold(), f"%{query.casefold()}%", username),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ValueError("Участник не найден в этой беседе.")
    return int(row["user_id"])


async def _latest_mandate(core: Any, chat_id: int, user_id: int) -> tuple[Any | None, str]:
    await _ensure_schema(core)
    conn = core.db._require_connection()
    cursor = await conn.execute(
        """
        SELECT * FROM government_mandates_v143
        WHERE chat_id=? AND user_id=?
        ORDER BY issued_at DESC,mandate_no DESC LIMIT 1
        """,
        (int(chat_id), int(user_id)),
    )
    row = await cursor.fetchone()
    if row is None:
        return None, ""
    now = _now()
    cursor = await conn.execute(
        """
        SELECT 1 FROM government_offices_v127
        WHERE chat_id=? AND user_id=? AND office_key=? AND seat_no=?
          AND starts_at=? AND ends_at>?
        LIMIT 1
        """,
        (
            int(chat_id),
            int(user_id),
            str(row["office_key"]),
            int(row["seat_no"]),
            int(row["office_starts_at"]),
            now,
        ),
    )
    active = await cursor.fetchone() is not None and int(row["revoked_at"] or 0) <= 0
    if active:
        return row, "active"
    if int(row["revoked_at"] or 0) > 0 or int(row["office_ends_at"]) > now:
        return row, "annulled"
    return row, "expired"


def _mandate_link(core: Any, chat_id: int) -> str:
    return gov._government_link(core, chat_id)


def install_government_mandates_v143(core: Any) -> None:
    if getattr(core, "_government_mandates_v143_installed", False):
        return
    core._government_mandates_v143_installed = True
    core.GOVERNMENT_VERSION = VERSION

    original_state = gov._state

    async def state_with_mandates(core_arg: Any, bot: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        payload = await original_state(core_arg, bot, chat_id, user_id)
        payload["version"] = VERSION
        payload["foundation_laws"] = [dict(item, law_type="foundation", active=True) for item in FOUNDATION_LAWS]
        payload["mandates"] = await _current_mandates(core_arg, chat_id, user_id)
        await _enrich_laws(core_arg, chat_id, payload.get("laws", []))
        return payload

    gov._state = state_with_mandates

    original_enact = gov._enact_bill

    async def enact_with_signature(core_arg: Any, bot: Any, bill: Any, actor_id: int) -> None:
        await original_enact(core_arg, bot, bill, actor_id)
        try:
            await _ensure_schema(core_arg)
            conn = core_arg.db._require_connection()
            cursor = await conn.execute(
                "SELECT law_id FROM government_laws_v127 WHERE bill_id=? ORDER BY enacted_at DESC LIMIT 1",
                (str(bill["bill_id"]),),
            )
            law = await cursor.fetchone()
            if law is not None:
                await conn.execute(
                    """
                    INSERT INTO government_law_meta_v143(law_id,signed_by,recorded_at)
                    VALUES(?,?,?) ON CONFLICT(law_id) DO UPDATE SET
                    signed_by=excluded.signed_by,recorded_at=excluded.recorded_at
                    """,
                    (str(law["law_id"]), int(actor_id), _now()),
                )
                await conn.commit()
        except Exception:
            core_arg.logging.exception("Не удалось записать подпись закона Reality 143")

    gov._enact_bill = enact_with_signature

    original_start = core.start_webapp_server

    async def start_with_mandates(bot: Any):
        if not ASSET_JS.is_file() or not ASSET_CSS.is_file():
            raise RuntimeError("Не найдены файлы интерфейса мандатов Reality 143")
        original_runner = core.web.AppRunner

        def index_html() -> str:
            source = (gov.APP_DIR / "index.html").read_text(encoding="utf-8")
            if "mandates-v143.css" not in source:
                source = source.replace(
                    "</head>",
                    '  <link rel="stylesheet" href="/government-v127/mandates-v143.css?v=143">\n</head>',
                )
            if "mandates-v143.js" not in source:
                source = source.replace(
                    "</body>",
                    '  <script src="/government-v127/mandates-v143.js?v=143"></script>\n</body>',
                )
            return source

        @core.web.middleware
        async def mandates_middleware(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/") or "/"
            if request.method.upper() == "GET":
                start_param = str(
                    request.query.get("tgWebAppStartParam")
                    or request.query.get("startapp")
                    or ""
                )
                if path == "/government-v127" or start_param.startswith(gov.GOV_PREFIX):
                    return core.web.Response(
                        text=index_html(),
                        content_type="text/html",
                        charset="utf-8",
                        headers={
                            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                            "Pragma": "no-cache",
                            "Expires": "0",
                            "X-Government": "reality-143",
                        },
                    )
                if path == "/government-v127/mandates-v143.js":
                    return core.web.FileResponse(
                        ASSET_JS,
                        headers={"Cache-Control": "no-store", "X-Government": "reality-143"},
                    )
                if path == "/government-v127/mandates-v143.css":
                    return core.web.FileResponse(
                        ASSET_CSS,
                        headers={"Cache-Control": "no-store", "X-Government": "reality-143"},
                    )
            if request.method.upper() == "POST" and path == "/government-v143/api/action":
                try:
                    user, chat_id, data = await gov._auth(core, request)
                    if str(data.get("action") or "") != "mandate_sign":
                        raise ValueError("Неизвестное действие с мандатом.")
                    mandate = await _sign_mandate(
                        core,
                        chat_id,
                        int(user.id),
                        str(data.get("office_key") or ""),
                        int(data.get("seat_no") or 1),
                        str(data.get("signature_data") or ""),
                    )
                    spec = _office_spec(str(mandate["office_key"]))
                    await gov._publish(
                        request.app["bot"],
                        chat_id,
                        "🏛 <b>ГОСУДАРСТВЕННЫЙ МАНДАТ ОФОРМЛЕН</b>\n\n"
                        f"Владелец: Telegram ID <code>{int(user.id)}</code>\n"
                        f"Должность: {spec['emoji']} <b>{html.escape(str(spec['title']))}</b>\n"
                        f"Номер: <b>№{int(mandate['mandate_no']):06d}</b>\n"
                        f"Код проверки: <code>{html.escape(str(mandate['verification_code']))}</code>\n\n"
                        "🔏 Электронная подпись принята. Полномочия подтверждены государственным реестром.",
                    )
                    return core.web.json_response(
                        {
                            "ok": True,
                            "message": f"Мандат №{int(mandate['mandate_no']):06d} подписан и выдан.",
                            "mandate": mandate,
                        }
                    )
                except PermissionError as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
                except Exception as exc:
                    return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)
            return await handler(request)

        def runner_with_mandates(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, mandates_middleware)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_mandates
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_mandates

    original_commands = core.group_bot_commands

    def commands_with_mandate() -> list[BotCommand]:
        commands = list(original_commands())
        if not any(item.command == "mandate" for item in commands):
            commands.append(BotCommand(command="mandate", description="Предъявить государственный мандат"))
        return commands

    core.group_bot_commands = commands_with_mandate

    @core.router.message(Command("mandate", "мандат"))
    async def cmd_mandate_v143(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        try:
            target_id = await _resolve_target(core, message)
            row, status = await _latest_mandate(core, int(message.chat.id), target_id)
            if row is None:
                await message.answer(
                    f"🏛 У Telegram ID <code>{target_id}</code> нет оформленного государственного мандата."
                )
                return
            spec = _office_spec(str(row["office_key"]))
            powers = MANDATE_POWERS.get(str(row["office_key"]), [])
            status_line = {
                "active": "🟢 Действующий",
                "expired": "⚪ Срок полномочий завершён",
                "annulled": "🔴 Аннулирован",
            }.get(status, status)
            rights_text = "\n".join(f"— {html.escape(item)};" for item in powers)
            validity = (
                "Все перечисленные полномочия действуют в полном объёме."
                if status == "active"
                else "Перечисленные полномочия больше не действуют. Документ сохранён только в государственном архиве."
            )
            link = _mandate_link(core, int(message.chat.id))
            markup = None
            if link:
                markup = InlineKeyboardMarkup(
                    inline_keyboard=[[
                        InlineKeyboardButton(text="📜 Открыть государственный реестр", url=link)
                    ]]
                )
            await message.answer(
                f"🏛 <b>МАНДАТ ГОСУДАРСТВА №{int(row['mandate_no']):06d}</b>\n\n"
                f"<b>Владелец:</b> Telegram ID <code>{target_id}</code>\n"
                f"<b>Должность:</b> {spec['emoji']} {html.escape(str(spec['title']))}\n"
                f"<b>Срок:</b> {gov._date_text(int(row['office_starts_at']))} — "
                f"{gov._date_text(int(row['office_ends_at']))}\n"
                f"<b>Статус:</b> {status_line}\n"
                f"<b>Подпись:</b> 🔏 подтверждена\n"
                f"<b>Код проверки:</b> <code>{html.escape(str(row['verification_code']))}</code>\n\n"
                f"<b>Мандат предоставляет право:</b>\n{rights_text}\n\n"
                "⚖️ <b>Правовое основание</b>\n"
                "Закон Реальности №1 «О честной государственной власти». Настоящий мандат подтверждает, "
                "что полномочия получены через установленную системой процедуру и принадлежат только указанному Telegram ID.\n\n"
                f"{validity}\n\n"
                "🔏 <b>Подлинность подтверждена государственным реестром системы «Главный герой».</b>",
                reply_markup=markup,
            )
        except Exception as exc:
            await message.answer(f"⚠️ {html.escape(str(exc))}")

    handlers = core.router.message.handlers
    preferred = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") == "cmd_mandate_v143"
    ]
    handlers[:] = preferred + [handler for handler in handlers if handler not in preferred]
