(()=>{
'use strict';
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();tg?.setHeaderColor?.('#071012');tg?.setBackgroundColor?.('#071012');
const $=id=>document.getElementById(id);
const canvas=$('game'),ctx=canvas.getContext('2d'),light=document.createElement('canvas'),lctx=light.getContext('2d');
const params=new URLSearchParams(location.search),chatId=params.get('chat_id')||'';
const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
let vw=1,vh=1,dpr=1,raf=0,last=performance.now(),audio=null;
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const distance=(a,b,c,d)=>Math.hypot(c-a,d-b);
const lerp=(a,b,t)=>a+(b-a)*t;
const loopCount=Math.max(0,Number(localStorage.getItem('nightHunterFactoryLoop')||0));
const shiftNumber=184+loopCount;

const OUTSIDE={w:1100,h:700};
const FACTORY={w:1800,h:1000};
const points={
 gate:{x:930,y:390,label:'ПРОХОДНАЯ'},
 post:{x:235,y:335,label:'ПОСТ ДЕЖУРНОГО'},
 machine4:{x:740,y:245,label:'СТАНОК №4'},
 switchboard:{x:1415,y:790,label:'ЭЛЕКТРОЩИТОВАЯ'},
 locker:{x:1090,y:160,label:'ШКАФЧИК МАСТЕРА'},
 compressor:{x:1150,y:590,label:'КОМПРЕССОРНАЯ'},
 oldDoor:{x:1610,y:525,label:'СТАРЫЙ ЦЕХ'},
 machine0:{x:1500,y:220,label:'СТАНОК №0'}
};
const optionalNotes=[
 {id:'maintenance',x:930,y:735,title:'Наряд на ремонт №047',kind:'ТЕХНИЧЕСКИЙ ДОКУМЕНТ',body:'Дата: сегодня.\nИсполнитель: И. Ивченков.\n\nРаботы выполнены в 05:55. Станок №0 запущен вручную.\n\nПодпись исполнителя уже стоит, хотя ты видишь этот лист впервые.'},
 {id:'photo',x:1430,y:275,title:'Фотография ночной бригады',kind:'АРХИВНАЯ ФОТОГРАФИЯ',body:'На обороте написано: «Смена №12».\n\nСреди рабочих стоит человек с твоим лицом. Фотография выцвела так сильно, будто ей несколько десятилетий.'}
];
const noteDefs={
 rules:{title:'Правила ночной смены',kind:'ИНСТРУКЦИЯ НА ПОСТУ',body:'1. После 23:00 не заходить в старый цех.\n2. Если станок работает без оператора — не нажимать аварийную остановку.\n3. Не отвечать на внутренний номер 047.\n4. Если услышишь три удара пресса — выключи фонарь.\n5. Не принимай смену повторно.'},
 operator:{title:'Записка предыдущего оператора',kind:'ЗАПИСКА В ШКАФЧИКЕ',body:'Я снова всё забыл.\n\nНе верь мастеру. Камеры показывают не прошлое, а следующую попытку. Пока неисправность существует, оно не может выйти из старого цеха.\n\nНе заканчивай ремонт станка №0.'},
 maintenance:optionalNotes[0],photo:optionalNotes[1]
};
const solids=[
 {x:60,y:60,w:350,h:250},{x:480,y:105,w:250,h:250},{x:800,y:105,w:250,h:250},{x:1120,y:105,w:250,h:250},
 {x:470,y:520,w:330,h:190},{x:870,y:520,w:250,h:190},{x:1190,y:500,w:250,h:230},{x:1450,y:690,w:260,h:190},
 {x:1535,y:95,w:210,h:310}
];
const shadowSpots=[{x:1020,y:440},{x:570,y:830},{x:1460,y:450},{x:840,y:420},{x:1600,y:610}];

const state={
 running:false,paused:false,demo:false,sessionId:null,scene:'outside',phase:0,score:0,repairs:0,
 signature:null,battery:100,flashlight:false,flashlightUnlocked:false,clock:'17:42',objective:'ДОЙДИ ДО ПРОХОДНОЙ',
 captionUntil:0,notes:new Set(),modal:null,cameraMode:null,cameraViewed:new Set(),repairType:null,
 ending:false,endingType:null,endingSubmitted:false,oldShopOpen:false,anomalySeen:false,
 shadow:{visible:false,x:0,y:0,until:0,next:0},checkpoint:{x:150,y:850}
};
const player={x:120,y:480,r:15,speed:165,facingX:1,facingY:0,walk:0};
const joy={id:null,x:0,y:0},keys=new Set(),camera={x:0,y:0};
let actionHeld=false,actionPointer=null,actionProgress=0,currentInteraction=null;

async function api(path,body={}){
 const r=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});
 const d=await r.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
 if(!r.ok||!d.ok)throw new Error(d.reason||'Ошибка игрового сервера.');return d;
}
function goGames(){location.href='/games/?'+new URLSearchParams({...Object.fromEntries(params),chat_id:chatId}).toString()}
function vibrate(type='light'){try{tg?.HapticFeedback?.impactOccurred?.(type)}catch(_){}}
function initAudio(){if(audio)return;try{const ac=new(window.AudioContext||window.webkitAudioContext)(),master=ac.createGain();master.gain.value=.1;master.connect(ac.destination);audio={ac,master}}catch(_){}}
function tone(freq=180,duration=.08,type='sine',volume=.12){if(!audio)return;const o=audio.ac.createOscillator(),g=audio.ac.createGain();o.type=type;o.frequency.value=freq;g.gain.setValueAtTime(volume,audio.ac.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.ac.currentTime+duration);o.connect(g).connect(audio.master);o.start();o.stop(audio.ac.currentTime+duration)}
function resize(){const r=canvas.getBoundingClientRect();vw=Math.max(1,r.width);vh=Math.max(1,r.height);dpr=Math.min(2,devicePixelRatio||1);canvas.width=Math.round(vw*dpr);canvas.height=Math.round(vh*dpr);light.width=canvas.width;light.height=canvas.height;ctx.setTransform(dpr,0,0,dpr,0,0);lctx.setTransform(dpr,0,0,dpr,0,0)}
function showCaption(text,seconds=3.5){$('caption').textContent=text;state.captionUntil=performance.now()+seconds*1000}
function banner(small,big){const el=$('eventBanner');el.querySelector('small').textContent=small;el.querySelector('b').textContent=big;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1800)}
function setTask(clock,objective,location,caption){state.clock=clock;state.objective=objective;if(location)$('location').textContent=location;if(caption)showCaption(caption,4)}
function staticBurst(ms=650){const el=$('staticFx');el.classList.add('show');tone(58,.18,'sawtooth',.16);setTimeout(()=>el.classList.remove('show'),ms);vibrate('medium')}
function pauseFor(id){state.paused=true;state.modal=id;$(id).classList.remove('hidden');resetJoystick();actionHeld=false;actionProgress=0}
function closeModal(id){$(id).classList.add('hidden');if(state.modal===id)state.modal=null;state.paused=false}

