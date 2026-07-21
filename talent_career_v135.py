from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import career_model_v120
import career_rewards_v120
import knowledge_economy_v85 as knowledge
import talent_system

LOGGER = logging.getLogger(__name__)
VERSION = "Reality 135 · Древо за карьеру"
START_POINTS = 5
CAREER_POINT_STEP = 50_000
MIGRATION_KEY = "career_tree_entitlement_v135"


def _entitled(career_points: int) -> int:
    return START_POINTS + max(0, int(career_points)) // CAREER_POINT_STEP


def _career(player: Any) -> int:
    return career_model_v120.career_value(player.points)


async def _ensure_profile(
    db: Any,
    chat_id: int,
    user_id: int,
    base_sync: Any = None,
    synced: bool = False,
) -> None:
    del base_sync, synced
    player = await db.get_player(chat_id, user_id)
    if player is None:
        return
    career = _career(player)
    deserved = _entitled(career)
    now = int(time.time())
    conn = db._require_connection()
    async with db.lock:
        cursor = await conn.execute(
            "SELECT total_points,spent_points FROM talent_profiles WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        talent = await cursor.fetchone()
        if talent is None:
            await conn.execute(
                "INSERT INTO talent_profiles(chat_id,user_id,total_points,spent_points,updated_at) "
                "VALUES(?,?,?,?,?)",
                (chat_id, user_id, deserved, 0, now),
            )
        cursor = await conn.execute(
            "SELECT entitled FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        economy = await cursor.fetchone()
        if economy is None:
            await conn.execute(
                "INSERT INTO knowledge_economy_v85(chat_id,user_id,career,entitled,updated_at) "
                "VALUES(?,?,?,?,?)",
                (chat_id, user_id, career, deserved, now),
            )
        else:
            previous = int(economy["entitled"] or 0)
            grant = max(0, deserved - previous)
            if grant:
                await conn.execute(
                    "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? "
                    "WHERE chat_id=? AND user_id=?",
                    (grant, now, chat_id, user_id),
                )
            await conn.execute(
                "UPDATE knowledge_economy_v85 SET career=?,entitled=?,updated_at=? "
                "WHERE chat_id=? AND user_id=?",
                (career, max(previous, deserved), now, chat_id, user_id),
            )
        await conn.commit()


async def _sync_profile(db: Any, chat_id: int, user_id: int) -> dict[str, int]:
    player = await db.get_player(chat_id, user_id)
    if player is None:
        raise ValueError("Сначала используй бота в этой беседе.")
    await _ensure_profile(db, chat_id, user_id)
    conn = db._require_connection()
    cursor = await conn.execute(
        "SELECT total_points,spent_points FROM talent_profiles WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    row = await cursor.fetchone()
    total = int(row["total_points"] or 0) if row else START_POINTS
    spent = int(row["spent_points"] or 0) if row else 0
    return {"total": total, "spent": spent, "available": max(0, total - spent)}


async def _positive_direct_only(
    core: Any,
    db: Any,
    chat_id: int,
    user_id: int,
    delta: int,
    reason: str,
) -> None:
    if delta <= 0 or knowledge._has(reason, knowledge.EXCLUDED_WORDS):
        return
    await _ensure_profile(db, chat_id, user_id)
    is_game = knowledge._has(reason, knowledge.GAME_WORDS)
    is_task = knowledge._has(reason, knowledge.TASK_WORDS)
    is_activity = knowledge._has(reason, knowledge.ACTIVITY_WORDS)
    player = await db.get_player(chat_id, user_id)
    conn = db._require_connection()
    now, week = int(time.time()), knowledge._week()
    async with db.lock:
        cursor = await conn.execute(
            "SELECT career,entitled,game_wins,tasks FROM knowledge_economy_v85 "
            "WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        profile = await cursor.fetchone()
        if profile is None:
            return
        await conn.execute(
            "INSERT OR IGNORE INTO knowledge_week_v85(chat_id,user_id,week_key,updated_at) "
            "VALUES(?,?,?,?)",
            (chat_id, user_id, week, now),
        )
        cursor = await conn.execute(
            "SELECT game_career,task_points,activity_points FROM knowledge_week_v85 "
            "WHERE chat_id=? AND user_id=? AND week_key=?",
            (chat_id, user_id, week),
        )
        weekly = await cursor.fetchone()
        game_career = int(weekly["game_career"] or 0)
        task_points = int(weekly["task_points"] or 0)
        activity_points = int(weekly["activity_points"] or 0)
        game_wins = int(profile["game_wins"] or 0)
        tasks = int(profile["tasks"] or 0)
        direct = 0

        if is_game:
            game_wins += 1
            if game_wins >= 25:
                direct += await knowledge._achievement(
                    conn, chat_id, user_id, "game25", 2, now
                )
        if is_task:
            tasks += 1
            if task_points < knowledge.TASK_WEEKLY_CAP:
                task_points += 1
                direct += 1
            if tasks >= 50:
                direct += await knowledge._achievement(
                    conn, chat_id, user_id, "tasks50", 3, now
                )
        if is_activity:
            await conn.execute(
                "INSERT OR IGNORE INTO knowledge_days_v85("
                "chat_id,user_id,week_key,day_key,created_at) VALUES(?,?,?,?,?)",
                (chat_id, user_id, week, knowledge._day(), now),
            )
            cursor = await conn.execute(
                "SELECT COUNT(*) amount FROM knowledge_days_v85 "
                "WHERE chat_id=? AND user_id=? AND week_key=?",
                (chat_id, user_id, week),
            )
            row = await cursor.fetchone()
            deserved_days = sum(
                int(row["amount"] or 0) >= threshold
                for threshold in knowledge.ACTIVITY_DAY_STEPS
            )
            if deserved_days > activity_points:
                direct += deserved_days - activity_points
                activity_points = deserved_days

        career = _career(player) if player is not None else int(profile["career"] or 0)
        entitled = max(int(profile["entitled"] or 0), _entitled(career))
        hero_min = int(getattr(core, "CAREER_HERO_MIN", 900_000))
        if player is not None and career >= hero_min:
            direct += await knowledge._achievement(
                conn, chat_id, user_id, "hero", 2, now
            )

        await conn.execute(
            "UPDATE knowledge_economy_v85 SET career=?,entitled=?,game_wins=?,tasks=?,updated_at=? "
            "WHERE chat_id=? AND user_id=?",
            (career, entitled, game_wins, tasks, now, chat_id, user_id),
        )
        await conn.execute(
            "UPDATE knowledge_week_v85 SET game_career=?,task_points=?,activity_points=?,updated_at=? "
            "WHERE chat_id=? AND user_id=? AND week_key=?",
            (game_career, task_points, activity_points, now, chat_id, user_id, week),
        )
        if direct:
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? "
                "WHERE chat_id=? AND user_id=?",
                (direct, now, chat_id, user_id),
            )
        await conn.commit()


async def _boss_achievement_career(
    core: Any,
    db: Any,
    boss_id: str,
    chat_id: int,
    user_id: int,
) -> None:
    player = await db.get_player(chat_id, user_id)
    career = _career(player) if player is not None else 0
    conn = db._require_connection()
    now = int(time.time())
    async with db.lock:
        cursor = await conn.execute(
            "INSERT OR IGNORE INTO knowledge_boss_events_v85("
            "boss_id,user_id,chat_id,created_at) VALUES(?,?,?,?)",
            (boss_id, user_id, chat_id, now),
        )
        if cursor.rowcount <= 0:
            await conn.commit()
            return
        await conn.execute(
            "UPDATE knowledge_economy_v85 SET boss_wins=boss_wins+1,updated_at=? "
            "WHERE chat_id=? AND user_id=?",
            (now, chat_id, user_id),
        )
        cursor = await conn.execute(
            "SELECT boss_wins FROM knowledge_economy_v85 WHERE chat_id=? AND user_id=?",
            (chat_id, user_id),
        )
        row = await cursor.fetchone()
        wins = int(row["boss_wins"] or 0) if row else 0
        grant = await knowledge._achievement(
            conn, chat_id, user_id, "boss1", 1, now
        )
        if wins >= 10:
            grant += await knowledge._achievement(
                conn, chat_id, user_id, "boss10", 3, now
            )
        hero_min = int(getattr(core, "CAREER_HERO_MIN", 900_000))
        if career >= hero_min:
            grant += await knowledge._achievement(
                conn, chat_id, user_id, "hero", 2, now
            )
        if grant:
            await conn.execute(
                "UPDATE talent_profiles SET total_points=total_points+?,updated_at=? "
                "WHERE chat_id=? AND user_id=?",
                (grant, now, chat_id, user_id),
            )
        await conn.commit()


async def _repair_existing(db: Any) -> None:
    conn = db._require_connection()
    now = int(time.time())
    async with db.lock:
        await conn.execute(
            "CREATE TABLE IF NOT EXISTS talent_career_meta_v135("
            "key TEXT PRIMARY KEY,value TEXT NOT NULL)"
        )
        cursor = await conn.execute(
            "SELECT 1 FROM talent_career_meta_v135 WHERE key=?",
            (MIGRATION_KEY,),
        )
        if await cursor.fetchone() is not None:
            await conn.commit()
            return
        cursor = await conn.execute(
            "SELECT t.chat_id,t.user_id,t.total_points,t.spent_points,"
            "COALESCE(p.points,0) wallet,COALESCE(p.career_points,0) career,"
            "k.entitled old_entitled "
            "FROM talent_profiles t "
            "LEFT JOIN players p ON p.chat_id=t.chat_id AND p.user_id=t.user_id "
            "LEFT JOIN knowledge_economy_v85 k ON k.chat_id=t.chat_id AND k.user_id=t.user_id"
        )
        rows = list(await cursor.fetchall())
        for row in rows:
            wallet = max(0, int(row["wallet"] or 0))
            career = max(0, int(row["career"] or 0))
            legacy_auto = min(15, 3 + wallet // 500)
            old_knowledge = int(row["old_entitled"] or 0)
            old_auto = max(legacy_auto, old_knowledge)
            new_auto = _entitled(career)
            total = int(row["total_points"] or 0)
            spent = int(row["spent_points"] or 0)
            corrected_total = max(spent, total + new_auto - old_auto)
            await conn.execute(
                "UPDATE talent_profiles SET total_points=?,updated_at=? "
                "WHERE chat_id=? AND user_id=?",
                (corrected_total, now, row["chat_id"], row["user_id"]),
            )
            await conn.execute(
                "INSERT INTO knowledge_economy_v85(chat_id,user_id,career,entitled,updated_at) "
                "VALUES(?,?,?,?,?) ON CONFLICT(chat_id,user_id) DO UPDATE SET "
                "career=excluded.career,entitled=excluded.entitled,updated_at=excluded.updated_at",
                (row["chat_id"], row["user_id"], career, new_auto, now),
            )
        await conn.execute(
            "INSERT INTO talent_career_meta_v135(key,value) VALUES(?,?)",
            (MIGRATION_KEY, str(now)),
        )
        await conn.commit()


def install_talent_career_v135(core: Any) -> None:
    if getattr(core, "_talent_career_v135_installed", False):
        return
    core._talent_career_v135_installed = True
    core.BOT_VERSION = VERSION
    core.TALENT_CAREER_POINT_STEP = CAREER_POINT_STEP

    original_connect = core.Database.connect

    async def connect_with_talent_career(self: Any) -> None:
        await original_connect(self)
        await _repair_existing(self)

    core.Database.connect = connect_with_talent_career
    talent_system.sync_profile = _sync_profile
    knowledge._ensure = _ensure_profile
    knowledge._positive = _positive_direct_only
    knowledge._boss_achievement = _boss_achievement_career

    old_file_response = core.web.FileResponse

    def file_response_with_career_help(path: Any, *args: Any, **kwargs: Any):
        file_path = Path(path)
        if file_path.name == "index.html" and file_path.parent.name == "talent_app":
            try:
                text = file_path.read_text(encoding="utf-8")
                old_variants = (
                    "Ты получаешь 3 стартовых очка и ещё по одному за каждые 500 очков влияния. Уже открытые очки не отнимаются при потере влияния.",
                    "Ты получаешь 5 стартовых очков и ещё по одному за каждые 500 карьерного влияния без лимита. Босс, задания, активные дни и достижения дают дополнительные очки, а от мини-игр в прогресс идёт 20% положительной награды.",
                )
                new_help = (
                    "Ты получаешь 5 стартовых очков и ещё по одному за каждые "
                    "50 000 карьерных очков. Обычное влияние и баланс кошелька не "
                    "учитываются. Босс, задания, активные дни и достижения дают "
                    "дополнительные очки Древа."
                )
                for old in old_variants:
                    text = text.replace(old, new_help)
                return core.web.Response(
                    text=text,
                    content_type="text/html",
                    headers={"Cache-Control": "no-store"},
                )
            except Exception:
                LOGGER.exception("Не удалось обновить подсказку карьерного Древа")
        return old_file_response(path, *args, **kwargs)

    core.web.FileResponse = file_response_with_career_help

    old_about = getattr(core, "about_bot_text", None)
    if callable(old_about):
        def about_bot_text_with_career() -> str:
            text = str(old_about())
            start = text.find("🌳 <b>БЫСТРАЯ ПРОКАЧКА ДРЕВА</b>")
            end = text.find("🎖 <b>РАЗОВЫЕ ДОСТИЖЕНИЯ</b>")
            if start < 0 or end <= start:
                return text
            block = (
                "🌳 <b>ПРОКАЧКА ДРЕВА ЗА КАРЬЕРУ</b>\n"
                "• 5 стартовых очков;\n"
                "• ещё 1 очко за каждые 50 000 карьерных очков;\n"
                "• обычное влияние, переводы, вклады и баланс кошелька не учитываются;\n"
                "• карьерные очки начисляются за задания, достижения, события, "
                "боссов и подходящую игровую активность;\n"
                "• прямые награды Древа за босса, задания, активные дни и достижения "
                "сохраняются.\n\n"
            )
            return text[:start] + block + text[end:]

        core.about_bot_text = about_bot_text_with_career

    original_award = career_rewards_v120.award

    async def award_with_talent_sync(
        career_core: Any,
        chat_id: int,
        user_id: int,
        amount: int,
        source_type: str,
        source_id: str,
        reason: str,
    ) -> int:
        granted = await original_award(
            career_core,
            chat_id,
            user_id,
            amount,
            source_type,
            source_id,
            reason,
        )
        if granted:
            try:
                await _sync_profile(career_core.db, int(chat_id), int(user_id))
            except Exception:
                LOGGER.exception(
                    "Не удалось синхронизировать очки Древа с карьерой: chat=%s user=%s",
                    chat_id,
                    user_id,
                )
        return granted

    career_rewards_v120.award = award_with_talent_sync
