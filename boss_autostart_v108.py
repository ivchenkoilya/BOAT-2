from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any

from aiogram.types import User


LOGGER = logging.getLogger(__name__)
VERSION = "Reality 108 · Автозапуск Центра Вселенной"
WARNING_BEFORE_SECONDS = 60 * 60
CHECK_INTERVAL_SECONDS = 30
RETRY_AFTER_SECONDS = 5 * 60
COOLDOWN_KEY_RE = re.compile(r"^chat:(-?\d+):boss$")


def _now() -> int:
    return int(time.time())


def _chat_id_from_key(value: str) -> int | None:
    match = COOLDOWN_KEY_RE.fullmatch(value)
    if match is None:
        return None
    try:
        chat_id = int(match.group(1))
    except (TypeError, ValueError):
        return None
    return chat_id if chat_id < 0 else None


async def _ensure_cycle_state(core: Any, chat_id: int, cooldown_started_at: int) -> Any:
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        await conn.execute(
            """
            INSERT INTO boss_autostart_state_v108(
                chat_id,cooldown_started_at,warning_sent_at,warning_attempt_at,
                launch_attempt_at,last_error,updated_at
            ) VALUES(?,?,0,0,0,NULL,?)
            ON CONFLICT(chat_id) DO UPDATE SET
                warning_sent_at=CASE
                    WHEN boss_autostart_state_v108.cooldown_started_at<>excluded.cooldown_started_at
                    THEN 0 ELSE boss_autostart_state_v108.warning_sent_at END,
                warning_attempt_at=CASE
                    WHEN boss_autostart_state_v108.cooldown_started_at<>excluded.cooldown_started_at
                    THEN 0 ELSE boss_autostart_state_v108.warning_attempt_at END,
                launch_attempt_at=CASE
                    WHEN boss_autostart_state_v108.cooldown_started_at<>excluded.cooldown_started_at
                    THEN 0 ELSE boss_autostart_state_v108.launch_attempt_at END,
                last_error=CASE
                    WHEN boss_autostart_state_v108.cooldown_started_at<>excluded.cooldown_started_at
                    THEN NULL ELSE boss_autostart_state_v108.last_error END,
                cooldown_started_at=excluded.cooldown_started_at,
                updated_at=excluded.updated_at
            """,
            (chat_id, cooldown_started_at, now),
        )
        cursor = await conn.execute(
            "SELECT * FROM boss_autostart_state_v108 WHERE chat_id=?",
            (chat_id,),
        )
        row = await cursor.fetchone()
        await conn.commit()
        return row


async def _claim_attempt(
    core: Any,
    chat_id: int,
    cooldown_started_at: int,
    field: str,
) -> bool:
    if field not in {"warning_attempt_at", "launch_attempt_at"}:
        raise ValueError("Unsupported attempt field")
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        cursor = await conn.execute(
            f"""
            UPDATE boss_autostart_state_v108
            SET {field}=?,updated_at=?
            WHERE chat_id=? AND cooldown_started_at=?
              AND {field}<=?
            """,
            (
                now,
                now,
                chat_id,
                cooldown_started_at,
                now - RETRY_AFTER_SECONDS,
            ),
        )
        await conn.commit()
        return cursor.rowcount > 0


async def _save_result(
    core: Any,
    chat_id: int,
    cooldown_started_at: int,
    *,
    warning_sent: bool = False,
    error: str | None = None,
) -> None:
    conn = core.db._require_connection()
    now = _now()
    async with core.db.lock:
        if warning_sent:
            await conn.execute(
                """
                UPDATE boss_autostart_state_v108
                SET warning_sent_at=?,last_error=NULL,updated_at=?
                WHERE chat_id=? AND cooldown_started_at=?
                """,
                (now, now, chat_id, cooldown_started_at),
            )
        else:
            await conn.execute(
                """
                UPDATE boss_autostart_state_v108
                SET last_error=?,updated_at=?
                WHERE chat_id=? AND cooldown_started_at=?
                """,
                ((error or "")[:1000] or None, now, chat_id, cooldown_started_at),
            )
        await conn.commit()


async def _send_warning(
    core: Any,
    bot: Any,
    chat_id: int,
    cooldown_started_at: int,
    remaining: int,
) -> None:
    if not await _claim_attempt(
        core,
        chat_id,
        cooldown_started_at,
        "warning_attempt_at",
    ):
        return

    time_text = (
        "через <b>1 час</b>"
        if remaining >= 55 * 60
        else f"примерно через <b>{core.human_duration(max(1, remaining))}</b>"
    )
    try:
        await bot.send_message(
            chat_id,
            "🌌 <b>ЦЕНТР ВСЕЛЕННОЙ ПРОБУЖДАЕТСЯ</b>\n\n"
            f"Новый рейд автоматически начнётся {time_text}.\n"
            "Карточка босса сама появится в этой беседе — ничего запускать вручную не нужно.\n\n"
            "⚔️ Подготовьте способности, лечение и защиту.",
        )
    except Exception as exc:
        await _save_result(
            core,
            chat_id,
            cooldown_started_at,
            error=f"warning: {type(exc).__name__}: {exc}",
        )
        LOGGER.exception("Не удалось предупредить чат %s об автобоссе", chat_id)
        return

    await _save_result(
        core,
        chat_id,
        cooldown_started_at,
        warning_sent=True,
    )


