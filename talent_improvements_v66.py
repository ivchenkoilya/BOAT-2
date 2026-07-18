from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import talent_mastery
import talent_system as talents
import talent_ux


FOCUS_COOLDOWN = 7 * 24 * 60 * 60
FOCUS_REQUIRED_SPENT = 5
WEEKLY_TREE_CAP = 12
RESET_PRICE = 250

FOCUS_INFO: dict[str, dict[str, Any]] = {
    "damage": {
        "emoji": "⚔️",
        "title": "Разрушитель эго",
        "description": "На 20% усиливает процентные эффекты ветки урона.",
        "keys": ("boss_damage", "boss_crit_chance", "boss_crit_power"),
    },
    "influence": {
        "emoji": "👑",
        "title": "Кумир публики",
        "description": "На 20% усиливает процентные эффекты ветки влияния.",
        "keys": ("influence", "activity", "tasks"),
    },
    "defense": {
        "emoji": "🛡️",
        "title": "Несокрушимый",
        "description": "На 20% усиливает процентные эффекты ветки защиты.",
        "keys": ("penalty_reduction", "avoid_penalty", "sabotage_reduction"),
    },
    "rewards": {
        "emoji": "🍀",
        "title": "Любимчик судьбы",
        "description": "На 20% усиливает процентные эффекты ветки наград.",
        "keys": ("game_reward", "rare_reward", "second_chance"),
    },
}

COSMETICS: dict[str, dict[str, str]] = {
    "damage": {
        "emoji": "🔥",
        "title": "Разрушитель эго",
        "reward": "Багровая рамка и эффект сокрушительного удара",
    },
    "influence": {
        "emoji": "🌟",
        "title": "Икона реальности",
        "reward": "Золотая рамка и сияющая аура профиля",
    },
    "defense": {
        "emoji": "🪽",
        "title": "Неуязвимый образ",
        "reward": "Ледяная рамка и эффект сюжетной брони",
    },
    "rewards": {
        "emoji": "💎",
        "title": "Фаворит судьбы",
        "reward": "Фиолетовая рамка и частицы удачи",
    },
}

RECOMMENDED_BUILDS: list[dict[str, Any]] = [
    {
        "key": "boss_hunter",
        "emoji": "⚔️",
        "title": "Боссоборец",
        "description": "Урон, шанс крита и мощный первый удар.",
        "branch": "damage",
        "skills": ["damage1", "damage2", "damage3", "damage4"],
    },
    {
        "key": "fast_growth",
        "emoji": "👑",
        "title": "Быстрый рост",
        "description": "Больше влияния за активность, задания и ежедневные награды.",
        "branch": "influence",
        "skills": ["influence1", "influence2", "influence3", "influence4"],
    },
    {
        "key": "invulnerable",
        "emoji": "🛡️",
        "title": "Неуязвимый",
        "description": "Снижение штрафов, отмена потерь и защита от конфликтов.",
        "branch": "defense",
        "skills": ["defense1", "defense2", "defense3", "defense4"],
    },
    {
        "key": "lucky_hero",
        "emoji": "🎲",
        "title": "Азартный герой",
        "description": "Усиленные игровые награды, редкая добыча и второй шанс.",
        "branch": "rewards",
        "skills": ["rewards1", "rewards2", "rewards3", "rewards4"],
    },
]

BUFF_NAMES = {
    "boss_damage": "Урон по боссу",
    "boss_crit_chance": "Шанс крита",
    "boss_crit_power": "Сила крита",
    "first_hit_x3": "Первый удар ×3",
    "influence": "Получаемое влияние",
    "activity": "Награды активности",
    "tasks": "Награды заданий",
    "daily_double": "Ежедневное удвоение",
    "penalty_reduction": "Снижение штрафов",
    "avoid_penalty": "Шанс отменить штраф",
    "sabotage_reduction": "Защита от конфликтов",
    "weekly_armor": "Сюжетная броня",
    "game_reward": "Награды мини-игр",
    "rare_reward": "Шанс редкой награды",
    "second_chance": "Второй шанс",
    "daily_reroll": "Переписать судьбу",
    "combo_double": "Каждый пятый удар ×2",
    "crit_break_shield": "Крит ломает щит босса",
    "loss_pity": "Упрямство судьбы",
}


def _week_key() -> str:
    iso = datetime.now(timezone.utc).date().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


async def _focus_row(db: Any, chat_id: int, user_id: int):
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT branch,changed_at FROM talent_focus_v66 WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    return await cursor.fetchone()


