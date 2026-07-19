from __future__ import annotations

import asyncio
import time
from typing import Any

import talent_optimizer_v69 as optimizer_v69
import talent_system as talents
import talent_ux


EXACT_CACHE: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}
EXACT_TASKS: dict[tuple[Any, ...], asyncio.Task[None]] = {}
EXACT_CACHE_TTL = 15 * 60
MAX_CACHE_ENTRIES = 96
_EXACT_SEMAPHORE: asyncio.Semaphore | None = None


STYLE = r"""
<style id="talent-optimizer-v70-style">
.v70-pending{margin:7px 0;padding:8px 9px;border:1px solid #c28aff42;border-radius:12px;background:#8d45c918;color:#d7c2e7;font-size:8px;line-height:1.4}
.v70-pending b{color:#efdfff}.v70-ready{color:#77ffc1!important}
</style>
"""


SCRIPT = r"""
<script id="talent-optimizer-v70-script">
(()=>{
 const wait=setInterval(()=>{
  if(typeof state!=='undefined'&&state?.optimizer_version===70){
   clearInterval(wait);bootV70();
  }
 },120);
 let timer=0,attempts=0,refreshing=false;
 const hasPending=()=>Boolean(state?.optimizer_pending||(state?.recommended_builds||[]).some(b=>b?.optimizer?.pending));
 function bootV70(){
  const oldApi=api;
  api=async function(path,body){
   let timeout;
   try{
    return await Promise.race([
     oldApi(path,body),
     new Promise((_,reject)=>{
      timeout=setTimeout(()=>reject(new Error('Сервер слишком долго отвечает. Попробуй ещё раз через несколько секунд.')),15000);
     })
    ]);
   }finally{clearTimeout(timeout)}
  };
  new MutationObserver(patchV70).observe(document.body,{childList:true,subtree:true});
  patchV70();scheduleRefresh();
 }
 function patchV70(){
  document.querySelectorAll('.v69-box').forEach(box=>{
   const card=box.closest('.v66-card'),button=card?.querySelector('[data-build]');
   if(!button)return;
   const build=(state.recommended_builds||[]).find(x=>x.key===button.dataset.build);
   let note=box.querySelector('.v70-pending');
   if(build?.optimizer?.pending){
    if(!note){note=document.createElement('div');note.className='v70-pending';box.appendChild(note)}
    note.innerHTML='<b>Точный перебор выполняется в фоне.</b><br>Древо уже работает. Предварительный персональный маршрут обновится автоматически.';
   }else if(note){
    note.className='v70-pending v70-ready';
    note.textContent='✓ Точный персональный расчёт завершён.';
    setTimeout(()=>note?.remove(),1800);
   }
  });
 }
 function scheduleRefresh(){
  clearTimeout(timer);
  if(!hasPending()||attempts>=30)return;
  timer=setTimeout(refreshExact,1000);
 }
 async function refreshExact(){
  if(refreshing||!hasPending())return;
  refreshing=true;attempts++;
  try{
   const next=await api('session',{});
   state=next;
   tree();
   patchV70();
   if(!hasPending()){
    try{toastShow('Точный расчёт сборок готов')}catch(_){}
   }
  }catch(_){}
  finally{
   refreshing=false;
   scheduleRefresh();
  }
 }
})();
</script>
"""


def _cache_key(
    chat_id: int,
    user_id: int,
    levels: dict[str, int],
    profile: dict[str, Any],
    focus: str | None,
    stats: dict[str, Any],
) -> tuple[Any, ...]:
    return (
        chat_id,
        user_id,
        int(profile.get("total", 0)),
        int(profile.get("available", 0)),
        tuple(sorted((key, int(value)) for key, value in levels.items() if int(value) > 0)),
        focus or "",
        stats["signature"],
    )


def _focused(branch: str, focus: str | None, spent: int, reset: bool) -> bool:
    if reset:
        return spent >= optimizer_v69.focus_v66.FOCUS_REQUIRED_SPENT
    return branch == focus


