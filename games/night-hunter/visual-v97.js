(()=>{
'use strict';
const $=id=>document.getElementById(id);
const stage=$('stage'),gameCanvas=$('game'),roomName=$('roomName'),interactLabel=$('interactLabel'),threatBar=$('threatBar'),soundIndicator=$('soundIndicator'),hideOverlay=$('hideOverlay'),hideShadow=$('hideShadow'),hideTitle=$('hideTitle'),hideMessage=$('hideMessage'),searchOverlay=$('searchOverlay'),searchGrid=$('searchGrid'),searchDanger=$('searchDanger'),joystick=$('joystick'),mapToggle=$('mapToggle');
const slots=[[4,6,20,24,-8],[28,5,20,24,5],[52,7,20,24,-3],[76,5,19,24,7],[6,36,21,25,4],[31,34,20,25,-6],[55,36,20,25,6],[78,34,18,25,-4],[5,67,20,25,-5],[29,66,20,25,5],[53,68,20,24,-7],[77,66,19,25,4]];
const labels={
'▥':'ПАПКА','▧':'ДОКУМЕНТ','⊕':'ДЕТАЛЬ','⌕':'ЛИНЗА','⚙':'ШЕСТЕРНЯ','◫':'КАРТА','◧':'ПЛАСТИНА','ϟ':'КАБЕЛЬ','✂':'НОЖНИЦЫ','⌘':'МОДУЛЬ','◇':'ЧИП','◌':'КАТУШКА','▤':'РЕШЁТКА','▣':'БЛОК','▰':'БАТАРЕЯ','✚':'АПТЕЧКА','🔋':'БАТАРЕЯ','💳':'КАРТА','🧪':'КОЛБА','🩹':'АПТЕЧКА','💾':'ЗАПИСЬ','⚗':'РЕАКТИВ','⚗️':'РЕАКТИВ','🔌':'КАБЕЛЬ','🔧':'КЛЮЧ','🪛':'ОТВЁРТКА','🔩':'БОЛТ','⚙️':'ШЕСТЕРНЯ','🧰':'ИНСТРУМЕНТЫ','🪚':'ПИЛА','✉':'КОНВЕРТ','✉️':'КОНВЕРТ','📁':'ПАПКА','📄':'ДОКУМЕНТ','📷':'ФОТО','🩺':'ПРИБОР','💉':'ШПРИЦ','🧻':'БИНТ','✂️':'НОЖНИЦЫ','🧤':'ПЕРЧАТКИ','🧬':'ОБРАЗЕЦ','🔬':'МИКРОСКОП','🧫':'ЧАШКА','🧲':'МАГНИТ','📼':'КАССЕТА','📀':'ДИСК','🔍':'ЛИНЗА','🗝':'КЛЮЧ','🗝️':'КЛЮЧ'
};
let decoratedFor=null,lastUiUpdate=0,lastHidden=null,lastHideTitle='',lastHideMessage='',lastRoomKey='',lastDangerClass='',lastDangerText='';
function setText(el,value){if(el&&el.textContent!==value)el.textContent=value}
function roomKey(text){text=(text||'').toUpperCase();if(text.includes('ЛАБОР'))return'lab';if(text.includes('АРХИВ'))return'archive';if(text.includes('МЕД'))return'med';if(text.includes('ГЕНЕР'))return'generator';if(text.includes('ЛИФТ'))return'elevator';if(text.includes('ОХРАН'))return'security';return'corridor'}
function syncRoom(){const key=roomKey(roomName?.textContent);if(stage&&key!==lastRoomKey){stage.dataset.room=key;lastRoomKey=key}}
function percentThreat(){const value=parseFloat(threatBar?.style.width||'0');return Number.isFinite(value)?value:0}
function syncHide(){
 const hidden=(interactLabel?.textContent||'').toUpperCase().includes('ВЫЙТИ');
 if(hidden!==lastHidden){hideOverlay?.classList.toggle('hidden',!hidden);lastHidden=hidden}
 if(!hidden)return;
 const threat=percentThreat(),sound=(soundIndicator?.textContent||'').toUpperCase();
 const near=threat>42||sound.includes('ШАГ')||sound.includes('БЕГ')||sound.includes('ШОРОХ');
 hideShadow?.classList.toggle('visible',near);
 hideOverlay?.classList.toggle('danger',threat>72);
 if(hideShadow){const x=sound.includes('←')?'-65%':sound.includes('→')?'-35%':'-50%';if(hideShadow.style.getPropertyValue('--shadow-x')!==x)hideShadow.style.setProperty('--shadow-x',x)}
 const title=threat>82?'ОН У ШКАФА':'ТЫ В УКРЫТИИ';
 const message=threat>82?'Не двигайся. Он проверяет комнату':threat>48?'Шаги становятся громче':'Слушай шаги и не включай свет';
 if(title!==lastHideTitle){setText(hideTitle,title);lastHideTitle=title}
 if(message!==lastHideMessage){setText(hideMessage,message);lastHideMessage=message}
}
function makePaperDraggable(el){
 if(el.dataset.dragReady)return;el.dataset.dragReady='1';let startX=0,startY=0,dx=0,dy=0,pointerId=null;
 el.addEventListener('pointerdown',event=>{event.preventDefault();pointerId=event.pointerId;startX=event.clientX-dx;startY=event.clientY-dy;el.classList.add('dragging');el.setPointerCapture?.(pointerId)});
 el.addEventListener('pointermove',event=>{if(event.pointerId!==pointerId)return;dx=event.clientX-startX;dy=event.clientY-startY;el.style.setProperty('--drag-x',dx+'px');el.style.setProperty('--drag-y',dy+'px')});
 const end=event=>{if(pointerId===null||event.pointerId!==pointerId)return;el.classList.remove('dragging');if(Math.hypot(dx,dy)>35){el.classList.add('removed','moved');el.click()}pointerId=null};
 el.addEventListener('pointerup',end);el.addEventListener('pointercancel',end)
}
function decorateSearch(){
 if(!searchOverlay||searchOverlay.classList.contains('hidden')){decoratedFor=null;return}
 const signature=(searchGrid?.childElementCount||0)+':'+($('searchTargetName')?.textContent||'');
 if(decoratedFor===signature)return;decoratedFor=signature;
 const children=[...(searchGrid?.children||[])];let itemIndex=0;
 for(const el of children){
  if(el.dataset.cover==='1'||el.classList.contains('cover')){
   el.classList.remove('loot-item','cover');el.classList.add('search-paper');el.textContent='';
   el.style.left=6+Math.random()*55+'%';el.style.top=12+Math.random()*58+'%';el.style.width=31+Math.random()*18+'%';el.style.height=52+Math.random()*30+'px';el.style.setProperty('--rotation',(-12+Math.random()*24)+'deg');makePaperDraggable(el);continue
  }
  const slot=slots[itemIndex%slots.length];itemIndex++;const icon=(el.textContent||'').trim();
  el.classList.remove('loot-item');el.classList.add('search-object');el.style.left=slot[0]+'%';el.style.top=slot[1]+'%';el.style.width=slot[2]+'%';el.style.height=slot[3]+'%';el.style.setProperty('--rotation',slot[4]+'deg');el.innerHTML=`<span>${icon}</span><small>${labels[icon]||'ДЕТАЛЬ'}</small>`
 }
}
function syncSearchDanger(){
 if(!searchDanger)return;const threat=percentThreat();
 const className=threat>75?'high':threat>45?'medium':'';
 const text=threat>75?'ШАГИ: СОВСЕМ РЯДОМ':threat>45?'ШАГИ: БЛИЗКО':'ШУМ: РАСТЁТ';
 if(className!==lastDangerClass){searchDanger.className=className;lastDangerClass=className}
 if(text!==lastDangerText){setText(searchDanger,text);lastDangerText=text}
}
function update(now){
 if(now-lastUiUpdate>=80){lastUiUpdate=now;syncRoom();syncHide();decorateSearch();syncSearchDanger()}
 requestAnimationFrame(update)
}
if(gameCanvas)gameCanvas.style.filter='brightness(1.12) contrast(1.035) saturate(1.04)';
if(hideOverlay){hideOverlay.style.pointerEvents='none';hideOverlay.style.background='rgba(0,0,0,.14)'}
if(mapToggle)mapToggle.textContent='🗺';
joystick?.addEventListener('pointerdown',()=>joystick.classList.add('used'),{once:true});
requestAnimationFrame(update)
})();