async def focus_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
    profile = await talents.sync_profile(db, chat_id, user_id)
    row = await _focus_row(db, chat_id, user_id)
    now = int(time.time())
    current = str(row["branch"]) if row else ""
    changed_at = int(row["changed_at"]) if row else 0
    return {
        "current": current or None,
        "current_title": FOCUS_INFO.get(current, {}).get("title") if current else None,
        "eligible": int(profile["spent"]) >= FOCUS_REQUIRED_SPENT,
        "required_spent": FOCUS_REQUIRED_SPENT,
        "spent": int(profile["spent"]),
        "ready_in": max(0, changed_at + FOCUS_COOLDOWN - now) if current else 0,
        "choices": [
            {"key": key, **value, "selected": key == current}
            for key, value in FOCUS_INFO.items()
        ],
    }


async def set_focus(db: Any, chat_id: int, user_id: int, branch: str) -> dict[str, Any]:
    if branch not in FOCUS_INFO:
        raise ValueError("Неизвестная специализация.")
    profile = await talents.sync_profile(db, chat_id, user_id)
    if int(profile["spent"]) < FOCUS_REQUIRED_SPENT:
        raise ValueError(
            f"Сначала вложи минимум {FOCUS_REQUIRED_SPENT} очков в древо."
        )
    row = await _focus_row(db, chat_id, user_id)
    now = int(time.time())
    if row is not None:
        current = str(row["branch"])
        if current == branch:
            return await talents.talent_state(db, chat_id, user_id)
        ready_at = int(row["changed_at"]) + FOCUS_COOLDOWN
        if ready_at > now:
            seconds = ready_at - now
            days = max(1, (seconds + 86399) // 86400)
            raise ValueError(f"Сменить специализацию можно через {days} дн.")
    conn = talents._conn(db)
    async with db.lock:
        await conn.execute(
            """
            INSERT INTO talent_focus_v66(chat_id,user_id,branch,changed_at)
            VALUES(?,?,?,?)
            ON CONFLICT(chat_id,user_id) DO UPDATE SET
              branch=excluded.branch,changed_at=excluded.changed_at
            """,
            (chat_id, user_id, branch, now),
        )
        await conn.commit()
    return await talents.talent_state(db, chat_id, user_id)


async def _sync_cosmetics(
    db: Any,
    chat_id: int,
    user_id: int,
    levels: dict[str, int],
) -> list[str]:
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT branch FROM talent_cosmetics_v66 WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    existing = {str(row["branch"]) for row in await cursor.fetchall()}
    unlocked: list[str] = []
    now = int(time.time())
    for branch, final_ids in talent_mastery.EXCLUSIVE_GROUPS.items():
        completed = any(
            int(levels.get(skill_id, 0))
            >= int(talents.SKILLS.get(skill_id, {}).get("max", 1))
            for skill_id in final_ids
        )
        if completed and branch not in existing:
            unlocked.append(branch)
    if unlocked:
        async with db.lock:
            for branch in unlocked:
                await conn.execute(
                    """
                    INSERT OR IGNORE INTO talent_cosmetics_v66(
                        chat_id,user_id,branch,unlocked_at
                    ) VALUES(?,?,?,?)
                    """,
                    (chat_id, user_id, branch, now),
                )
            await conn.commit()
    return unlocked


async def _cosmetics_state(db: Any, chat_id: int, user_id: int) -> list[dict[str, Any]]:
    conn = talents._conn(db)
    cursor = await conn.execute(
        "SELECT branch,unlocked_at FROM talent_cosmetics_v66 WHERE chat_id=? AND user_id=?",
        (chat_id, user_id),
    )
    unlocked = {
        str(row["branch"]): int(row["unlocked_at"])
        for row in await cursor.fetchall()
    }
    return [
        {
            "branch": branch,
            **spec,
            "unlocked": branch in unlocked,
            "unlocked_at": unlocked.get(branch, 0),
        }
        for branch, spec in COSMETICS.items()
    ]


STYLE = r"""
<style id="talent-reality-v66-style">
.v66-progress{position:relative;z-index:19;margin:0 9px 8px;padding:9px 10px;border-radius:17px;border:1px solid #ffffff14;background:linear-gradient(105deg,rgba(var(--rgb),.12),#100b1dde);display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center}.v66-progress small{display:block;color:#aa9fb8;font-size:8px;font-weight:900;letter-spacing:.45px}.v66-progress b{display:block;margin-top:2px;font-size:11px}.v66-track{height:6px;margin-top:6px;border-radius:99px;background:#090610;overflow:hidden}.v66-track i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--c),var(--c2));box-shadow:0 0 12px rgba(var(--rgb),.55);transition:.45s}.v66-quick{display:flex;gap:5px}.v66-quick button{min-width:45px;height:38px;border:1px solid #ffffff14;border-radius:12px;background:#1b122a;color:white;font-size:7px;font-weight:950}.v66-quick button span{display:block;font-size:15px;line-height:15px;margin-bottom:2px}
.v66-overlay{position:fixed;inset:0;z-index:240;display:none;align-items:flex-end;padding:12px;background:#030207ce;backdrop-filter:blur(13px)}.v66-overlay.show{display:flex}.v66-panel{width:min(100%,620px);max-height:89vh;overflow:auto;margin:0 auto;border:1px solid #ffffff20;border-radius:27px 27px 18px 18px;background:radial-gradient(circle at 50% -8%,rgba(var(--rgb),.28),transparent 34%),linear-gradient(#281b41,#0c0816);box-shadow:0 30px 95px #000d;color:#fff}.v66-head{position:sticky;top:0;z-index:3;display:flex;align-items:center;gap:8px;padding:14px 15px;background:#211534eb;border-bottom:1px solid #ffffff12;backdrop-filter:blur(14px)}.v66-head h2{flex:1;margin:0;font-size:18px}.v66-close{width:38px;height:38px;border:1px solid #ffffff18;border-radius:13px;background:#110b1d;color:white;font-size:18px}.v66-body{padding:13px}.v66-note{padding:10px 11px;margin-bottom:10px;border:1px solid #ffffff11;border-radius:14px;background:#ffffff08;color:#bfb4c9;font-size:10px;line-height:1.45}.v66-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.v66-card{padding:11px;border:1px solid #ffffff13;border-radius:17px;background:linear-gradient(145deg,#20152f,#0e0918)}.v66-card.active{border-color:rgba(var(--rgb),.55);box-shadow:0 0 23px rgba(var(--rgb),.16)}.v66-card h3{margin:0 0 5px;font-size:12px}.v66-card p{margin:4px 0;color:#b8adbf;font-size:9px;line-height:1.4}.v66-card small{color:#988ca3;font-size:8px}.v66-card button{width:100%;min-height:35px;margin-top:8px;border:0;border-radius:11px;background:linear-gradient(135deg,var(--c),var(--c2));color:white;font-size:9px;font-weight:950}.v66-card button:disabled{opacity:.38}.v66-buff{display:flex;align-items:center;gap:9px;padding:9px 10px;margin:6px 0;border:1px solid #ffffff10;border-radius:14px;background:#120c1e}.v66-buff span{font-size:20px}.v66-buff div{flex:1}.v66-buff b{display:block;font-size:10px}.v66-buff small{display:block;margin-top:3px;color:#9e92aa;font-size:8px}.v66-buff strong{color:var(--c);font-size:12px}.v66-section{margin:14px 0 7px;color:var(--c);font-size:9px;font-weight:950;letter-spacing:.7px;text-transform:uppercase}.v66-cosmetic{opacity:.42}.v66-cosmetic.unlocked{opacity:1;border-color:#ffd36d55}.v66-change{display:grid;grid-template-columns:1fr auto 1fr;gap:7px;align-items:center;margin-top:9px;padding:9px;border:1px solid rgba(var(--rgb),.2);border-radius:14px;background:rgba(var(--rgb),.075)}.v66-change>div{text-align:center}.v66-change small{display:block;color:#9f93aa;font-size:7px;letter-spacing:.5px}.v66-change b{display:block;margin-top:3px;font-size:10px}.v66-change>strong{color:var(--c);font-size:15px}.v66-legend{margin-top:8px;padding:8px 9px;border:1px solid #ffd36d45;border-radius:12px;background:#ffd36d0d;color:#ffe39a;font-size:9px;line-height:1.35}.nodewrap.recommended .node{border-color:#65ffb2!important;box-shadow:0 0 0 3px #65ffb225,0 0 35px #65ffb25c!important;animation:v66recommend 1.35s ease-in-out infinite!important}.nodewrap.recommended:after{content:"СЛЕДУЮЩИЙ";position:absolute;left:50%;top:-17px;transform:translateX(-50%);padding:3px 6px;border-radius:99px;background:#153c2b;color:#83ffc2;border:1px solid #65ffb255;font-size:6px;font-weight:950;letter-spacing:.45px}@keyframes v66recommend{50%{filter:brightness(1.3);transform:translate(-50%,-50%) translateY(-3px)}}.v66-celebrate{position:fixed;inset:0;z-index:300;display:none;place-items:center;padding:20px;background:#030207dd;backdrop-filter:blur(12px)}.v66-celebrate.show{display:grid}.v66-celebrate-card{max-width:360px;padding:24px;border:1px solid #ffd36d66;border-radius:27px;text-align:center;background:radial-gradient(circle at 50% 0,#ffd36d35,transparent 45%),linear-gradient(#2d1d3e,#0e0918);box-shadow:0 0 70px #ffd36d35}.v66-celebrate-card i{font-style:normal;font-size:54px}.v66-celebrate-card h2{margin:10px 0 6px}.v66-celebrate-card p{color:#c7b9cd;font-size:11px;line-height:1.45}.v66-celebrate-card button{width:100%;min-height:44px;border:0;border-radius:14px;background:linear-gradient(135deg,#ffd36d,#e68b45);color:#241306;font-weight:950}
@media(max-width:390px){.v66-grid{grid-template-columns:1fr}.v66-progress{padding:8px}.v66-quick button{min-width:41px}.v66-body{padding:11px}}
</style>
"""


SCRIPT = r"""
<script id="talent-reality-v66-script">
(()=>{
const wait=setInterval(()=>{if(typeof state!=='undefined'&&state?.points&&typeof tree==='function'&&document.getElementById('upgrade')){clearInterval(wait);bootV66()}},100);
let v66Overlay,v66Body,v66Title,v66Mode='buffs',recommendedKey=localStorage.getItem('talentRecommendedBuild')||'';
const v66Esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const v66FmtTime=s=>{s=Math.max(0,Number(s)||0);if(!s)return'доступно сейчас';const d=Math.floor(s/86400),h=Math.ceil((s%86400)/3600);return d?`${d} дн. ${h} ч`:`${h} ч`};
const v66BuffNames={boss_damage:'Урон по боссу',boss_crit_chance:'Шанс крита',boss_crit_power:'Сила крита',first_hit_x3:'Первый удар ×3',influence:'Получаемое влияние',activity:'Награды активности',tasks:'Награды заданий',daily_double:'Ежедневное удвоение',penalty_reduction:'Снижение штрафов',avoid_penalty:'Шанс отменить штраф',sabotage_reduction:'Защита от конфликтов',weekly_armor:'Сюжетная броня',game_reward:'Награды мини-игр',rare_reward:'Шанс редкой награды',second_chance:'Второй шанс',daily_reroll:'Переписать судьбу',combo_double:'Каждый пятый удар ×2',crit_break_shield:'Крит ломает щит',loss_pity:'Упрямство судьбы'};
const v66BuffIcons={boss_damage:'⚔️',boss_crit_chance:'🎯',boss_crit_power:'💥',first_hit_x3:'🔥',influence:'👑',activity:'💬',tasks:'🧩',daily_double:'🌟',penalty_reduction:'🛡️',avoid_penalty:'✨',sabotage_reduction:'⚖️',weekly_armor:'🪽',game_reward:'🎁',rare_reward:'🍀',second_chance:'🔁',daily_reroll:'🔮',combo_double:'⚔️',crit_break_shield:'💢',loss_pity:'🎲'};

function bootV66(){
 document.querySelector('.points small').textContent='ОЧКОВ ДРЕВА';
 installProgress();installOverlay();patchGuide();wrapTreeV66();wrapOpenSkillV66();fixUpgradeV66();refreshV66();
}
function installProgress(){if(document.getElementById('v66Progress'))return;const el=document.createElement('section');el.id='v66Progress';el.className='v66-progress';el.innerHTML=`<div><small>ОЧКИ ДРЕВА ЗА РЕЙДЫ</small><b id="v66WeekText">0 / 12 за неделю</b><div class="v66-track"><i id="v66WeekFill"></i></div></div><div class="v66-quick"><button data-v66="buffs"><span>✨</span>БАФФЫ</button><button data-v66="recommend"><span>🧭</span>СБОРКИ</button><button data-v66="focus"><span>👑</span>ПУТЬ</button></div>`;document.querySelector('.branch')?.insertAdjacentElement('afterend',el);el.querySelectorAll('[data-v66]').forEach(b=>b.onclick=()=>openV66(b.dataset.v66))}
function installOverlay(){v66Overlay=document.createElement('div');v66Overlay.className='v66-overlay';v66Overlay.innerHTML='<section class="v66-panel"><header class="v66-head"><h2 id="v66Title">Древо знаний</h2><button class="v66-close">✕</button></header><div class="v66-body" id="v66Body"></div></section>';document.body.appendChild(v66Overlay);v66Body=v66Overlay.querySelector('#v66Body');v66Title=v66Overlay.querySelector('#v66Title');v66Overlay.querySelector('.v66-close').onclick=closeV66;v66Overlay.onclick=e=>{if(e.target===v66Overlay)closeV66()};const celebrate=document.createElement('div');celebrate.id='v66Celebrate';celebrate.className='v66-celebrate';celebrate.innerHTML='<div class="v66-celebrate-card"><i id="v66CelebrateIcon">🏆</i><h2 id="v66CelebrateTitle">Новый титул</h2><p id="v66CelebrateText"></p><button>ЗАБРАТЬ НАГРАДУ</button></div>';document.body.appendChild(celebrate);celebrate.querySelector('button').onclick=()=>celebrate.classList.remove('show')}
function patchGuide(){const earn=document.querySelector('#guide .earn');if(earn)earn.innerHTML='<b>Как получить очки древа</b>Стартовые очки и новые очки за влияние сохраняются навсегда.<br><br>За победу над боссом: 🥇 4 · 🥈 3 · 🥉 2 · активному участнику 1. За рейды можно получить до <b>12 очков в неделю</b>.'}
function wrapTreeV66(){if(tree.v66)return;const old=tree;tree=function(...args){const result=old(...args);requestAnimationFrame(()=>{decorateRecommendation();refreshHeaderV66()});return result};tree.v66=true;tree()}
function wrapOpenSkillV66(){if(openSkill.v66)return;const old=openSkill;openSkill=function(skill){const result=old(skill);requestAnimationFrame(()=>requestAnimationFrame(()=>decorateCardV66(skill)));return result};openSkill.v66=true}
function fixUpgradeV66(){const button=document.getElementById('upgrade');button.onclick=async()=>{if(!selected||busy)return;const chosen={...selected};busy=true;button.disabled=true;button.textContent='ПРОКАЧИВАЕМ…';try{const next=await api('upgrade',{skill_id:chosen.id});state=next;busy=false;tree(chosen.id);openSkill({...chosen,unlocked:true});refreshV66();toastShow(`Навык «${chosen.name}» улучшен`);tg?.HapticFeedback?.notificationOccurred?.('success');const fresh=(next.new_cosmetics||[])[0];if(fresh)showCosmetic(fresh)}catch(e){busy=false;openSkill(chosen);toastShow(e.message);tg?.HapticFeedback?.notificationOccurred?.('error')}finally{busy=false;setTimeout(()=>{if(selected&&document.getElementById('sheet')?.classList.contains('show'))openSkill({...selected,unlocked:true})},0)}}}
function refreshV66(){refreshHeaderV66();decorateRecommendation();if(v66Overlay?.classList.contains('show'))renderV66()}
function refreshHeaderV66(){const weekly=state.weekly_tree||{earned:0,cap:12},earned=Number(weekly.earned||0),cap=Math.max(1,Number(weekly.cap||12));const text=document.getElementById('v66WeekText'),fill=document.getElementById('v66WeekFill');if(text)text.textContent=`${earned} / ${cap} за неделю`;if(fill)fill.style.width=Math.min(100,earned/cap*100)+'%'}
function openV66(mode){v66Mode=mode;v66Overlay.classList.add('show');renderV66();tg?.HapticFeedback?.impactOccurred?.('light')}
function closeV66(){v66Overlay?.classList.remove('show')}
function renderV66(){if(v66Mode==='buffs')renderBuffs();if(v66Mode==='recommend')renderRecommendations();if(v66Mode==='focus')renderFocus();if(v66Mode==='rewards')renderRewards()}
function renderBuffs(){v66Title.textContent='✨ Мои суммарные баффы';const buffs=Object.entries(state.buffs||{}).filter(([,v])=>Number(v)>0);let html=`<div class="v66-note">Все эффекты уже применяются в боте. Здесь показан итог с учётом личных талантов, специализации, типажа дня и общего древа беседы.</div><div class="v66-grid"><div class="v66-card"><h3>🌳 Очки развития</h3><p>Всего: <b>${state.points.total}</b><br>Потрачено: <b>${state.points.spent}</b><br>Свободно: <b>${state.points.available}</b></p></div><div class="v66-card"><h3>📅 Рейдовый прогресс</h3><p>${state.weekly_tree?.earned||0} из ${state.weekly_tree?.cap||12} очков за текущую неделю.</p></div></div><div class="v66-section">Активные эффекты</div>`;html+=buffs.length?buffs.map(([k,v])=>{const binary=['first_hit_x3','daily_double','weekly_armor','daily_reroll','combo_double','crit_break_shield','loss_pity'].includes(k);return `<div class="v66-buff"><span>${v66BuffIcons[k]||'✨'}</span><div><b>${v66Esc(v66BuffNames[k]||k)}</b><small>${binary?'Уникальная механика активна':'Суммарный эффект всех источников'}</small></div><strong>${binary?'АКТИВНО':'+'+Math.round(Number(v)*1000)/10+'%'}</strong></div>`}).join(''):'<div class="v66-note">Прокачай первый талант, чтобы здесь появились усиления.</div>';html+='<div class="v66-section">Источники</div><div class="v66-grid">'+(state.buff_sources||[]).map(x=>`<div class="v66-card"><h3>${v66Esc(x.name)} · ${x.level} ур.</h3><p>${v66Esc(x.effect||'Активный талант')}</p><small>${v66Esc(x.branch_title||x.branch)}</small></div>`).join('')+'</div><button class="master-tool" style="width:100%;margin-top:10px" data-open-rewards><b>🏆</b>ТИТУЛЫ И РАМКИ</button>';v66Body.innerHTML=html;v66Body.querySelector('[data-open-rewards]')?.addEventListener('click',()=>{v66Mode='rewards';renderV66()})}
function renderRecommendations(){v66Title.textContent='🧭 Рекомендуемые сборки';v66Body.innerHTML='<div class="v66-note">Выбор сборки ничего не тратит. Древо подсветит следующий рекомендуемый талант, а решение о покупке останется за тобой.</div><div class="v66-grid">'+(state.recommended_builds||[]).map(b=>{const done=(b.skills||[]).filter(id=>Number(state.levels?.[id]||0)>=Number(state.skill_meta?.[id]?.max||1)).length;return `<article class="v66-card ${recommendedKey===b.key?'active':''}"><h3>${v66Esc(b.emoji)} ${v66Esc(b.title)}</h3><p>${v66Esc(b.description)}</p><small>Готово ${done}/${b.skills.length}</small><button data-build="${v66Esc(b.key)}">${recommendedKey===b.key?'ВЫБРАНО · ПОКАЗАТЬ':'ВЫБРАТЬ И ПОКАЗАТЬ'}</button></article>`}).join('')+'</div>';v66Body.querySelectorAll('[data-build]').forEach(btn=>btn.onclick=()=>chooseRecommendation(btn.dataset.build))}
function chooseRecommendation(key){const build=(state.recommended_builds||[]).find(x=>x.key===key);if(!build)return;recommendedKey=key;localStorage.setItem('talentRecommendedBuild',key);branch=build.branch;theme();tabsRender();tree();centerTree();refreshV66();closeV66();toastShow(`Подсвечена сборка «${build.title}»`)}
function decorateRecommendation(){document.querySelectorAll('.nodewrap.recommended').forEach(x=>x.classList.remove('recommended'));const build=(state.recommended_builds||[]).find(x=>x.key===recommendedKey);if(!build||build.branch!==branch)return;const next=(build.skills||[]).find(id=>Number(state.levels?.[id]||0)<Number(state.skill_meta?.[id]?.max||1));if(!next)return;const name=state.skill_meta?.[next]?.real_name;document.querySelectorAll('.nodewrap').forEach(w=>{if(w.querySelector('.name')?.textContent?.trim()===name)w.classList.add('recommended')})}
function renderFocus(){v66Title.textContent='👑 Основная специализация';const f=state.focus||{choices:[],eligible:false,spent:0,required_spent:5,ready_in:0};let html=`<div class="v66-note">После вложения ${f.required_spent||5} очков выбери главный путь. Он добавит ещё 20% к процентным эффектам выбранной ветки. Менять путь можно не чаще одного раза в неделю.</div>`;if(!f.eligible)html+=`<div class="v66-note">🔒 Вложено ${f.spent||0}/${f.required_spent||5}. Прокачай ещё ${(f.required_spent||5)-(f.spent||0)} очк.</div>`;html+='<div class="v66-grid">'+(f.choices||[]).map(c=>`<article class="v66-card ${c.selected?'active':''}"><h3>${v66Esc(c.emoji)} ${v66Esc(c.title)}</h3><p>${v66Esc(c.description)}</p><small>${c.selected?'Текущая специализация':f.ready_in?'Смена через '+v66FmtTime(f.ready_in):'Можно выбрать'}</small><button data-focus="${v66Esc(c.key)}" ${!f.eligible||(!c.selected&&f.ready_in)?'disabled':''}>${c.selected?'ВЫБРАНО':'ВЫБРАТЬ'}</button></article>`).join('')+'</div>';v66Body.innerHTML=html;v66Body.querySelectorAll('[data-focus]').forEach(btn=>btn.onclick=()=>chooseFocus(btn.dataset.focus))}
async function chooseFocus(key){try{state=await api('focus',{branch:key});refreshV66();renderFocus();tree();toastShow('Основная специализация обновлена');tg?.HapticFeedback?.notificationOccurred?.('success')}catch(e){toastShow(e.message);tg?.HapticFeedback?.notificationOccurred?.('error')}}
function renderRewards(){v66Title.textContent='🏆 Титулы и рамки';v66Body.innerHTML='<div class="v66-note">Полностью заверши один из финальных путей ветки, чтобы навсегда получить косметическую награду. Награды не исчезают после сброса билда.</div><div class="v66-grid">'+(state.cosmetics||[]).map(c=>`<article class="v66-card v66-cosmetic ${c.unlocked?'unlocked':''}"><h3>${v66Esc(c.emoji)} ${v66Esc(c.title)}</h3><p>${v66Esc(c.reward)}</p><small>${c.unlocked?'ПОЛУЧЕНО':'ЗАВЕРШИ ФИНАЛЬНЫЙ ПУТЬ'}</small></article>`).join('')+'</div>'}
function decorateCardV66(skill){const meta=state.skill_meta?.[skill.id],card=document.querySelector('#sheet .card');if(!meta||!card)return;let box=card.querySelector('.v66-change');if(!box){box=document.createElement('div');box.className='v66-change';const anchor=card.querySelector('.card-master-preview')||document.getElementById('cardeffect');anchor?.insertAdjacentElement('afterend',box)}const lines=meta.preview?.lines||[];const line=lines.find(x=>String(x).includes('→'))||lines[0]||'';if(String(line).includes('→')){const parts=String(line).split('→'),left=parts[0].trim(),right=parts.slice(1).join('→').trim();box.innerHTML=`<div><small>СЕЙЧАС</small><b>${v66Esc(left)}</b></div><strong>→</strong><div><small>ПОСЛЕ</small><b>${v66Esc(right)}</b></div>`}else box.innerHTML=`<div style="grid-column:1/-1"><small>ПОСЛЕ ПРОКАЧКИ</small><b>${v66Esc(line)}</b></div>`;let legend=card.querySelector('.v66-legend');if(!legend){legend=document.createElement('div');legend.className='v66-legend';box.insertAdjacentElement('afterend',legend)}const finalSkill=['damage4','damage7','damage9','damage11','influence4','influence7','influence9','influence11','defense4','defense7','defense9','defense11','rewards4','rewards7','rewards9','rewards11'].includes(skill.id);legend.style.display=finalSkill?'block':'none';if(finalSkill)legend.textContent='👑 Легендарный финал: меняет правила игры и открывает косметическую награду ветки.'}
function showCosmetic(c){const overlay=document.getElementById('v66Celebrate');document.getElementById('v66CelebrateIcon').textContent=c.emoji||'🏆';document.getElementById('v66CelebrateTitle').textContent=c.title||'Новый титул';document.getElementById('v66CelebrateText').textContent=c.reward||'Получена новая косметическая награда.';overlay.classList.add('show');tg?.HapticFeedback?.notificationOccurred?.('success')}
})();
</script>
"""


def install_talent_improvements_v66(core: Any) -> None:
    if getattr(talents, "_talent_improvements_v66_installed", False):
        return
    talents._talent_improvements_v66_installed = True

    original_ensure = talents.ensure_schema

    async def ensure_schema(db: Any) -> None:
        await original_ensure(db)
        conn = talents._conn(db)
        async with db.lock:
            await conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS talent_focus_v66(
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    changed_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,user_id)
                );
                CREATE TABLE IF NOT EXISTS talent_cosmetics_v66(
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    unlocked_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,user_id,branch)
                );
                CREATE TABLE IF NOT EXISTS talent_reset_weeks_v66(
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    week_key TEXT NOT NULL,
                    used_at INTEGER NOT NULL,
                    PRIMARY KEY(chat_id,user_id,week_key)
                );
                """
            )
            await conn.commit()

    talents.ensure_schema = ensure_schema

    original_buffs_for = talents.buffs_for

    async def buffs_for(db: Any, chat_id: int, user_id: int) -> dict[str, float]:
        combined = await original_buffs_for(db, chat_id, user_id)
        row = await _focus_row(db, chat_id, user_id)
        if row is None:
            return combined
        branch = str(row["branch"])
        info = FOCUS_INFO.get(branch)
        if not info:
            return combined
        levels = await talents.levels_for(db, chat_id, user_id)
        personal = talents.calculate_buffs(levels)
        for key in info["keys"]:
            combined[key] = float(combined.get(key, 0.0)) + float(
                personal.get(key, 0.0)
            ) * 0.20
        return combined

    talents.buffs_for = buffs_for

    original_builds_state = talent_mastery._builds_state

    async def builds_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_builds_state(db, chat_id, user_id)
        conn = talents._conn(db)
        cursor = await conn.execute(
            "SELECT 1 FROM talent_reset_weeks_v66 WHERE chat_id=? AND user_id=? AND week_key=?",
            (chat_id, user_id, _week_key()),
        )
        weekly_used = await cursor.fetchone() is not None
        first_free = bool(data.get("free_reset"))
        if first_free:
            mode = "first_free"
        elif not weekly_used:
            mode = "weekly_free"
        else:
            mode = "paid"
        data.update(
            {
                "free_reset": mode != "paid",
                "reset_mode": mode,
                "reset_price": RESET_PRICE,
                "weekly_free_used": weekly_used,
                "reset_note": {
                    "first_free": "Первый сброс бесплатный.",
                    "weekly_free": "Доступен бесплатный сброс этой недели.",
                    "paid": f"Бесплатный сброс уже использован. Цена: {RESET_PRICE} влияния.",
                }[mode],
            }
        )
        return data

    talent_mastery._builds_state = builds_state

    async def reset_build(
        core_obj: Any,
        db: Any,
        chat_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        builds = await builds_state(db, chat_id, user_id)
        player = await db.get_player(chat_id, user_id)
        if player is None:
            raise ValueError("Игрок не найден.")
        mode = str(builds.get("reset_mode") or "paid")
        if mode == "paid":
            if int(player.points) < RESET_PRICE:
                raise ValueError(f"Для сброса нужно {RESET_PRICE} очков влияния.")
            await db.add_points_with_balance(
                chat_id,
                user_id,
                -RESET_PRICE,
                "admin_talent_reset_v66",
            )
        conn = talents._conn(db)
        now = int(time.time())
        async with db.lock:
            await conn.execute(
                "DELETE FROM talent_levels WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            await conn.execute(
                "UPDATE talent_profiles SET spent_points=0,updated_at=? WHERE chat_id=? AND user_id=?",
                (now, chat_id, user_id),
            )
            await conn.execute(
                "UPDATE talent_meta SET free_reset_used=1,active_build_slot=NULL WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            await conn.execute(
                "DELETE FROM talent_focus_v66 WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            await conn.execute(
                "DELETE FROM talent_active_effects WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            await conn.execute(
                "DELETE FROM talent_active_cooldowns WHERE chat_id=? AND user_id=?",
                (chat_id, user_id),
            )
            if mode != "paid":
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO talent_reset_weeks_v66(
                        chat_id,user_id,week_key,used_at
                    ) VALUES(?,?,?,?)
                    """,
                    (chat_id, user_id, _week_key(), now),
                )
            await conn.commit()
        return await talents.talent_state(db, chat_id, user_id)

    talent_mastery._reset_build = reset_build

    original_state = talents.talent_state

    async def talent_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_state(db, chat_id, user_id)
        levels = {str(k): int(v) for k, v in (data.get("levels") or {}).items()}
        new_branches = await _sync_cosmetics(db, chat_id, user_id, levels)
        data["buffs"] = await talents.buffs_for(db, chat_id, user_id)
        data["focus"] = await focus_state(db, chat_id, user_id)
        data["cosmetics"] = await _cosmetics_state(db, chat_id, user_id)
        data["new_cosmetics"] = [
            {"branch": branch, **COSMETICS[branch]} for branch in new_branches
        ]
        conn = talents._conn(db)
        earned = 0
        try:
            cursor = await conn.execute(
                """
                SELECT tree_points FROM knowledge_weekly
                WHERE chat_id=? AND user_id=? AND week_key=?
                """,
                (chat_id, user_id, _week_key()),
            )
            row = await cursor.fetchone()
            earned = int(row["tree_points"] if row else 0)
        except Exception:
            earned = 0
        data["weekly_tree"] = {"earned": earned, "cap": WEEKLY_TREE_CAP}
        data["recommended_builds"] = RECOMMENDED_BUILDS
        branch_titles = {
            "damage": "Урон",
            "influence": "Влияние",
            "defense": "Защита",
            "rewards": "Награды",
            "special": "Особые таланты",
        }
        sources = []
        for skill_id, level in levels.items():
            if level <= 0:
                continue
            spec = talents.SKILLS.get(skill_id)
            if not spec:
                continue
            sources.append(
                {
                    "id": skill_id,
                    "name": str(spec.get("name") or skill_id),
                    "level": level,
                    "branch": str(spec.get("branch") or "special"),
                    "branch_title": branch_titles.get(
                        str(spec.get("branch") or "special"),
                        "Особые таланты",
                    ),
                    "effect": str(spec.get("effect") or ""),
                }
            )
        data["buff_sources"] = sources
        data["buff_names"] = BUFF_NAMES
        data["builds"] = await builds_state(db, chat_id, user_id)
        return data

    talents.talent_state = talent_state

    original_upgrade = talents.upgrade_skill

    async def upgrade_skill(
        db: Any,
        chat_id: int,
        user_id: int,
        skill_id: str,
    ) -> dict[str, Any]:
        await original_upgrade(db, chat_id, user_id, skill_id)
        return await talents.talent_state(db, chat_id, user_id)

    talents.upgrade_skill = upgrade_skill

    talent_ux.STYLE += STYLE
    talent_ux.SCRIPT += SCRIPT
