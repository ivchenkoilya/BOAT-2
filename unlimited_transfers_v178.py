from __future__ import annotations

from typing import Any

import finance_system_v112 as finance
import finance_transfer_limit_v133 as finance_transfer
import government_treasury_contributions_v150 as contributions


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


def install_unlimited_transfers_v178(core: Any) -> None:
    if getattr(core, "_unlimited_transfers_v178_installed", False):
        return
    core._unlimited_transfers_v178_installed = True
    core.FINANCE_SYSTEM_VERSION = VERSION

    # Активный обработчик Reality 133 и старый резервный обработчик читают эти
    # значения во время запроса. Дневной предел больше не может быть достигнут.
    finance_transfer.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL
    finance.TRANSFER_DAILY_LIMIT = UNLIMITED_SENTINEL

    # Государственный вклад не имеет фиксированного верхнего предела. Реальным
    # пределом остаётся только обычный баланс пользователя и диапазон SQLite.
    contributions.MAX_CONTRIBUTION = UNLIMITED_SENTINEL

    @core.web.middleware
    async def unlimited_transfers_assets(request: Any, handler: Any):
        if (
            request.method.upper() == "GET"
            and str(request.path or "") == "/government-v150/treasury-contributions-v150.js"
        ):
            source = contributions.ASSET_JS.read_text(encoding="utf-8")
            return core.web.Response(
                text=_unlimited_contribution_script(source),
                content_type="application/javascript",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Unlimited-Transfers": "178",
                },
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_with_unlimited_transfers(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, unlimited_transfers_assets)
        return application

    core.web.Application = application_with_unlimited_transfers
