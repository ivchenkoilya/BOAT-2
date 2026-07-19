(()=>{
'use strict';
const $=id=>document.getElementById(id);
const stage=$('bossStage');
const modal=$('modal');
const modalContent=$('modalContent');
let lastPhase=$('phaseText')?.textContent||'';
let animationEnabled=localStorage.getItem('raidAnimations')!=='off';
let vibrationEnabled=localStorage.getItem('raidVibration')!=='off';

function replay(el,cls,ms=800){if(!el||!animationEnabled)return;el.classList.remove(cls);void el.offsetWidth;el.classList.add(cls);setTimeout(()=>el.classList.remove(cls),ms)}
function helpMarkup(){return `<div class="help-tabs"><button class="active" data-help-tab="play">КАК ИГРАТЬ</button><button data-help-tab="about">ОБ ИГРЕ</button><button data-help-tab="settings">ЭФФЕКТЫ</button></div>
<section class="help-panel active" data-help-panel="play"><h3>КАК ПОБЕДИТЬ ЭГО</h3>
<div class="help-step"><span>⚔</span><div><b>Задеть эго</b><small>Основной удар. Нажимай после окончания короткого кулдауна.</small></div></div>
<div class="help-step"><span>🛡</span><div><b>Защита</b><small>Снижает урон следующей атаки босса.</small></div></div>
<div class="help-step"><span>✚</span><div><b>Лечение</b><small>Восстанавливает здоровье героя, если оно не полное.</small></div></div>
<div class="help-step"><span>✦</span><div><b>Способность роли</b><small>Сильное особое действие с долгой перезарядкой.</small></div></div>
<div class="help-step"><span>4</span><div><b>Фазы босса</b><small>Чем меньше HP у Центра Вселенной, тем опаснее его атаки.</small></div></div></section>
<section class="help-panel" data-help-panel="about"><h3>О ЦЕНТРЕ ВСЕЛЕННОЙ</h3><p class="help-copy">Общий рейдовый босс для участников чата. Герои объединяются, наносят урон, лечат отряд и защищаются от атак. Победа засчитывается всему отряду, а рейтинг определяет самых влиятельных участников боя.</p><p class="help-copy">Каждая роль получает собственную способность. Состояние боя синхронизируется с сервером, поэтому здоровье и рейтинг общие для всех игроков.</p><p class="help-copy"><b>Версия интерфейса:</b> Battle HUD 7</p></section>
<section class="help-panel" data-help-panel="settings"><h3>ЭФФЕКТЫ</h3><div class="settings-row"><span>Боевые анимации</span><button class="switch ${animationEnabled?'on':''}" data-setting="animations" aria-label="Боевые анимации"></button></div><div class="settings-row"><span>Вибрация Telegram</span><button class="switch ${vibrationEnabled?'on':''}" data-setting="vibration" aria-label="Вибрация"></button></div><p class="help-copy">Отключение анимаций уменьшает нагрузку на слабых телефонах.</p></section>`}
function openHelp(){modalContent.dataset.type='help';modalContent.innerHTML=helpMarkup();modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';window.Telegram?.WebApp?.BackButton?.show?.()}
function setupHelp(){document.addEventListener('click',e=>{
 const help=e.target.closest('[data-open-help]');if(help){openHelp();return}
 const tab=e.target.closest('[data-help-tab]');if(tab){document.querySelectorAll('[data-help-tab]').forEach(b=>b.classList.toggle('active',b===tab));document.querySelectorAll('[data-help-panel]').forEach(p=>p.classList.toggle('active',p.dataset.helpPanel===tab.dataset.helpTab));return}
 const setting=e.target.closest('[data-setting]');if(setting){if(setting.dataset.setting==='animations'){animationEnabled=!animationEnabled;localStorage.setItem('raidAnimations',animationEnabled?'on':'off')}else{vibrationEnabled=!vibrationEnabled;localStorage.setItem('raidVibration',vibrationEnabled?'on':'off')}setting.classList.toggle('on');return}
 const action=e.target.closest('[data-action]');if(!action||action.disabled)return;const type=action.dataset.action;
 if(vibrationEnabled)window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.(type==='hit'?'heavy':'medium');
 if(type==='hit'||type==='ability')replay(stage,'hit',430);
 if(type==='heal'){replay(document.querySelector('.fx-heal'),'play',850);document.querySelectorAll('.fighter').forEach(x=>replay(x,'heal-flash',720))}
 if(type==='defend')replay(document.querySelector('.fx-shield'),'play',800);
});}
function observePhase(){const phase=$('phaseText');if(!phase)return;new MutationObserver(()=>{const next=phase.textContent;if(next&&next!==lastPhase&&lastPhase){const overlay=$('phaseTransition');if(overlay){overlay.textContent=next==='ПОБЕДА'?'ЭГО РАЗРУШЕНО':`ФАЗА ${next}`;replay(overlay,'show',1500)}}lastPhase=next}).observe(phase,{childList:true,subtree:true,characterData:true})}
function timerSeconds(value){const parts=String(value||'').trim().split(':').map(Number);if(parts.some(Number.isNaN))return 999;if(parts.length===3)return parts[0]*3600+parts[1]*60+parts[2];if(parts.length===2)return parts[0]*60+parts[1];return parts.length===1?parts[0]:999}
function observeBossWarning(){const next=$('nextAction');if(!next)return;let warned=false;setInterval(()=>{const seconds=timerSeconds(next.textContent);if(seconds<=3&&seconds>=0&&!warned){warned=true;replay($('bossWarning'),'show',3100)}if(seconds>4)warned=false},200)}
function clarifyBossEffects(){
 const panel=$('bossEffectsPanel');
 const toggle=$('bossEffectsToggle');
 const shield=$('shieldText');
 const effect=$('effectText');
 if(toggle){const label=toggle.querySelector('span');if(label)label.textContent='СТАТУС БОССА';toggle.setAttribute('aria-label','Показать активные эффекты босса')}
 if(panel&&!panel.querySelector('.effects-explainer')){
  const title=document.createElement('div');
  title.className='effects-explainer';
  title.innerHTML='<b>ЧТО СЕЙЧАС ДЕЛАЕТ БОСС</b><small>Эти эффекты мешают вашему отряду</small>';
  panel.prepend(title);
  const items=panel.querySelectorAll('.effect-item');
  if(items[0]){const b=items[0].querySelector('b'),s=items[0].querySelector('small');if(b)b.textContent='Сарказм';if(s)s.textContent='Ослабляет ваши обычные удары'}
  if(items[1]){const b=items[1].querySelector('b');if(b)b.textContent='Щит ЧСВ'}
  if(items[2]){const b=items[2].querySelector('b');if(b)b.textContent='Особый эффект'}
 }
 const rewrite=()=>{
  if(shield){const raw=shield.textContent.trim();const match=raw.match(/(\d+)/);const next=raw==='разбит'?'Щит разрушен':match?`Ослабит ещё ${match[1]} ударов`:raw;if(next&&next!==raw)shield.textContent=next}
  if(effect){const raw=effect.textContent.trim();let next=raw;if(/^антихил\s+/i.test(raw))next=`Лечение заблокировано · ${raw.replace(/^антихил\s+/i,'')}`;else if(raw==='атака сорвана')next='Следующая атака сорвана';else if(raw==='нет')next='Нет активного эффекта';if(next!==raw)effect.textContent=next}
 };
 rewrite();
 [shield,effect].filter(Boolean).forEach(node=>new MutationObserver(rewrite).observe(node,{childList:true,subtree:true,characterData:true}));
}
function observeFighters(){const fighters=$('fighters');if(!fighters)return;let previous=new Map();new MutationObserver(()=>{document.querySelectorAll('.fighter').forEach((card,index)=>{const hp=card.querySelector('em')?.textContent||'';if(previous.has(index)&&previous.get(index)!==hp)replay(card,'hp-changed',520);previous.set(index,hp)})}).observe(fighters,{childList:true,subtree:true})}
setupHelp();observePhase();observeBossWarning();clarifyBossEffects();observeFighters();
})();
