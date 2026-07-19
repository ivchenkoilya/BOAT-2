from __future__ import annotations

import contextvars
import time
from typing import Any

import talent_bonus_display_v73 as bonus_v73
import talent_system as talents
import talent_ux


OLD_DUST = 500
OLD_EXTRAS = 1000
OLD_SECONDARY = 2000
OLD_HERO = 3000

NEW_DUST = 1000
NEW_EXTRAS = 3000
NEW_SECONDARY = 6000
NEW_HERO = 10000

MIGRATION_KEY = "reality74_role_economy_scale"
_FATE_BREAKDOWN: contextvars.ContextVar[dict[str, Any] | None] = contextvars.ContextVar(
    "reality74_fate_breakdown", default=None
)


UI_PATCH = r"""
<style id="talent-luck-stability-v74-style">
body.luck-stable::before,
body.luck-stable .world *,
body.luck-stable .world *::before,
body.luck-stable .world *::after{
  animation:none!important;
  transition:none!important;
}
body.luck-stable .world{
  contain:paint;
  backface-visibility:hidden;
  -webkit-backface-visibility:hidden;
  will-change:auto!important;
}
body.luck-stable .edge,
body.luck-stable .edge.on{
  stroke-dasharray:none!important;
  stroke-dashoffset:0!important;
  filter:none!important;
}
body.luck-stable .nodewrap,
body.luck-stable .nodewrap .node{
  filter:none!important;
  will-change:auto!important;
}
body.luck-stable .nodewrap.available .node{
  transform:none!important;
  box-shadow:0 16px 34px #0007,0 0 25px rgba(var(--rgb),.22)!important;
}
</style>
<script id="talent-luck-stability-v74-script">
(()=>{
 const syncLuckMode=()=>{
  try{
   document.body.classList.toggle(
    'luck-stable',
    typeof branch!=='undefined'&&branch==='rewards'
   );
  }catch(_){}
 };
 const wait=setInterval(()=>{
  if(typeof branch==='undefined')return;
  clearInterval(wait);syncLuckMode();
 },100);
 document.addEventListener('click',()=>setTimeout(syncLuckMode,0),false);
 document.addEventListener('pointerup',()=>setTimeout(syncLuckMode,0),false);
})();
</script>
"""


def _scale_old_points(points: int) -> int:
    """Переносит старый баланс в новую шкалу, сохраняя роль и порядок игроков."""
    value = int(points)
    if value < 0:
        return value
    if value < OLD_DUST:
        return value * 2
    if value < OLD_EXTRAS:
        return NEW_DUST + (value - OLD_DUST) * 4
    if value < OLD_SECONDARY:
        return NEW_EXTRAS + (value - OLD_EXTRAS) * 3
    if value < OLD_HERO:
        return NEW_SECONDARY + (value - OLD_SECONDARY) * 4
    return NEW_HERO + (value - OLD_HERO) * 4


async def _table_exists(conn: Any, table_name: str) -> bool:
    cursor = await conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
        (table_name,),
    )
    return await cursor.fetchone() is not None


