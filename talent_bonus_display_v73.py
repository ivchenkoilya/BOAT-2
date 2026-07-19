from __future__ import annotations

import contextvars
from typing import Any, Awaitable, Callable

import talent_system as talents
import talent_ux


_PENDING_AWARDS: contextvars.ContextVar[list[dict[str, Any]] | None] = (
    contextvars.ContextVar("talent_v73_pending_awards", default=None)
)

_PROTECTED_WORDS = ("admin", "transfer", "restore", "hero_day", "stake")
_GAME_WORDS = ("coin", "dice", "roulette", "game", "fate", "boss")
_ACTIVITY_WORDS = ("message", "reaction", "voice", "reply", "activity")
_TASK_WORDS = ("task", "mission", "action")


SCRIPT = r"""
<script id="talent-luck-v73-script">
(()=>{
 const wait=setInterval(()=>{
  if(typeof B==='undefined'||!B?.rewards)return;
  clearInterval(wait);
  B.rewards.tab='Удача';
  B.rewards.title='Удача и азарт';
  B.rewards.desc='Увеличивает выигрыши, шанс редких бонусов и помогает избежать проигрыша.';
  B.rewards.bonus='+ удача в играх';
  try{if(typeof tabsRender==='function')tabsRender();if(typeof theme==='function'&&branch==='rewards')theme()}catch(_){}
 },100);
})();
</script>
"""


def _has(reason: str, words: tuple[str, ...]) -> bool:
    value = str(reason or "").casefold()
    return any(word in value for word in words)


async def _tree_percent(
    db: Any,
    chat_id: int,
    user_id: int,
    reason: str,
) -> float:
    """Возвращает применимый процент усиления для конкретного начисления."""
    if _has(reason, _PROTECTED_WORDS):
        return 0.0
    try:
        buffs = await talents.buffs_for(db, chat_id, user_id)
    except Exception:
        return 0.0
    percent = float(buffs.get("influence", 0.0))
    if _has(reason, _ACTIVITY_WORDS):
        percent += float(buffs.get("activity", 0.0))
    if _has(reason, _TASK_WORDS):
        percent += float(buffs.get("tasks", 0.0))
    if _has(reason, _GAME_WORDS):
        percent += float(buffs.get("game_reward", 0.0))
    return max(0.0, percent)


def _points(value: Any) -> int:
    if hasattr(value, "points"):
        return int(value.points)
    return int(value)


def _push_award(item: dict[str, Any]) -> None:
    current = list(_PENDING_AWARDS.get() or [])
    current.append(item)
    _PENDING_AWARDS.set(current)


def _take_awards(user_id: int | None = None) -> list[dict[str, Any]]:
    current = list(_PENDING_AWARDS.get() or [])
    _PENDING_AWARDS.set([])
    if user_id is not None:
        own = [item for item in current if int(item.get("user_id", 0)) == int(user_id)]
        if own:
            return own
    users = {int(item.get("user_id", 0)) for item in current}
    return current if len(users) <= 1 else []


def _format_percent(value: float) -> str:
    number = round(max(0.0, value) * 100, 1)
    return str(int(number)) if number.is_integer() else str(number).replace(".", ",")


def _award_block(items: list[dict[str, Any]]) -> str:
    if not items:
        return ""
    base = sum(max(0, int(item.get("base", 0))) for item in items)
    actual = sum(max(0, int(item.get("actual", 0))) for item in items)
    bonus = max(0, actual - base)
    weighted = sum(
        max(0, int(item.get("base", 0))) * max(0.0, float(item.get("percent", 0.0)))
        for item in items
    )
    percent = weighted / base if base > 0 else 0.0
    deterministic = max(0, int(round(base * percent)))
    special = max(0, bonus - deterministic)

    lines = [
        "🌳 <b>БОНУС ДРЕВА ЗНАНИЙ</b>",
        f"📈 Усиление этого начисления: <b>+{_format_percent(percent)}%</b>",
    ]
    if bonus > 0:
        lines.append(f"➕ Добавлено талантами: <b>+{bonus}</b>")
        if special > 0:
            lines.append(f"✨ Особые таланты и удача: <b>+{special}</b>")
        lines.append(f"🏆 Итог: <b>+{actual}</b> вместо <b>+{base}</b>")
    elif percent > 0:
        lines.append("➕ Процент активен, но эта награда слишком мала для дополнительного целого очка.")
        lines.append(f"🏆 Начислено: <b>+{actual}</b>")
    else:
        lines.append("➕ Усиления для этого типа действия пока не прокачаны.")
        lines.append(f"🏆 Начислено: <b>+{actual}</b>")
    return "\n".join(lines)


