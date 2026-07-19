from __future__ import annotations

import asyncio, math, time
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

import talent_improvements_v66 as focus_v66
import talent_mastery
import talent_system as talents
import talent_ux

BRANCH_INFO = {
    "damage": ("⚔️", "Оптимум урона", "урона за рейд"),
    "influence": ("👑", "Оптимум влияния", "влияния за неделю"),
    "defense": ("🛡️", "Оптимум защиты", "сохранённого влияния за неделю"),
    "rewards": ("🎲", "Оптимум наград", "чистого влияния за неделю"),
}
CACHE: dict[tuple[Any, ...], tuple[float, list[dict[str, Any]]]] = {}

STYLE = r"""
<style id="talent-optimizer-v69-style">
.v67-side.dynamic{color:#d4b6ff;border-color:#b875ff55;background:#8f45cf18}.v69-box{margin:8px 0;padding:9px;border:1px solid #ffffff12;border-radius:14px;background:linear-gradient(145deg,#171022,#0b0712)}.v69-row{display:grid;grid-template-columns:1fr auto;gap:7px;padding:6px 0;border-bottom:1px solid #ffffff0b}.v69-row:last-child{border:0}.v69-row small{display:block;color:#94899f;font-size:7px}.v69-row b{font-size:9px}.v69-row strong{color:#7fffc1;font-size:10px;text-align:right}.v69-reset strong{color:#ffd079}.v69-next{margin:7px 0;padding:7px;border:1px solid #65ffb23b;border-radius:11px;background:#1537296b;color:#9affce;font-size:8px}.v69-why{color:#b7acbf;font-size:8px;line-height:1.45}.v69-confidence{display:inline-flex;margin-top:7px;padding:3px 7px;border-radius:99px;border:1px solid #ffffff14;font-size:7px;font-weight:950}.v69-confidence.high{color:#74ffc0;border-color:#65ffb244}.v69-confidence.medium{color:#ffd77c;border-color:#ffd36d44}.v69-confidence.low{color:#ff9aa8;border-color:#ff748844}.v69-note{margin:0 0 10px;padding:9px;border:1px solid #b56dff31;border-radius:13px;background:#8d45c914;color:#c9b9d5;font-size:9px;line-height:1.45}@media(max-width:390px){.v69-row{grid-template-columns:1fr}.v69-row strong{text-align:left}}
</style>
"""
SCRIPT = r"""
<script id="talent-optimizer-v69-script">
(()=>{const wait=setInterval(()=>{if(typeof state!=='undefined'&&state?.optimizer_version===69){clearInterval(wait);boot()}},120);let q=false;const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),num=v=>new Intl.NumberFormat('ru-RU',{maximumFractionDigits:1}).format(Number(v)||0);function boot(){new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});setInterval(schedule,550);schedule()}function schedule(){if(q)return;q=true;requestAnimationFrame(()=>{q=false;patch()})}function patch(){const body=document.getElementById('v66Body'),buttons=[...(body?.querySelectorAll('[data-build]')||[])];if(!buttons.length)return;const title=document.getElementById('v66Title');if(title)title.textContent='🧠 Персональные сборки';const note=body.querySelector('.v66-note');if(note&&!note.dataset.v69){note.dataset.v69='1';note.innerHTML='<b>Серверный оптимизатор.</b><br>Он перебирает все допустимые варианты с учётом твоих очков, прокачки, блокировок и личной статистики.'}if(!body.querySelector('.v69-note')){const n=document.createElement('div');n.className='v69-note';n.innerHTML='«Без сброса» — лучшее продолжение текущего дерева. «После сброса» — абсолютный максимум при новом распределении всех очков.';note?.insertAdjacentElement('afterend',n)}buttons.forEach(btn=>{const b=(state.recommended_builds||[]).find(x=>x.key===btn.dataset.build),card=btn.closest('.v66-card');if(!b?.optimizer||!card)return;const o=b.optimizer,a=b.absolute||{},sig=[o.score,o.gain,o.next_id,a.score,a.route,o.confidence].join('|');if(card.dataset.v69===sig)return;card.dataset.v69=sig;card.querySelector('.v69-box')?.remove();const box=document.createElement('div');box.className='v69-box';const next=o.next_name?`${esc(o.next_name)} · уровень ${o.next_level}`:'Все выгодные улучшения уже получены';box.innerHTML=`<div class="v69-row"><div><small>ЛУЧШЕЕ БЕЗ СБРОСА</small><b>${esc(o.route)}</b></div><strong>${num(o.score)} ${esc(o.unit)}</strong></div><div class="v69-row"><div><small>ПРИРОСТ</small><b>${o.spent_extra?`Потратить ${o.spent_extra} очк.`:'Очки не требуются'}</b></div><strong>+${num(Math.max(0,o.gain))}</strong></div><div class="v69-next">✨ Следующий шаг: <b>${next}</b></div><div class="v69-row v69-reset"><div><small>МАКСИМУМ ПОСЛЕ СБРОСА</small><b>${esc(a.route)}</b><br><small>${esc(a.note)}</small></div><strong>${num(a.score)} ${esc(o.unit)}</strong></div><div class="v69-why"><b>Почему:</b> ${esc(o.reason)}</div><span class="v69-confidence ${esc(o.confidence)}">${esc(o.confidence_title)} · ${esc(o.sample)}</span>`;btn.insertAdjacentElement('beforebegin',box);const small=card.querySelector(':scope > small');if(small)small.textContent=`Проверено вариантов: ${o.checked}`;btn.textContent=localStorage.getItem('talentRecommendedBuild')===b.key?'ВЫБРАНО · ПОКАЗАТЬ':'ПОКАЗАТЬ МОЙ МАРШРУТ'})}})();
</script>
"""

