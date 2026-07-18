from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web


STYLE = r"""
<style id="talent-ux-v6">
.brand .kicker,.brand h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.brand h1{font-size:18px!important}
.controls #zin,.controls #zout{display:none!important}.controls{right:10px!important}
.card{position:relative}.talent-x{position:absolute;right:13px;top:13px;z-index:5;width:38px;height:38px;border-radius:13px;border:1px solid #ffffff1c;background:#171022e8;color:#fff;font-size:18px;font-weight:900}
.node{border-radius:27px!important;background:radial-gradient(circle at 28% 18%,#ffffff2e,transparent 34%),linear-gradient(145deg,#49336d,#100a20)!important}.node:before{content:"";position:absolute;inset:7px;border-radius:20px;border:1px solid #ffffff10}
.node svg,.cardicon svg,.tab svg,.emblem svg{filter:drop-shadow(0 5px 9px #0007);stroke-linecap:round;stroke-linejoin:round}
.world{width:1000px!important;height:1180px!important}.lines{width:1000px!important;height:1180px!important}
.nodewrap{width:132px!important}.nodewrap .name,.nodewrap .effect{max-width:130px;margin-left:auto;margin-right:auto}.nodewrap .name{font-size:11px!important}.nodewrap .effect{font-size:8.5px!important}
.path-label{position:absolute;transform:translate(-50%,-50%);font-size:8px;font-weight:950;letter-spacing:.65px;color:rgba(var(--rgb),.72);padding:5px 8px;border:1px solid rgba(var(--rgb),.19);border-radius:99px;background:#100b1de8;box-shadow:0 0 14px rgba(var(--rgb),.08)}
.path-label.major{font-size:9px;color:var(--c);border-color:rgba(var(--rgb),.27);background:rgba(var(--rgb),.08)}
.sheet.show{pointer-events:auto!important}.sheet.show .card{pointer-events:auto!important}
</style>
"""