def _append_block(text: str, user_id: int | None = None) -> str:
    items = _take_awards(user_id)
    block = _award_block(items)
    if not block or "БОНУС ДРЕВА ЗНАНИЙ" in str(text):
        return str(text)
    result = f"{text}\n\n{block}"
    if len(result) <= 4000:
        return result
    base = sum(max(0, int(item.get("base", 0))) for item in items)
    actual = sum(max(0, int(item.get("actual", 0))) for item in items)
    bonus = max(0, actual - base)
    compact = f"🌳 Древо знаний добавило: <b>+{bonus}</b> · итог <b>+{actual}</b>."
    return f"{text}\n\n{compact}" if len(str(text)) + len(compact) + 2 <= 4090 else str(text)


def _replace_positional(
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
    index: int,
    value: str,
    keyword: str = "text",
) -> tuple[tuple[Any, ...], dict[str, Any]]:
    if keyword in kwargs:
        updated = dict(kwargs)
        updated[keyword] = value
        return args, updated
    values = list(args)
    if len(values) > index:
        values[index] = value
    return tuple(values), kwargs


def install_talent_bonus_display_v73(core: Any) -> None:
    if getattr(core, "_talent_bonus_display_v73_installed", False):
        return
    core._talent_bonus_display_v73_installed = True

    original_add = core.Database.add_points_with_balance

    async def add_points_with_breakdown(self: Any, *args: Any, **kwargs: Any):
        extracted = talents._extract_score_args(args, kwargs)
        result = await original_add(self, *args, **kwargs)
        if extracted is None:
            return result
        chat_id, user_id, base_delta, reason = extracted
        if base_delta <= 0 or _has(reason, _PROTECTED_WORDS):
            return result
        try:
            before, after = result
            actual = _points(after) - _points(before)
            if actual <= 0:
                return result
            percent = await _tree_percent(self, chat_id, user_id, reason)
            _push_award(
                {
                    "chat_id": chat_id,
                    "user_id": user_id,
                    "base": int(base_delta),
                    "actual": int(actual),
                    "percent": percent,
                    "reason": str(reason or ""),
                }
            )
        except Exception:
            # Отображение бонуса никогда не должно мешать самому начислению.
            pass
        return result

    core.Database.add_points_with_balance = add_points_with_breakdown

    original_dispatch = getattr(core, "edit_dispatched_message", None)
    if original_dispatch is not None:
        async def edit_dispatched_message(*args: Any, **kwargs: Any):
            values = list(args)
            message = values[0] if values else kwargs.get("message")
            user_id = getattr(getattr(message, "from_user", None), "id", None)
            if len(values) > 3:
                values[3] = _append_block(str(values[3]), user_id)
            elif "result_text" in kwargs:
                kwargs = dict(kwargs)
                kwargs["result_text"] = _append_block(str(kwargs["result_text"]), user_id)
            return await original_dispatch(*tuple(values), **kwargs)
        core.edit_dispatched_message = edit_dispatched_message

    def wrap_text_method(owner: Any, method_name: str, text_index: int) -> None:
        original = getattr(owner, method_name, None)
        if original is None or getattr(original, "_talent_v73_wrapped", False):
            return

        async def wrapped(self: Any, *args: Any, **kwargs: Any):
            user_id = getattr(getattr(self, "from_user", None), "id", None)
            if "text" in kwargs:
                text = str(kwargs["text"])
            elif len(args) > text_index:
                text = str(args[text_index])
            else:
                return await original(self, *args, **kwargs)
            enriched = _append_block(text, user_id)
            new_args, new_kwargs = _replace_positional(
                args, kwargs, text_index, enriched, "text"
            )
            return await original(self, *new_args, **new_kwargs)

        wrapped._talent_v73_wrapped = True
        setattr(owner, method_name, wrapped)

    # Покрывает inline-карточки, результаты Шара судьбы, callback-игры,
    # обычные ответы команд и прямые сообщения бота.
    wrap_text_method(core.Message, "answer", 0)
    wrap_text_method(core.Message, "edit_text", 0)
    wrap_text_method(core.Bot, "send_message", 1)
    wrap_text_method(core.Bot, "edit_message_text", 0)

    talent_ux.SCRIPT += SCRIPT