async def _auto_start(
    core: Any,
    bot: Any,
    chat_id: int,
    cooldown_started_at: int,
) -> None:
    if not await _claim_attempt(
        core,
        chat_id,
        cooldown_started_at,
        "launch_attempt_at",
    ):
        return

    starter = User(
        id=int(core.DEVELOPER_ID),
        is_bot=False,
        first_name="Автозапуск рейда",
        username=str(getattr(core, "DEVELOPER_USERNAME", "") or "RealityAutoBoss"),
    )
    try:
        started, result_text = await core.start_boss_battle(chat_id, starter, bot)
    except Exception as exc:
        await _save_result(
            core,
            chat_id,
            cooldown_started_at,
            error=f"launch: {type(exc).__name__}: {exc}",
        )
        LOGGER.exception("Автозапуск Центра Вселенной упал в чате %s", chat_id)
        return

    if started:
        await _save_result(core, chat_id, cooldown_started_at)
        LOGGER.info("Центр Вселенной автоматически запущен в чате %s", chat_id)
        return

    # Если другой процесс или участник успел запустить бой, новый кулдаун уже
    # записан и следующий проход переключится на новый цикл. Остальные ошибки
    # повторно проверяются через RETRY_AFTER_SECONDS.
    await _save_result(
        core,
        chat_id,
        cooldown_started_at,
        error=f"not_started: {result_text}",
    )


async def _check_chat(
    core: Any,
    bot: Any,
    chat_id: int,
    cooldown_started_at: int,
) -> None:
    state = await _ensure_cycle_state(core, chat_id, cooldown_started_at)
    if state is None:
        return

    now = _now()
    starts_at = cooldown_started_at + int(core.BOSS_COOLDOWN_SECONDS)
    remaining = starts_at - now
    active = await core.db.get_active_boss(chat_id)

    if active is not None:
        return

    if remaining > 0:
        if (
            remaining <= WARNING_BEFORE_SECONDS
            and int(state["warning_sent_at"] or 0) <= 0
        ):
            await _send_warning(
                core,
                bot,
                chat_id,
                cooldown_started_at,
                remaining,
            )
        return

    await _auto_start(core, bot, chat_id, cooldown_started_at)


async def _watch_loop(core: Any, bot: Any) -> None:
    while True:
        try:
            conn = core.db._require_connection()
            cursor = await conn.execute(
                """
                SELECT cooldown_key,last_used_at
                FROM timed_cooldowns
                WHERE cooldown_key LIKE 'chat:%:boss'
                ORDER BY last_used_at ASC
                """
            )
            rows = await cursor.fetchall()
            for row in rows:
                chat_id = _chat_id_from_key(str(row["cooldown_key"]))
                if chat_id is None:
                    continue
                try:
                    await _check_chat(
                        core,
                        bot,
                        chat_id,
                        int(row["last_used_at"]),
                    )
                except asyncio.CancelledError:
                    raise
                except Exception:
                    LOGGER.exception("Ошибка проверки автобосса в чате %s", chat_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            LOGGER.exception("Ошибка цикла автоматического запуска босса")

        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def install_boss_autostart_v108(core: Any) -> None:
    if getattr(core, "_boss_autostart_v108_installed", False):
        return
    core._boss_autostart_v108_installed = True
    core.BOSS_AUTOSTART_VERSION = VERSION

    original_connect = core.Database.connect

    async def connect_with_boss_autostart(self: Any) -> None:
        await original_connect(self)
        conn = self._require_connection()
        async with self.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS boss_autostart_state_v108(
                    chat_id INTEGER PRIMARY KEY,
                    cooldown_started_at INTEGER NOT NULL DEFAULT 0,
                    warning_sent_at INTEGER NOT NULL DEFAULT 0,
                    warning_attempt_at INTEGER NOT NULL DEFAULT 0,
                    launch_attempt_at INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at INTEGER NOT NULL DEFAULT 0
                );
                """
            )
            await conn.commit()

    core.Database.connect = connect_with_boss_autostart

    original_start_server = core.start_webapp_server

    async def start_server_with_boss_autostart(bot: Any):
        runner = await original_start_server(bot)
        core.spawn_background_task(_watch_loop(core, bot))
        LOGGER.info("%s активирован", VERSION)
        return runner

    core.start_webapp_server = start_server_with_boss_autostart
