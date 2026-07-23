from __future__ import annotations

import secrets
from typing import Any

import finance_system_v112 as finance
import finance_transfer_limit_v133 as finance_transfer
import government_reality_v177_funds as fund_bridge
import government_treasury_contributions_v150 as contributions
import government_v127 as gov
from government_reality_v177_common import LEGACY_TO_STRUCTURE


VERSION = "Reality 178 · Безлимитные переводы"
# Совместимость со старыми обработчиками: их проверка остаётся безопасной,
# но предел выше максимально возможного значения SQLite INTEGER.
UNLIMITED_SENTINEL = 9_223_372_036_854_775_807


def _unlimited_contribution_script(source: str) -> str:
    """Remove the fixed one-million cap from the government contribution client."""
    source = source.replace(
        'max="${Number(data.max_amount)||1000000}"',
        'max="${Math.max(Number(data.min_amount)||100,Number(data.available_balance)||0)}"',
    )
    source = source.replace(
        "if(!Number.isFinite(amount)||amount<100||amount>1000000){",
        "if(!Number.isFinite(amount)||amount<100){",
    )
    source = source.replace(
        "toast('Размер вклада должен быть от 100 до 1 000 000 влияния.','error');",
        "toast('Минимальный вклад — 100 влияния. Максимум ограничен только твоим балансом.','error');",
    )
    return source


async def _unlimited_contribution_api(core: Any, request: Any):
    """Final server handler: no fixed cap, only the player's real balance."""
    try:
        user, chat_id, data = await gov._auth(core, request)
        user_id = int(user.id)
        amount = int(data.get("amount") or 0)
        fund_key = str(data.get("fund_key") or "general")
        note = str(data.get("note") or "").strip()

        if amount < contributions.MIN_CONTRIBUTION:
            raise ValueError(
                f"Минимальный вклад — {gov._fmt(contributions.MIN_CONTRIBUTION)} влияния."
            )
        if amount > UNLIMITED_SENTINEL:
            raise ValueError("Сумма слишком большая для хранения в базе данных.")
        if fund_key not in contributions.FUND_SPECS:
            raise ValueError("Выбран неизвестный государственный фонд.")
        if len(note) > 200:
            raise ValueError("Комментарий к вкладу не может быть длиннее 200 символов.")

        structure_key = LEGACY_TO_STRUCTURE.get(fund_key)
        if not structure_key:
            raise ValueError("Для выбранного фонда не настроен единый государственный баланс.")

        await contributions._ensure_schema(core)
        await fund_bridge.ensure_schema(core)
        await gov._ensure_state(core, int(chat_id))

        conn = core.db._require_connection()
        now = gov._now()
        contribution_id = secrets.token_urlsafe(12)
        title = str(contributions.FUND_SPECS[fund_key]["title"])

        async with core.db.lock:
            cursor = await conn.execute(
                """
                UPDATE players SET points=points-?,updated_at=?
                WHERE chat_id=? AND user_id=? AND points>=?
                """,
                (amount, now, int(chat_id), user_id, amount),
            )
            if int(cursor.rowcount or 0) <= 0:
                await conn.rollback()
                cursor = await conn.execute(
                    "SELECT points FROM players WHERE chat_id=? AND user_id=?",
                    (int(chat_id), user_id),
                )
                row = await cursor.fetchone()
                balance = int(row["points"] if row else 0)
                raise ValueError(
                    f"Недостаточно влияния. Твой баланс: {gov._fmt(balance)}."
                )

            # Reality 177 uses structure funds as the only source of truth. The money is
            # credited there directly, so it is neither duplicated in free treasury nor
            # passed through the legacy one-million-limited balance.
            await fund_bridge.credit_fund_locked(
                core, int(chat_id), str(structure_key), int(amount)
            )
            await conn.execute(
                """
                INSERT INTO government_contributions_v150(
                    contribution_id,chat_id,user_id,amount,fund_key,note,created_at
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    contribution_id,
                    int(chat_id),
                    user_id,
                    amount,
                    fund_key,
                    note,
                    now,
                ),
            )
            await conn.execute(
                "INSERT INTO score_log(chat_id,user_id,delta,reason,created_at) VALUES(?,?,?,?,?)",
                (
                    int(chat_id),
                    user_id,
                    -amount,
                    f"government_contribution_{fund_key}_v178",
                    now,
                ),
            )
            reason = f"Добровольный вклад: {title}"
            if note:
                reason = f"{reason} — {note}"
            await gov._treasury_log(
                core,
                int(chat_id),
                amount,
                reason,
                "voluntary_contribution_v178",
                contribution_id,
                user_id,
            )
            await conn.commit()

        return core.web.json_response(
            {
                "ok": True,
                "message": (
                    f"Вклад {gov._fmt(amount)} влияния зачислен в «{title}». "
                    "Фиксированного верхнего лимита нет."
                ),
            }
        )
    except PermissionError as exc:
        return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
    except Exception as exc:
        return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)


def install_unlimited_transfers_v178(core: Any) -> None:
    if getattr(core, "_unlimited_transfers_v178_installed", False):
        return
    core._unlimited_transfers_v178_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    # Активный обработчик Reality 133 и старый резервный обработчик читают эти
    # значения во время запроса. Дневной предел больше не может быть достигнут.
    finance_transfer.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL
    finance.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL

    # Оставлено для совместимости со старым состоянием API. Финальный POST ниже
    # больше не полагается на эту константу и проверяет только реальный баланс.
    contributions.MAX_CONTRIBUTION = UNLIMITED_SENTINEL

    @core.web.middleware
    async def unlimited_transfers_assets(request: Any, handler: Any):
        path = str(request.path or "")
        method = request.method.upper()

        if method == "POST" and path == "/government-v150/api/contribute":
            return await _unlimited_contribution_api(core, request)

        if method == "GET" and path == "/government-v150/treasury-contributions-v150.js":
            source = contributions.ASSET_JS.read_text(encoding="utf-8")
            return core.web.Response(
                text=_unlimited_contribution_script(source),
                content_type="application/javascript",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Unlimited-Transfers": "178-server-fix",
                },
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_unlimited_transfers(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, unlimited_transfers_assets)
        return application

    core.web.Application = application_with_unlimited_transfers
