(()=>{
'use strict';

const $=id=>document.getElementById(id);
const canvas=$('factoryCanvas');
const ctx=canvas?.getContext('2d');
if(!canvas||!ctx)throw new Error('Не найден игровой canvas.');

const ui={
  app:$('factoryApp'),stage:$('gameStage'),intro:$('introOverlay'),start:$('startButton'),back:$('backButton'),
  zone:$('zoneLabel'),clock:$('gameClock'),objective:$('objectiveTitle'),objectiveText:$('objectiveText'),
  ordersDone:$('ordersDone'),ordersTotal:$('ordersTotal'),ordersBar:$('ordersBar'),currentOrder:$('currentOrder'),
  score:$('scoreValue'),phone:$('phoneToast'),phoneSender:$('phoneSender'),phoneMessage:$('phoneMessage'),
  joystick:$('joystick'),knob:$('joystickKnob'),action:$('actionButton'),actionIcon:$('actionIcon'),
  actionLabel:$('actionLabel'),actionHint:$('actionHint'),run:$('runButton'),
  dialog:$('dialogOverlay'),dialogPortrait:$('dialogPortrait'),dialogPortraitText:$('dialogPortraitText'),
  dialogRole:$('dialogRole'),dialogName:$('dialogName'),dialogText:$('dialogText'),dialogChoices:$('dialogChoices'),dialogContinue:$('dialogContinue'),
  work:$('workOverlay'),workDepartment:$('workDepartment'),workTitle:$('workTitle'),workCounter:$('workCounter'),
  workDescription:$('workDescription'),workBoard:$('workBoard'),workBar:$('workBar'),workHint:$('workHint'),
  route:$('routeOverlay'),routeBath:$('routeBath'),routeGate:$('routeGate'),routeWork:$('routeWork'),gateRouteHint:$('gateRouteHint'),
  ending:$('endingOverlay'),endingIcon:$('endingIcon'),endingEyebrow:$('endingEyebrow'),endingTitle:$('endingTitle'),
  endingText:$('endingText'),endingQuote:$('endingQuote'),resultOrders:$('resultOrders'),resultScore:$('resultScore'),
  resultTime:$('resultTime'),restart:$('restartButton'),games:$('gamesButton')
};

const tg=window.Telegram?.WebApp;
try{tg?.ready?.();tg?.expand?.()}catch(_){ }

const WORLD={w:1600,h:1000};
const rooms=[
  {id:'post',x:35,y:95,w:155,h:210,label:'ПРОХОДНАЯ',fill:'#263a37'},
  {id:'cnc',x:240,y:75,w:430,h:290,label:'ЛАЗЕРНЫЙ УЧАСТОК',fill:'#28403c'},
  {id:'paint',x:735,y:75,w:285,h:235,label:'ЗОНА ПОКРАСКИ',fill:'#3d3a32'},
  {id:'seats',x:1080,y:75,w:355,h:235,label:'ИЗГОТОВЛЕНИЕ СИДУШЕК',fill:'#343c3a'},
  {id:'assembly1',x:735,y:365,w:300,h:225,label:'СБОРКА ТРЕНАЖЁРОВ №1',fill:'#293b38'},
  {id:'assembly2',x:1080,y:365,w:355,h:225,label:'СБОРКА ТРЕНАЖЁРОВ №2',fill:'#293b38'},
  {id:'break',x:240,y:680,w:300,h:225,label:'КОМНАТА ОТДЫХА',fill:'#40382e'},
  {id:'bath',x:600,y:680,w:250,h:225,label:'БАНЯ',fill:'#30433e'},
  {id:'yard',x:910,y:650,w:510,h:270,label:'ДВОР',fill:'#26352f'}
];
const points={
  gate:{x:105,y:520},post:{x:125,y:210},cnc:{x:455,y:325},paint:{x:875,y:275},seats:{x:1250,y:275},
  assembly1:{x:885,y:550},assembly2:{x:1250,y:550},break:{x:390,y:825},bath:{x:720,y:825},yard:{x:1120,y:790},exit:{x:1495,y:790}
};
const orderNames=[
  'Стойка приседа напольная','Жим ногами + гакк-присед','Супер Гакс 3 в 1','Гравитрон','Бицепс-машина',
  'Машина Смита','Стойки под штангу','Скамья Скотта','Горизонтальная тяга','Кроссовер',
  'Силовая рама','Комплект деталей для сборки'
];

const state={
  started:false,paused:false,ending:false,stage:0,route:'',orders:0,total:50,score:0,time:'08:00',
  shvartsHelp:false,bathKey:false,player:{x:72,y:520,r:17},camera:{x:0,y:0},input:{x:0,y:0,sprint:false},
  lastFrame:0,near:false,currentTarget:points.gate,actionText:'НАЧАТЬ СМЕНУ',actionHint:'У ВОРОТ',
  phoneTimer:0,audio:null,hum:null
};

const timeline={
  0:{time:'08:00',target:'gate',title:'ЗАЙДИ НА ЗАВОД',text:'Сегодня нужно закрыть 50 заказов. Отец сказал, что потом постарается отпустить тебя в выходной.',action:'НАЧАТЬ СМЕНУ',hint:'ВОЙТИ ЧЕРЕЗ ПРОХОДНУЮ'},
  1:{time:'08:10',target:'post',title:'ПОЛУЧИ СПИСОК ЗАКАЗОВ',text:'Отец ждёт у проходной с распечаткой. В списке стойки, Гакс, Машина Смита и ещё десятки позиций.',action:'ВЗЯТЬ СПИСОК',hint:'ОТЕЦ ЖДЁТ'},
  2:{time:'08:25',target:'cnc',title:'ВЫРЕЖИ ПЕРВУЮ ПАРТИЮ',text:'Подготовь лист, расставь детали и запусти резку первых двенадцати заказов.',action:'РАБОТАТЬ НА ЧПУ',hint:'ПЕРВАЯ ПАРТИЯ'},
  3:{time:'10:05',target:'paint',title:'ОТНЕСИ ДЕТАЛИ В ПОКРАСКУ',text:'Красильщик ждёт готовые элементы. Отметь детали, которые нужно покрыть порошковой краской.',action:'ПЕРЕДАТЬ ДЕТАЛИ',hint:'ЗОНА ПОКРАСКИ'},
  4:{time:'11:15',target:'seats',title:'ПРОВЕРЬ ЗАКАЗЫ НА СИДУШКИ',text:'Производству сидушек нужны основания и крепления. Собери комплект без ошибок.',action:'СОБРАТЬ КОМПЛЕКТ',hint:'УЧАСТОК СИДУШЕК'},
  5:{time:'12:00',target:'break',title:'ЗАЙДИ НА ОБЕД',text:'В комнате отдыха сидят отец, дядя Шварц, красильщик и помощник сборщика.',action:'ЗАЙТИ В КОМНАТУ',hint:'ОБЕДЕННЫЙ ПЕРЕРЫВ'},
  6:{time:'13:05',target:'cnc',title:'ВЫРЕЖИ ВТОРУЮ ПАРТИЮ',text:'Обед закончился. Отец уже положил возле лазера новый список и просит не тянуть время.',action:'ЗАПУСТИТЬ РЕЗКУ',hint:'ВТОРАЯ ПАРТИЯ'},
  7:{time:'14:20',target:'assembly1',title:'ПЕРЕДАЙ КОМПЛЕКТ НА СБОРКУ',text:'Сборщикам не хватает креплений для Гравитрона и Гакса. Закрой семь позиций.',action:'СОБРАТЬ КРЕПЛЕНИЯ',hint:'СБОРКА №1'},
  8:{time:'15:30',target:'assembly2',title:'ЗАКРОЙ ПОСЛЕДНИЕ УЗЛЫ',text:'До отъезда отца остаётся чуть больше часа. На втором участке ждут последние детали.',action:'ЗАКРУТИТЬ УЗЛЫ',hint:'СБОРКА №2'},
  9:{time:'16:20',target:'cnc',title:'ДОДЕЛАЙ ПОСЛЕДНЮЮ ПАРТИЮ',text:'Осталось шесть заказов. Отец стоит рядом и уже держит в руках ещё одну бумажку.',action:'ЗАКРЫТЬ 50 ЗАКАЗОВ',hint:'ФИНАЛЬНАЯ ПАРТИЯ'},
  10:{time:'16:38',target:'break',title:'ЗАБЕРИ КЛЮЧ ИЗ ШКАФЧИКА ОТЦА',text:'Отец и Шварц уехали в 16:35. Шкафчик не запирается, внутри лежит ключ от двери во двор.',action:'ОТКРЫТЬ ШКАФЧИК',hint:'КОМНАТА ОТДЫХА'},
  11:{time:'16:45',target:'bath',title:'ПРОЙДИ В БАНЮ ЗА ЛАЗЕРОМ',text:'Дверь в пристройку находится за лазерным станком. Через баню можно выйти во двор.',action:'ОТКРЫТЬ БАНЮ',hint:'КЛЮЧ У ТЕБЯ'},
  12:{time:'16:52',target:'exit',title:'ВЫЙДИ СО ДВОРА',text:'Осталась последняя дверь. За ней дорога, друзья и поездка с палатками.',action:'УЙТИ С ЗАВОДА',hint:'ПОСЛЕДНИЕ МЕТРЫ'},
  20:{time:'16:42',target:'gate',title:'ПОПРОБУЙ ОТКРЫТЬ ВОРОТА',text:'Ключи были у отца и дяди Шварца. Сейчас станет понятно, помог ли тебе сварщик.',action:'ОТКРЫТЬ ВОРОТА',hint:'РИСКОВАННЫЙ ПУТЬ'},
  30:{time:'16:40',target:'cnc',title:'ДОДЕЛАЙ ЕЩЁ ТРИ ЗАКАЗА',text:'Ты решил не спорить. Друзья выезжают без тебя, а лазер снова запускается.',action:'ПРОДОЛЖИТЬ РАБОТУ',hint:'ЕЩЁ ТРИ ЗАКАЗА'}
};

function clamp(v,min,max){return Math.max(min,Math.min(max,v));}
function distance(a,b){return Math.hypot(a.x-b.x,a.y-b.y);}
function haptic(type='light'){try{tg?.HapticFeedback?.impactOccurred?.(type)}catch(_){ }}

function initAudio(){
  if(state.audio)return;
  try{
    const AudioContext=window.AudioContext||window.webkitAudioContext;
    if(!AudioContext)return;
    state.audio=new AudioContext();
    const osc=state.audio.createOscillator(),gain=state.audio.createGain();
    osc.type='sawtooth';osc.frequency.value=48;gain.gain.value=.013;
    osc.connect(gain).connect(state.audio.destination);osc.start();state.hum={osc,gain};
  }catch(_){ }
}
function beep(freq=420,duration=.08,volume=.05){
  if(!state.audio)return;
  try{const o=state.audio.createOscillator(),g=state.audio.createGain();o.frequency.value=freq;g.gain.value=volume;o.connect(g).connect(state.audio.destination);o.start();g.gain.exponentialRampToValueAtTime(.001,state.audio.currentTime+duration);o.stop(state.audio.currentTime+duration);}catch(_){ }
}

function resize(){
  const rect=canvas.getBoundingClientRect();
  const dpr=Math.min(2,window.devicePixelRatio||1);
  canvas.width=Math.max(1,Math.floor(rect.width*dpr));canvas.height=Math.max(1,Math.floor(rect.height*dpr));
  ctx.setTransform(dpr,0,0,dpr,0,0);
}
window.addEventListener('resize',resize);

function worldToScreen(x,y){return{x:x-state.camera.x,y:y-state.camera.y};}
function screenSize(){const r=canvas.getBoundingClientRect();return{w:r.width,h:r.height};}

function zoneForPlayer(){
  const p=state.player;
  for(const room of rooms){if(p.x>=room.x&&p.x<=room.x+room.w&&p.y>=room.y&&p.y<=room.y+room.h)return room.label;}
  if(p.x<205)return 'ПРОХОДНАЯ И ВОРОТА';
  return 'ЦЕХ ALIV GYM';
}

function drawRoom(room){
  const p=worldToScreen(room.x,room.y);
  ctx.fillStyle=room.fill;ctx.fillRect(p.x,p.y,room.w,room.h);
  ctx.strokeStyle='rgba(161,210,196,.20)';ctx.lineWidth=3;ctx.strokeRect(p.x,p.y,room.w,room.h);
  ctx.fillStyle='rgba(224,238,233,.72)';ctx.font='800 14px system-ui';ctx.textAlign='center';ctx.fillText(room.label,p.x+room.w/2,p.y+25);
}

function drawFactoryDetails(){
  const c=worldToScreen(270,130);
  ctx.fillStyle='#142321';ctx.fillRect(c.x,c.y,350,155);ctx.strokeStyle='#6d8d86';ctx.lineWidth=5;ctx.strokeRect(c.x,c.y,350,155);
  ctx.fillStyle='#7ebeb0';ctx.fillRect(c.x+248,c.y+25,65,65);ctx.fillStyle='#d9bc68';ctx.beginPath();ctx.arc(c.x+325,c.y+122,13,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#e5d18e';ctx.font='900 13px system-ui';ctx.fillText('ЛАЗЕРНЫЙ СТАНОК',c.x+175,c.y+185);

  const paint=worldToScreen(775,140);for(let i=0;i<3;i++){ctx.fillStyle=['#6b5b3e','#4c615c','#725047'][i];ctx.fillRect(paint.x+i*78,paint.y+28,54,112);ctx.strokeStyle='#b5b6a2';ctx.strokeRect(paint.x+i*78,paint.y+28,54,112);}
  const seats=worldToScreen(1120,145);for(let i=0;i<4;i++){ctx.fillStyle='#202b29';ctx.beginPath();ctx.roundRect(seats.x+(i%2)*125,seats.y+Math.floor(i/2)*68,95,47,18);ctx.fill();ctx.strokeStyle='#798e88';ctx.stroke();}
  const a1=worldToScreen(775,425);for(let i=0;i<3;i++){ctx.strokeStyle='#86a19a';ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(a1.x+i*82,a1.y+105);ctx.lineTo(a1.x+35+i*82,a1.y+20);ctx.lineTo(a1.x+70+i*82,a1.y+105);ctx.stroke();}
  const a2=worldToScreen(1125,425);for(let i=0;i<3;i++){ctx.strokeStyle='#718c85';ctx.lineWidth=7;ctx.strokeRect(a2.x+i*95,a2.y+25,62,122);ctx.beginPath();ctx.moveTo(a2.x+i*95,a2.y+85);ctx.lineTo(a2.x+62+i*95,a2.y+85);ctx.stroke();}
  const br=worldToScreen(280,735);ctx.fillStyle='#5b4933';ctx.fillRect(br.x,br.y+38,215,48);for(let i=0;i<4;i++){ctx.fillStyle='#26332f';ctx.beginPath();ctx.arc(br.x+22+i*58,br.y+112,18,0,Math.PI*2);ctx.fill();}
  const bath=worldToScreen(625,735);ctx.fillStyle='#8c7b5d';ctx.fillRect(bath.x+18,bath.y+32,175,60);ctx.fillStyle='#b7c6c1';ctx.fillRect(bath.x+35,bath.y+115,145,38);
  const yard=worldToScreen(955,715);ctx.strokeStyle='#738b81';ctx.lineWidth=6;ctx.strokeRect(yard.x,yard.y,390,150);for(let i=0;i<6;i++){ctx.fillStyle='#4e625b';ctx.fillRect(yard.x+25+i*58,yard.y+105,35,35);}
}

function drawGate(){
  const p=worldToScreen(20,410);ctx.fillStyle='#14201e';ctx.fillRect(p.x,p.y,180,250);ctx.strokeStyle='#879a94';ctx.lineWidth=5;ctx.strokeRect(p.x,p.y,180,250);
  for(let i=0;i<8;i++){ctx.strokeStyle='#596d67';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(p.x+15+i*22,p.y);ctx.lineTo(p.x+15+i*22,p.y+250);ctx.stroke();}
  ctx.fillStyle='#dfc16d';ctx.font='900 16px system-ui';ctx.fillText('ALIV GYM',p.x+90,p.y-15);
}

function drawNPC(x,y,label,type='worker'){
  const p=worldToScreen(x,y);const scale=type==='shvarts'?1.35:1;
  ctx.save();ctx.translate(p.x,p.y);ctx.scale(scale,scale);
  ctx.fillStyle=type==='father'?'#222927':type==='shvarts'?'#3d4946':'#2d3936';ctx.beginPath();ctx.roundRect(-14,-28,28,48,10);ctx.fill();
  ctx.fillStyle='#a57b62';ctx.beginPath();ctx.arc(0,-38,11,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#111b19';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(-8,18);ctx.lineTo(-10,35);ctx.moveTo(8,18);ctx.lineTo(10,35);ctx.stroke();
  ctx.restore();ctx.fillStyle='#d8e4df';ctx.font='800 10px system-ui';ctx.textAlign='center';ctx.fillText(label,p.x,p.y+48*scale);
}

function drawNPCs(){
  if(state.stage<10&&state.stage!==20&&state.stage!==30){
    const fatherPos=state.stage<=1?{x:150,y:245}:state.stage<=4?{x:570,y:370}:state.stage===5?{x:330,y:780}:state.stage<=8?{x:690,y:445}:{x:545,y:365};
    drawNPC(fatherPos.x,fatherPos.y,'ОТЕЦ','father');
    const shvartsPos=state.stage===5?{x:445,y:780}:{x:1040,y:615};drawNPC(shvartsPos.x,shvartsPos.y,'ШВАРЦ','shvarts');
    if(state.stage===5){drawNPC(285,850,'КРАСИЛЬЩИК');drawNPC(485,850,'ПОМОЩНИК');}
  }
}

function drawPlayer(){
  const p=worldToScreen(state.player.x,state.player.y);ctx.save();ctx.translate(p.x,p.y);
  ctx.fillStyle='rgba(0,0,0,.25)';ctx.beginPath();ctx.ellipse(0,17,21,9,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#263a37';ctx.beginPath();ctx.roundRect(-13,-20,26,38,9);ctx.fill();
  ctx.fillStyle='#a67a61';ctx.beginPath();ctx.arc(0,-29,10,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#111a18';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(-7,14);ctx.lineTo(-10,31);ctx.moveTo(7,14);ctx.lineTo(10,31);ctx.stroke();ctx.restore();
}

function drawTarget(now){
  const target=state.currentTarget;if(!target)return;const p=worldToScreen(target.x,target.y);const pulse=1+Math.sin(now/230)*.12;
  ctx.save();ctx.translate(p.x,p.y);ctx.scale(pulse,pulse);ctx.strokeStyle='#f2d477';ctx.lineWidth=4;ctx.beginPath();ctx.arc(0,0,28,0,Math.PI*2);ctx.stroke();ctx.fillStyle='rgba(242,212,119,.13)';ctx.fill();ctx.fillStyle='#f5dc8b';ctx.beginPath();ctx.moveTo(0,-48);ctx.lineTo(-10,-32);ctx.lineTo(10,-32);ctx.closePath();ctx.fill();ctx.restore();
}

function draw(now){
  const size=screenSize();ctx.clearRect(0,0,size.w,size.h);
  ctx.fillStyle='#182724';ctx.fillRect(0,0,size.w,size.h);
  const grid=worldToScreen(0,0);ctx.strokeStyle='rgba(145,183,172,.07)';ctx.lineWidth=1;
  for(let x=0;x<=WORLD.w;x+=80){const sx=x-state.camera.x;ctx.beginPath();ctx.moveTo(sx,-state.camera.y);ctx.lineTo(sx,WORLD.h-state.camera.y);ctx.stroke();}
  for(let y=0;y<=WORLD.h;y+=80){const sy=y-state.camera.y;ctx.beginPath();ctx.moveTo(-state.camera.x,sy);ctx.lineTo(WORLD.w-state.camera.x,sy);ctx.stroke();}
  ctx.fillStyle='#1b2d29';ctx.fillRect(grid.x,grid.y,WORLD.w,WORLD.h);
  ctx.fillStyle='#273a36';ctx.fillRect(-state.camera.x,430-state.camera.y,WORLD.w,180);
  for(const room of rooms)drawRoom(room);
  drawGate();drawFactoryDetails();drawNPCs();drawTarget(now);drawPlayer();
}

function updateCamera(){
  const s=screenSize();state.camera.x=clamp(state.player.x-s.w/2,0,Math.max(0,WORLD.w-s.w));state.camera.y=clamp(state.player.y-s.h/2,0,Math.max(0,WORLD.h-s.h));
}

function update(dt){
  if(!state.started||state.paused||state.ending)return;
  let{x,y}=state.input;const len=Math.hypot(x,y);if(len>1){x/=len;y/=len;}
  const speed=state.input.sprint?330:215;state.player.x=clamp(state.player.x+x*speed*dt,30,WORLD.w-30);state.player.y=clamp(state.player.y+y*speed*dt,45,WORLD.h-35);
  updateCamera();ui.zone.textContent=zoneForPlayer();
  state.near=distance(state.player,state.currentTarget)<92;
  ui.action.classList.toggle('hidden',!state.near);ui.action.classList.toggle('ready',state.near);
}

function loop(now){
  const dt=Math.min(.04,(now-state.lastFrame)/1000||0);state.lastFrame=now;update(dt);draw(now);requestAnimationFrame(loop);
}

function setInput(x,y){state.input.x=x;state.input.y=y;}
function setupJoystick(){
  let active=false,pointerId=null;
  const move=e=>{if(!active||e.pointerId!==pointerId)return;const r=ui.joystick.getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2;let dx=e.clientX-cx,dy=e.clientY-cy;const max=r.width*.31,len=Math.hypot(dx,dy);if(len>max){dx=dx/len*max;dy=dy/len*max;}ui.knob.style.transform=`translate(${dx}px,${dy}px)`;setInput(dx/max,dy/max);};
  ui.joystick.addEventListener('pointerdown',e=>{active=true;pointerId=e.pointerId;ui.joystick.setPointerCapture(e.pointerId);move(e);});
  ui.joystick.addEventListener('pointermove',move);
  const end=e=>{if(e.pointerId!==pointerId)return;active=false;pointerId=null;ui.knob.style.transform='';setInput(0,0);};
  ui.joystick.addEventListener('pointerup',end);ui.joystick.addEventListener('pointercancel',end);
  const keys=new Set();window.addEventListener('keydown',e=>{keys.add(e.key.toLowerCase());if(e.key==='Shift')state.input.sprint=true;syncKeys(keys);});window.addEventListener('keyup',e=>{keys.delete(e.key.toLowerCase());if(e.key==='Shift')state.input.sprint=false;syncKeys(keys);});
  ui.run.addEventListener('pointerdown',()=>{state.input.sprint=true;ui.run.classList.add('active');});
  const stopRun=()=>{state.input.sprint=false;ui.run.classList.remove('active');};ui.run.addEventListener('pointerup',stopRun);ui.run.addEventListener('pointercancel',stopRun);ui.run.addEventListener('pointerleave',stopRun);
}
function syncKeys(keys){setInput((keys.has('d')||keys.has('arrowright')?1:0)-(keys.has('a')||keys.has('arrowleft')?1:0),(keys.has('s')||keys.has('arrowdown')?1:0)-(keys.has('w')||keys.has('arrowup')?1:0));}

function updateHud(){
  ui.clock.textContent=state.time;ui.ordersDone.textContent=String(state.orders);ui.ordersTotal.textContent=String(state.total);ui.ordersBar.style.width=`${clamp(state.orders/state.total*100,0,100)}%`;ui.score.textContent=String(state.score);
  ui.currentOrder.textContent=state.orders>=50?'Дополнительно: 3 срочных заказа':orderNames[Math.min(orderNames.length-1,Math.floor(state.orders/5))];
}

function setStage(index,teleport=false){
  state.stage=index;const data=timeline[index];if(!data)return;
  state.time=data.time;state.currentTarget=points[data.target];state.actionText=data.action;state.actionHint=data.hint;
  ui.clock.textContent=data.time;ui.objective.textContent=data.title;ui.objectiveText.textContent=data.text;ui.actionLabel.textContent=data.action;ui.actionHint.textContent=data.hint;ui.actionIcon.textContent=index===2||index===6||index===9||index===30?'⚙️':index===10?'🔑':index===11?'🚪':'✋';
  if(teleport){state.player.x=state.currentTarget.x-130;state.player.y=state.currentTarget.y+20;updateCamera();}
  updateHud();
}

function showPhone(message,sender='ДРУЗЬЯ'){
  ui.phoneSender.textContent=sender;ui.phoneMessage.textContent=message;ui.phone.classList.remove('show');void ui.phone.offsetWidth;ui.phone.classList.add('show');haptic('light');clearTimeout(state.phoneTimer);state.phoneTimer=setTimeout(()=>ui.phone.classList.remove('show'),4300);
}

function showDialog({name='Отец',role='ОТЕЦ · ДИРЕКТОР',text='',portrait='О',kind='father',choices=null,button='ПОНЯЛ',onClose=null}){
  state.paused=true;ui.dialog.classList.remove('hidden');ui.dialogPortrait.className='characterPortrait '+(kind||'');ui.dialogPortraitText.textContent=portrait;ui.dialogRole.textContent=role;ui.dialogName.textContent=name;ui.dialogText.textContent=text;ui.dialogChoices.innerHTML='';
  ui.dialogContinue.textContent=button;ui.dialogContinue.classList.toggle('hidden',Array.isArray(choices)&&choices.length>0);
  let closed=false;const close=()=>{if(closed)return;closed=true;ui.dialog.classList.add('hidden');state.paused=false;onClose?.();};
  ui.dialogContinue.onclick=close;
  if(Array.isArray(choices))for(const choice of choices){const b=document.createElement('button');b.type='button';b.textContent=choice.label;b.onclick=()=>{choice.action?.();close();};ui.dialogChoices.appendChild(b);}
  haptic(kind==='shvarts'?'heavy':'medium');beep(kind==='shvarts'?170:250,.12,.045);
}

function openWork({department,title,description,count=6,icon='✦',onDone}){
  state.paused=true;ui.work.classList.remove('hidden');ui.workDepartment.textContent=department;ui.workTitle.textContent=title;ui.workDescription.textContent=description;ui.workHint.textContent='Нажимай только на подсвеченный элемент.';ui.workBoard.innerHTML='';ui.workBar.style.width='0%';let progress=0,target=-1,finished=false;
  const cells=[];for(let i=0;i<12;i++){const cell=document.createElement('button');cell.type='button';cell.className='workCell';cell.textContent=icon;cell.onclick=()=>{if(finished)return;if(i!==target){cell.classList.add('wrong');beep(120,.08,.055);haptic('light');setTimeout(()=>cell.classList.remove('wrong'),220);return;}cell.classList.remove('target');cell.classList.add('done');progress++;ui.workCounter.textContent=`${progress}/${count}`;ui.workBar.style.width=`${progress/count*100}%`;beep(520+progress*35,.07,.045);haptic('light');if(progress>=count){finished=true;ui.workHint.textContent='Задание выполнено.';setTimeout(()=>{ui.work.classList.add('hidden');state.paused=false;onDone?.();},650);}else chooseTarget();};cells.push(cell);ui.workBoard.appendChild(cell);}
  function chooseTarget(){const available=cells.map((c,i)=>c.classList.contains('done')?-1:i).filter(i=>i>=0);target=available[Math.floor(Math.random()*available.length)];cells[target].classList.add('target');}
  ui.workCounter.textContent=`0/${count}`;chooseTarget();
}

function addOrders(amount,pointsAward=amount*16){state.orders+=amount;state.score+=pointsAward;updateHud();}

function fatherAdds(text,nextStage,friendMessage=''){
  showDialog({text,onClose:()=>{if(friendMessage)showPhone(friendMessage);setStage(nextStage);}});
}

function lunchScene(){
  showDialog({name:'Дядя Шварц',role:'СВАРЩИК · ВТОРОЙ НАЧАЛЬНИК',portrait:'Ш',kind:'shvarts',text:'Ну что, турист? Говорят, в палатки собрался. Отец тебя ещё не отпускал.',choices:[
    {label:'Спокойно сказать, что очень нужен выходной',action:()=>{state.shvartsHelp=true;showPhone('Ладно. Если решишь уйти — ключ от ворот будет под моей сварочной курткой. Я ничего не видел.','ДЯДЯ ШВАРЦ');}},
    {label:'Промолчать и вернуться к работе',action:()=>{state.shvartsHelp=false;showPhone('Молчишь — значит работать хочешь. Ключи останутся у нас.','ДЯДЯ ШВАРЦ');}}
  ],onClose:()=>setStage(6)});
}

function openRouteChoice(){
  state.paused=true;ui.route.classList.remove('hidden');ui.gateRouteHint.textContent=state.shvartsHelp?'Шварц обещал оставить ключ под курткой':'Ключей нет — отец может вернуться';
}
function chooseRoute(route){
  ui.route.classList.add('hidden');state.paused=false;state.route=route;
  if(route==='bath'){showPhone('Мы уже грузим палатки. Последний шанс успеть.');setStage(10,true);}
  else if(route==='gate'){setStage(20,true);}
  else{state.total=53;updateHud();setStage(30,true);}
}

function ending(type){
  state.ending=true;state.paused=true;ui.ending.classList.remove('hidden');let data;
  if(type==='bath')data={icon:'🏕️',eye:'КОНЦОВКА · СВОБОДА ЧЕРЕЗ БАНЮ',title:'Ты всё-таки ушёл',text:'Ты забрал ключ из шкафчика отца, прошёл через баню, вышел во двор и закрыл дверь за собой. Впервые работа осталась ждать тебя, а не наоборот.',quote:'«Мы уже разожгли костёр. Давай быстрее».',time:'16:58'};
  else if(type==='gate')data={icon:'🤝',eye:'КОНЦОВКА · ШВАРЦ ПОМОГ',title:'Сварщик ничего не видел',text:'Под сварочной курткой действительно лежал ключ. Дядя Шварц сдержал слово, а ворота ALIV GYM закрылись за твоей спиной.',quote:'«Ладно, турист. Иногда надо уметь уйти».',time:'16:49'};
  else if(type==='caught')data={icon:'📞',eye:'КОНЦОВКА · ПОЙМАН',title:'Отец вернулся раньше',text:'Ключа у ворот не оказалось. Камера отправила уведомление отцу, и через несколько минут его машина снова въехала во двор. Поездка отменена, впереди рабочие выходные.',quote:'«Пиздуй пахать, простофиля».',time:'17:06'};
  else data={icon:'⚙️',eye:'КОНЦОВКА · ЗАЛОЖНИК ЗАВОДА',title:'Ты закрыл ещё три заказа',text:'Список наконец опустел, но друзья уже уехали. На столе лежит новая бумажка на понедельник. Отец пишет, что выходной пока под вопросом.',quote:'«Молодец. Завтра тоже выйдешь — там срочно».',time:'18:14'};
  ui.endingIcon.textContent=data.icon;ui.endingEyebrow.textContent=data.eye;ui.endingTitle.textContent=data.title;ui.endingText.textContent=data.text;ui.endingQuote.textContent=data.quote;ui.resultOrders.textContent=String(state.orders);ui.resultScore.textContent=String(state.score);ui.resultTime.textContent=data.time;
  try{localStorage.setItem('factoryEscapeBest',String(Math.max(state.score,Number(localStorage.getItem('factoryEscapeBest')||0))))}catch(_){ }
  haptic(type==='caught'?'heavy':'medium');beep(type==='caught'?110:660,.3,.07);
}

function interact(){
  if(!state.started||state.paused||state.ending||!state.near)return;
  haptic('medium');beep(360,.07,.045);
  switch(state.stage){
    case 0:showDialog({text:'Сегодня закрываешь пятьдесят заказов. Если всё сделаешь — постараюсь отпустить тебя в выходной. Только без разговоров и опозданий.',onClose:()=>setStage(1)});break;
    case 1:showDialog({text:'Начни со стоек, Гакса и Машины Смита. Закончишь — подойду и скажу, что делать дальше.',onClose:()=>{showPhone('Палатки нашли. Завтра выезжаем, тебя считать?');setStage(2);}});break;
    case 2:openWork({department:'ЛАЗЕРНЫЙ УЧАСТОК',title:'РАСКРОЙ ПЕРВОЙ ПАРТИИ',description:'Отметь правильные точки размещения деталей на листе.',count:7,icon:'◈',onDone:()=>{addOrders(12,210);fatherAdds('Нормально. Но не расслабляйся — там ещё восемь позиций добавились.',3,'Мы закупаем еду. Скинь, что тебе брать.');}});break;
    case 3:openWork({department:'ЗОНА ПОКРАСКИ',title:'МАРКИРОВКА ДЕТАЛЕЙ',description:'Выбери детали, которые готовы к порошковой окраске.',count:6,icon:'▰',onDone:()=>{addOrders(6,130);fatherAdds('Красильщик забрал детали. Теперь сходи к сидушкам — там опять чего-то не хватает.',4);}});break;
    case 4:openWork({department:'ИЗГОТОВЛЕНИЕ СИДУШЕК',title:'КОМПЛЕКТАЦИЯ ОСНОВАНИЙ',description:'Собери крепления и основания для сидений тренажёров.',count:5,icon:'⬡',onDone:()=>{addOrders(4,105);fatherAdds('Обед пять минут. Потом сразу к станку. Список я уже положил.',5,'Мы решили ехать пораньше. Ты точно освободишься?');}});break;
    case 5:lunchScene();break;
    case 6:openWork({department:'ЛАЗЕРНЫЙ УЧАСТОК',title:'ВТОРАЯ ПАРТИЯ',description:'Расставь детали плотнее, чтобы не тратить лишний металл.',count:8,icon:'◇',onDone:()=>{addOrders(10,190);fatherAdds('Ещё немного. Потом, может быть, отпущу. Но сначала закрой сборку.',7);}});break;
    case 7:openWork({department:'СБОРКА ТРЕНАЖЁРОВ №1',title:'КРЕПЛЕНИЯ ДЛЯ ГАКСА',description:'Затяни отмеченные соединения и передай комплект сборщикам.',count:6,icon:'🔩',onDone:()=>{addOrders(7,145);fatherAdds('На втором участке тоже ждут. Не стой, до конца смены мало времени.',8,'Мы уже собрали машины. Без тебя выезжать не хочется.');}});break;
    case 8:openWork({department:'СБОРКА ТРЕНАЖЁРОВ №2',title:'ФИНАЛЬНЫЕ УЗЛЫ',description:'Проверь соединения Машины Смита и Кроссовера.',count:5,icon:'✣',onDone:()=>{addOrders(5,120);fatherAdds('Осталось шесть. Мы со Шварцем скоро поедем, а ты всё доделаешь.',9);}});break;
    case 9:openWork({department:'ЛАЗЕРНЫЙ УЧАСТОК',title:'ПОСЛЕДНИЕ ШЕСТЬ ЗАКАЗОВ',description:'Закрой список из пятидесяти заказов и останови станок.',count:8,icon:'◆',onDone:()=>{addOrders(6,250);state.time='16:35';updateHud();showDialog({text:'Мы со Шварцем поехали. Тут ещё три срочных заказа нашлись. Доделаешь — позвонишь. И не вздумай бросить.',button:'ХОРОШО',onClose:()=>{showPhone('Они уехали. Завод пустой. Сейчас или никогда.','МЫСЛИ');openRouteChoice();}});}});break;
    case 10:state.bathKey=true;state.score+=80;updateHud();showDialog({name:'Шкафчик отца',role:'КОМНАТА ОТДЫХА',portrait:'🔑',kind:'friend',text:'Шкафчик не заперт. Под рабочими бумагами лежит ключ от двери во двор.',button:'ЗАБРАТЬ КЛЮЧ',onClose:()=>{showPhone('Ты там не ушёл? Я ещё три заказа скинул.','ОТЕЦ');setStage(11);}});break;
    case 11:if(!state.bathKey)return;state.score+=100;state.player.x=1030;state.player.y=790;updateCamera();showDialog({name:'Баня',role:'ПРИСТРОЙКА ЗА ЛАЗЕРНЫМ СТАНКОМ',portrait:'🚪',kind:'friend',text:'Дверь открылась. В бане пусто. Сзади виден выход во двор.',button:'ВЫЙТИ ВО ДВОР',onClose:()=>setStage(12)});break;
    case 12:state.score+=200;updateHud();ending('bath');break;
    case 20:if(state.shvartsHelp){state.score+=180;updateHud();ending('gate');}else ending('caught');break;
    case 30:openWork({department:'ЛАЗЕРНЫЙ УЧАСТОК',title:'ЕЩЁ ТРИ СРОЧНЫХ ЗАКАЗА',description:'Друзья уже выехали. Закончи работу, которую отец прислал после отъезда.',count:7,icon:'⚙',onDone:()=>{addOrders(3,90);ending('work');}});break;
  }
}

function resetGame(){
  state.started=true;state.paused=false;state.ending=false;state.stage=0;state.route='';state.orders=0;state.total=50;state.score=0;state.time='08:00';state.shvartsHelp=false;state.bathKey=false;state.player.x=72;state.player.y=520;state.input.x=0;state.input.y=0;state.input.sprint=false;
  ui.ending.classList.add('hidden');ui.route.classList.add('hidden');ui.dialog.classList.add('hidden');ui.work.classList.add('hidden');ui.intro.classList.add('hidden');updateCamera();setStage(0);updateHud();showPhone('Палатки и мангал уже нашли. Завтра ты с нами?');
}

function start(){initAudio();state.audio?.resume?.();resetGame();}
function goBack(){try{if(tg?.close){tg.close();return;}}catch(_){ }history.back();}

ui.action.onclick=interact;ui.routeBath.onclick=()=>chooseRoute('bath');ui.routeGate.onclick=()=>chooseRoute('gate');ui.routeWork.onclick=()=>chooseRoute('work');ui.restart.onclick=resetGame;ui.games.onclick=goBack;ui.back.onclick=goBack;
setupJoystick();resize();updateCamera();setStage(0);requestAnimationFrame(loop);

window.FactoryEscape={start,reset:resetGame};
window.__FACTORY_ESCAPE_READY__=true;
window.dispatchEvent(new Event('factory-escape-ready'));
})();