function rounded(x,y,w,h,r=10){ctx.beginPath();ctx.roundRect(x,y,w,h,r)}
function drawPlayer(now){
 const moving=Math.hypot(joy.x,joy.y)>.08||keys.size>0,step=moving?Math.sin(player.walk)*4:0,a=Math.atan2(player.facingY,player.facingX),breath=Math.sin(now/470)*.7;
 ctx.save();ctx.translate(player.x,player.y);ctx.rotate(a);ctx.fillStyle='#0007';ctx.beginPath();ctx.ellipse(2,12,20,11,0,0,Math.PI*2);ctx.fill();
 ctx.strokeStyle='#1b292d';ctx.lineWidth=8;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-5,7);ctx.lineTo(-8-step,25);ctx.moveTo(6,7);ctx.lineTo(9+step,25);ctx.stroke();
 ctx.fillStyle='#28474a';rounded(-16,-15+breath,32,35,9);ctx.fill();ctx.fillStyle='#122024';rounded(-20,-10+breath,10,26,5);ctx.fill();
 ctx.fillStyle='#e7ad89';ctx.beginPath();ctx.arc(0,-19+breath,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#17272a';ctx.beginPath();ctx.arc(0,-22+breath,10,Math.PI,Math.PI*2);ctx.fill();
 if(state.flashlightUnlocked){ctx.strokeStyle='#d7e1dd';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(10,-2+breath);ctx.lineTo(31,-2+breath);ctx.stroke();ctx.fillStyle=state.flashlight?'#fff0a8':'#536064';ctx.fillRect(28,-6+breath,11,8)}
 ctx.restore();
}
function drawOutside(now){
 ctx.fillStyle='#e8d4a6';ctx.fillRect(0,0,OUTSIDE.w,OUTSIDE.h);ctx.fillStyle='#434b4f';ctx.fillRect(0,0,OUTSIDE.w,230);ctx.fillStyle='#2d3437';ctx.fillRect(0,0,OUTSIDE.w,18);ctx.strokeStyle='#f3e5b099';ctx.lineWidth=5;ctx.setLineDash([44,30]);ctx.beginPath();ctx.moveTo(0,112);ctx.lineTo(OUTSIDE.w,112);ctx.stroke();ctx.setLineDash([]);
 for(let i=0;i<5;i++){const x=((now*.042+i*275)%1450)-190,y=i%2?145:48;ctx.fillStyle=i%2?'#78504b':'#456979';rounded(x,y,90,42,11);ctx.fill();ctx.fillStyle='#cce8ed88';ctx.fillRect(x+17,y+7,48,13)}
 ctx.fillStyle='#c7b98f';ctx.fillRect(0,230,OUTSIDE.w,470);ctx.strokeStyle='#fff2';ctx.lineWidth=1;for(let y=260;y<700;y+=60){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(OUTSIDE.w,y);ctx.stroke()}for(let x=10;x<1100;x+=85){ctx.beginPath();ctx.moveTo(x,230);ctx.lineTo(x,700);ctx.stroke()}
 const trees=[[130,330],[330,570],[560,330],[745,570]];for(const [x,y] of trees){ctx.fillStyle='#5c4125';ctx.fillRect(x-5,y,10,35);const s=Math.sin(now/900+x)*2.5;ctx.fillStyle='#659b61';ctx.beginPath();ctx.arc(x+s,y-18,28,0,Math.PI*2);ctx.arc(x-21+s*.5,y-2,20,0,Math.PI*2);ctx.arc(x+20+s*.5,y-2,20,0,Math.PI*2);ctx.fill()}
 ctx.fillStyle='#26383d';ctx.fillRect(820,190,280,510);ctx.fillStyle='#5d8f9655';for(let y=225;y<510;y+=68)for(let x=845;x<1080;x+=58)ctx.fillRect(x,y,42,43);
 ctx.fillStyle='#111b1f';ctx.fillRect(875,325,135,250);ctx.fillStyle='#8bd1c06b';ctx.fillRect(895,355,95,180);ctx.strokeStyle='#d6fff1aa';ctx.lineWidth=3;ctx.strokeRect(895,355,95,180);ctx.fillStyle='#efd58d';ctx.font='900 18px system-ui';ctx.textAlign='center';ctx.fillText('ОРФЕЙ',942,286);ctx.font='800 10px system-ui';ctx.fillText('МАШИНОСТРОИТЕЛЬНЫЙ ЗАВОД',942,306);
 const p=(Math.sin(now/190)+1)/2;ctx.strokeStyle=`rgba(255,224,137,${.5+p*.4})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(points.gate.x,points.gate.y,32+p*5,0,Math.PI*2);ctx.stroke();
 drawPlayer(now);
 const sun=ctx.createRadialGradient(120,80,12,120,80,420);sun.addColorStop(0,'rgba(255,248,191,.38)');sun.addColorStop(1,'rgba(255,215,120,0)');ctx.fillStyle=sun;ctx.fillRect(0,0,900,600)
}
function machine(x,y,w,h,label,color='#30484d',active=false,now=0){
 ctx.fillStyle='#0b1113';ctx.fillRect(x+9,y+10,w,h);ctx.fillStyle=color;rounded(x,y,w,h,12);ctx.fill();ctx.strokeStyle='#587177';ctx.lineWidth=3;ctx.stroke();ctx.fillStyle='#101d20';ctx.fillRect(x+14,y+14,w-28,h*.45);ctx.fillStyle=active?'#e6c974':'#4f696b';ctx.fillRect(x+w-34,y+17,13,13);ctx.fillStyle='#dbe8e4';ctx.font='900 11px system-ui';ctx.textAlign='center';ctx.fillText(label,x+w/2,y+h-17);if(active){ctx.strokeStyle='#7de8d4';ctx.lineWidth=3;ctx.beginPath();ctx.arc(x+w*.47,y+h*.35,20+Math.sin(now/100)*2,now/300,now/300+Math.PI*1.4);ctx.stroke()}}
function drawFactory(now){
 const night=state.phase>=3;ctx.fillStyle=night?'#071012':'#8c9892';ctx.fillRect(0,0,FACTORY.w,FACTORY.h);
 const floor=ctx.createLinearGradient(0,0,FACTORY.w,FACTORY.h);floor.addColorStop(0,night?'#152326':'#b6b9ac');floor.addColorStop(1,night?'#071012':'#7d8c88');ctx.fillStyle=floor;ctx.fillRect(25,25,1750,950);
 ctx.strokeStyle=night?'#d5fff00b':'#ffffff24';ctx.lineWidth=1;for(let x=40;x<1780;x+=50){ctx.beginPath();ctx.moveTo(x,25);ctx.lineTo(x,975);ctx.stroke()}for(let y=40;y<980;y+=50){ctx.beginPath();ctx.moveTo(25,y);ctx.lineTo(1775,y);ctx.stroke()}
 ctx.strokeStyle='#e0bd5d55';ctx.lineWidth=5;ctx.setLineDash([28,18]);ctx.beginPath();ctx.moveTo(420,450);ctx.lineTo(1500,450);ctx.moveTo(400,860);ctx.lineTo(1420,860);ctx.stroke();ctx.setLineDash([]);
 ctx.fillStyle=night?'#0d2226':'#547375';rounded(60,60,350,250,13);ctx.fill();ctx.strokeStyle='#6ac5ba77';ctx.lineWidth=4;ctx.stroke();ctx.fillStyle='#081417';rounded(90,90,290,90,8);ctx.fill();for(let i=0;i<4;i++){ctx.fillStyle=i===2&&state.phase>=3?'#6c1724':'#1d4a4d';ctx.fillRect(105+i*66,105,52,45);ctx.fillStyle='#8ce2d524';ctx.fillRect(111+i*66,111,20,4)}ctx.fillStyle='#d8eee9';ctx.font='900 15px system-ui';ctx.textAlign='center';ctx.fillText('ПОСТ ДЕЖУРНОГО',235,220);ctx.fillStyle='#e5d6a8';ctx.fillRect(170,235,130,18);
 machine(490,115,240,230,'СТАНОК №3','#304c50',false,now);machine(810,115,240,230,'СТАНОК №4','#304c50',state.phase===2,now);machine(1130,115,240,230,'СТАНОК №5','#304c50',state.phase>=7&&Math.floor(now/550)%2===0,now);
 machine(480,530,320,180,'ЛАЗЕРНЫЙ УЧАСТОК','#3c454b',state.phase>=4,now);machine(870,530,250,180,'ГИБОЧНЫЙ ПРЕСС','#45443c',state.phase>=5&&Math.floor(now/400)%2===0,now);
 ctx.fillStyle='#5f432b';rounded(1190,500,250,230,16);ctx.fill();ctx.strokeStyle='#b67b3f';ctx.lineWidth=4;ctx.stroke();ctx.fillStyle='#263238';ctx.beginPath();ctx.arc(1300,590,72,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#d09451';ctx.lineWidth=8;ctx.stroke();ctx.fillStyle='#e6cf8d';ctx.font='900 12px system-ui';ctx.fillText('КОМПРЕССОР',1315,700);
 ctx.fillStyle='#27363a';rounded(1450,690,260,190,12);ctx.fill();ctx.strokeStyle='#6b7d7f';ctx.lineWidth=3;ctx.stroke();for(let i=0;i<8;i++){ctx.fillStyle=i<4&&state.phase===4?'#8a2e3d':'#355c54';ctx.fillRect(1475+(i%4)*52,720+Math.floor(i/4)*65,30,44)}ctx.fillStyle='#dbe8e4';ctx.font='900 12px system-ui';ctx.fillText('ГЛАВНЫЙ ЩИТ',1580,858);
 ctx.fillStyle='#394c50';ctx.fillRect(1160,75,100,95);ctx.strokeStyle='#70878b';ctx.strokeRect(1160,75,100,95);ctx.fillStyle='#d3c17e';ctx.font='900 9px system-ui';ctx.fillText('МАСТЕР',1210,128);
 ctx.fillStyle='#0b1113';ctx.fillRect(1535,95,210,310);ctx.strokeStyle=state.oldShopOpen?'#efcf79':'#71333e';ctx.lineWidth=4;ctx.strokeRect(1535,95,210,310);ctx.fillStyle=state.oldShopOpen?'#e5cb78':'#ff5a71';ctx.font='900 13px system-ui';ctx.fillText(state.oldShopOpen?'СТАРЫЙ ЦЕХ ОТКРЫТ':'СТАРЫЙ ЦЕХ · ЗАКРЫТ',1640,455);
 if(state.oldShopOpen){machine(1548,108,184,270,'СТАНОК №0','#26171c',state.phase>=9,now);ctx.fillStyle='#ff4c6622';ctx.fillRect(1548,108,184,270)}
 for(const n of optionalNotes){if(state.notes.has(n.id))continue;ctx.save();ctx.translate(n.x,n.y);ctx.fillStyle='#ead8a8';ctx.rotate(-.12);ctx.fillRect(-13,-17,26,34);ctx.fillStyle='#6e5637';ctx.fillRect(-7,-8,14,2);ctx.fillRect(-7,-2,14,2);ctx.restore()}
 const t=getMainTarget();if(t){const pulse=(Math.sin(now/170)+1)/2;ctx.strokeStyle=`rgba(243,210,126,${.5+pulse*.4})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(t.x,t.y,29+pulse*5,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#efd486';ctx.font='900 9px system-ui';ctx.fillText(t.label,t.x,t.y-40)}
 if(state.shadow.visible){ctx.save();ctx.translate(state.shadow.x,state.shadow.y);ctx.globalAlpha=.82;ctx.fillStyle='#010304';ctx.beginPath();ctx.ellipse(0,12,22,48,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(0,-38,17,0,Math.PI*2);ctx.fill();ctx.fillStyle='#ff3e58';ctx.beginPath();ctx.arc(-5,-40,2.5,0,Math.PI*2);ctx.arc(5,-40,2.5,0,Math.PI*2);ctx.fill();ctx.restore()}
 drawPlayer(now);
}
function drawFlashlight(){
 if(state.scene!=='factory'||state.phase<2)return;const darkness=state.flashlight?0.68:0.86;lctx.setTransform(dpr,0,0,dpr,0,0);lctx.clearRect(0,0,vw,vh);lctx.fillStyle=`rgba(0,0,0,${darkness})`;lctx.fillRect(0,0,vw,vh);
 const px=player.x-camera.x,py=player.y-camera.y,a=Math.atan2(player.facingY,player.facingX);lctx.globalCompositeOperation='destination-out';
 const amb=lctx.createRadialGradient(px,py,4,px,py,state.flashlight?72:28);amb.addColorStop(0,'rgba(0,0,0,.95)');amb.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=amb;lctx.beginPath();lctx.arc(px,py,state.flashlight?74:30,0,Math.PI*2);lctx.fill();
 if(state.flashlight){lctx.save();lctx.translate(px,py);lctx.rotate(a);const beam=lctx.createLinearGradient(0,0,560,0);beam.addColorStop(0,'rgba(0,0,0,1)');beam.addColorStop(.7,'rgba(0,0,0,.78)');beam.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=beam;lctx.beginPath();lctx.moveTo(0,-14);lctx.lineTo(560,-105);lctx.lineTo(560,105);lctx.lineTo(0,14);lctx.closePath();lctx.fill();lctx.restore()}
 lctx.globalCompositeOperation='source-over';ctx.drawImage(light,0,0,vw,vh)
}
function render(now){
 const world=state.scene==='outside'?OUTSIDE:FACTORY,maxX=Math.max(0,world.w-vw),maxY=Math.max(0,world.h-vh),tx=clamp(player.x-vw/2,0,maxX),ty=clamp(player.y-vh/2,0,maxY);camera.x=lerp(camera.x,tx,.12);camera.y=lerp(camera.y,ty,.12);
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vw,vh);ctx.save();ctx.translate(-camera.x,-camera.y);if(state.scene==='outside')drawOutside(now);else drawFactory(now);ctx.restore();drawFlashlight();
}

function moveVector(){let x=joy.x,y=joy.y;if(keys.has('a')||keys.has('arrowleft'))x--;if(keys.has('d')||keys.has('arrowright'))x++;if(keys.has('w')||keys.has('arrowup'))y--;if(keys.has('s')||keys.has('arrowdown'))y++;const m=Math.hypot(x,y);return m>1?{x:x/m,y:y/m,m:1}:{x,y,m}}
function pointInRect(x,y,r,p=0){return x>=r.x-p&&x<=r.x+r.w+p&&y>=r.y-p&&y<=r.y+r.h+p}
function canMoveFactory(x,y){if(x<35||x>1765||y<35||y>965)return false;for(const s of solids)if(pointInRect(x,y,s,player.r-2))return false;if(!state.oldShopOpen&&x>1515&&x<1760&&y>70&&y<430)return false;return true}
function updatePlayer(dt){const v=moveVector();if(v.m>.06){player.facingX=v.x;player.facingY=v.y;const speed=player.speed*(state.flashlight&&state.phase>=4?.94:1),nx=player.x+v.x*speed*dt,ny=player.y+v.y*speed*dt;if(state.scene==='outside'){player.x=clamp(nx,35,1065);player.y=clamp(ny,245,665)}else{if(canMoveFactory(nx,player.y))player.x=nx;if(canMoveFactory(player.x,ny))player.y=ny}player.walk+=dt*12}}
function inFlashlight(x,y){if(!state.flashlight)return false;const dx=x-player.x,dy=y-player.y,d=Math.hypot(dx,dy);if(d>570||d<1)return false;return (dx/d)*player.facingX+(dy/d)*player.facingY>.88}
function updateShadow(now){
 if(state.scene!=='factory'||state.phase<4||state.phase>=10||state.paused)return;
 if(state.shadow.visible){if(now>state.shadow.until||inFlashlight(state.shadow.x,state.shadow.y)){state.shadow.visible=false;state.shadow.next=now+7000+Math.random()*6500;if(inFlashlight(state.shadow.x,state.shadow.y)){staticBurst(280);showCaption('Фигура исчезла, когда луч коснулся её лица.',3)}}else if(distance(player.x,player.y,state.shadow.x,state.shadow.y)<75&&!state.flashlight){state.shadow.visible=false;state.battery=Math.max(0,state.battery-16);state.shadow.next=now+9000;staticBurst(900);showCaption('Что-то прошло совсем рядом. На рации остался только твой голос.',4)}}
 else if(now>state.shadow.next){const spots=shadowSpots.filter(p=>distance(player.x,player.y,p.x,p.y)>280),p=spots[Math.floor(Math.random()*spots.length)]||shadowSpots[0];state.shadow.visible=true;state.shadow.x=p.x;state.shadow.y=p.y;state.shadow.until=now+4200;state.shadow.next=now+11000}
}
function updateBattery(dt){if(!state.flashlightUnlocked)return;if(state.flashlight){state.battery=Math.max(0,state.battery-dt*.72);if(state.battery<=0){state.flashlight=false;$('flashlight').classList.remove('on');$('flashlightState').textContent='ПУСТО';showCaption('Фонарь разрядился. На посту осталась запасная батарея.',4)}}}

function getMainTarget(){
 if(state.scene==='outside'&&state.phase===0)return points.gate;if(state.scene!=='factory')return null;
 return ({1:points.post,2:points.machine4,3:points.post,4:points.switchboard,5:points.locker,6:points.compressor,7:points.post,8:points.oldDoor,9:points.machine0,10:points.post})[state.phase]||null
}
function nearestOptionalNote(){if(state.scene!=='factory')return null;let best=null,bd=Infinity;for(const n of optionalNotes){if(state.notes.has(n.id))continue;const d=distance(player.x,player.y,n.x,n.y);if(d<bd){best=n;bd=d}}return best&&bd<90?{note:best,distance:bd}:null}
function getInteraction(){
 if(!state.running||state.paused||state.ending)return null;const note=nearestOptionalNote();if(note)return{x:note.note.x,y:note.note.y,distance:note.distance,radius:72,label:'ПРОЧИТАТЬ',sub:note.note.title,icon:'▤',action:()=>collectNote(note.note.id)};
 const p=getMainTarget();if(!p)return null;const d=distance(player.x,player.y,p.x,p.y),base={x:p.x,y:p.y,distance:d,radius:88};
 if(state.phase===0)return{...base,label:'ПРИНЯТЬ СМЕНУ',sub:'ПОСТАВИТЬ ПОДПИСЬ',icon:'✎',action:()=>openJournal('start')};
 if(state.phase===1)return{...base,label:'СЕСТЬ ЗА ПОСТ',sub:'ПРОВЕРИТЬ КАМЕРЫ',icon:'◫',action:()=>openCameras('initial')};
 if(state.phase===2)return{...base,label:'ОТКРЫТЬ ПАНЕЛЬ',sub:'ОХЛАЖДЕНИЕ СТАНКА №4',icon:'⚙',action:()=>openRepair('coolant')};
 if(state.phase===3)return{...base,label:'ПРОВЕРИТЬ КАМЕРЫ',sub:'НЕСООТВЕТСТВИЕ В ЦЕХЕ',icon:'◉',action:()=>openCameras('anomaly')};
 if(state.phase===4)return{...base,label:'ОТКРЫТЬ ЩИТ',sub:'ВОССТАНОВИТЬ ПИТАНИЕ',icon:'⚡',action:()=>openRepair('breaker')};
 if(state.phase===5)return{...base,label:'ОТКРЫТЬ ШКАФЧИК',sub:'ЛИЧНЫЕ ВЕЩИ МАСТЕРА',icon:'▰',action:()=>{collectNote('operator');state.phase=6;setTask('00:40','ПРОВЕРЬ КОМПРЕССОРНУЮ','ОСНОВНОЙ ЦЕХ','Из компрессорной доносится стук, хотя установка отключена.')}};
 if(state.phase===6)return{...base,label:'ДИАГНОСТИКА',sub:'ВЫРОВНЯТЬ ДАВЛЕНИЕ',icon:'◌',action:()=>openRepair('compressor')};
 if(state.phase===7)return{...base,label:'ОТКРЫТЬ КАМЕРЫ',sub:'ПОЯВИЛСЯ НОВЫЙ КАНАЛ',icon:'◉',action:()=>openCameras('zero')};
 if(state.phase===8)return{...base,label:'ОТКРЫТЬ ДВЕРЬ',sub:'СТАРЫЙ ЦЕХ · КЛЮЧ 047',icon:'▣',action:()=>{state.oldShopOpen=true;state.phase=9;state.checkpoint={x:1510,y:500};setTask('02:40','НАЙДИ СТАНОК №0','СТАРЫЙ ЦЕХ','За дверью работает оборудование, которого нет на плане.');banner('ДОСТУП 047','СТАРЫЙ ЦЕХ ОТКРЫТ');staticBurst(500)}};
 if(state.phase===9)return{...base,label:'ЗАПУСТИТЬ ДИАГНОСТИКУ',sub:'СТАНОК №0',icon:'0',action:()=>openRepair('zero')};
 if(state.phase===10)return{...base,label:'ПЕРЕДАТЬ СМЕНУ',sub:'ЗАПОЛНИТЬ ЖУРНАЛ',icon:'✎',action:()=>openJournal('transfer')};return null
}
function updateAction(dt){
 currentInteraction=getInteraction();const el=$('action');if(!currentInteraction){el.classList.add('hidden');actionProgress=0;return}const show=currentInteraction.distance<currentInteraction.radius+58;el.classList.toggle('hidden',!show);if(!show){actionProgress=0;return}const near=currentInteraction.distance<currentInteraction.radius;el.disabled=!near;el.classList.toggle('ready',near);$('actionIcon').textContent=currentInteraction.icon;$('actionLabel').textContent=currentInteraction.label;$('actionSub').textContent=near?currentInteraction.sub:'ПОДОЙДИ БЛИЖЕ';if(near&&actionHeld)actionProgress=Math.min(1,actionProgress+dt/0.58);else if(!actionHeld)actionProgress=Math.max(0,actionProgress-dt*2);el.style.setProperty('--hold-angle',actionProgress.toFixed(3)+'turn');if(actionProgress>=1){actionProgress=0;actionHeld=false;el.classList.remove('holding');currentInteraction.action();vibrate('medium')}}
function updateHud(){
 $('clock').textContent=state.clock;$('objective').textContent=state.objective;$('score').textContent=Math.round(state.score);$('notesCount').textContent=state.notes.size;
 $('batteryHud').classList.toggle('hidden',!state.flashlightUnlocked);$('batteryBar').style.width=state.battery+'%';$('batteryText').textContent=Math.ceil(state.battery)+'%';$('flashlight').classList.toggle('hidden',!state.flashlightUnlocked);$('flashlight').classList.toggle('on',state.flashlight);$('flashlightState').textContent=state.battery<=0?'ПУСТО':state.flashlight?'ВКЛ':'ВЫКЛ'
}

function setupSignatureCanvas(){
 const c=$('signatureCanvas'),g=c.getContext('2d');let drawing=false,lastPoint=null,ink=0;
 function clear(){g.clearRect(0,0,c.width,c.height);g.fillStyle='#f8efd9';g.fillRect(0,0,c.width,c.height);g.strokeStyle='#354851';g.lineWidth=4;g.lineCap='round';g.lineJoin='round';ink=0;$('confirmSignature').disabled=state.journalMode!=='transfer'}
 function pos(e){const r=c.getBoundingClientRect();return{x:(e.clientX-r.left)*c.width/r.width,y:(e.clientY-r.top)*c.height/r.height}}
 c.addEventListener('pointerdown',e=>{e.preventDefault();drawing=true;lastPoint=pos(e);c.setPointerCapture?.(e.pointerId)});
 c.addEventListener('pointermove',e=>{if(!drawing)return;e.preventDefault();const p=pos(e);g.beginPath();g.moveTo(lastPoint.x,lastPoint.y);g.lineTo(p.x,p.y);g.stroke();ink+=distance(lastPoint.x,lastPoint.y,p.x,p.y);lastPoint=p;if(ink>120)$('confirmSignature').disabled=false});
 const stop=()=>{drawing=false;lastPoint=null};c.addEventListener('pointerup',stop);c.addEventListener('pointercancel',stop);$('clearSignature').onclick=clear;clear();return{clear,canvas:c}
}
const signaturePad=setupSignatureCanvas();
function journalRows(mode){
 if(mode==='start')return`<div class="journalRow header"><span>ДАТА</span><span>ВРЕМЯ</span><span>СОТРУДНИК</span><span>СОСТОЯНИЕ / ПОДПИСЬ</span></div><div class="journalRow"><span>20.07</span><span>17:55</span><span>И. Ивченков</span><span>Оборудование остановлено</span></div>${loopCount?'<div class="journalRow anomaly"><span>20.07</span><span>23:47</span><span>И. Ивченков</span><span>Смена уже принята</span></div>':''}`;
 return`<div class="journalRow header"><span>ВРЕМЯ</span><span>СТАТУС</span><span>СМЕНУ СДАЛ</span><span>СМЕНУ ПРИНЯЛ</span></div><div class="journalRow anomaly"><span>06:00</span><span>ЗАВЕРШЕНА</span><span>И. Ивченков · подпись есть</span><span>${mode==='accept'?'Поставьте подпись':'—'}</span></div>`
}
function openJournal(mode){
 state.journalMode=mode;pauseFor('journalModal');$('journalTitle').textContent=mode==='start'?'ЖУРНАЛ ПРИЁМА СМЕНЫ':mode==='transfer'?'ЖУРНАЛ ПЕРЕДАЧИ СМЕНЫ':'ПОДТВЕРЖДЕНИЕ ПРИЁМА СМЕНЫ';$('shiftStamp').textContent='СМЕНА №'+shiftNumber;$('journalTable').innerHTML=journalRows(mode);$('signatureLabel').textContent=mode==='start'?'ПОСТАВЬТЕ ПОДПИСЬ В ПОЛЕ':mode==='accept'?'ПОДПИШИТЕ ГРАФУ «СМЕНУ ПРИНЯЛ»':'ВАША ПОДПИСЬ УЖЕ СТОИТ В ГРАФЕ «СМЕНУ СДАЛ»';signaturePad.clear();$('confirmSignature').textContent=mode==='transfer'?'ПРОВЕРИТЬ КАМЕРУ ПРОХОДНОЙ':'ПОДТВЕРДИТЬ';$('confirmSignature').disabled=mode!=='transfer';$('clearSignature').classList.toggle('hidden',mode==='transfer');$('signatureCanvas').classList.toggle('hidden',mode==='transfer');$('closeJournal').classList.toggle('hidden',mode==='accept')
}
$('confirmSignature').onclick=()=>{
 const mode=state.journalMode;if(mode==='start'){state.signature=$('signatureCanvas').toDataURL();closeModal('journalModal');state.scene='factory';state.phase=1;player.x=145;player.y=850;camera.x=0;camera.y=500;state.checkpoint={x:145,y:850};setTask('18:00','ДОЙДИ ДО ПОСТА ДЕЖУРНОГО','ПРОХОДНАЯ ЗАВОДА','Производство остановлено. Нужно проверить камеры и принять ключи.');banner('СМЕНА №'+shiftNumber,'СМЕНА ПРИНЯТА');tone(620,.12,'sine',.12)}
 else if(mode==='transfer'){closeModal('journalModal');openChoice()}
 else if(mode==='accept'){state.signature=$('signatureCanvas').toDataURL();closeModal('journalModal');beginEnding('sign')}
};
$('closeJournal').onclick=()=>closeModal('journalModal');

const cameraDefs=[
 {id:1,name:'ПРОХОДНАЯ'},{id:2,name:'ОСНОВНОЙ ЦЕХ'},{id:3,name:'СТАНОК №4'},{id:4,name:'КОМПРЕССОРНАЯ'},{id:5,name:'ЭЛЕКТРОЩИТОВАЯ'},{id:6,name:'СТАРЫЙ КОРИДОР'},{id:7,name:'КАМЕРА У ПОСТА'},{id:0,name:'ЦЕХ 0'}
];
function cameraRequirements(mode){return mode==='initial'?[1,2,3,4]:mode==='anomaly'?[2,5,7]:[1,6,0]}
function drawCamera(id){
 const c=$('cameraFeed'),g=c.getContext('2d'),w=c.width,h=c.height;g.clearRect(0,0,w,h);const grad=g.createLinearGradient(0,0,w,h);grad.addColorStop(0,'#203234');grad.addColorStop(1,'#030708');g.fillStyle=grad;g.fillRect(0,0,w,h);g.strokeStyle='#d9fff012';for(let x=0;x<w;x+=55){g.beginPath();g.moveTo(x,0);g.lineTo(x,h);g.stroke()}for(let y=0;y<h;y+=55){g.beginPath();g.moveTo(0,y);g.lineTo(w,y);g.stroke()}
 g.fillStyle='#c5d4d0';g.font='900 22px monospace';g.fillText('CAM '+String(id).padStart(2,'0')+' · '+(cameraDefs.find(q=>q.id===id)?.name||''),24,34);
 if(id===1){g.fillStyle='#162326';g.fillRect(90,135,780,300);g.fillStyle='#76a9a655';g.fillRect(150,180,280,180);g.fillStyle='#d0b870';g.fillRect(520,185,220,16);if(state.cameraMode==='zero'){drawCameraPerson(g,700,340,true);g.fillStyle='#ff6075';g.fillText('СОТРУДНИК УЖЕ НА ТЕРРИТОРИИ',450,495)}}
 else if(id===2){for(let i=0;i<3;i++){g.fillStyle='#24383c';g.fillRect(100+i*270,150,210,250);g.fillStyle=i===1&&state.phase>=3?'#9b2c40':'#526a6d';g.fillRect(260+i*270,175,18,18)}if(state.cameraMode==='anomaly')drawCameraPerson(g,760,355,false)}
 else if(id===3){g.fillStyle='#263c40';g.fillRect(250,110,460,330);g.fillStyle='#8d263a';g.fillRect(610,145,28,28);g.fillStyle='#deca8b';g.font='900 28px monospace';g.fillText('ОШИБКА ОХЛАЖДЕНИЯ',280,480)}
 else if(id===4){g.fillStyle='#5b422d';g.beginPath();g.arc(480,280,130,0,Math.PI*2);g.fill();g.strokeStyle='#cb8a4a';g.lineWidth=15;g.stroke();g.fillStyle='#e3d28e';g.fillText('0 BAR',450,290)}
 else if(id===5){for(let i=0;i<8;i++){g.fillStyle=i<4?'#852d3d':'#35564f';g.fillRect(180+(i%4)*150,150+Math.floor(i/4)*150,80,100)}g.fillStyle='#ff6276';g.fillText('ПЕРЕГРУЗКА ЛИНИИ 047',300,490)}
 else if(id===6){g.fillStyle='#080b0c';g.fillRect(120,90,720,390);g.strokeStyle='#57464b';g.strokeRect(120,90,720,390);g.fillStyle='#ff596f';g.fillText(state.cameraMode==='zero'?'ДВЕРЬ ОТКРЫТА':'НЕТ СИГНАЛА',370,285);if(state.cameraMode==='zero')drawCameraPerson(g,510,390,false)}
 else if(id===7){g.fillStyle='#0a1416';g.fillRect(130,100,700,390);drawCameraPerson(g,505,365,false);g.fillStyle='#ff5a70';g.fillText('ОБЪЕКТ СМОТРИТ В КАМЕРУ',300,500)}
 else{g.fillStyle='#0b080a';g.fillRect(210,80,540,410);g.strokeStyle='#7d2d3c';g.lineWidth=5;g.strokeRect(210,80,540,410);g.fillStyle='#281319';g.fillRect(340,130,280,300);g.fillStyle='#ff425e';g.font='900 36px monospace';g.fillText('СТАНОК №0',360,285);g.font='900 22px monospace';g.fillText('ОПЕРАТОР: И. ИВЧЕНКОВ',270,470)}
 for(let i=0;i<120;i++){g.fillStyle=`rgba(255,255,255,${Math.random()*.12})`;g.fillRect(Math.random()*w,Math.random()*h,Math.random()*4+1,1)}
}
function drawCameraPerson(g,x,y,arriving){g.fillStyle='#010203';g.beginPath();g.ellipse(x,y,34,85,0,0,Math.PI*2);g.fill();g.beginPath();g.arc(x,y-83,27,0,Math.PI*2);g.fill();if(!arriving){g.fillStyle='#ff425c';g.beginPath();g.arc(x-8,y-86,4,0,Math.PI*2);g.arc(x+8,y-86,4,0,Math.PI*2);g.fill()}}
function openCameras(mode){
 state.cameraMode=mode;state.cameraViewed=new Set();pauseFor('cameraModal');$('cameraTitle').textContent=mode==='initial'?'ПЕРВИЧНАЯ ПРОВЕРКА':mode==='anomaly'?'АВАРИЙНАЯ ПРОВЕРКА':'ОБНАРУЖЕН НЕИЗВЕСТНЫЙ КАНАЛ';const controls=$('cameraControls');controls.innerHTML='';const available=mode==='initial'?cameraDefs.filter(c=>c.id>=1&&c.id<=4):mode==='anomaly'?cameraDefs.filter(c=>[2,5,7].includes(c.id)):cameraDefs.filter(c=>[1,6,0].includes(c.id));for(const cam of available){const b=document.createElement('button');b.textContent='CAM '+String(cam.id).padStart(2,'0')+' · '+cam.name;b.dataset.id=cam.id;if((mode==='anomaly'&&cam.id===7)||(mode==='zero'&&cam.id===0))b.classList.add('anomaly');b.onclick=()=>selectCamera(cam.id,b);controls.appendChild(b)}$('closeCameras').disabled=true;$('cameraStatus').textContent='Проверьте обязательные камеры.';selectCamera(available[0].id,controls.firstElementChild)
}
function selectCamera(id,button){for(const b of $('cameraControls').children)b.classList.remove('active');button?.classList.add('active','checked');state.cameraViewed.add(Number(id));drawCamera(Number(id));$('cameraTime').textContent=state.clock+':'+String(Math.floor(Math.random()*60)).padStart(2,'0');const req=cameraRequirements(state.cameraMode),done=req.filter(x=>state.cameraViewed.has(x)).length;$('cameraStatus').textContent=done===req.length?(state.cameraMode==='initial'?'На станке №4 горит авария охлаждения.':state.cameraMode==='anomaly'?'Камера у поста показывает фигуру, которой нет в цехе.':'Появился канал CAM 00. В официальном плане такого цеха нет.'):`Проверено ${done} из ${req.length} обязательных камер.`;$('closeCameras').disabled=done!==req.length;tone(id===0||id===7?70:420,.06,id===0||id===7?'sawtooth':'sine',.08);if(id===0||id===7)staticBurst(220)}
$('closeCameras').onclick=()=>{
 const mode=state.cameraMode;closeModal('cameraModal');if(mode==='initial'){state.phase=2;state.flashlightUnlocked=true;state.flashlight=true;state.notes.add('rules');setTask('21:14','ПРОВЕРЬ СТАНОК №4','ПОСТ ДЕЖУРНОГО','Станок остановлен, но индикатор охлаждения горит красным. Возьми фонарь и проверь панель.');banner('ЗАЯВКА 014','ОШИБКА ОХЛАЖДЕНИЯ');setTimeout(()=>openNote('rules'),500)}else if(mode==='anomaly'){state.phase=4;state.anomalySeen=true;setTask('22:30','ВОССТАНОВИ ПИТАНИЕ В ЩИТОВОЙ','ПОСТ ДЕЖУРНОГО','После появления фигуры половина завода обесточилась.');banner('АВАРИЯ ЛИНИИ 047','ПИТАНИЕ ОТКЛЮЧЕНО');state.shadow.next=performance.now()+3500}else{state.phase=8;setTask('00:20','ОТКРОЙ СТАРЫЙ ЦЕХ','ПОСТ ДЕЖУРНОГО','CAM 00 показывает работающий станок за дверью, которой раньше не было.');banner('НЕИЗВЕСТНЫЙ КАНАЛ','CAM 00');state.shadow.next=performance.now()+2500}
};

function openRepair(type){state.repairType=type;pauseFor('repairModal');$('repairWorkspace').innerHTML='';$('repairConfirm').disabled=true;const data={coolant:['СТАНОК №4 · ОХЛАЖДЕНИЕ','Выставьте три клапана по схеме: подача 2, байпас 1, обратная линия 3.','ЗАЯВКА 014'],breaker:['ГЛАВНЫЙ ЩИТ · ЛИНИЯ 047','Запомните аварийную последовательность и включите автоматы в том же порядке.','АВАРИЯ 047'],compressor:['КОМПРЕССОР · ДАВЛЕНИЕ','Настройте подачу и сброс так, чтобы давление удерживалось в зелёной зоне 55–65 бар.','ЗАЯВКА 031'],zero:['СТАНОК №0 · РУЧНОЙ ЗАПУСК','Восстановите последовательность временных меток, найденных во время смены.','ЦИКЛ '+shiftNumber]}[type];$('repairTitle').textContent=data[0];$('repairDescription').textContent=data[1];$('repairCode').textContent=data[2];if(type==='coolant')buildCoolant();else if(type==='breaker')buildBreaker();else if(type==='compressor')buildCompressor();else buildZero()}
function buildCoolant(){const ws=$('repairWorkspace');ws.innerHTML='<div class="pipe"></div><div class="valves"></div><div class="pipe"></div>';const targets=[2,1,3],values=[0,0,0],wrap=ws.querySelector('.valves');targets.forEach((target,i)=>{const v=document.createElement('div');v.className='valve';const b=document.createElement('button');b.textContent='0';const s=document.createElement('small');s.textContent=['ПОДАЧА · ЦЕЛЬ 2','БАЙПАС · ЦЕЛЬ 1','ОБРАТНАЯ · ЦЕЛЬ 3'][i];b.onclick=()=>{values[i]=(values[i]+1)%4;b.textContent=values[i];b.style.setProperty('--turn',values[i]*90+'deg');const ok=values.every((q,k)=>q===targets[k]);$('repairConfirm').disabled=!ok;$('repairHint').textContent=ok?'Контур собран. Можно запускать насос.':'Поверните клапаны до указанных положений.';tone(260+values[i]*80,.05,'square',.07)};v.append(b,s);wrap.appendChild(v)});$('repairHint').textContent='Каждое нажатие поворачивает клапан на одну позицию.'}
function buildBreaker(){const ws=$('repairWorkspace'),sequence=[2,4,1,3];ws.innerHTML='<div class="sequenceLights"><i></i><i></i><i></i><i></i></div><div class="breakerGrid"></div>';const lights=[...ws.querySelectorAll('.sequenceLights i')],grid=ws.querySelector('.breakerGrid');let input=[],ready=false;sequence.forEach((n,i)=>{setTimeout(()=>{lights[n-1].classList.add('on');setTimeout(()=>lights[n-1].classList.remove('on'),380);if(i===sequence.length-1)setTimeout(()=>{ready=true;$('repairHint').textContent='Теперь повторите последовательность.'},520)},i*620)});for(let i=1;i<=4;i++){const b=document.createElement('button');b.textContent='АВТОМАТ '+i;b.onclick=()=>{if(!ready)return;input.push(i);if(i===sequence[input.length-1]){b.classList.add('correct');tone(430+input.length*90,.07,'square',.08);if(input.length===sequence.length){$('repairConfirm').disabled=false;$('repairHint').textContent='Линия 047 восстановлена.'}}else{staticBurst(240);input=[];for(const q of grid.children)q.classList.remove('correct');$('repairHint').textContent='Неверный порядок. Последовательность сброшена.'}};grid.appendChild(b)}$('repairHint').textContent='Запомните порядок вспышек.'}
function buildCompressor(){const ws=$('repairWorkspace');ws.innerHTML='<div class="compressorPanel"><div class="gauge"><label>ПОДАЧА</label><input id="flowRange" type="range" min="0" max="100" value="20"><b id="flowValue">20</b></div><div class="gauge"><label>СБРОС</label><input id="reliefRange" type="range" min="0" max="100" value="80"><b id="reliefValue">80</b></div><div class="pressureMeter"><i id="pressureNeedle"></i></div><div class="gauge"><label>ДАВЛЕНИЕ</label><span></span><b id="pressureValue">0 BAR</b></div></div>';const flow=$('flowRange'),relief=$('reliefRange');function calc(){const f=Number(flow.value),r=Number(relief.value),pressure=clamp(f*.82+(100-r)*.42,0,100);$('flowValue').textContent=f;$('reliefValue').textContent=r;$('pressureValue').textContent=Math.round(pressure)+' BAR';$('pressureNeedle').style.left=pressure+'%';const ok=pressure>=55&&pressure<=65&&f>=55&&r>=45;$('repairConfirm').disabled=!ok;$('repairHint').textContent=ok?'Давление стабильно. Компрессор готов к запуску.':'Зелёная зона: 55–65 бар. Подача должна быть выше 55, сброс — выше 45.'}flow.oninput=calc;relief.oninput=calc;calc()}
function buildZero(){const ws=$('repairWorkspace'),sequence=['17:42','23:47','06:00'];ws.innerHTML='<div class="machineZero"><div class="pulse">ПУЛЬС ОПЕРАТОРА: 0</div><div class="timeNodes"></div><div class="memoryStrip">ТЕКУЩИЙ ЦИКЛ: '+shiftNumber+'<br>ОПЕРАТОР: И. ИВЧЕНКОВ<br>СОСТОЯНИЕ: НЕ ЗАВЕРШЁН</div></div>';const wrap=ws.querySelector('.timeNodes'),memory=ws.querySelector('.memoryStrip');let step=0;for(const value of ['06:00','17:42','23:47']){const b=document.createElement('button');b.textContent=value;b.onclick=()=>{if(value===sequence[step]){b.classList.add('done');b.disabled=true;step++;ws.querySelector('.pulse').textContent='ПУЛЬС ОПЕРАТОРА: '+[47,112,184][step-1];memory.innerHTML=[`ВРЕМЯ ПРИХОДА ПОДТВЕРЖДЕНО.<br>Подпись найдена до входа оператора.`,`ТРЕВОГА ПОДТВЕРЖДЕНА.<br>Камера показывает следующую версию оператора.`,`КОНЕЦ СМЕНЫ ПОДТВЕРЖДЁН.<br>Доступно действие: ЗАВЕРШИТЬ РЕМОНТ ОПЕРАТОРА.`][step-1];tone(120+step*90,.16,'sawtooth',.12);if(step===3){$('repairConfirm').disabled=false;$('repairConfirm').textContent='ЗАВЕРШИТЬ РЕМОНТ ОПЕРАТОРА';$('repairHint').textContent='После завершения станок удалит текущую неисправность.'}}else{staticBurst(420);$('repairHint').textContent='Неверная временная метка. Станок помнит другой порядок.'}};wrap.appendChild(b)}$('repairHint').textContent='Вспомните: приход → тревога → окончание смены.'}
$('repairConfirm').onclick=()=>finishRepair(state.repairType);
function finishRepair(type){closeModal('repairModal');state.repairs++;state.score+=type==='zero'?520:220;vibrate('heavy');tone(type==='zero'?48:650,type==='zero'?.7:.18,type==='zero'?'sawtooth':'sine',type==='zero'?.25:.12);if(type==='coolant'){state.phase=3;setTask('21:48','ВЕРНИСЬ НА ПОСТ И ПРОВЕРЬ КАМЕРЫ','СТАНОК №4','Насос заработал. На экране станка появилась строка: «Оператор внутри рабочей зоны».');banner('ЗАЯВКА 014','НЕИСПРАВНОСТЬ УСТРАНЕНА')}else if(type==='breaker'){state.phase=5;setTask('23:47','ПРОВЕРЬ ШКАФЧИК МАСТЕРА','ЭЛЕКТРОЩИТОВАЯ','Свет вернулся. В журнале появилась вторая подпись с временем 23:47.');banner('СИСТЕМА','СМЕНА ПРИНЯТА ПОВТОРНО');staticBurst(700)}else if(type==='compressor'){state.phase=7;setTask('01:14','ВЕРНИСЬ К КАМЕРАМ','КОМПРЕССОРНАЯ','По трубам прошли три удара. На мониторе поста появился новый канал.');banner('ВНУТРЕННИЙ НОМЕР 047','ВХОДЯЩИЙ ВЫЗОВ');state.flashlight=false}else{state.phase=10;state.shadow.visible=false;setTask('05:55','ВЕРНИСЬ НА ПОСТ И ПЕРЕДАЙ СМЕНУ','СТАРЫЙ ЦЕХ','Все аномалии исчезли. За окнами начинает светлеть.');banner('ЦИКЛ '+shiftNumber,'РЕМОНТ ОПЕРАТОРА ЗАВЕРШЁН');state.flashlight=true;state.battery=100}}

function collectNote(id){if(state.notes.has(id)){openNote(id);return}state.notes.add(id);state.score+=90;openNote(id);updateHud()}
function openNote(id){const n=noteDefs[id];if(!n)return;pauseFor('noteModal');$('noteKind').textContent=n.kind||'НАЙДЕНА ЗАПИСКА';$('noteTitle').textContent=n.title;$('noteBody').textContent=n.body;state.openNoteId=id}
$('closeNote').onclick=()=>closeModal('noteModal');
$('notes').onclick=()=>{pauseFor('notesModal');renderNotesList()};$('closeNotes').onclick=()=>closeModal('notesModal');
function renderNotesList(){const list=$('notesList');list.innerHTML='';if(!state.notes.size){list.innerHTML='<div class="notesEmpty">Пока ничего не найдено.</div>';return}for(const id of state.notes){const n=noteDefs[id];if(!n)continue;const b=document.createElement('button');const title=document.createElement('b'),sub=document.createElement('small');title.textContent=n.title;sub.textContent=n.kind||'ДОКУМЕНТ';b.append(title,sub);b.onclick=()=>{closeModal('notesModal');openNote(id)};list.appendChild(b)}}

function openChoice(){pauseFor('choiceModal');drawChoiceFeed();tone(74,.35,'sawtooth',.14)}
function drawChoiceFeed(){const c=$('choiceFeed'),g=c.getContext('2d'),w=c.width,h=c.height;g.fillStyle='#baa976';g.fillRect(0,0,w,h);g.fillStyle='#344247';g.fillRect(0,h*.55,w,h*.45);g.fillStyle='#1d2a2e';g.fillRect(w*.62,0,w*.38,h);g.fillStyle='#80aeb055';g.fillRect(w*.68,h*.16,w*.22,h*.58);drawCameraPerson(g,w*.47,h*.77,true);g.fillStyle='#ff536b';g.font='900 17px monospace';g.fillText('17:42 · СМЕНА №'+(shiftNumber+1),20,30);for(let i=0;i<90;i++){g.fillStyle=`rgba(255,255,255,${Math.random()*.1})`;g.fillRect(Math.random()*w,Math.random()*h,3,1)}}
$('signAgain').onclick=()=>{closeModal('choiceModal');openJournal('accept')};$('refuseSign').onclick=()=>{closeModal('choiceModal');beginEnding('refuse')};
async function beginEnding(type){
 state.ending=true;state.endingType=type;state.paused=true;localStorage.setItem('nightHunterFactoryLoop',String(loopCount+1));const raw=Math.round(state.score+state.repairs*180+state.notes.size*90+(type==='sign'?520:380));$('resultScore').textContent=raw;$('resultRepairs').textContent=state.repairs+'/4';$('resultNotes').textContent=state.notes.size+'/4';
 if(type==='sign'){$('endingEyebrow').textContent='СМЕНА №'+(shiftNumber+1)+' ПРИНЯТА';$('endingTitle').textContent='Ты передал смену самому себе';$('endingText').textContent='Дверь открывается. Снаружи снова тот же солнечный вечер — 17:42. Навстречу идёт новая версия тебя и не узнаёт человека, который только что закончил смену.';$('endingQuote').textContent='«В следующий раз не ремонтируй станок №0». Ниже появляются новые слова: «Ты уже пробовал».'}
 else{$('endingEyebrow').textContent='СМЕНА НЕ ПРИНЯТА';$('endingTitle').textContent='Завод начинает смену заново';$('endingText').textContent='Все станки запускаются одновременно. Белая вспышка — и ты снова стоишь перед проходной в солнечную погоду. Ты ничего не помнишь, а телефон сообщает: «Ты опаздываешь на первую смену».';$('endingQuote').textContent='В журнале уже стоит твоя подпись. Время приёма: 23:47.'}
 setTimeout(()=>{$('endingModal').classList.remove('hidden');state.modal='endingModal'},800);if(state.demo||!state.sessionId){$('reward').textContent='Демо-режим: результат не начисляется.';return}try{const d=await api('finish',{session_id:state.sessionId,score:raw,stats:{ending:type,repairs:state.repairs,notes:state.notes.size,loop:loopCount+1,battery:Math.round(state.battery)}});$('reward').innerHTML=d.actual_reward>0?`Начислено <b>+${d.actual_reward}</b> влияния. Баланс: <b>${d.balance}</b>.`:(d.message||'Результат сохранён.')}catch(e){$('reward').textContent='Сервер не сохранил результат: '+e.message}
}
$('again').onclick=()=>location.reload();$('toGames').onclick=goGames;$('back').onclick=goGames;

function toggleFlashlight(){if(!state.flashlightUnlocked||state.battery<=0)return;state.flashlight=!state.flashlight;$('flashlight').classList.toggle('on',state.flashlight);tone(state.flashlight?520:180,.05,'square',.06);if(state.phase===7&&state.flashlight){showCaption('Три удара пресса повторяются. В правилах было сказано выключить фонарь.',3)}}
$('flashlight').onclick=toggleFlashlight;
function joystickUpdate(e){const r=$('joystick').getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,dx=e.clientX-cx,dy=e.clientY-cy,max=r.width*.34,m=Math.hypot(dx,dy)||1,s=Math.min(1,max/m),x=dx*s,y=dy*s;joy.x=x/max;joy.y=y/max;$('joystickKnob').style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px))`}
function resetJoystick(){joy.id=null;joy.x=joy.y=0;$('joystickKnob').style.transform='translate(-50%,-50%)'}
$('joystick').addEventListener('pointerdown',e=>{e.preventDefault();joy.id=e.pointerId;$('joystick').setPointerCapture?.(e.pointerId);joystickUpdate(e)});$('joystick').addEventListener('pointermove',e=>{if(e.pointerId===joy.id)joystickUpdate(e)});$('joystick').addEventListener('pointerup',resetJoystick);$('joystick').addEventListener('pointercancel',resetJoystick);
$('action').addEventListener('pointerdown',e=>{if(e.pointerType==='mouse'&&e.button!==0)return;e.preventDefault();actionPointer=e.pointerId;actionHeld=true;$('action').classList.add('holding');$('action').setPointerCapture?.(e.pointerId)});const releaseAction=e=>{if(e&&actionPointer!==null&&e.pointerId!==actionPointer)return;actionPointer=null;actionHeld=false;$('action').classList.remove('holding')};$('action').addEventListener('pointerup',releaseAction);$('action').addEventListener('pointercancel',releaseAction);
window.addEventListener('keydown',e=>{keys.add(e.key.toLowerCase());if(e.key.toLowerCase()==='e')actionHeld=true;if(e.key.toLowerCase()==='f')toggleFlashlight()});window.addEventListener('keyup',e=>{keys.delete(e.key.toLowerCase());if(e.key.toLowerCase()==='e')actionHeld=false});document.addEventListener('visibilitychange',()=>{if(document.hidden){resetJoystick();actionHeld=false}});

function tick(now){const dt=Math.min(.04,(now-last)/1000||0);last=now;if(state.running&&!state.paused&&!state.ending){updatePlayer(dt);updateBattery(dt);updateShadow(now);updateAction(dt)}else if(!state.running){currentInteraction=null;$('action').classList.add('hidden')}updateHud();render(now);raf=requestAnimationFrame(tick)}
function startGame(demo=false){state.demo=demo;state.running=true;state.paused=false;state.scene='outside';state.phase=0;state.score=0;state.repairs=0;state.battery=100;state.flashlight=false;state.flashlightUnlocked=false;state.notes.clear();player.x=120;player.y=480;camera.x=0;camera.y=0;$('intro').classList.add('hidden');initAudio();try{audio?.ac?.resume?.()}catch(_){}setTask('17:42','ДОЙДИ ДО ПРОХОДНОЙ','ДОРОГА К ЗАВОДУ',loopCount?'Дорога кажется знакомой. В кармане лежит записка, которой ты не помнишь.':'Тёплый вечер. Ты идёшь на первую ночную смену.');banner('СМЕНА №'+shiftNumber,'ПРИБЫТИЕ')}
async function prepare(){try{const d=await api('start',{game:'night-hunter'});state.sessionId=d.session_id;$('start').textContent='ПРИНЯТЬ НОЧНУЮ СМЕНУ';$('start').classList.remove('loading');$('start').onclick=()=>startGame(false)}catch(e){$('start').classList.add('hidden');$('demo').classList.remove('hidden');$('demo').onclick=()=>startGame(true);$('startError').textContent=e.message+' Доступен демонстрационный режим.'}}
new ResizeObserver(resize).observe(canvas);window.addEventListener('resize',resize);resize();prepare();raf=requestAnimationFrame(tick);
})();