def _ids(branch: str) -> tuple[str, ...]:
    return tuple(sorted((k for k,v in talents.SKILLS.items() if v.get("branch")==branch),key=lambda x:int("".join(filter(str.isdigit,x)) or 0)))

def _parents(skill: str) -> tuple[str, ...]:
    s=talents.SKILLS[skill]; raw=s.get("parents")
    return tuple(map(str,raw)) if raw else ((str(s["parent"]),) if s.get("parent") else ())

def _cost(levels: dict[str,int], ids: tuple[str,...]|None=None) -> int:
    allowed=set(ids) if ids else None
    return sum(int(v)*int(talents.SKILLS.get(k,{}).get("cost",1)) for k,v in levels.items() if int(v)>0 and (allowed is None or k in allowed))

@lru_cache(maxsize=8)
def _configs(branch: str) -> tuple[tuple[tuple[int,...],int],...]:
    ids=_ids(branch); pos={k:i for i,k in enumerate(ids)}; finals=set(talent_mastery.EXCLUSIVE_GROUPS.get(branch,())); start=(0,)*len(ids); stack=[start]; seen={start}; out=[]
    while stack:
        st=stack.pop(); lv=dict(zip(ids,st)); out.append((st,_cost(lv,ids))); chosen=next((x for x in finals if lv.get(x,0)>0),None)
        for i,k in enumerate(ids):
            spec=talents.SKILLS[k]
            if st[i]>=int(spec.get("max",1)) or any(p in pos and st[pos[p]]<=0 for p in _parents(k)): continue
            if k in finals and st[i]==0 and chosen and chosen!=k: continue
            nxt=list(st); nxt[i]+=1; nt=tuple(nxt)
            if nt not in seen: seen.add(nt); stack.append(nt)
    return tuple(sorted(out,key=lambda x:(x[1],x[0])))

def _replace(base: dict[str,int], branch: str, branch_levels: dict[str,int]) -> dict[str,int]:
    ids=set(_ids(branch)); result={k:int(v) for k,v in base.items() if k not in ids and int(v)>0}; result.update({k:int(v) for k,v in branch_levels.items() if int(v)>0}); return result

def _buffs(levels: dict[str,int], branch: str, focused: bool) -> dict[str,float]:
    b=dict(talents.calculate_buffs(levels))
    if focused:
        for key in focus_v66.FOCUS_INFO.get(branch,{}).get("keys",()): b[key]=float(b.get(key,0))*1.2
    return b

def _clamp(v: float, high: float=.8) -> float: return max(0.,min(high,float(v)))

