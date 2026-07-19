from __future__ import annotations

import time
from typing import Any

import talent_optimizer_v69 as optimizer_v69
import talent_optimizer_v70 as optimizer_v70
import talent_system as talents
import talent_ux


FAST_CACHE: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}
FAST_CACHE_TTL = 120
MAX_FAST_CACHE = 128


SCRIPT = r"""
<script id="talent-optimizer-v71-script">
(()=>{
 const wait=setInterval(()=>{
  if(typeof state!=='undefined'&&state?.optimizer_runtime_version===71){
   clearInterval(wait);bootV71();
  }
 },100);
 function bootV71(){
  const oldApi=api;
  api=async function(path,body){
   let timeout;
   try{
    return await Promise.race([
     oldApi(path,body),
     new Promise((_,reject)=>{
      timeout=setTimeout(()=>reject(new Error('Сервер не успел ответить. Кнопка разблокирована — попробуй ещё раз.')),8000);
     })
    ]);
   }finally{clearTimeout(timeout)}
  };
 }
})();
</script>
"""


def _trim_cache() -> None:
    if len(FAST_CACHE) <= MAX_FAST_CACHE:
        return
    oldest = sorted(FAST_CACHE.items(), key=lambda item: item[1][0])
    for key, _ in oldest[: len(FAST_CACHE) - MAX_FAST_CACHE]:
        FAST_CACHE.pop(key, None)


async def _fast_personal(
    db: Any,
    chat_id: int,
    user_id: int,
    levels: dict[str, int],
    profile: dict[str, Any],
    focus: str | None,
) -> list[dict[str, Any]]:
    stats = await optimizer_v69._stats(db, chat_id, user_id)
    key = (
        chat_id,
        user_id,
        int(profile.get("total", 0)),
        int(profile.get("available", 0)),
        tuple(sorted((skill, int(level)) for skill, level in levels.items() if int(level) > 0)),
        focus or "",
        stats["signature"],
    )
    cached = FAST_CACHE.get(key)
    now = time.monotonic()
    if cached and now - cached[0] < FAST_CACHE_TTL:
        return cached[1]

    # Ограниченный персональный расчёт выполняется синхронно и занимает только
    # несколько десятков сравнений. Никаких фоновых CPU-задач здесь нет.
    builds = optimizer_v70._quick_calculate(levels, profile, focus, stats)
    for build in builds:
        optimizer = build.get("optimizer")
        if isinstance(optimizer, dict):
            optimizer["pending"] = False
            optimizer["confidence_title"] = str(optimizer.get("confidence_title") or "Персональный расчёт")
        absolute = build.get("absolute")
        if isinstance(absolute, dict):
            note = str(absolute.get("note") or "")
            absolute["note"] = note.replace("Предварительно ", "")
        build["description"] = "Персональный маршрут, рассчитанный без тяжёлой фоновой нагрузки."

    FAST_CACHE[key] = (now, builds)
    _trim_cache()
    return builds


def install_talent_optimizer_v71(core: Any) -> None:
    if getattr(talents, "_talent_optimizer_v71_installed", False):
        return
    talents._talent_optimizer_v71_installed = True

    # Reality 69 ищет функцию оптимизации через глобальное имя. Заменяем её
    # быстрым вариантом, поэтому session/upgrade больше не создают полный перебор.
    optimizer_v69._optimized = _fast_personal

    # На случай установки без полного перезапуска отменяем ранее созданные задачи.
    for task in list(optimizer_v70.EXACT_TASKS.values()):
        if not task.done():
            task.cancel()
    optimizer_v70.EXACT_TASKS.clear()
    optimizer_v70.EXACT_CACHE.clear()

    original_state = talents.talent_state

    async def state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_state(db, chat_id, user_id)
        # Значение 69 оставлено для уже установленного интерфейса персональных
        # карточек. Отдельное поле показывает фактический рабочий слой.
        data["optimizer_version"] = 69
        data["optimizer_runtime_version"] = 71
        data["optimizer_pending"] = False
        data["optimizer_method"] = "fast_personal_no_background"
        return data

    talents.talent_state = state
    talent_ux.SCRIPT += SCRIPT
