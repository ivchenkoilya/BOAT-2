from __future__ import annotations

from typing import Any

import talent_system as talents
import talent_ux


OPTIMAL_BUILDS: list[dict[str, Any]] = [
    {
        "key": "boss_hunter",
        "emoji": "🎯",
        "title": "Боссоборец-критовик",
        "description": "Левая ветка урона: быстрый выход в крит, усиление силы крита и тройной первый удар.",
        "branch": "damage",
        "side": "left",
        "side_title": "ЛЕВАЯ ВЕТКА",
        "route": "Острый язык → Больное место → Безжалостный выпад → Крушение эго",
        "skills": ["damage1", "damage2", "damage3", "damage4"],
        "plan": [
            {"id": "damage1", "level": 1},
            {"id": "damage2", "level": 1},
            {"id": "damage3", "level": 1},
            {"id": "damage4", "level": 1},
            {"id": "damage1", "level": 3},
            {"id": "damage2", "level": 3},
            {"id": "damage3", "level": 2},
        ],
    },
    {
        "key": "relentless_pressure",
        "emoji": "⚔️",
        "title": "Безжалостный натиск",
        "description": "Правая ветка урона: стабильный урон, серия быстрых выпадов и сильный финальный крит.",
        "branch": "damage",
        "side": "right",
        "side_title": "ПРАВАЯ ВЕТКА",
        "route": "Острый язык → Тяжёлый аргумент → Серия выпадов → Приговор эго",
        "skills": ["damage1", "damage5", "damage10", "damage11"],
        "plan": [
            {"id": "damage1", "level": 1},
            {"id": "damage5", "level": 1},
            {"id": "damage10", "level": 1},
            {"id": "damage11", "level": 1},
            {"id": "damage1", "level": 3},
            {"id": "damage5", "level": 3},
            {"id": "damage10", "level": 3},
        ],
    },
    {
        "key": "public_star",
        "emoji": "🌟",
        "title": "Звезда беседы",
        "description": "Левая ветка влияния: максимум пользы от сообщений, заданий и ежедневного удвоения.",
        "branch": "influence",
        "side": "left",
        "side_title": "ЛЕВАЯ ВЕТКА",
        "route": "Заметная личность → Центр внимания → Восходящая звезда → Культ личности",
        "skills": ["influence1", "influence2", "influence3", "influence4"],
        "plan": [
            {"id": "influence1", "level": 1},
            {"id": "influence2", "level": 1},
            {"id": "influence3", "level": 1},
            {"id": "influence4", "level": 1},
            {"id": "influence1", "level": 3},
            {"id": "influence2", "level": 3},
            {"id": "influence3", "level": 2},
        ],
    },
    {
        "key": "fast_growth",
        "emoji": "👑",
        "title": "Быстрый рост",
        "description": "Правая ветка влияния: задания, репутация и самый большой постоянный прирост влияния.",
        "branch": "influence",
        "side": "right",
        "side_title": "ПРАВАЯ ВЕТКА",
        "route": "Заметная личность → Живой авторитет → Безупречная репутация → Властитель внимания",
        "skills": ["influence1", "influence5", "influence10", "influence11"],
        "plan": [
            {"id": "influence1", "level": 1},
            {"id": "influence5", "level": 1},
            {"id": "influence10", "level": 1},
            {"id": "influence11", "level": 1},
            {"id": "influence1", "level": 3},
            {"id": "influence5", "level": 3},
            {"id": "influence10", "level": 3},
        ],
    },
    {
        "key": "story_armor",
        "emoji": "🪽",
        "title": "Сюжетная броня",
        "description": "Левая ветка защиты: отмена штрафов, защита от конфликтов и полное спасение раз в неделю.",
        "branch": "defense",
        "side": "left",
        "side_title": "ЛЕВАЯ ВЕТКА",
        "route": "Толстая кожа → Железные нервы → Ответный удар → Сюжетная броня",
        "skills": ["defense1", "defense2", "defense3", "defense4"],
        "plan": [
            {"id": "defense1", "level": 1},
            {"id": "defense2", "level": 1},
            {"id": "defense3", "level": 1},
            {"id": "defense4", "level": 1},
            {"id": "defense1", "level": 3},
            {"id": "defense2", "level": 3},
            {"id": "defense3", "level": 2},
        ],
    },
    {
        "key": "invulnerable",
        "emoji": "🛡️",
        "title": "Неуязвимый",
        "description": "Правая ветка защиты: устойчивость к штрафам, контрмеры и высокий шанс полностью избежать потери.",
        "branch": "defense",
        "side": "right",
        "side_title": "ПРАВАЯ ВЕТКА",
        "route": "Толстая кожа → Холодный разум → Контрмера → Неуязвимый образ",
        "skills": ["defense1", "defense5", "defense10", "defense11"],
        "plan": [
            {"id": "defense1", "level": 1},
            {"id": "defense5", "level": 1},
            {"id": "defense10", "level": 1},
            {"id": "defense11", "level": 1},
            {"id": "defense1", "level": 3},
            {"id": "defense5", "level": 3},
            {"id": "defense10", "level": 3},
        ],
    },
    {
        "key": "lucky_hero",
        "emoji": "🔮",
        "title": "Азартный герой",
        "description": "Левая ветка наград: редкие бонусы, второй шанс и ежедневная отмена первого проигрыша.",
        "branch": "rewards",
        "side": "left",
        "side_title": "ЛЕВАЯ ВЕТКА",
        "route": "Богатая добыча → Любимчик судьбы → Второй шанс → Переписать судьбу",
        "skills": ["rewards1", "rewards2", "rewards3", "rewards4"],
        "plan": [
            {"id": "rewards1", "level": 1},
            {"id": "rewards2", "level": 1},
            {"id": "rewards3", "level": 1},
            {"id": "rewards4", "level": 1},
            {"id": "rewards1", "level": 3},
            {"id": "rewards2", "level": 3},
            {"id": "rewards3", "level": 2},
        ],
    },
    {
        "key": "jackpot_hunter",
        "emoji": "💰",
        "title": "Охотник за большим кушем",
        "description": "Правая ветка наград: высокий размер выигрыша, золотые случаи и усиленная страховка от проигрыша.",
        "branch": "rewards",
        "side": "right",
        "side_title": "ПРАВАЯ ВЕТКА",
        "route": "Богатая добыча → Охотник за удачей → Золотой случай → Избранник судьбы",
        "skills": ["rewards1", "rewards5", "rewards6", "rewards7"],
        "plan": [
            {"id": "rewards1", "level": 1},
            {"id": "rewards5", "level": 1},
            {"id": "rewards6", "level": 1},
            {"id": "rewards7", "level": 1},
            {"id": "rewards1", "level": 3},
            {"id": "rewards5", "level": 3},
            {"id": "rewards6", "level": 2},
        ],
    },
]


