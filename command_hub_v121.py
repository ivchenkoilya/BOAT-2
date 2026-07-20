from __future__ import annotations

import html
from typing import Any

from aiogram import F, Bot
from aiogram.filters import Command
from aiogram.types import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import game_center_v75 as game_center
import talent_system
from career_ui_v120 import career_text


VERSION = "Reality 121 · Центры команд"
PREFIX = "hub121"


VISIBLE_COMMANDS = (
    ("start", "Описание и запуск бота"),
    ("me", "Моя роль, баланс и карьера"),
    ("stats", "Подробная статистика"),
    ("top", "Карьерный рейтинг беседы"),
    ("influence", "Получить влияние и карьерный прогресс"),
    ("event", "Текущее событие беседы"),
    ("boss", "Битва с Центром Вселенной"),
    ("games", "Игры и развлечения"),
    ("talents", "Древо, билды и усиления"),
    ("finance", "Переводы, займы и долги"),
    ("power", "Власть, саботаж и конфликты"),
    ("roles", "Роли и карьерное влияние"),
    ("feedback", "Предложить улучшение"),
    ("help", "Все разделы и скрытые команды"),
)


def _commands() -> list[BotCommand]:
    return [BotCommand(command=command, description=description) for command, description in VISIBLE_COMMANDS]


def _row(*buttons: InlineKeyboardButton) -> list[InlineKeyboardButton]:
    return list(buttons)


def _callback(text: str, action: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=f"{PREFIX}:{action}")


def _game_link(core: Any, chat_id: int) -> str:
    return game_center._game_link(core, int(chat_id))


def _talent_link(core: Any, chat_id: int) -> str:
    if core.WEBAPP_SHORT_NAME and core.BOT_PUBLIC_USERNAME:
        return (
            f"https://t.me/{core.BOT_PUBLIC_USERNAME}/{core.WEBAPP_SHORT_NAME}"
            f"?startapp={talent_system.TALENT_PREFIX}{int(chat_id)}"
        )
    if core.WEBAPP_PUBLIC_URL:
        return f"{core.WEBAPP_PUBLIC_URL.rstrip('/')}/talents/?chat_id={int(chat_id)}"
    return ""


def games_markup(core: Any, chat_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    link = _game_link(core, chat_id)
    if link:
        rows.append(_row(InlineKeyboardButton(text="🎮 Открыть игровой центр", url=link)))
    rows.extend(
        [
            _row(_callback("🎲 Кубик", "games:dice"), _callback("🪙 Монетка", "games:coin")),
            _row(_callback("🔮 Шар судьбы", "games:fate"), _callback("🎰 Рулетка", "games:roulette")),
            _row(_callback("🎭 Типаж дня", "games:today"), _callback("🎯 Тайное задание", "games:secret")),
            _row(_callback("⚡ Действие", "games:action"), _callback("⚔️ Битва эго", "games:ego")),
            _row(_callback("✨ Аура", "games:aura"), _callback("🧠 Уровень ЧСВ", "games:chsv")),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def talents_markup(core: Any, chat_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    link = _talent_link(core, chat_id)
    if link:
        rows.append(_row(InlineKeyboardButton(text="🌳 Открыть древо развития", url=link)))
    rows.extend(
        [
            _row(_callback("💫 Мои усиления", "talents:buffs"), _callback("👥 Развитие беседы", "talents:chat")),
            _row(_callback("🧩 Где билды?", "talents:builds"), _callback("⚡ Активные способности", "talents:active")),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def power_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(_callback("🌟 Герой дня", "power:hero"), _callback("💣 Саботаж", "power:sabotage")),
            _row(_callback("🏛 Импичмент", "power:impeachment"), _callback("⚔️ Бунт", "power:rebellion")),
            _row(_callback("🎭 Способности ролей", "power:abilities")),
            _row(_callback("📜 Правила власти", "power:rules"), _callback("🔄 Обновить статус", "power:refresh")),
        ]
    )


def roles_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(_callback("⭐ Моя карьера", "roles:career"), _callback("🌌 Все роли", "roles:all")),
            _row(_callback("🏆 Карьерный топ", "roles:top"), _callback("🎭 Способности", "roles:abilities")),
        ]
    )


def wager_markup(game: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(
                _callback("100", f"wager:{game}:100"),
                _callback("1 000", f"wager:{game}:1000"),
            ),
            _row(
                _callback("10 000", f"wager:{game}:10000"),
                _callback("50 000", f"wager:{game}:50000"),
            ),
            _row(_callback("⬅️ Назад к играм", "games:menu")),
        ]
    )


def ego_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            _row(_callback("30", "ego:30"), _callback("100", "ego:100"), _callback("500", "ego:500")),
            _row(_callback("⬅️ Назад к играм", "games:menu")),
        ]
    )