async def _migrate_old_balances(db: Any) -> None:
    conn = getattr(db, "connection", None)
    if conn is None:
        return

    async with db.lock:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS economy_migrations (
                migration_key TEXT PRIMARY KEY,
                applied_at INTEGER NOT NULL
            )
            """
        )
        cursor = await conn.execute(
            "SELECT 1 FROM economy_migrations WHERE migration_key = ? LIMIT 1",
            (MIGRATION_KEY,),
        )
        if await cursor.fetchone() is not None:
            await conn.commit()
            return

        cursor = await conn.execute("SELECT chat_id, user_id, points FROM players")
        player_rows = await cursor.fetchall()
        if player_rows:
            await conn.executemany(
                "UPDATE players SET points = ?, updated_at = ? WHERE chat_id = ? AND user_id = ?",
                [
                    (
                        _scale_old_points(int(row["points"])),
                        int(time.time()),
                        int(row["chat_id"]),
                        int(row["user_id"]),
                    )
                    for row in player_rows
                ],
            )

        if await _table_exists(conn, "hero_day_state"):
            cursor = await conn.execute(
                "SELECT chat_id, original_points, assigned_points FROM hero_day_state"
            )
            rows = await cursor.fetchall()
            if rows:
                await conn.executemany(
                    """
                    UPDATE hero_day_state
                    SET original_points = ?, assigned_points = ?
                    WHERE chat_id = ?
                    """,
                    [
                        (
                            _scale_old_points(int(row["original_points"])),
                            _scale_old_points(int(row["assigned_points"])),
                            int(row["chat_id"]),
                        )
                        for row in rows
                    ],
                )

        if await _table_exists(conn, "impeachments"):
            cursor = await conn.execute(
                "SELECT impeachment_id, target_start_points FROM impeachments"
            )
            rows = await cursor.fetchall()
            if rows:
                await conn.executemany(
                    "UPDATE impeachments SET target_start_points = ? WHERE impeachment_id = ?",
                    [
                        (
                            _scale_old_points(int(row["target_start_points"])),
                            str(row["impeachment_id"]),
                        )
                        for row in rows
                    ],
                )

        if await _table_exists(conn, "sabotages"):
            cursor = await conn.execute(
                "SELECT sabotage_id, boost_amount FROM sabotages WHERE boost_amount > 0"
            )
            rows = await cursor.fetchall()
            if rows:
                updates: list[tuple[int, str]] = []
                for row in rows:
                    old_boost = int(row["boost_amount"])
                    old_original = OLD_HERO - old_boost
                    new_boost = max(0, NEW_HERO - _scale_old_points(old_original))
                    updates.append((new_boost, str(row["sabotage_id"])))
                await conn.executemany(
                    "UPDATE sabotages SET boost_amount = ? WHERE sabotage_id = ?",
                    updates,
                )

        await conn.execute(
            "INSERT INTO economy_migrations (migration_key, applied_at) VALUES (?, ?)",
            (MIGRATION_KEY, int(time.time())),
        )
        await conn.commit()


def _signed(value: int) -> str:
    number = int(value)
    if number > 0:
        return f"+{number}"
    if number < 0:
        return f"−{abs(number)}"
    return "0"


def _fate_block(data: dict[str, Any]) -> str:
    base = int(data.get("base", 0))
    actual = int(data.get("actual", 0))
    percent = max(0.0, float(data.get("percent", 0.0)))
    lines = [
        "🌳 <b>КАК ПОВЛИЯЛО ДРЕВО ЗНАНИЙ</b>",
        f"🔮 Базовый исход Шара: <b>{_signed(base)}</b>",
    ]

    if base > 0:
        bonus = max(0, actual - base)
        percent_text = bonus_v73._format_percent(percent)
        lines.append(f"📈 Усиление награды: <b>+{percent_text}%</b>")
        if bonus > 0:
            deterministic = max(0, int(round(base * percent)))
            special = max(0, bonus - deterministic)
            lines.append(f"➕ Добавлено древом: <b>+{bonus}</b>")
            if special > 0:
                lines.append(f"🍀 Удача и особые таланты: <b>+{special}</b>")
        else:
            lines.append("➕ Процент активен, но округление не добавило целого очка.")
    elif base < 0:
        saved = max(0, abs(base) - abs(min(0, actual)))
        if actual == 0:
            lines.append("🛡 Древо полностью отменило потерю.")
        elif saved > 0:
            lines.append(f"🛡 Древо сохранило: <b>+{saved}</b> очков")
        else:
            lines.append("🛡 Защитные таланты не сработали на этот исход.")
    else:
        lines.append("🍀 Исход был нулевым, поэтому усиливать было нечего.")

    lines.append(f"🏆 Итоговое изменение: <b>{_signed(actual)}</b>")
    return "\n".join(lines)


def _append_fate_block(text: str, data: dict[str, Any]) -> str:
    if "КАК ПОВЛИЯЛО ДРЕВО ЗНАНИЙ" in str(text):
        return str(text)
    block = _fate_block(data)
    result = f"{text}\n\n{block}"
    return result if len(result) <= 4000 else str(text)


def _roles_text() -> str:
    return (
        "📜 <b>ИЕРАРХИЯ РЕАЛЬНОСТИ</b> 📜\n\n"
        "🪑 <b>Декорация</b> — от 0 до 999 очков.\n"
        "Ты присутствуешь, но сюжет пока почти не замечает тебя.\n\n"
        "🌫 <b>Пыль</b> — от 1000 до 2999 очков.\n"
        "Тебя уже замечают, но влияние ещё легко развеять.\n\n"
        "👥 <b>Массовка</b> — от 3000 до 5999 очков.\n"
        "Ты стал полноценной частью событий и можешь давить числом и активностью.\n\n"
        "🎭 <b>Второстепенная роль</b> — от 6000 до 9999 очков.\n"
        "Твоё мнение весит много, а до центра внимания остаётся последний рывок.\n\n"
        "👑 <b>Главный герой</b> — от 10 000 очков.\n"
        "Ты достиг вершины и теперь должен удерживать корону.\n\n"
        "🌳 Очки древа: 3 стартовых и ещё 1 за каждые 1000 влияния. "
        "Дополнительные очки выдаются за рейды против Центра Вселенной."
    )


def install_economy_fate_ui_v74(core: Any) -> None:
    if getattr(core, "_economy_fate_ui_v74_installed", False):
        return
    core._economy_fate_ui_v74_installed = True

    core.DUST_MIN_POINTS = NEW_DUST
    core.EXTRAS_MIN_POINTS = NEW_EXTRAS
    core.SECONDARY_MIN_POINTS = NEW_SECONDARY
    core.HERO_MIN_POINTS = NEW_HERO
    core.ADMIN_ROLE_POINTS = {
        "decoration": ("🪑 Декорация", 0),
        "dust": ("🌫 Пыль", NEW_DUST),
        "extras": ("👥 Массовка", NEW_EXTRAS),
        "secondary": ("🎭 Второстепенная роль", NEW_SECONDARY),
        "hero": ("👑 Главный герой", NEW_HERO),
    }
    core.roles_text = _roles_text

    # Новая выдача очков древа. Уже открытые очки не отнимаются, потому что
    # talent_profiles сохраняет максимальное когда-либо открытое значение.
    talents._entitled_points = lambda influence: min(
        12, 3 + max(0, int(influence)) // 1000
    )

    original_connect = core.Database.connect

    async def connect_with_economy_v74(self: Any) -> None:
        await original_connect(self)
        await _migrate_old_balances(self)

    core.Database.connect = connect_with_economy_v74

    previous_hero_day = getattr(core, "build_hero_of_day_text", None)
    if previous_hero_day is not None:
        async def build_hero_of_day_text(chat_id: int) -> str:
            text = await previous_hero_day(chat_id)
            return text.replace("3000 очков", "10 000 очков")
        core.build_hero_of_day_text = build_hero_of_day_text

    original_add = core.Database.add_points_with_balance

    async def add_points_with_fate_breakdown(self: Any, *args: Any, **kwargs: Any):
        extracted = talents._extract_score_args(args, kwargs)
        result = await original_add(self, *args, **kwargs)
        if extracted is None:
            return result
        chat_id, user_id, base_delta, reason = extracted
        if "fate_orb_result" not in str(reason or "").casefold():
            return result
        try:
            before, after = result
            actual = int(after.points) - int(before)
            percent = await bonus_v73._tree_percent(
                self, chat_id, user_id, str(reason or "")
            )
            _FATE_BREAKDOWN.set(
                {
                    "user_id": user_id,
                    "base": int(base_delta),
                    "actual": actual,
                    "percent": percent,
                }
            )
        except Exception:
            _FATE_BREAKDOWN.set(None)
        return result

    core.Database.add_points_with_balance = add_points_with_fate_breakdown

    original_edit_callback = getattr(core, "edit_callback_text", None)
    if original_edit_callback is not None:
        async def edit_callback_text(*args: Any, **kwargs: Any):
            data = _FATE_BREAKDOWN.get()
            if data is not None:
                _FATE_BREAKDOWN.set(None)
                callback = args[0] if args else kwargs.get("callback")
                user_id = getattr(getattr(callback, "from_user", None), "id", None)
                try:
                    bonus_v73._take_awards(user_id)
                except Exception:
                    pass
                values = list(args)
                if len(values) > 2:
                    values[2] = _append_fate_block(str(values[2]), data)
                    args = tuple(values)
                elif "text_value" in kwargs:
                    kwargs = dict(kwargs)
                    kwargs["text_value"] = _append_fate_block(
                        str(kwargs["text_value"]), data
                    )
                elif "text" in kwargs:
                    kwargs = dict(kwargs)
                    kwargs["text"] = _append_fate_block(str(kwargs["text"]), data)
            return await original_edit_callback(*args, **kwargs)

        core.edit_callback_text = edit_callback_text

    talent_ux.SCRIPT += UI_PATCH
