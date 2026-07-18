(()=>{
'use strict';
const $=s=>document.querySelector(s);const $$=s=>[...document.querySelectorAll(s)];
const stage=$('#bossStage'),hp=$('#bossHpFill'),hpText=$('#bossHpText'),phaseText=$('#phaseText'),logs=$('#logs');
const layer=document.createElement('div');layer.className='v17-layer';layer.innerHTML='<div class="event-banner" id="v17Banner"></div><div class="phase-splash" id="v17Phase"><div><b></b><small></small></div></div><div class="screen-flash" id="v17Flash"></div>';document.body.appendChild(layer);
const loader=document.createElement('div');loader.className='loading-raid';loader.innerHTML='<div style="text-align:center"><div class="rune"></div><h2>ЦЕНТР ВСЕЛЕННОЙ</h2><p>Пробуждаем босса…</p></div>';document.body.appendChild(loader);
setTimeout(()=>loader.classList.add('hide'),1100);setTimeout(()=>loader.remove(),1800);
if(hp&&hp.parentElement){const trail=document.createElement('div');trail.className='hp-trail';trail.style.width=hp.style.width||'100%';hp.parentElement.insertBefore(trail,hp);}
let lastHp=null,lastPhase='',bannerTimer;
function banner(text){const el=$('#v17Banner');el.textContent=text;el.classList.add('show');clearTimeout(bannerTimer);bannerTimer=setTimeout(()=>el.classList.remove('show'),2200)}
function flash(type=''){const el=$('#v17Flash');el.className='screen-flash '+type;void el.offsetWidth;el.classList.add('show')}
function number(text,type,x=innerWidth*.5,y=innerHeight*.38){const el=document.createElement('div');el.className='floating-number '+type;el.textContent=text;el.style.left=`${x+(Math.random()*50-25)}px`;el.style.top=`${y+(Math.random()*35-18)}px`;document.body.appendChild(el);setTimeout(()=>el.remove(),1100)}
function phaseSplash(value){const el=$('#v17Phase'),b=el.querySelector('b'),s=el.querySelector('small');b.textContent=value==='ПОБЕДА'?'ПОБЕДА':`ФАЗА ${value}`;s.textContent=value==='ПОБЕДА'?'Эго босса разрушено':'Босс становится опаснее';el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1350);flash();}
function parseHp(){const m=(hpText?.textContent||'').replace(/\s/g,'').match(/(\d+)\/(\d+)/);return m?{cur:+m[1],max:+m[2]}:null}
function updateScene(){const p=parseHp();if(p&&p.max){const ratio=p.cur/p.max;stage?.classList.toggle('low-hp',ratio<=.25);if(lastHp!==null&&p.cur<lastHp){const dmg=lastHp-p.cur;number(`−${dmg}`,dmg>500?'critical':'damage');stage?.classList.remove('hit-react');void stage?.offsetWidth;stage?.classList.add('hit-react');flash();const trail=$('.hp-trail');if(trail){trail.style.width=`${lastHp/p.max*100}%`;setTimeout(()=>trail.style.width=`${ratio*100}%`,40)}}lastHp=p.cur;}
 const ph=phaseText?.textContent||'';const n=parseInt(ph)||0;stage?.classList.remove('phase-1','phase-2','phase-3','phase-4');if(n)stage?.classList.add(`phase-${n}`);if(lastPhase&&ph&&ph!==lastPhase)phaseSplash(ph);if(ph)lastPhase=ph;
}
function classifyLogs(){if(!logs)return;$$('#logs .log-entry').forEach(el=>{const t=el.textContent.toLowerCase();el.classList.remove('log-damage','log-heal','log-shield','log-ability');if(/леч|восстанов|hp/.test(t))el.classList.add('log-heal');else if(/щит|защит|отраз/.test(t))el.classList.add('log-shield');else if(/способ|кульминац|✨/.test(t))el.classList.add('log-ability');else if(/урон|задел|атак|−/.test(t))el.classList.add('log-damage')})}
const observer=new MutationObserver(()=>{updateScene();classifyLogs()});observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['style','class']});
function actionFx(type,button){const r=button.getBoundingClientRect(),x=r.left+r.width/2,y=r.top;if(type==='heal'){flash('heal');number('+HP','heal',x,y);banner('✚ ЛЕЧЕНИЕ АКТИВИРОВАНО')}else if(type==='defend'){flash('shield');number('ЩИТ','block',x,y);banner('🛡 ЗАЩИТА АКТИВНА')}else if(type==='ability'){flash();number('СПОСОБНОСТЬ','critical',x,y);banner('✦ СПОСОБНОСТЬ РОЛИ')}else{flash();number('УДАР','damage',x,y)}}
$$('[data-action]').forEach(btn=>btn.addEventListener('click',()=>{if(!btn.disabled)actionFx(btn.dataset.action,btn)},true));
$$('.bottom-nav button').forEach(btn=>btn.addEventListener('click',()=>{btn.classList.remove('nav-anim');void btn.offsetWidth;btn.classList.add('nav-anim')},true));
updateScene();classifyLogs();
setTimeout(()=>banner('⚔ РЕЙД НАЧАЛСЯ'),1900);
})();