def _greedy_target(
    branch: str,
    levels: dict[str, int],
    stats: dict[str, Any],
    budget: int,
    *,
    reset: bool,
    focus: str | None,
) -> tuple[dict[str, int], float, int, list[dict[str, int]], int]:
    ids = optimizer_v69._ids(branch)
    current = {key: 0 if reset else int(levels.get(key, 0)) for key in ids}
    base = {} if reset else levels
    spent = 0 if reset else optimizer_v69._cost(current, ids)
    remaining = max(0, int(budget))
    finals = set(optimizer_v69.talent_mastery.EXCLUSIVE_GROUPS.get(branch, ()))
    plan: list[dict[str, int]] = []
    checked = 0

    while remaining > 0:
        chosen_final = next((key for key in finals if current.get(key, 0) > 0), None)
        before = optimizer_v69._score(
            branch,
            optimizer_v69._replace(base, branch, current),
            stats,
            _focused(branch, focus, spent, reset),
        )
        options: list[tuple[float, float, str, int]] = []
        for key in ids:
            spec = talents.SKILLS[key]
            cost = int(spec.get("cost", 1))
            if cost > remaining or current[key] >= int(spec.get("max", 1)):
                continue
            if any(parent in current and current[parent] <= 0 for parent in optimizer_v69._parents(key)):
                continue
            if key in finals and current[key] == 0 and chosen_final and chosen_final != key:
                continue
            trial = dict(current)
            trial[key] += 1
            trial_spent = spent + cost
            after = optimizer_v69._score(
                branch,
                optimizer_v69._replace(base, branch, trial),
                stats,
                _focused(branch, focus, trial_spent, reset),
            )
            gain = after - before
            checked += 1
            options.append((gain / max(1, cost), gain, key, cost))
        if not options:
            break
        efficiency, gain, key, cost = max(
            options,
            key=lambda item: (item[0], item[1], -item[3], item[2]),
        )
        if gain <= 1e-9:
            break
        current[key] += 1
        spent += cost
        remaining -= cost
        plan.append({"id": key, "level": current[key]})

    score = optimizer_v69._score(
        branch,
        optimizer_v69._replace(base, branch, current),
        stats,
        _focused(branch, focus, spent, reset),
    )
    return current, score, spent, plan, checked


