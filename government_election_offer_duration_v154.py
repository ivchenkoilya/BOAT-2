from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import government_election_shadow_v153 as shadow
import government_mandate_luxury_v147 as luxury
import government_v127 as gov


VERSION = "Reality 154 · Предложения до конца выборов"
APP_DIR = Path(__file__).resolve().parent / "governmentapp_v127"
ASSET_JS = APP_DIR / "election-offer-duration-v154.js"
# Базовый Reality 153 ограничивает срок через min(now + OFFER_LIFETIME, voting_ends_at).
# Большое значение гарантирует, что фактическим сроком всегда станет конец голосования.
UNTIL_ELECTION_END = 365 * 24 * 60 * 60


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


def _inject_asset(previous_inject: Callable[[str], str], source: str) -> str:
    source = previous_inject(source)
    if "election-offer-duration-v154.js" not in source:
        source = source.replace(
            "</body>",
            '  <script src="/government-v154/election-offer-duration-v154.js?v=154"></script>\n</body>',
        )
    return source


async def _extend_pending_offers(core: Any) -> None:
    """Extend all still-pending offers to their election voting deadline."""
    await shadow._ensure_schema(core)
    conn = core.db._require_connection()
    await conn.execute(
        """
        UPDATE government_vote_bribes_v153
        SET expires_at=(
            SELECT e.voting_ends_at
            FROM government_elections_v127 e
            WHERE e.election_id=government_vote_bribes_v153.election_id
        )
        WHERE status='pending'
          AND EXISTS(
            SELECT 1 FROM government_elections_v127 e
            WHERE e.election_id=government_vote_bribes_v153.election_id
              AND e.phase='voting'
              AND e.voting_ends_at>government_vote_bribes_v153.expires_at
          )
        """
    )
    await conn.commit()


def install_government_election_offer_duration_v154(core: Any) -> None:
    if getattr(core, "_government_election_offer_duration_v154_installed", False):
        return
    core._government_election_offer_duration_v154_installed = True
    core.GOVERNMENT_VERSION = VERSION

    shadow.OFFER_LIFETIME = UNTIL_ELECTION_END

    async def send_offer_until_election_end(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        target_id: int,
        amount: int,
        office_title: str,
    ) -> None:
        try:
            link = gov._government_link(core_arg, int(chat_id))
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
                "Личность кандидата скрыта. Предложение действует "
                "<b>до завершения этих выборов</b>.",
                reply_markup=markup,
            )
        except Exception:
            pass

    shadow._send_secret_offer_notice = send_offer_until_election_end

    previous_create = shadow._create_bribe_offer

    async def create_offer_until_election_end(
        core_arg: Any,
        bot: Any,
        chat_id: int,
        buyer_id: int,
        election_id: str,
        target_id: int,
        amount: int,
    ) -> str:
        await previous_create(
            core_arg,
            bot,
            chat_id,
            buyer_id,
            election_id,
            target_id,
            amount,
        )
        return "Тайное предложение отправлено и действует до завершения выборов."

    shadow._create_bribe_offer = create_offer_until_election_end

    original_connect = core.Database.connect

    async def connect_with_extended_offers(self: Any) -> None:
        await original_connect(self)
        await _extend_pending_offers(core)

    core.Database.connect = connect_with_extended_offers

    previous_inject = luxury._inject_assets

    def inject_with_duration(source: str) -> str:
        return _inject_asset(previous_inject, source)

    luxury._inject_assets = inject_with_duration

    original_start = core.start_webapp_server

    async def start_with_offer_duration(bot: Any):
        if not ASSET_JS.is_file():
            raise RuntimeError("Не найден интерфейс срока тайных предложений Reality 154")
        original_runner = core.web.AppRunner

        async def asset(_: Any):
            return core.web.FileResponse(
                ASSET_JS,
                headers={
                    "Cache-Control": "no-store",
                    "X-Government-Election-Offer-Duration": "154",
                },
            )

        def runner_with_duration(app: Any, *args: Any, **kwargs: Any):
            keys = _route_keys(app)
            path = "/government-v154/election-offer-duration-v154.js"
            if ("GET", path) not in keys:
                app.router.add_get(path, asset)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_duration
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_offer_duration