def _score(branch: str, levels: dict[str,int], stats: dict[str,Any], focused: bool) -> float:
    b=_buffs(levels,branch,focused)
    if branch=="damage":
        s=stats[branch]; hits=max(1.,float(s["hits"])); hit=max(1.,float(s["hit"])); base=hits*hit
        return base*(1+max(0.,b.get("boss_damage",0)))+hits*hit*_clamp(b.get("boss_crit_chance",0),.85)*(.75+max(0.,b.get("boss_crit_power",0)))+(2*hit if b.get("first_hit_x3",0)>0 else 0)
    if branch=="influence":
        s=stats[branch]; result=s["positive"]*(1+max(0.,b.get("influence",0)))+s["activity"]*max(0.,b.get("activity",0))+s["tasks"]*max(0.,b.get("tasks",0)); return result+(s["first"] if b.get("daily_double",0)>0 else 0)
    if branch=="defense":
        s=stats[branch]; normal=float(s["normal"]); conflict=float(s["conflict"]); baseline=normal+conflict
        if b.get("weekly_armor",0)>0:
            armor=min(baseline,float(s["largest"])); take=min(conflict if conflict>=normal else normal,armor)
            if conflict>=normal: conflict-=take; normal=max(0.,normal-(armor-take))
            else: normal-=take; conflict=max(0.,conflict-(armor-take))
        avoid=_clamp(b.get("avoid_penalty",0)); reduction=_clamp(b.get("penalty_reduction",0)); cr=_clamp(reduction+b.get("sabotage_reduction",0)); remain=normal*(1-avoid)*(1-reduction)+conflict*(1-avoid)*(1-cr); return baseline-remain
    s=stats[branch]; reward=s["wins"]*(1+max(0.,b.get("game_reward",0))); reward+=reward*.5*_clamp(b.get("rare_reward",0),.75); second=_clamp(b.get("second_chance",0)); loss=s["losses"]*(1-second)
    if b.get("daily_reroll",0)>0: loss=max(0.,loss-s["first_loss"]*(1-second))
    return reward-loss

def _confidence(n:int,mid:int,high:int)->tuple[str,str]:
    return ("high","Высокая точность") if n>=high else (("medium","Средняя точность") if n>=mid else ("low","Предварительный расчёт"))

async def _stats(db:Any,chat_id:int,user_id:int)->dict[str,Any]:
    conn=talents._conn(db); player=await db.get_player(chat_id,user_id); behavior={}
    try: behavior=dict(await db.get_behavior(chat_id,user_id))
    except Exception: pass
    now=int(time.time()); cur=await conn.execute("SELECT id,delta,reason,created_at FROM score_log WHERE chat_id=? AND user_id=? AND created_at>=? ORDER BY id LIMIT 2500",(chat_id,user_id,now-30*86400)); logs=list(await cur.fetchall())
    cur=await conn.execute("SELECT bf.damage_done,bf.attacks,bf.critical_hits FROM boss_fighters bf JOIN boss_battles bb ON bb.boss_id=bf.boss_id WHERE bb.chat_id=? AND bf.user_id=? ORDER BY bb.created_at DESC LIMIT 8",(chat_id,user_id)); raids=list(await cur.fetchall())
    oldest=int(logs[0]["created_at"]) if logs else now; days=max(7.,min(30.,(now-oldest)/86400 if oldest<now else 7.)); factor=7/days
    game=("coin","dice","roulette","game","fate","boss","duel","stake"); activity=("message","reaction","voice","reply","activity","truth","compliment"); tasks=("task","mission","action_task","secret"); conflicts=("sabotage","impeachment","rebellion","revolt"); protected=("admin","transfer","restore","hero_day")
    pos=act=task=win=normal=conflict=loss=0.; pc=nc=gc=tc=0; first={}; first_loss={}; weekly=defaultdict(float)
    for r in logs:
        d=int(r["delta"]); reason=str(r["reason"] or "").lower()
        if any(x in reason for x in protected): continue
        dt=datetime.fromtimestamp(int(r["created_at"]),timezone.utc); day=dt.strftime("%Y-%m-%d"); week=dt.strftime("%Y-W%W"); isg=any(x in reason for x in game); isa=any(x in reason for x in activity); ist=any(x in reason for x in tasks); isc=any(x in reason for x in conflicts)
        if d>0:
            pos+=d; pc+=1; first.setdefault(day,float(d))
            if isa: act+=d
            if ist: task+=d; tc+=1
            if isg: win+=d; gc+=1
        elif d<0:
            v=float(abs(d)); nc+=1; weekly[week]=max(weekly[week],v); conflict+=v if isc else 0; normal+=0 if isc else v
            if isg: loss+=v; gc+=1; first_loss.setdefault(day,v)
    messages=int(behavior.get("messages",getattr(player,"message_count",0) if player else 0) or 0); units=messages+int(behavior.get("replies_sent",0) or 0)+2*int(behavior.get("voice_messages",0) or 0)+int(behavior.get("reactions_given",0) or 0)+int(behavior.get("reactions_received",0) or 0); fa=max(70.,min(700.,math.sqrt(max(1,units))*24)); ft=max(15.,min(180.,int(behavior.get("positive_actions",0) or 0)*8)); games=max(3.,min(18.,int(behavior.get("inline_uses",0) or 0)/8))
    pweek=pos*factor if pos else fa+ft; aweek=act*factor if act else fa; tweek=task*factor if task else ft; fweek=sum(first.values())*factor if first else max(10.,pweek*.16); wins=win*factor if win else games*14; losses=loss*factor if loss else games*8; fl=sum(first_loss.values())*factor if first_loss else min(losses,games*4); normal=normal*factor; conflict=conflict*factor
    if normal+conflict<=0: normal=max(20.,min(180.,int(behavior.get("negative_actions",0) or 0)*7+25)); conflict=max(5.,min(120.,int(behavior.get("rebellion_supports",0) or 0)*8))
    largest=sum(weekly.values())/max(1,len(weekly)) if weekly else max(15.,(normal+conflict)*.35); attacks=sum(int(r["attacks"] or 0) for r in raids); damage=sum(int(r["damage_done"] or 0) for r in raids); dc=_confidence(attacks,8,25); ic=_confidence(pc,10,40); fc=_confidence(nc,3,10); rc=_confidence(gc,5,15)
    return {"signature":(int(logs[-1]["id"]) if logs else 0,len(raids),attacks,damage,messages),"damage":{"hits":attacks/len(raids) if raids and attacks else 8.,"hit":damage/attacks if attacks and damage else 150.,"confidence":dc,"sample":f"{len(raids)} рейд., {attacks} атак"},"influence":{"positive":pweek,"activity":aweek,"tasks":tweek,"first":fweek,"confidence":ic,"sample":f"{pc} начислений, {messages} сообщений"},"defense":{"normal":normal,"conflict":conflict,"largest":largest,"confidence":fc,"sample":f"{nc} штрафов за {days:.0f} дн."},"rewards":{"wins":wins,"losses":losses,"first_loss":fl,"confidence":rc,"sample":f"{gc} игровых результатов за {days:.0f} дн."}}