SCRIPT = r"""
<script id="talent-ux-v6-script">
(()=>{
const $=s=>document.querySelector(s),tg=window.Telegram?.WebApp,clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
Object.assign(I,{
 hammer:'<svg viewBox="0 0 48 48"><path fill="currentColor" d="M8 10h23l9 9-10 10-7-7v21H8V10Z"/></svg>',
 break:'<svg viewBox="0 0 48 48"><rect x="7" y="7" width="34" height="34" rx="10" fill="currentColor"/><path d="m27 7-8 15 9 3-7 16" stroke="#160e25" stroke-width="5" fill="none"/></svg>',
 network:'<svg viewBox="0 0 48 48"><circle cx="24" cy="10" r="6" fill="currentColor"/><circle cx="10" cy="35" r="6" fill="currentColor"/><circle cx="38" cy="35" r="6" fill="currentColor"/><path d="m21 15-8 15M27 15l8 15M16 35h16" stroke="currentColor" stroke-width="4"/></svg>',
 legend:'<svg viewBox="0 0 48 48"><path fill="currentColor" d="m24 4 6 14 14 6-14 6-6 14-6-14-14-6 14-6 6-14Z"/></svg>',
 mind:'<svg viewBox="0 0 48 48"><path fill="currentColor" d="M17 7C8 7 5 18 10 25c-3 7 2 13 12 13V12c0-3-2-5-5-5Zm14 0c9 0 12 11 7 18 3 7-2 13-12 13V12c0-3 2-5 5-5Z"/></svg>',
 dice:'<svg viewBox="0 0 48 48"><rect x="6" y="6" width="36" height="36" rx="10" fill="currentColor"/><g fill="#160e25"><circle cx="16" cy="16" r="3"/><circle cx="32" cy="16" r="3"/><circle cx="24" cy="24" r="3"/><circle cx="16" cy="32" r="3"/><circle cx="32" cy="32" r="3"/></g></svg>',
 bolt:'<svg viewBox="0 0 48 48"><path fill="currentColor" d="M28 3 10 27h12l-2 18 18-25H26l2-17Z"/></svg>',
 seal:'<svg viewBox="0 0 48 48"><circle cx="24" cy="21" r="15" fill="currentColor"/><path fill="currentColor" opacity=".72" d="m16 34-3 11 11-6 11 6-3-11Z"/></svg>',
 mirror:'<svg viewBox="0 0 48 48"><rect x="9" y="5" width="30" height="35" rx="15" fill="currentColor"/><path d="M19 13c-4 5-5 12-2 18" stroke="white" stroke-opacity=".48" stroke-width="3"/><path fill="currentColor" d="M21 40h6v5h-6z"/></svg>',
 jackpot:'<svg viewBox="0 0 48 48"><path fill="currentColor" d="M8 8h32v32H8z"/><path d="M15 15h18M15 24h18M15 33h18" stroke="#160e25" stroke-width="5"/><circle cx="15" cy="15" r="3" fill="white" opacity=".7"/><circle cx="24" cy="24" r="3" fill="white" opacity=".7"/><circle cx="33" cy="33" r="3" fill="white" opacity=".7"/></svg>'
});

const D={
 damage:[
  ['damage1','Острый язык','sword',3,1,null,'+3% урона','Увеличивает обычный урон.',500,930],
  ['damage2','Больное место','target',3,1,'damage1','+2% шанса крита','Открывает левую школу критов.',300,760],
  ['damage3','Безжалостный выпад','flame',2,2,'damage2','+15% силы крита','Усиливает мощность критов.',140,570],
  ['damage4','Крушение эго','eye',1,4,'damage3','Первый удар ×3','Финал пути сокрушения.',100,330],
  ['damage5','Тяжёлый аргумент','hammer',3,1,'damage1','+2% урона','Открывает правую школу давления.',700,760],
  ['damage6','Разрушитель самооценки','break',2,2,'damage5','+10% силы крита','Разрушает защиту эго.',640,570],
  ['damage7','Финальное слово','aura',1,4,'damage6','+3% шанса крита','Финал пути разрушения.',610,330],
  ['damage8','Идеальный момент','bolt',3,1,'damage2','+1,5% шанса крита','Альтернативная ветка точности.',360,570],
  ['damage9','Пробитая гордость','target',2,2,'damage8','+4% урона','Финал пути точности.',390,330],
  ['damage10','Серия выпадов','sword',3,1,'damage5','+1,5% урона','Альтернативная ветка темпа.',860,570],
  ['damage11','Приговор эго','eye',1,4,'damage10','+12% силы крита','Финал пути темпа.',900,330]
 ],
 influence:[
  ['influence1','Заметная личность','crown',3,1,null,'+2% влияния','Общий прирост влияния.',500,930],
  ['influence2','Центр внимания','voice',3,1,'influence1','+3% за активность','Открывает путь публичности.',300,760],
  ['influence3','Восходящая звезда','chart',2,2,'influence2','+5% за задания','Награды за задания.',140,570],
  ['influence4','Культ личности','aura',1,4,'influence3','Награда ×2','Финал пути славы.',100,330],
  ['influence5','Живой авторитет','network',3,1,'influence1','+2% за активность','Открывает путь авторитета.',700,760],
  ['influence6','Легенда беседы','legend',2,2,'influence5','+4% за задания','Усиливает миссии.',640,570],
  ['influence7','Икона реальности','aura',1,4,'influence6','+5% влияния','Финал пути легенды.',610,330],
  ['influence8','Сильная подача','voice',3,1,'influence2','+2,5% за активность','Альтернативная ветка общения.',360,570],
  ['influence9','Вирусная слава','bolt',2,2,'influence8','+4% влияния','Финал вирусной известности.',390,330],
  ['influence10','Безупречная репутация','seal',3,1,'influence5','+3% за задания','Альтернативная ветка доверия.',860,570],
  ['influence11','Властитель внимания','crown',1,4,'influence10','+7% влияния','Финал абсолютного авторитета.',900,330]
 ],
 defense:[
  ['defense1','Толстая кожа','shield',3,1,null,'−4% штрафов','Снижает обычные потери.',500,930],
  ['defense2','Железные нервы','armor',3,1,'defense1','5% отмены','Открывает путь выдержки.',300,760],
  ['defense3','Ответный удар','counter',2,2,'defense2','−10% конфликтов','Ослабляет саботаж и бунт.',140,570],
  ['defense4','Сюжетная броня','wings',1,4,'defense3','Защита раз в неделю','Финал активной защиты.',100,330],
  ['defense5','Холодный разум','mind',3,1,'defense1','−3% штрафов','Открывает путь контроля.',700,760],
  ['defense6','Непоколебимость','shield',2,2,'defense5','+4% отмены','Дополнительная защита.',640,570],
  ['defense7','Недосягаемый','wings',1,4,'defense6','−15% конфликтов','Финал непоколебимости.',610,330],
  ['defense8','Самоконтроль','mind',3,1,'defense2','+2,5% отмены','Альтернативная ветка выдержки.',360,570],
  ['defense9','Абсолютное спокойствие','aura',2,2,'defense8','−6% штрафов','Финал полного спокойствия.',390,330],
  ['defense10','Контрмера','counter',3,1,'defense5','−8% конфликтов','Альтернативная ветка ответа.',860,570],
  ['defense11','Неуязвимый образ','mirror',1,4,'defense10','+8% отмены','Финал отражения штрафов.',900,330]
 ],
 rewards:[
  ['rewards1','Богатая добыча','chest',3,1,null,'+5% наград','Увеличивает награды игр.',500,930],
  ['rewards2','Любимчик судьбы','clover',3,1,'rewards1','+3% редкого бонуса','Открывает путь редкой удачи.',300,760],
  ['rewards3','Второй шанс','repeat',2,2,'rewards2','5% отмены проигрыша','Иногда отменяет проигрыш.',140,570],
  ['rewards4','Переписать судьбу','orb',1,4,'rewards3','Отмена раз в день','Финал второго шанса.',100,330],
  ['rewards5','Охотник за удачей','dice',3,1,'rewards1','+4% наград','Открывает путь большой добычи.',700,760],
  ['rewards6','Золотой случай','chest',2,2,'rewards5','+2,5% редкого бонуса','Больше редких наград.',640,570],
  ['rewards7','Избранник судьбы','aura',1,4,'rewards6','+8% отмены проигрыша','Финал избранника.',610,330],
  ['rewards8','Чутьё на добычу','clover',3,1,'rewards2','+2% редкого бонуса','Альтернативная ветка поиска.',360,570],
  ['rewards9','Большой куш','jackpot',2,2,'rewards8','+7% наград','Финал пути джекпота.',390,330],
  ['rewards10','Страховка судьбы','repeat',3,1,'rewards5','+4% второго шанса','Альтернативная ветка страховки.',860,570],
  ['rewards11','Любимец фортуны','orb',1,4,'rewards10','+6% редкого бонуса','Финал абсолютной удачи.',900,330]
 ]
};

const LABELS={
 damage:[['КРИТИЧЕСКИЙ УДАР',300,675,'major'],['ДАВЛЕНИЕ',700,675,'major'],['СОКРУШЕНИЕ',120,455,''],['ТОЧНОСТЬ',375,455,''],['РАЗРУШЕНИЕ',625,455,''],['ТЕМП',880,455,'']],
 influence:[['ПУБЛИЧНОСТЬ',300,675,'major'],['АВТОРИТЕТ',700,675,'major'],['СЛАВА',120,455,''],['ПОДАЧА',375,455,''],['ЛЕГЕНДА',625,455,''],['РЕПУТАЦИЯ',880,455,'']],
 defense:[['ВЫДЕРЖКА',300,675,'major'],['КОНТРОЛЬ',700,675,'major'],['ОТВЕТ',120,455,''],['СПОКОЙСТВИЕ',375,455,''],['СТОЙКОСТЬ',625,455,''],['КОНТРМЕРА',880,455,'']],
 rewards:[['РЕДКАЯ УДАЧА',300,675,'major'],['ДОБЫЧА',700,675,'major'],['ВТОРОЙ ШАНС',120,455,''],['ДЖЕКПОТ',375,455,''],['ИЗБРАННИК',625,455,''],['СТРАХОВКА',880,455,'']]
};

function curve(a,b){const d=a[0]<b[0]?-42:a[0]>b[0]?42:0,m=(a[1]+b[1])/2;return`M${a[0]} ${a[1]}C${a[0]+d} ${m},${b[0]-d} ${m},${b[0]} ${b[1]}`}
function enhancedTree(flash=''){
 lines.setAttribute('viewBox','0 0 1000 1180');
 lines.querySelectorAll('.dyn').forEach(x=>x.remove());
 world.querySelectorAll('.nodewrap,.path-label').forEach(x=>x.remove());
 const ns=D[branch],root=[500,1080],byId=Object.fromEntries(ns.map(n=>[n[0],n]));
 const edge=(a,b,on)=>{const p=document.createElementNS('http://www.w3.org/2000/svg','path');p.setAttribute('d',curve(a,b));p.setAttribute('class','edge dyn '+(on?'on':''));lines.appendChild(p)};
 edge(root,[ns[0][8],ns[0][9]],true);
 ns.slice(1).forEach(n=>{const p=byId[n[5]];edge([p[8],p[9]],[n[8],n[9]],(state.levels[n[5]]||0)>0)});
 LABELS[branch].forEach(v=>{const x=document.createElement('div');x.className='path-label '+v[3];x.textContent=v[0];x.style.left=v[1]+'px';x.style.top=v[2]+'px';world.appendChild(x)});
 const add=(n,isRoot=false)=>{const[id,name,icon,max,cost,parent,effect,desc,x,y]=n,lvl=isRoot?1:(state.levels[id]||0),ok=isRoot||!parent||(state.levels[parent]||0)>0,w=document.createElement('div');w.className='nodewrap '+(isRoot?'root learned ':!ok?'locked ':lvl>=max?'maxed ':lvl?'learned ':'available ')+(flash===id?'flash':'');w.style.left=(isRoot?500:x)+'px';w.style.top=(isRoot?1080:y)+'px';w.innerHTML=`<button class="node">${I[icon]}<i class="lvl">${lvl}/${max}</i><i class="lock">${I.lock}</i></button><div class="name">${name}</div><div class="effect">${effect}</div>`;w.querySelector('button').onclick=e=>{e.stopPropagation();openSkill({id,name,icon,max,cost,effect,desc,index:isRoot?0:1,unlocked:ok})};world.appendChild(w)};
 add(['core','Пробуждение','core',1,0,null,'Открывает путь','Центральный узел.'],true);ns.forEach(n=>add(n));points.textContent=state.points.available;
}
tree=enhancedTree;
centerTree=function(){scale=innerWidth<390?.52:.58;tx=viewport.clientWidth/2-500*scale;ty=viewport.clientHeight/2-650*scale;apply()};

viewport.onpointerdown=viewport.onpointermove=viewport.onpointerup=viewport.onpointercancel=null;
const pointers=new Map();let mode='',last={},startDistance=0,startScale=scale,anchor={};
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y),middle=(a,b)=>({x:(a.x+b.x)/2,y:(a.y+b.y)/2});
viewport.addEventListener('pointerdown',e=>{pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});viewport.setPointerCapture?.(e.pointerId);if(pointers.size===1){mode='pan';last={x:e.clientX,y:e.clientY}}else if(pointers.size===2){const[a,b]=[...pointers.values()],m=middle(a,b);mode='pinch';startDistance=Math.max(1,distance(a,b));startScale=scale;anchor={x:(m.x-tx)/scale,y:(m.y-ty)/scale}}e.preventDefault()},{passive:false,capture:true});
viewport.addEventListener('pointermove',e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,{x:e.clientX,y:e.clientY});if(mode==='pinch'&&pointers.size>1){const[a,b]=[...pointers.values()],m=middle(a,b);scale=clamp(startScale*distance(a,b)/startDistance,.38,1.35);tx=m.x-anchor.x*scale;ty=m.y-anchor.y*scale;apply()}else if(mode==='pan'&&pointers.size===1){tx+=e.clientX-last.x;ty+=e.clientY-last.y;last={x:e.clientX,y:e.clientY};apply()}e.preventDefault()},{passive:false,capture:true});
const release=e=>{pointers.delete(e.pointerId);if(pointers.size===1){last={...[...pointers.values()][0]};mode='pan'}else if(!pointers.size)mode='';e.preventDefault()};
viewport.addEventListener('pointerup',release,{passive:false,capture:true});viewport.addEventListener('pointercancel',release,{passive:false,capture:true});hint.textContent='Одним пальцем — двигать • Двумя — масштабировать';

const sheetEl=$('#sheet'),closeEl=$('#close'),shut=e=>{e?.preventDefault();e?.stopPropagation();sheetEl?.classList.remove('show')};['click','pointerup','touchend'].forEach(v=>closeEl?.addEventListener(v,shut,{passive:false,capture:true}));const card=sheetEl?.querySelector('.card');if(card&&!card.querySelector('.talent-x')){const x=document.createElement('button');x.className='talent-x';x.type='button';x.textContent='✕';x.onclick=shut;card.prepend(x)}

const brand=$('.brand');let tries=0;const identity=setInterval(()=>{tries++;const u=state?.user||{},t=tg?.initDataUnsafe?.user||{},full=u.full_name||[t.first_name,t.last_name].filter(Boolean).join(' '),raw=u.username||t.username||'',username=raw?'@'+String(raw).replace(/^@/,''):'';if(full||username){brand.querySelector('h1').textContent=full||username;brand.querySelector('.kicker').textContent=username||'ДРЕВО РАЗВИТИЯ';clearInterval(identity)}else if(tries>50)clearInterval(identity)},150);
let viewTries=0;const viewTimer=setInterval(()=>{viewTries++;if(state?.points&&Number.isFinite(+state.points.available)){theme();tabsRender();enhancedTree();centerTree();clearInterval(viewTimer)}else if(viewTries>50)clearInterval(viewTimer)},150);
})();
</script>
"""


def install_ux(core: Any) -> None:
    if getattr(core, "_talent_ux_installed", False):
        return
    core._talent_ux_installed = True
    original = core.web.FileResponse

    def response(path: Any, *args: Any, **kwargs: Any):
        file_path = Path(path)
        if file_path.name == "index.html" and file_path.parent.name == "talent_app":
            text = file_path.read_text(encoding="utf-8")
            text = text.replace("</head>", STYLE + "\n</head>")
            text = text.replace("</body>", SCRIPT + "\n</body>")
            return web.Response(text=text, content_type="text/html")
        return original(path, *args, **kwargs)

    core.web.FileResponse = response