async def _safe_edit(callback: CallbackQuery, text: str, markup: InlineKeyboardMarkup | None) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:
        await callback.message.answer(text, reply_markup=markup)


async def _send_article(core: Any, message: Message, article: Any) -> None:
    text, markup = core.article_text_and_markup(article)
    sent = await message.answer(text, reply_markup=markup)
    article_id = str(getattr(article, "id", ""))
    if article_id.startswith("sabotage:"):
        sabotage_id = article_id.split(":", 2)[1]
        await core.db.bind_sabotage_message(sabotage_id, message.chat.id, sent.message_id)
    elif article_id.startswith("impeachment:"):
        impeachment_id = article_id.split(":", 2)[1]
        await core.db.bind_impeachment_message(impeachment_id, message.chat.id, sent.message_id)


async def power_text(core: Any, chat_id: int) -> str:
    hero_line = "не выбран"
    hero_state = await core.db.get_hero_day_state(chat_id)
    if hero_state is not None:
        hero = await core.db.get_player(chat_id, int(hero_state["user_id"]))
        if hero is not None:
            hero_line = core.player_link(hero)

    sabotage_ids = list(await core.db.active_sabotage_usurper_ids(chat_id))
    sabotage_line = "нет активного саботажа"
    if sabotage_ids:
        players = []
        for user_id in sabotage_ids[:3]:
            player = await core.db.get_player(chat_id, int(user_id))
            if player is not None:
                players.append(core.player_link(player))
        if players:
            sabotage_line = ", ".join(players)

    return (
        "👑 <b>ВЛАСТЬ И КОНФЛИКТЫ</b>\n\n"
        f"🌟 Герой дня: {hero_line}\n"
        f"💣 Саботажный статус: {sabotage_line}\n\n"
        "Выборы, захват власти, импичмент, бунт и способности ролей "
        "теперь находятся в одном разделе."
    )


async def talents_buffs_text(core: Any, chat_id: int, user_id: int) -> str:
    player = await core.db.get_player(chat_id, user_id)
    if player is None:
        return "Сначала используй бота в этой беседе."
    profile = await talent_system.sync_profile(core.db, chat_id, user_id)
    buffs = await talent_system.buffs_for(core.db, chat_id, user_id)
    return (
        "💫 <b>МОИ УСИЛЕНИЯ ДРЕВА</b>\n\n"
        f"Участник: {core.player_link(player)}\n"
        f"Очки: <b>{profile['spent']} потрачено · {profile['available']} свободно</b>\n\n"
        f"⚔ Урон по боссу: <b>+{round(buffs['boss_damage'] * 100)}%</b>\n"
        f"📈 Получение влияния: <b>+{round(buffs['influence'] * 100)}%</b>\n"
        f"🛡 Снижение потерь: <b>{round(buffs['penalty_reduction'] * 100)}%</b>\n"
        f"🎁 Награды игр: <b>+{round(buffs['game_reward'] * 100)}%</b>"
    )