def _quick_calculate(
    levels: dict[str, int],
    profile: dict[str, Any],
    focus: str | None,
    stats: dict[str, Any],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    total = int(profile.get("total", 0))
    available = int(profile.get("available", 0))

    for branch, (emoji, title, unit) in optimizer_v69.BRANCH_INFO.items():
        current_score = optimizer_v69._score(branch, levels, stats, branch == focus)
        target, score, spent, plan, checked = _greedy_target(
            branch,
            levels,
            stats,
            available,
            reset=False,
            focus=focus,
        )
        next_step = plan[0] if plan else None
        absolute, absolute_score, absolute_spent, absolute_plan, absolute_checked = _greedy_target(
            branch,
            {},
            stats,
            total,
            reset=True,
            focus=None,
        )
        confidence, confidence_title = stats[branch]["confidence"]
        route = optimizer_v69._route(plan)
        absolute_route = optimizer_v69._route(absolute_plan)

        result.append(
            {
                "key": f"optimizer_{branch}",
                "emoji": emoji,
                "title": title,
                "description": "Предварительный персональный маршрут. Точный перебор выполняется в фоне.",
                "branch": branch,
                "side": "dynamic",
                "side_title": "ПЕРСОНАЛЬНЫЙ РАСЧЁТ",
                "route": route,
                "skills": [key for key, value in target.items() if value > 0],
                "plan": plan,
                "optimizer": {
                    "score": round(score, 2),
                    "current_score": round(current_score, 2),
                    "gain": round(score - current_score, 2),
                    "spent_extra": max(
                        0,
                        spent - optimizer_v69._cost(levels, optimizer_v69._ids(branch)),
                    ),
                    "unit": unit,
                    "route": route,
                    "next_id": next_step["id"] if next_step else None,
                    "next_name": talents.SKILLS.get(next_step["id"], {}).get("name")
                    if next_step
                    else None,
                    "next_level": next_step["level"] if next_step else None,
                    "reason": optimizer_v69._why(branch, stats),
                    "confidence": confidence,
                    "confidence_title": confidence_title,
                    "sample": stats[branch]["sample"],
                    "checked": checked,
                    "pending": True,
                },
                "absolute": {
                    "score": round(absolute_score, 2),
                    "route": absolute_route,
                    "plan": absolute_plan,
                    "levels": absolute,
                    "checked": absolute_checked,
                    "note": (
                        f"Предварительно использует {absolute_spent}/{total} очков. "
                        "Точный максимум пересчитывается в фоне."
                    ),
                },
            }
        )
    return result


def _mark_ready(builds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for build in builds:
        optimizer = build.get("optimizer")
        if isinstance(optimizer, dict):
            optimizer["pending"] = False
    return builds


def _trim_cache() -> None:
    if len(EXACT_CACHE) <= MAX_CACHE_ENTRIES:
        return
    oldest = sorted(EXACT_CACHE.items(), key=lambda item: item[1][0])
    for key, _ in oldest[: len(EXACT_CACHE) - MAX_CACHE_ENTRIES]:
        EXACT_CACHE.pop(key, None)


async def _exact_worker(
    key: tuple[Any, ...],
    levels: dict[str, int],
    profile: dict[str, Any],
    focus: str | None,
    stats: dict[str, Any],
) -> None:
    global _EXACT_SEMAPHORE
    if _EXACT_SEMAPHORE is None:
        _EXACT_SEMAPHORE = asyncio.Semaphore(1)
    try:
        async with _EXACT_SEMAPHORE:
            builds = await asyncio.to_thread(
                optimizer_v69._calculate,
                dict(levels),
                dict(profile),
                focus,
                stats,
            )
        EXACT_CACHE[key] = (time.monotonic(), _mark_ready(builds))
        _trim_cache()
    except Exception:
        # Быстрый персональный маршрут уже возвращён, поэтому ошибка фонового
        # уточнения не должна ломать загрузку дерева или прокачку.
        pass
    finally:
        EXACT_TASKS.pop(key, None)


async def _optimized_nonblocking(
    db: Any,
    chat_id: int,
    user_id: int,
    levels: dict[str, int],
    profile: dict[str, Any],
    focus: str | None,
) -> list[dict[str, Any]]:
    stats = await optimizer_v69._stats(db, chat_id, user_id)
    key = _cache_key(chat_id, user_id, levels, profile, focus, stats)
    cached = EXACT_CACHE.get(key)
    if cached and time.monotonic() - cached[0] < EXACT_CACHE_TTL:
        return cached[1]

    task = EXACT_TASKS.get(key)
    if task is None or task.done():
        EXACT_TASKS[key] = asyncio.create_task(
            _exact_worker(key, dict(levels), dict(profile), focus, stats)
        )
    return _quick_calculate(levels, profile, focus, stats)


def install_talent_optimizer_v70(core: Any) -> None:
    if getattr(talents, "_talent_optimizer_v70_installed", False):
        return
    talents._talent_optimizer_v70_installed = True

    # Reality 69 обращается к этой функции через глобальное имя, поэтому
    # подмена убирает тяжёлый перебор из запросов session/upgrade.
    optimizer_v69._optimized = _optimized_nonblocking

    original_state = talents.talent_state

    async def state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_state(db, chat_id, user_id)
        builds = list(data.get("recommended_builds") or [])
        data["optimizer_version"] = 70
        data["optimizer_pending"] = any(
            bool((build.get("optimizer") or {}).get("pending"))
            for build in builds
        )
        data["optimizer_method"] = (
            "nonblocking_exact_background"
            if data["optimizer_pending"]
            else "exhaustive_personal_expected_value"
        )
        return data

    talents.talent_state = state
    talent_ux.STYLE += STYLE
    talent_ux.SCRIPT += SCRIPT