STYLE = r"""
<style id="talent-recommendations-v67-style">
.v67-side{display:inline-flex;margin:0 0 6px;padding:3px 7px;border-radius:99px;border:1px solid #ffffff1a;background:#ffffff08;font-size:7px;font-weight:950;letter-spacing:.55px}.v67-side.left{color:#8bc8ff;border-color:#5dabff55;background:#3179bb15}.v67-side.right{color:#ffbd78;border-color:#ff9b4655;background:#c9672815}.v67-route{margin:8px 0;padding:8px 9px;border-radius:12px;border:1px solid #ffffff10;background:#0d0917;color:#bcb1c5;font-size:8px;line-height:1.42}.v67-route b{display:block;margin-bottom:3px;color:#fff;font-size:8px}.v67-route em{display:block;margin-top:5px;color:#79ffc0;font-style:normal;font-weight:900}.v67-route.warn{border-color:#ff6d7f55;background:#6f1d2a1b}.v67-route.warn em{color:#ff8f9c}.v67-route-chip{display:flex;align-items:center;gap:5px;max-width:210px;margin-left:auto;padding:5px 7px;border-radius:10px;border:1px solid #66ffc044;background:#153a2b99;color:#8affc8;font-size:7px;font-weight:950;line-height:1.2}.v67-route-chip.right{border-color:#ff9d5355;background:#4b2b1699;color:#ffc38d}.v67-route-chip.conflict{border-color:#ff657855;background:#4f172199;color:#ff9aa7}.nodewrap.v67-path .node{box-shadow:0 0 0 2px #69aef520,0 15px 32px #0008,0 0 22px #69aef52c!important}.nodewrap.v67-done .node{border-color:#ffd36d99!important;box-shadow:0 0 0 2px #ffd36d1d,0 15px 32px #0008,0 0 24px #ffd36d35!important}.nodewrap.v67-next .node{border-color:#65ffb2!important;box-shadow:0 0 0 4px #65ffb227,0 0 38px #65ffb26b!important;animation:v67Next 1.25s ease-in-out infinite!important}.nodewrap.v67-next:after{content:"СЛЕДУЮЩИЙ ШАГ";position:absolute;left:50%;top:-18px;transform:translateX(-50%);padding:3px 6px;border-radius:99px;background:#153c2b;color:#83ffc2;border:1px solid #65ffb255;font-size:6px;font-weight:950;letter-spacing:.4px;white-space:nowrap}.nodewrap.v67-conflict .node{border-color:#ff687a!important;box-shadow:0 0 30px #ff52654a!important}.nodewrap.v67-conflict:after{content:"ПУТЬ ЗАБЛОКИРОВАН";position:absolute;left:50%;top:-18px;transform:translateX(-50%);padding:3px 6px;border-radius:99px;background:#4d1720;color:#ff9aa6;border:1px solid #ff687a55;font-size:6px;font-weight:950;white-space:nowrap}@keyframes v67Next{50%{filter:brightness(1.28);transform:scale(1.045)}}
@media(max-width:390px){.v67-route-chip{max-width:155px}.v67-route{font-size:7.5px}}
</style>
"""