def _why(branch:str,s:dict[str,Any])->str:
    if branch=="damage": return f"В среднем у тебя {s[branch]['hits']:.1f} атак за рейд: алгоритм сравнил постоянный урон, криты и ценность первого удара."
    if branch=="influence": return "Алгоритм отдельно взвесил обычную активность, задания, общий множитель и ежедневное удвоение."
    if branch=="defense": return "Алгоритм сравнил обычные штрафы, конфликтные потери, шанс отмены и недельную броню."
    return "Алгоритм сравнил средние выигрыши, проигрыши, редкие бонусы и ежедневную отмену поражения."

def _plan(branch:str,target:dict[str,int],base:dict[str,int],stats:dict[str,Any],focused:bool)->list[dict[str,int]]:
    ids=_ids(branch); current={k:0 for k in ids}; out=[]; finals=set(talent_mastery.EXCLUSIVE_GROUPS.get(branch,()))
    while any(current[k]<target.get(k,0) for k in ids):
        before=_score(branch,_replace(base,branch,current),stats,focused); chosen=next((x for x in finals if current.get(x,0)>0),None); options=[]
        for k in ids:
            if current[k]>=target.get(k,0) or any(p in current and current[p]<=0 for p in _parents(k)): continue
            if k in finals and current[k]==0 and chosen and chosen!=k: continue
            trial=dict(current); trial[k]+=1; gain=(_score(branch,_replace(base,branch,trial),stats,focused)-before)/max(1,int(talents.SKILLS[k].get("cost",1))); options.append((gain,k))
        if not options: break
        k=max(options)[1]; current[k]+=1; out.append({"id":k,"level":current[k]})
    return out

def _route(plan:list[dict[str,int]])->str:
    names=[]
    for x in plan:
        n=str(talents.SKILLS.get(x["id"],{}).get("name",x["id"])); names.append(n) if n not in names else None
    return "Текущая прокачка уже оптимальна" if not names else " → ".join(names[:5])+(f" → ещё {len(names)-5}" if len(names)>5 else "")