async def chat_buffs_text(core: Any, chat_id: int) -> str:
    conn = core.db._require_connection()
    cursor = await conn.execute(
        "SELECT p.user_id,p.full_name,COALESCE(t.spent_points,0) spent "
        "FROM players p LEFT JOIN talent_profiles t "
        "ON t.chat_id=p.chat_id AND t.user_id=p.user_id "
        "WHERE p.chat_id=? ORDER BY spent DESC,p.points DESC LIMIT 10",
        (chat_id,),
    )
    rows = list(await cursor.fetchall())
    if not rows:
        return "Пока никто не открыл древо развития."
    lines = ["👥 <b>РАЗВИТИЕ УЧАСТНИКОВ</b>", ""]
    for index, row in enumerate(rows, 1):
        lines.append(
            f"{index}. <b>{html.escape(str(row['full_name']))}</b> — "
            f"{int(row['spent'])} потраченных очков"
        )
    return "\n".join(lines)


def help_text() -> str:
    return (
        "🧭 <b>ЦЕНТРЫ КОМАНД</b>\n\n"
        "🎮 /games — игры, судьба, задания, аура и ЧСВ\n"
        "🌳 /talents — древо, билды и усиления\n"
        "💸 /finance — переводы, займы и долги\n"
        "👑 /power — Герой дня, саботаж, импичмент и бунт\n"
        "🌌 /roles — роли, карьера и способности\n"
        "🌠 /event — ежедневное событие\n"
        "🌌 /boss — общий рейд\n\n"
        "<b>Скрытые быстрые команды продолжают работать:</b>\n"
        "/dice, /coin, /fate, /today, /secret, /ego, /roulette, /action, "
        "/aura, /chsv, /hero_day, /sabotage, /impeachment, /rebellion, "
        "/abilities, /career, /career_roles, /buffs, /chat_buffs, /builds, "
        "/active_talents, /community_tree, /transfer, /loan, /repay, /debts, /credit."
    )