SCRIPT = r"""
<script id="talent-recommendations-v67-script">
(()=>{
const wait=setInterval(()=>{if(typeof state!=='undefined'&&state?.points&&typeof tree==='function'){clearInterval(wait);bootV67()}},120);
let scheduled=false;
const esc67=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function bootV67(){document.addEventListener('click',e=>{const b=e.target.closest?.('[data-build]');if(b){localStorage.setItem('talentRecommendedBuild',b.dataset.build||'');setTimeout(schedule67,60)}},true);new MutationObserver(schedule67).observe(document.body,{childList:true,subtree:true});setInterval(schedule67,450);schedule67()}
function schedule67(){if(scheduled)return;scheduled=true;requestAnimationFrame(()=>{scheduled=false;apply67()})}
function build67(){const key=localStorage.getItem('talentRecommendedBuild')||'';return(state.recommended_builds||[]).find(x=>x.key===key)}
function level67(id){return Number(state.levels?.[id]||0)}
function meta67(id){return state.skill_meta?.[id]||{}}
function plan67(build){return(build?.plan?.length?build.plan:(build?.skills||[]).map(id=>({id,level:Number(meta67(id).max||1)})))}
function next67(build){for(const step of plan67(build)){if(level67(step.id)<Number(step.level||1)){const m=meta67(step.id);return{...step,meta:m,conflict:m.blocked_by||''}}}return null}
function node67(id){const name=meta67(id).real_name||meta67(id).name;return[...document.querySelectorAll('.nodewrap')].find(w=>w.querySelector('.name')?.textContent?.trim()===name)}
function apply67(){enhanceCards67();decoratePath67()}
function enhanceCards67(){document.querySelectorAll('[data-build]').forEach(button=>{const build=(state.recommended_builds||[]).find(x=>x.key===button.dataset.build);const card=button.closest('.v66-card');if(!build||!card)return;const next=next67(build),done=plan67(build).filter(s=>level67(s.id)>=Number(s.level||1)).length,total=plan67(build).length;const signature=[build.key,next?.id,next?.level,next?.conflict,done,total].join('|');if(card.dataset.v67===signature)return;card.dataset.v67=signature;card.querySelectorAll('.v67-side,.v67-route').forEach(x=>x.remove());const side=document.createElement('span');side.className='v67-side '+(build.side||'left');side.textContent=build.side_title||(build.side==='right'?'ПРАВАЯ ВЕТКА':'ЛЕВАЯ ВЕТКА');card.prepend(side);const route=document.createElement('div');route.className='v67-route'+(next?.conflict?' warn':'');const nextName=next?(next.meta.real_name||next.meta.name||next.id):'Сборка полностью завершена';const status=next?.conflict?`Заблокировано талантом «${next.conflict}». Нужен сброс или другая сборка.`:next?`Следующий шаг: ${nextName}, уровень ${next.level}`:'Все рекомендуемые уровни получены.';route.innerHTML=`<b>${esc67(build.route||'Оптимальный маршрут')}</b>Шагов выполнено: ${done}/${total}<em>${esc67(status)}</em>`;button.insertAdjacentElement('beforebegin',route)})}
function decoratePath67(){document.querySelectorAll('.nodewrap').forEach(w=>w.classList.remove('recommended','v67-path','v67-done','v67-next','v67-conflict'));document.querySelector('.v67-route-chip')?.remove();const build=build67();if(!build||build.branch!==branch)return;const unique=[...new Set(build.skills||[])];unique.forEach(id=>{const node=node67(id);if(!node)return;const max=Number(meta67(id).max||1);node.classList.add(level67(id)>=max?'v67-done':'v67-path')});const next=next67(build);if(next){const node=node67(next.id);if(node)node.classList.add(next.conflict?'v67-conflict':'v67-next')}const chip=document.createElement('div');chip.className='v67-route-chip '+(build.side||'left')+(next?.conflict?' conflict':'');chip.textContent=next?.conflict?`⚠ ${build.title}: путь заблокирован`:`🧭 ${build.title} · ${build.side_title||''}`;document.querySelector('.branch')?.appendChild(chip)}
})();
</script>
"""


def install_talent_recommendations_v67(core: Any) -> None:
    if getattr(talents, "_talent_recommendations_v67_installed", False):
        return
    talents._talent_recommendations_v67_installed = True

    original_state = talents.talent_state

    async def talent_state(db: Any, chat_id: int, user_id: int) -> dict[str, Any]:
        data = await original_state(db, chat_id, user_id)
        data["recommended_builds"] = OPTIMAL_BUILDS
        data["recommendations_version"] = 67
        return data

    talents.talent_state = talent_state
    talent_ux.STYLE += STYLE
    talent_ux.SCRIPT += SCRIPT