def _best(branch:str,current:dict[str,int],stats:dict[str,Any],budget:int,reset:bool,focus:str|None)->tuple[dict[str,int],float,int,int]:
    ids=_ids(branch); cur={k:int(current.get(k,0)) for k in ids}; base={} if reset else current; best={k:0 for k in ids} if reset else dict(cur); best_score=_score(branch,_replace(base,branch,best),stats,False if reset else branch==focus); best_cost=0 if reset else _cost(cur,ids); checked=0; cur_cost=_cost(cur,ids)
    for st,cost in _configs(branch):
        candidate=dict(zip(ids,st))
        if reset:
            if cost>budget: continue
            focused=cost>=focus_v66.FOCUS_REQUIRED_SPENT
        else:
            if any(candidate[k]<cur[k] for k in ids) or cost-cur_cost>budget: continue
            focused=branch==focus
        checked+=1; score=_score(branch,_replace(base,branch,candidate),stats,focused)
        if score>best_score+1e-9 or (abs(score-best_score)<=1e-9 and cost<best_cost): best,best_score,best_cost=candidate,score,cost
    return best,best_score,best_cost,checked

def _calculate(levels:dict[str,int],profile:dict[str,Any],focus:str|None,stats:dict[str,Any])->list[dict[str,Any]]:
    result=[]; total=int(profile.get("total",0)); available=int(profile.get("available",0))
    for branch,(emoji,title,unit) in BRANCH_INFO.items():
        current_score=_score(branch,levels,stats,branch==focus); target,score,cost,checked=_best(branch,levels,stats,available,False,focus); other={k:v for k,v in levels.items() if talents.SKILLS.get(k,{}).get("branch")!=branch}; plan=_plan(branch,target,other,stats,branch==focus); nxt=next((x for x in plan if int(levels.get(x["id"],0))<x["level"]),None); absolute,abs_score,abs_cost,abs_checked=_best(branch,{},stats,total,True,None); abs_plan=_plan(branch,absolute,{},stats,abs_cost>=focus_v66.FOCUS_REQUIRED_SPENT); conf,conf_title=stats[branch]["confidence"]; route=_route(plan); abs_route=_route(abs_plan)
        result.append({"key":f"optimizer_{branch}","emoji":emoji,"title":title,"description":"Персональный маршрут, рассчитанный по твоей статистике.","branch":branch,"side":"dynamic","side_title":"ПЕРСОНАЛЬНЫЙ РАСЧЁТ","route":route,"skills":[k for k,v in target.items() if v>0],"plan":plan,"optimizer":{"score":round(score,2),"current_score":round(current_score,2),"gain":round(score-current_score,2),"spent_extra":max(0,cost-_cost(levels,_ids(branch))),"unit":unit,"route":route,"next_id":nxt["id"] if nxt else None,"next_name":talents.SKILLS.get(nxt["id"],{}).get("name") if nxt else None,"next_level":nxt["level"] if nxt else None,"reason":_why(branch,stats),"confidence":conf,"confidence_title":conf_title,"sample":stats[branch]["sample"],"checked":checked},"absolute":{"score":round(abs_score,2),"route":abs_route,"plan":abs_plan,"levels":absolute,"checked":abs_checked,"note":f"Использует {abs_cost}/{total} очков. Разница с текущим деревом: {abs_score-current_score:+.1f} {unit}."}})
    return result

async def _optimized(db:Any,chat_id:int,user_id:int,levels:dict[str,int],profile:dict[str,Any],focus:str|None)->list[dict[str,Any]]:
    stats=await _stats(db,chat_id,user_id); key=(chat_id,user_id,int(profile.get("total",0)),int(profile.get("available",0)),tuple(sorted((k,int(v)) for k,v in levels.items() if int(v)>0)),focus or "",stats["signature"]); now=time.monotonic(); cached=CACHE.get(key)
    if cached and now-cached[0]<75: return cached[1]
    builds=await asyncio.to_thread(_calculate,levels,profile,focus,stats); CACHE.clear(); CACHE[key]=(now,builds); return builds

def install_talent_optimizer_v69(core:Any)->None:
    if getattr(talents,"_talent_optimizer_v69_installed",False): return
    talents._talent_optimizer_v69_installed=True; original=talents.talent_state
    async def state(db:Any,chat_id:int,user_id:int)->dict[str,Any]:
        data=await original(db,chat_id,user_id); levels={str(k):int(v) for k,v in (data.get("levels") or {}).items()}; profile=dict(data.get("points") or {}); focus=str((data.get("focus") or {}).get("current") or "") or None; data["recommended_builds"]=await _optimized(db,chat_id,user_id,levels,profile,focus); data["optimizer_version"]=69; data["optimizer_method"]="exhaustive_personal_expected_value"; return data
    talents.talent_state=state; talent_ux.STYLE+=STYLE; talent_ux.SCRIPT+=SCRIPT