def install_command_hub_v121(core: Any) -> None:
    if getattr(core, "_command_hub_v121_installed", False):
        return
    core._command_hub_v121_installed = True
    core.COMMAND_HUB_VERSION = VERSION

    # Финальный фиксированный список: остальные команды остаются рабочими,
    # но больше не засоряют выпадающее меню Telegram.
    core.group_bot_commands = _commands

    obsolete = {
        "cmd_games",
        "cmd_talents",
        "cmd_roles",
        "cmd_help",
        "cmd_abilities",
    }
    handlers = core.router.message.handlers
    handlers[:] = [
        handler
        for handler in handlers
        if getattr(handler.callback, "__name__", "") not in obsolete
    ]

    @core.router.message(Command("games", "hunt"))
    async def cmd_games_hub_v121(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        await message.answer(
            "🎮 <b>ИГРЫ И РАЗВЛЕЧЕНИЯ</b>\n\n"
            "Mini App, ставки, Шар судьбы, задания и проверки характера — "
            "всё находится здесь.",
            reply_markup=games_markup(core, int(message.chat.id)),
        )

    @core.router.message(Command("talents", "tree"))
    async def cmd_talents_hub_v121(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        await talent_system.sync_profile(core.db, message.chat.id, message.from_user.id)
        await message.answer(
            "🌳 <b>ДРЕВО И УСИЛЕНИЯ</b>\n\n"
            "В Mini App находятся обычные и особые таланты, активные способности, "
            "билды, сброс и общее древо беседы.",
            reply_markup=talents_markup(core, int(message.chat.id)),
        )

    @core.router.message(Command("power", "conflicts", "authority"))
    async def cmd_power_hub_v121(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        await message.answer(
            await power_text(core, int(message.chat.id)),
            reply_markup=power_markup(),
        )

    @core.router.message(Command("roles"))
    async def cmd_roles_hub_v121(message: Message) -> None:
        if not message.from_user or not core.is_group(message):
            return
        await core.db.upsert_player(message.chat.id, message.from_user)
        await message.answer(
            "🌌 <b>РОЛИ И КАРЬЕРА</b>\n\n"
            "Постоянная роль зависит от карьерного влияния. Здесь можно увидеть "
            "свой прогресс, все пороги, способности и рейтинг.",
            reply_markup=roles_markup(),
        )

    @core.router.message(Command("help", "commands", "rules"))
    async def cmd_help_hub_v121(message: Message) -> None:
        await message.answer(help_text())

    @core.router.callback_query(F.data.startswith(f"{PREFIX}:"))
    async def command_hub_callback_v121(callback: CallbackQuery, bot: Bot) -> None:
        if callback.message is None or not callback.from_user:
            await callback.answer("Сообщение больше недоступно.", show_alert=True)
            return
        chat_id = int(callback.message.chat.id)
        if not core.is_group(callback.message):
            await callback.answer("Раздел работает только в группе.", show_alert=True)
            return
        await core.db.upsert_player(chat_id, callback.from_user)
        action = str(callback.data or "")[len(PREFIX) + 1 :]

        if action == "games:menu":
            await callback.answer()
            await _safe_edit(
                callback,
                "🎮 <b>ИГРЫ И РАЗВЛЕЧЕНИЯ</b>\n\nВыбери действие:",
                games_markup(core, chat_id),
            )
            return
        if action in {"games:dice", "games:coin"}:
            game = action.split(":", 1)[1]
            title = "Кубик" if game == "dice" else "Монетка"
            await callback.answer()
            await _safe_edit(
                callback,
                f"{'🎲' if game == 'dice' else '🪙'} <b>{title.upper()}</b>\n\nВыбери ставку. "
                f"Для другой суммы используй <code>/{game} число</code>.",
                wager_markup(game),
            )
            return
        if action.startswith("wager:"):
            _, game, amount_text = action.split(":", 2)
            await callback.answer("Бросок запущен…")
            article = await core.prepare_bot_game_result(
                callback.from_user, game, int(amount_text), chat_id
            )
            await _send_article(core, callback.message, article)
            return
        if action == "games:fate":
            player = await core.db.get_player(chat_id, callback.from_user.id)
            await callback.answer()
            await callback.message.answer(
                core.fate_invitation_text(player),
                reply_markup=core.fate_start_keyboard(callback.from_user.id, chat_id),
            )
            return
        if action == "games:roulette":
            await callback.answer("Рулетка вращается…")
            await callback.message.answer(await core.apply_roulette(chat_id, callback.from_user))
            return
        if action == "games:today":
            player = await core.db.get_player(chat_id, callback.from_user.id)
            await callback.answer()
            await callback.message.answer(await core.build_today_type_text(chat_id, player))
            return
        if action == "games:secret":
            remaining = await core.db.timed_remaining(
                f"chat:{chat_id}:secret_mission:{callback.from_user.id}",
                core.SECRET_MISSION_COOLDOWN_SECONDS,
            )
            await callback.answer()
            if remaining:
                await callback.message.answer(
                    "🎯 Новое тайное задание через "
                    f"<b>{core.human_duration(remaining)}</b>."
                )
            else:
                await callback.message.answer(
                    "🎯 <b>ТАЙНОЕ ЗАДАНИЕ</b>\n\n"
                    "Нажми кнопку — условие увидит только владелец задания.",
                    reply_markup=core.secret_mission_button(callback.from_user.id, chat_id),
                )
            return
        if action == "games:action":
            await callback.answer()
            article = await core.prepare_action_task(callback.from_user, chat_id)
            await _send_article(core, callback.message, article)
            return
        if action == "games:ego":
            await callback.answer()
            await _safe_edit(
                callback,
                "⚔️ <b>БИТВА ЭГО</b>\n\nВыбери быструю ставку или используй "
                "<code>/ego число</code>.",
                ego_markup(),
            )
            return
        if action.startswith("ego:"):
            stake = action.split(":", 1)[1]
            await callback.answer()
            article = await core.prepare_ego_challenge_result(
                callback.from_user, stake, chat_id
            )
            await _send_article(core, callback.message, article)
            return
        if action in {"games:aura", "games:chsv"}:
            metric = action.split(":", 1)[1]
            player = await core.db.get_player(chat_id, callback.from_user.id)
            await callback.answer()
            await callback.message.answer(await core.build_metric_text(chat_id, player, metric))
            return

        if action == "talents:buffs":
            await callback.answer()
            await callback.message.answer(
                await talents_buffs_text(core, chat_id, callback.from_user.id)
            )
            return
        if action == "talents:chat":
            await callback.answer()
            await callback.message.answer(await chat_buffs_text(core, chat_id))
            return
        if action in {"talents:builds", "talents:active"}:
            await callback.answer()
            section = "🧩 Билды и сброс" if action.endswith("builds") else "⚡ Активные способности"
            await callback.message.answer(
                f"{section} находятся внутри Mini App Древа. Открой <b>/talents</b> "
                "и выбери соответствующую кнопку над деревом."
            )
            return

        if action == "power:refresh":
            await callback.answer("Статус обновлён")
            await _safe_edit(callback, await power_text(core, chat_id), power_markup())
            return
        if action == "power:hero":
            await callback.answer("Проводим выборы…")
            text = await core.execute_timed_feature_auto(
                chat_id, callback.from_user, "hero"
            )
            await callback.message.answer(text)
            return
        if action == "power:sabotage":
            await callback.answer()
            article = await core.prepare_sabotage_result(callback.from_user, chat_id, bot)
            await _send_article(core, callback.message, article)
            return
        if action == "power:impeachment":
            await callback.answer()
            article = await core.prepare_impeachment_article(callback.from_user, chat_id)
            await _send_article(core, callback.message, article)
            return
        if action == "power:rebellion":
            await callback.answer()
            article = await core.prepare_rebellion_result(callback.from_user, chat_id)
            await _send_article(core, callback.message, article)
            return
        if action == "power:abilities":
            await callback.answer()
            await callback.message.answer(core.role_ability_info_text())
            return
        if action == "power:rules":
            await callback.answer()
            await callback.message.answer(
                "📜 <b>ПРАВИЛА ВЛАСТИ</b>\n\n"
                "🌟 Герой дня — временное звание.\n"
                "💣 Саботаж позволяет временно захватить корону.\n"
                "🏛 Импичмент работает против постоянного Главного героя.\n"
                "⚔️ Бунт направлен против активного Саботажного героя.\n"
                "🌌 Центр Вселенной обычному импичменту не подлежит."
            )
            return

        if action == "roles:career":
            player = await core.db.get_player(chat_id, callback.from_user.id)
            await callback.answer()
            await callback.message.answer(await career_text(core, chat_id, player))
            return
        if action == "roles:all":
            await callback.answer()
            await callback.message.answer(core.roles_text())
            return
        if action == "roles:top":
            await callback.answer()
            await callback.message.answer(
                await core.build_top_text(chat_id, heading="Карьерная иерархия")
            )
            return
        if action == "roles:abilities":
            await callback.answer()
            await callback.message.answer(core.role_ability_info_text())
            return

        await callback.answer("Неизвестный раздел.", show_alert=True)

    message_handlers = core.router.message.handlers
    preferred_names = {
        "cmd_games_hub_v121",
        "cmd_talents_hub_v121",
        "cmd_power_hub_v121",
        "cmd_roles_hub_v121",
        "cmd_help_hub_v121",
    }
    preferred = [
        handler
        for handler in message_handlers
        if getattr(handler.callback, "__name__", "") in preferred_names
    ]
    message_handlers[:] = preferred + [
        handler for handler in message_handlers if handler not in preferred
    ]

    callback_handlers = core.router.callback_query.handlers
    preferred_callbacks = [
        handler
        for handler in callback_handlers
        if getattr(handler.callback, "__name__", "") == "command_hub_callback_v121"
    ]
    callback_handlers[:] = preferred_callbacks + [
        handler for handler in callback_handlers if handler not in preferred_callbacks
    ]
