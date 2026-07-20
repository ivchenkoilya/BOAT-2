/* Reality 107: playable sunny arrival, security-desk opening and the Last Shift story. */
const V107={version:'Reality 107 · Last Shift'};
const v107MissionStart=startGame;
const v107MissionFinish=finish;
const v107BossUpdate=updateBoss;
let v107EquipmentOffered=false;
let v107Prologue={active:false,demo:false,scene:'street',step:0,last:0,startedAt:0,actionProgress:0,actionLock:false,captionUntil:0};

function v107ShowCaption(text,seconds=3){
 const el=$('caption');if(el)el.textContent=text;v107Prologue.captionUntil=performance.now()+seconds*1000;
}
function v107Clock(text){const el=$('timer');if(el)el.textContent=text}
function v107Objective(text){const el=$('objective');if(el)el.textContent=text}
function v107Room(text){const el=$('roomName');if(el)el.textContent=text}
function v107HideAction(){
 if(!v106ActionButton)return;v106ActionButton.classList.add('hidden');v106ActionButton.classList.remove('ready','holding','pressed');v106ActionButton.disabled=true;v106ActionButton.style.setProperty('--action-angle','0turn');v106ReleaseAction();v107Prologue.actionProgress=0;
}
function v107ActionContext(point,label,sub,icon,need=.8,radius=86){
 const distance=dist(player.x,player.y,point.x,point.y);return{point,label,sub,icon,need,radius,distance,near:distance<radius};
}
function v107HandlePrologueAction(dt,c,onComplete){
 if(!v106ActionButton||!c){v107HideAction();return}
 const show=c.distance<c.radius+38;v106ActionButton.classList.toggle('hidden',!show);
 if(!show){v107Prologue.actionProgress=0;v106ReleaseAction();return}
 v106ActionButton.disabled=!c.near;v106ActionButton.classList.toggle('ready',c.near);
 if(v106ActionIcon)v106ActionIcon.textContent=c.icon;
 if(v106ActionLabel)v106ActionLabel.textContent=c.label;
 if(v106ActionSub)v106ActionSub.textContent=c.near?c.sub:'ПОДОЙДИ БЛИЖЕ';
 if(c.near&&v106ActionHeld&&!v107Prologue.actionLock)v107Prologue.actionProgress=Math.min(c.need,v107Prologue.actionProgress+dt);
 else if(!v106ActionHeld)v107Prologue.actionProgress=Math.max(0,v107Prologue.actionProgress-dt*.9);
 v106ActionButton.style.setProperty('--action-angle',(v107Prologue.actionProgress/c.need).toFixed(3)+'turn');
 if(v107Prologue.actionProgress>=c.need&&!v107Prologue.actionLock){v107Prologue.actionLock=true;v106ReleaseAction();onComplete();setTimeout(()=>{v107Prologue.actionLock=false},220)}
}
function v107Move(dt,bounds){
 const v=moveVector(),m=Math.hypot(v.x,v.y);if(m>.06){player.facingX=v.x;player.facingY=v.y;player.walk+=dt*12;player.x=clamp(player.x+v.x*150*dt,bounds.x1,bounds.x2);player.y=clamp(player.y+v.y*150*dt,bounds.y1,bounds.y2)}
}
function v107DrawCivilian(now){
 const moving=Math.hypot(joy.x,joy.y)>.06,step=moving?Math.sin(player.walk)*4:0,a=moving?Math.atan2(joy.y,joy.x):Math.atan2(player.facingY,player.facingX);
 ctx.save();ctx.translate(player.x,player.y);ctx.rotate(a);ctx.fillStyle='#0004';ctx.beginPath();ctx.ellipse(0,13,18,9,0,0,Math.PI*2);ctx.fill();
 ctx.strokeStyle='#25323a';ctx.lineWidth=7;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-5,7);ctx.lineTo(-8-step,23);ctx.moveTo(6,7);ctx.lineTo(9+step,23);ctx.stroke();
 ctx.fillStyle='#354d58';ctx.beginPath();ctx.roundRect(-14,-15,28,32,9);ctx.fill();ctx.fillStyle='#1c272d';ctx.beginPath();ctx.roundRect(-18,-10,9,23,4);ctx.fill();
 ctx.fillStyle='#e7b08f';ctx.beginPath();ctx.arc(0,-19,9,0,Math.PI*2);ctx.fill();ctx.fillStyle='#1a262b';ctx.beginPath();ctx.arc(0,-21,9,Math.PI,Math.PI*2);ctx.fill();ctx.restore();
}
function v107Tree(x,y,now){
 ctx.fillStyle='#513a22';ctx.fillRect(x-5,y-4,10,28);const sway=Math.sin(now/900+x)*3;ctx.fillStyle='#5f9a62';ctx.beginPath();ctx.arc(x+sway,y-18,27,0,Math.PI*2);ctx.arc(x-20+sway*.6,y-5,19,0,Math.PI*2);ctx.arc(x+20+sway*.7,y-4,20,0,Math.PI*2);ctx.fill();ctx.fillStyle='#8ec57b55';ctx.beginPath();ctx.arc(x-7+sway,y-26,12,0,Math.PI*2);ctx.fill();
}
function v107DrawStreet(now){
 const W=1100,H=700;ctx.fillStyle='#e9d6ad';ctx.fillRect(0,0,W,H);ctx.fillStyle='#4c5358';ctx.fillRect(0,0,W,235);ctx.fillStyle='#343a3e';ctx.fillRect(0,0,W,18);ctx.strokeStyle='#f3e5b088';ctx.lineWidth=5;ctx.setLineDash([44,30]);ctx.beginPath();ctx.moveTo(0,115);ctx.lineTo(W,115);ctx.stroke();ctx.setLineDash([]);
 for(let i=0;i<4;i++){const x=((now*.045+i*300)%1400)-180;ctx.fillStyle=i%2?'#8e3d35':'#385d72';ctx.beginPath();ctx.roundRect(x,52+i%2*82,92,42,12);ctx.fill();ctx.fillStyle='#c8e6ef88';ctx.fillRect(x+18,58+i%2*82,45,13)}
 ctx.fillStyle='#c9b98e';ctx.fillRect(0,235,W,465);ctx.strokeStyle='#ffffff24';ctx.lineWidth=2;for(let y=260;y<H;y+=64){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}for(let x=20;x<W;x+=92){ctx.beginPath();ctx.moveTo(x,235);ctx.lineTo(x,H);ctx.stroke()}
 for(const [x,y] of [[135,315],[320,560],[545,315],[720,560]])v107Tree(x,y,now);
 ctx.fillStyle='#25353c';ctx.fillRect(850,205,250,495);ctx.fillStyle='#80b9c455';for(let y=235;y<520;y+=70)for(let x=875;x<1080;x+=60)ctx.fillRect(x,y,44,46);
 ctx.fillStyle='#111b20';ctx.fillRect(900,350,120,210);ctx.fillStyle='#a8e4d977';ctx.fillRect(920,378,80,150);ctx.strokeStyle='#d9fff2aa';ctx.strokeRect(920,378,80,150);ctx.fillStyle='#f1d691';ctx.font='900 17px system-ui';ctx.textAlign='center';ctx.fillText('ORPHEUS',965,300);ctx.font='800 10px system-ui';ctx.fillText('СЛУЖЕБНЫЙ ВХОД',965,329);
 const pulse=(Math.sin(now/220)+1)/2;ctx.strokeStyle=`rgba(255,226,145,${.55+pulse*.35})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(965,455,30+pulse*5,0,Math.PI*2);ctx.stroke();
 ctx.fillStyle='#73532633';for(let i=0;i<8;i++){ctx.save();ctx.translate(100+i*120,285);ctx.rotate(-.55);ctx.fillRect(0,0,18,150);ctx.restore()}v107DrawCivilian(now);
}
function v107DrawLobby(now){
 const W=900,H=700,g=ctx.createLinearGradient(0,0,W,H);g.addColorStop(0,'#edf2e8');g.addColorStop(1,'#b8c9c5');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 ctx.fillStyle='#8fc5d844';ctx.fillRect(0,0,150,H);ctx.strokeStyle='#d7ffff99';for(let y=0;y<H;y+=90){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(150,y);ctx.stroke()}for(let x=0;x<150;x+=50){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()}
 ctx.strokeStyle='#ffffff55';for(let x=170;x<W;x+=78){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,H);ctx.stroke()}for(let y=40;y<H;y+=78){ctx.beginPath();ctx.moveTo(150,y);ctx.lineTo(W,y);ctx.stroke()}
 ctx.fillStyle='#354b52';ctx.beginPath();ctx.roundRect(275,215,250,105,18);ctx.fill();ctx.fillStyle='#d4b76f';ctx.fillRect(300,240,200,8);ctx.fillStyle='#111b20';ctx.beginPath();ctx.roundRect(365,275,76,35,8);ctx.fill();ctx.fillStyle='#f7e5b0';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText('ЖУРНАЛ СМЕН',403,298);
 for(let i=0;i<3;i++){ctx.fillStyle='#53676c';ctx.fillRect(565+i*58,360,34,105);ctx.fillStyle='#86e7d4';ctx.fillRect(570+i*58,380,24,8)}
 ctx.fillStyle='#26363d';ctx.fillRect(735,175,135,360);ctx.fillStyle='#0b1115';ctx.fillRect(755,215,95,285);ctx.strokeStyle='#8ab4bd';ctx.lineWidth=3;ctx.strokeRect(755,215,95,285);ctx.beginPath();ctx.moveTo(802,215);ctx.lineTo(802,500);ctx.stroke();ctx.fillStyle='#dfc782';ctx.font='900 11px system-ui';ctx.fillText('ЛИФТ',802,195);
 ctx.fillStyle='#507c63';ctx.beginPath();ctx.arc(210,530,31,0,Math.PI*2);ctx.fill();ctx.fillStyle='#72543a';ctx.fillRect(203,548,14,42);v107DrawCivilian(now);
}
function v107DrawCorridor(now){
 const W=1080,H=700;ctx.fillStyle='#8d9b96';ctx.fillRect(0,0,W,H);ctx.fillStyle='#2e3b40';ctx.fillRect(0,0,W,110);ctx.fillStyle='#596a6b';ctx.fillRect(0,570,W,130);ctx.strokeStyle='#ffffff18';for(let x=0;x<W;x+=80){ctx.beginPath();ctx.moveTo(x,110);ctx.lineTo(x,570);ctx.stroke()}for(let y=140;y<570;y+=62){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}
 for(let i=0;i<5;i++){const x=110+i*185;ctx.fillStyle='#27373c';ctx.fillRect(x,170,110,225);ctx.fillStyle='#a9d7d744';ctx.fillRect(x+14,190,82,95);ctx.fillStyle='#e7d796';ctx.font='800 9px system-ui';ctx.textAlign='center';ctx.fillText('ОФИС '+(i+1),x+55,420)}
 ctx.fillStyle='#13262b';ctx.fillRect(820,130,250,430);ctx.strokeStyle='#76d8cc88';ctx.lineWidth=3;ctx.strokeRect(820,130,250,430);ctx.fillStyle='#77d8cb22';ctx.fillRect(840,155,210,160);ctx.fillStyle='#081215';ctx.beginPath();ctx.roundRect(855,350,175,72,10);ctx.fill();ctx.fillStyle='#79e6d8';ctx.fillRect(875,365,45,26);ctx.fillRect(934,365,45,26);ctx.fillStyle='#d9fff8';ctx.font='900 12px system-ui';ctx.fillText('ПОСТ ОХРАНЫ',945,330);
 const darkness=clamp((player.x-450)/540,0,.48);ctx.fillStyle=`rgba(0,15,20,${darkness})`;ctx.fillRect(0,0,W,H);v107DrawCivilian(now);
}
function v107DrawElevator(now,elapsed){
 const g=ctx.createLinearGradient(0,0,0,vh);g.addColorStop(0,'#344148');g.addColorStop(1,'#0b1115');ctx.fillStyle=g;ctx.fillRect(0,0,vw,vh);ctx.strokeStyle='#7e929866';ctx.lineWidth=3;ctx.strokeRect(vw*.14,vh*.08,vw*.72,vh*.82);ctx.beginPath();ctx.moveTo(vw/2,vh*.08);ctx.lineTo(vw/2,vh*.9);ctx.stroke();
 const floors=elapsed<1?'12':elapsed<1.8?'9':elapsed<2.5?'6':elapsed<3.05?'3':elapsed<3.35?'0':'4';ctx.fillStyle=floors==='0'?'#ff536b':'#f1d884';ctx.font='900 42px system-ui';ctx.textAlign='center';ctx.fillText(floors,vw/2,vh*.2);ctx.font='800 11px system-ui';ctx.fillText(floors==='0'?'ЭТАЖ НЕ СУЩЕСТВУЕТ':'ЭТАЖ ОХРАНЫ',vw/2,vh*.25);
 if(elapsed>2.7&&elapsed<3.25){ctx.globalAlpha=.55;ctx.fillStyle='#030608';ctx.beginPath();ctx.arc(vw*.67,vh*.54,24,0,Math.PI*2);ctx.fill();ctx.fillRect(vw*.62,vh*.54,50,115);ctx.fillStyle='#ff3d55';ctx.beginPath();ctx.arc(vw*.65,vh*.54,3,0,Math.PI*2);ctx.arc(vw*.69,vh*.54,3,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1}
 ctx.fillStyle='#9eb1b3';ctx.font='700 10px system-ui';ctx.fillText('♪ спокойная музыка лифта ♪',vw/2,vh*.82);
}
function v107DrawDesk(now,elapsed){
 ctx.fillStyle='#061014';ctx.fillRect(0,0,vw,vh);const cols=2,rows=2,gap=10,mx=18,my=55,mw=(vw-mx*2-gap)/cols,mh=Math.min(170,(vh*.52-gap)/rows);
 for(let i=0;i<4;i++){const x=mx+(i%2)*(mw+gap),y=my+Math.floor(i/2)*(mh+gap);ctx.fillStyle='#0b2328';ctx.fillRect(x,y,mw,mh);ctx.strokeStyle=i===2&&elapsed>5.4?'#ff3f58':'#4e9b94';ctx.strokeRect(x,y,mw,mh);ctx.fillStyle='#78d7ce44';ctx.fillRect(x+12,y+12,mw-24,9);ctx.fillStyle='#b7d9d6';ctx.font='800 8px system-ui';ctx.textAlign='left';ctx.fillText(['ХОЛЛ','ЛИФТЫ','КАМЕРА 3-B','АРХИВ'][i],x+12,y+35);if(i===2&&elapsed>4.6){ctx.fillStyle='#030506';ctx.beginPath();ctx.arc(x+mw*.58,y+mh*.62,16,0,Math.PI*2);ctx.fill();ctx.fillStyle='#ff4057';ctx.beginPath();ctx.arc(x+mw*.55,y+mh*.59,2.5,0,Math.PI*2);ctx.arc(x+mw*.61,y+mh*.59,2.5,0,Math.PI*2);ctx.fill()}}
 const time=elapsed<1.8?'18:00':elapsed<3.5?'21:14':'23:47';ctx.fillStyle=elapsed>5.4?'#ff536b':'#f2dc97';ctx.font='900 30px system-ui';ctx.textAlign='center';ctx.fillText(time,vw/2,vh*.69);ctx.font='800 10px system-ui';ctx.fillStyle='#93aaa8';ctx.fillText(elapsed<3.5?'ОБЫЧНАЯ НОЧНАЯ СМЕНА':'ДВИЖЕНИЕ: ЭТАЖ 3 · ЗОНА B',vw/2,vh*.74);
 if(elapsed>5.4){const pulse=(Math.sin(now/85)+1)/2;ctx.fillStyle=`rgba(255,24,54,${.07+pulse*.08})`;ctx.fillRect(0,0,vw,vh);ctx.fillStyle='#ff6177';ctx.font='900 15px system-ui';ctx.fillText('ТРЕВОГА · КАМЕРА 3-B',vw/2,vh*.82)}
}
function v107DrawPrologue(now){
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vw,vh);
 if(v107Prologue.scene==='elevator'){v107DrawElevator(now,(now-v107Prologue.startedAt)/1000);return}
 if(v107Prologue.scene==='desk'){v107DrawDesk(now,(now-v107Prologue.startedAt)/1000);return}
 const worldW=v107Prologue.scene==='street'?1100:v107Prologue.scene==='lobby'?900:1080,maxX=Math.max(0,worldW-vw),camX=clamp(player.x-vw*.42,0,maxX);ctx.save();ctx.translate(-camX,0);
 if(v107Prologue.scene==='street')v107DrawStreet(now);else if(v107Prologue.scene==='lobby')v107DrawLobby(now);else v107DrawCorridor(now);ctx.restore();
 if(v107Prologue.scene==='street'){const glow=ctx.createRadialGradient(vw*.12,vh*.08,10,vw*.12,vh*.08,vw*.75);glow.addColorStop(0,'rgba(255,244,185,.32)');glow.addColorStop(1,'rgba(255,218,130,0)');ctx.fillStyle=glow;ctx.fillRect(0,0,vw,vh)}
}
function v107EnterScene(scene){
 v107HideAction();v107Prologue.scene=scene;v107Prologue.step=0;v107Prologue.startedAt=performance.now();v107Prologue.actionProgress=0;
 if(scene==='lobby'){player.x=110;player.y=460;v107Clock('17:46');v107Room('ВЕСТИБЮЛЬ');v107Objective('ОТМЕТЬСЯ В ЖУРНАЛЕ СМЕН');v107ShowCaption('В журнале уже стоит твоя подпись напротив сегодняшней даты.',4)}
 else if(scene==='elevator'){document.body.classList.add('v107Cutscene');v107Clock('17:48');v107Room('ЛИФТ');v107Objective('ПОДНИМАЕМСЯ НА ЭТАЖ ОХРАНЫ');v107ShowCaption('На панели на секунду появляется этаж 0.',4)}
 else if(scene==='corridor'){document.body.classList.remove('v107Cutscene');player.x=80;player.y=360;v107Clock('17:52');v107Room('СЛУЖЕБНЫЙ ЭТАЖ');v107Objective('ДОЙДИ ДО КОМНАТЫ ОХРАНЫ');v107ShowCaption('Сотрудники уже ушли. В офисах всё ещё работают мониторы.',4)}
 else if(scene==='desk'){document.body.classList.add('v107Cutscene');v107Clock('18:00');v107Room('ПОСТ ОХРАНЫ');v107Objective('ПРОВЕРЯЙ КАМЕРЫ');v107ShowCaption('Смена №184. Не поднимайся выше шестого этажа.',5)}
}
function v107PrologueTick(now){
 if(!v107Prologue.active)return;const dt=Math.min(.04,(now-v107Prologue.last)/1000||0);v107Prologue.last=now;
 if(v107Prologue.scene==='street'){
  v107Move(dt,{x1:60,x2:980,y1:300,y2:620});v107Clock('17:42');v107Room('ДОРОГА НА СМЕНУ');v107Objective('ДОЙДИ ДО СЛУЖЕБНОГО ВХОДА');
  const c=v107ActionContext({x:965,y:455},'ПРИЛОЖИТЬ ПРОПУСК','СЛУЖЕБНЫЙ ВХОД','▰',.75,82);v107HandlePrologueAction(dt,c,()=>{tone(720,.09,'sine',.1);v107EnterScene('lobby')});
 }else if(v107Prologue.scene==='lobby'){
  v107Move(dt,{x1:70,x2:835,y1:160,y2:610});
  if(v107Prologue.step===0){const c=v107ActionContext({x:403,y:330},'ОТМЕТИТЬСЯ','ЖУРНАЛ НОЧНОЙ СМЕНЫ','✎',.85,90);v107HandlePrologueAction(dt,c,()=>{v107Prologue.step=1;v107Objective('ВЫЗОВИ ЛИФТ');v107ShowCaption('Подпись уже была здесь. Она исчезла, когда ты коснулся страницы.',4);tone(420,.12,'triangle',.08)})}
  else{const c=v107ActionContext({x:802,y:430},'ВЫЗВАТЬ ЛИФТ','ЭТАЖ ОХРАНЫ','⇧',.55,92);v107HandlePrologueAction(dt,c,()=>v107EnterScene('elevator'))}
 }else if(v107Prologue.scene==='elevator'){
  v107HideAction();if(now-v107Prologue.startedAt>4300)v107EnterScene('corridor');
 }else if(v107Prologue.scene==='corridor'){
  v107Move(dt,{x1:55,x2:990,y1:250,y2:520});const c=v107ActionContext({x:930,y:385},'СЕСТЬ ЗА СТОЛ','НАЧАТЬ НОЧНУЮ СМЕНУ','◫',.9,94);v107HandlePrologueAction(dt,c,()=>v107EnterScene('desk'));
 }else if(v107Prologue.scene==='desk'){
  v107HideAction();const elapsed=(now-v107Prologue.startedAt)/1000;if(elapsed>7.6)v107BeginLastShift();
 }
 v107DrawPrologue(now);raf=requestAnimationFrame(v107PrologueTick);
}
function v107StartPrologue(demo=false){
 const duration=Math.max(360,Number(state.time)||360);v104BaseReset();state.time=duration;state.demo=demo;state.running=false;state.paused=true;state.finished=false;fireHeld=false;aim.active=false;
 v107Prologue={active:true,demo,scene:'street',step:0,last:performance.now(),startedAt:performance.now(),actionProgress:0,actionLock:false,captionUntil:0};player.x=100;player.y=470;player.facingX=1;player.facingY=0;
 document.body.classList.add('v107Prologue');document.body.classList.remove('v107Cutscene');$('intro').classList.add('hidden');$('finish').classList.add('hidden');$('score').textContent='0';v107ShowCaption('Тёплый вечер. До первой ночной смены осталось несколько минут.',4);resize();cancelAnimationFrame(raf);raf=requestAnimationFrame(v107PrologueTick);
}
startGame=function(demo=false){initAudio();try{audio?.ac?.resume?.()}catch(_){}v107StartPrologue(demo)};

/* The old rescue radio calls are ignored; the same HUD becomes the building service channel. */
v104Radio=function(speaker,text){
 if(speaker==='АННА')return;const s=v104StoryState();if(!s)return;s.radioSpeaker=speaker;s.radioText=text;s.lastRadioAt=performance.now();const panel=$('radioHud');if(panel){panel.classList.add('show');$('radioSpeaker').textContent=speaker;$('radioText').textContent=text;const channel=$('survivorHp');if(channel)channel.textContent='СЛУЖЕБНЫЙ КАНАЛ'}setCaption(speaker+': '+text,4.8);tone(speaker==='СИСТЕМА'?420:590,.07,'sine',.07)
};
function v107InitMission(){
 const now=performance.now();state.story={active:true,lastShift:true,phase:0,progress:0,nextSpawn:now+5000,lastRadioAt:0,choice:null,choiceOpen:false,bossSpawned:false,extractProgress:0,radioText:'',radioSpeaker:'ДИСПЕТЧЕР',survivor:{x:-9999,y:-9999,hp:1,maxHp:1,rescued:false,hidden:true}};
 state.activeRoom=99;state.roomsCleared=0;state.unlockedThrough=6;state.breakers=[];state.pods=[];state.spawnQueue=[];state.telegraphs=[];state.enemies=[];state.enemyBullets=[];state.bullets=[];state.grenadeObjs=[];state.corpses=[];state.time=Math.max(360,Number(state.time)||360);state.last=now;player.x=260;player.y=225;player.facingX=1;player.facingY=0;doorClosed=()=>false;v107EquipmentOffered=false;
 $('storyChoice')?.classList.add('hidden');$('radioSpeaker').textContent='ДИСПЕТЧЕР';$('radioText').textContent='Смена простая. Проверяй камеры и реагируй на тревоги.';$('survivorHp').textContent='СЛУЖЕБНЫЙ КАНАЛ';v104Radio('ДИСПЕТЧЕР','Камера 3-B потеряла сигнал. Проверь терминал охраны.');setTimeout(()=>setCaption('Подойди к терминалу и удерживай кнопку ДЕЙСТВИЕ.',4.5),260)
}
function v107BeginLastShift(){
 if(!v107Prologue.active)return;v107Prologue.active=false;cancelAnimationFrame(raf);v107HideAction();document.body.classList.remove('v107Prologue','v107Cutscene');v107MissionStart(v107Prologue.demo);v107InitMission();
}

v104Objective=function(){
 const s=v104StoryState();if(!s?.lastShift)return'СИСТЕМА ЗАГРУЖАЕТСЯ';
 if(s.phase===0)return'ПРОВЕРЬ КАМЕРУ 3-B';
 if(s.phase===1)return'ПИТАНИЕ: '+state.breakers.filter(b=>b.active).length+'/3';
 if(s.phase===2)return'НАЙДИ ЛИЧНОЕ ДЕЛО В АРХИВЕ';
 if(s.phase===3)return'ОТКРОЙ ЗАПИСЬ КАМЕРЫ 06';
 if(s.phase===4)return'УДАЛИ ПРОТОКОЛ СМЕНЫ';
 if(s.phase===5)return'ДОБЕРИСЬ ДО ЛИФТА';
 if(s.phase===6){const boss=state.enemies.find(e=>e.type==='boss');return boss?'НАЧАЛЬНИК СМЕНЫ: '+Math.max(0,Math.ceil(boss.hp)):'ПЕРЕЖИВИ ПОСЛЕДНЮЮ МИНУТУ'}
 if(s.phase===7)return'ЗАВЕРШЕНИЕ СМЕНЫ: '+Math.round(Math.min(100,s.extractProgress/4*100))+'%';return'СМЕНА ЗАВЕРШЕНА'
};
currentObjectiveText=v104Objective;
v104Target=function(){
 const s=v104StoryState();if(!s?.lastShift)return null;if(s.phase===0||s.phase===4)return v104Points.terminal;if(s.phase===1){const b=state.breakers.find(q=>!q.active);return b?{x:b.x,y:b.y,label:'РУБИЛЬНИК'}:v104Points.generator}if(s.phase===2)return{x:v104Points.card.x,y:v104Points.card.y,label:'ЛИЧНОЕ ДЕЛО'};if(s.phase===3)return{x:v104Points.sample.x,y:v104Points.sample.y,label:'КАМЕРА 06'};if(s.phase===5||s.phase===7)return{x:v104Points.elevator.x,y:v104Points.elevator.y,label:s.phase===7?'ЗАВЕРШИТЬ СМЕНУ':'ЛИФТ'};return null
};
v104DrawSurvivor=function(now){const a=v104StoryState()?.survivor;if(a?.hidden)return};

v106ActionContext=function(){
 const s=v104StoryState();if(!s?.lastShift||state.finished)return null;let point=null,label='',sub='УДЕРЖИВАЙ',icon='✋',radius=86,need=1,progress=0;
 if(s.phase===0){point=v104Points.terminal;label='ПРОВЕРИТЬ';sub='КАМЕРЫ ОХРАНЫ';icon='◫';need=1;progress=s.progress/need}
 else if(s.phase===1){const q=v106NearestBreaker();if(!q)return null;point=q.point;label='ВКЛЮЧИТЬ';sub='РУБИЛЬНИК ПИТАНИЯ';icon='⚡';need=1.05;progress=(q.point.progress||0)/need}
 else if(s.phase===2){point=v104Points.card;label='ЗАБРАТЬ ДЕЛО';sub='АРХИВ ПЕРСОНАЛА';icon='▰';need=.8;progress=s.progress/need}
 else if(s.phase===3){point=v104Points.sample;label='ОТКРЫТЬ ЗАПИСЬ';sub='КАМЕРА 06';icon='◉';need=.65;progress=s.progress/need;radius=92}
 else if(s.phase===4){point=v104Points.terminal;label='УДАЛИТЬ';sub='ПРОТОКОЛ СМЕНЫ №184';icon='⌫';need=1.2;progress=s.progress/need}
 else if(s.phase===5){point=v104Points.elevator;label='ВЫЗВАТЬ ЛИФТ';sub='05:55 · ВЫХОД ЗАБЛОКИРОВАН';icon='⇧';need=.55;progress=s.progress/need;radius=96}
 else if(s.phase===7){point=v104Points.elevator;label='ЗАВЕРШИТЬ СМЕНУ';sub='УДЕРЖИВАЙ ДО 06:00';icon='✓';need=4;progress=s.extractProgress/need;radius=94}
 else return null;const distance=dist(player.x,player.y,point.x,point.y);return{phase:s.phase,point,label,sub,icon,radius,need,progress:clamp(progress,0,1),distance,near:distance<radius,companionReady:true}
};
function v107Advance(next,speaker,text,score=120){const s=v104StoryState();s.phase=next;s.progress=0;state.roomsCleared=Math.min(6,next);state.score+=score;v104Radio(speaker,text)}
updateObjective=function(dt,now){
 const s=v104StoryState();if(!s?.lastShift)return;if(s.phase>=1&&s.phase<=6)v104Ambient(now);const c=v106ActionContext();v106CurrentAction=c;
 if(s.phase===0){const active=c?.near&&v106ActionHeld;s.progress=active?Math.min(1,s.progress+dt):Math.max(0,s.progress-dt*.7);if(s.progress>=1){state.breakers=breakerTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,active:false,progress:0}));v106ConsumeAction();v107Advance(1,'СИСТЕМА','Камера 3-B отключена. Главная сеть обесточена — запусти три рубильника.',140)}}
 else if(s.phase===1){for(const b of state.breakers)if(!b.active){const near=c?.point===b&&c.near&&v106ActionHeld;b.progress=near?Math.min(1.05,b.progress+dt):Math.max(0,b.progress-dt*.5);if(b.progress>=1.05){b.active=true;v106ConsumeAction();state.score+=75;particles(b.x,b.y,18,'#ffca68');tone(680,.16,'square',.15);v104Radio('СИСТЕМА','Рубильник '+state.breakers.filter(q=>q.active).length+' из 3 активирован.')}}if(state.breakers.length&&state.breakers.every(b=>b.active)){v107Advance(2,'ДИСПЕТЧЕР','Питание вернулось. В архиве обнаружено личное дело на твоё имя.',180);if(!v107EquipmentOffered){v107EquipmentOffered=true;setTimeout(()=>showUpgrades(0),180)}}}
 else if(s.phase===2){const active=c?.near&&v106ActionHeld;s.progress=active?Math.min(.8,s.progress+dt):Math.max(0,s.progress-dt*.7);if(s.progress>=.8){v106ConsumeAction();v107Advance(3,'ЗАПИСЬ','Если ты снова это слышишь, значит они опять очистили тебе память. Не смотри в камеру 06.',210)}}
 else if(s.phase===3){const active=c?.near&&v106ActionHeld;s.progress=active?Math.min(.65,s.progress+dt):Math.max(0,s.progress-dt*.9);if(s.progress>=.65){v106ConsumeAction();v107Advance(4,'СИСТЕМА','Нарушение протокола. Все выходы заблокированы. Удалите запись смены №184.',220);for(const t of ['runner','walker','spitter','brute'])queueSpawn(t,roomAt(player.x,player.y),.45+rand()*.7);state.shake=9;tone(48,.6,'sawtooth',.24)}}
 else if(s.phase===4){const active=c?.near&&v106ActionHeld;s.progress=active?Math.min(1.2,s.progress+dt):Math.max(0,s.progress-dt*.65);if(s.progress>=1.2){v106ConsumeAction();v107Advance(5,'СИСТЕМА','05:55. Смена заканчивается через пять минут. Оставайтесь на рабочем месте.',260)}}
 else if(s.phase===5){const active=c?.near&&v106ActionHeld;s.progress=active?Math.min(.55,s.progress+dt):Math.max(0,s.progress-dt*.8);if(s.progress>=.55){v106ConsumeAction();s.phase=6;s.bossSpawned=true;state.roomsCleared=5;spawnEnemy('boss',390,760);queueSpawn('runner',5,.7);queueSpawn('walker',5,1.1);banner(5,'НАЧАЛЬНИК СМЕНЫ');v104Radio('СИСТЕМА','Несанкционированное завершение смены. Начальник смены направлен к лифту.')}}
 else if(s.phase===6&&s.bossSpawned&&!state.enemies.some(e=>e.type==='boss')){s.phase=7;s.extractProgress=0;state.roomsCleared=6;v104Radio('СИСТЕМА','05:59. Удерживайте кнопку завершения смены до 06:00.')}
 else if(s.phase===7){const active=c?.near&&v106ActionHeld;s.extractProgress=active?Math.min(4,s.extractProgress+dt):Math.max(0,s.extractProgress-dt*.7);if(s.extractProgress>=4){v106ConsumeAction();s.phase=8;state.score+=620;finish(true,'Смена завершена. На телефоне новое сообщение: «Следующая смена начинается сегодня в 23:47».')}}
};
updateBoss=function(e,dt,now){v107BossUpdate(e,dt,now);if(v104StoryState()?.lastShift&&e.type==='boss')$('bossPhase').textContent='НАЧАЛЬНИК СМЕНЫ · ФАЗА '+e.phase};
const v107HudBase=updateHud;
updateHud=function(now){v107HudBase(now);const s=v104StoryState();if(s?.lastShift){$('objective').textContent=v104Objective();$('survivorHp').textContent='СЛУЖЕБНЫЙ КАНАЛ';if(s.phase===6){const boss=state.enemies.find(e=>e.type==='boss');if(boss)$('bossPhase').textContent='НАЧАЛЬНИК СМЕНЫ · ФАЗА '+boss.phase}}};
finish=async function(success,reason){const p=v107MissionFinish(success,reason);$('resultEyebrow').textContent=success?'СМЕНА ЗАВЕРШЕНА':'СМЕНА СОРВАНА';$('resultTitle').textContent=success?'06:00':'Охранник не вернулся';$('resultIcon').textContent=success?'◷':'☣';await p};
