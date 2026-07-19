(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#020608');tg?.setBackgroundColor?.('#020608');
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const chatId=params.get('chat_id')||'';
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const canvas=$('game'),ctx=canvas.getContext('2d',{alpha:false});
  const roomName=$('roomName'),scoreEl=$('score'),timerEl=$('timer'),objectiveEl=$('objective'),livesEl=$('lives');
  const batteryEl=$('battery'),batteryBar=$('batteryBar'),threatEl=$('threat'),threatBar=$('threatBar');
  const caption=$('caption'),warning=$('warning');
  const rooms=[
    {name:'ПОСТ ОХРАНЫ',tone:'#244a50',doors:[1,2],cover:true,search:'Терминал сообщает: объект реагирует на шум.'},
    {name:'МЕДИЦИНСКИЙ БЛОК',tone:'#31514c',doors:[0,3],cover:true,search:'На каталке свежие царапины.'},
    {name:'АРХИВ',tone:'#51472c',doors:[0,3,4],cover:true,search:'Стеллажи качаются, хотя ветра нет.'},
    {name:'ЛАБОРАТОРИЯ',tone:'#333b59',doors:[1,2,5],cover:false,search:'Камера содержания открыта изнутри.'},
    {name:'ГЕНЕРАТОРНАЯ',tone:'#584326',doors:[2,5],cover:true,search:'Главный рубильник ждёт запуска.'},
    {name:'ЛИФТОВОЙ ХОЛЛ',tone:'#39464d',doors:[3,4],cover:false,search:'Лифт не отвечает без питания.'}
  ];
  const state={running:false,finished:false,demo:false,sessionId:null,seed:0,time:150,last:0,room:0,monsterRoom:4,monsterTarget:0,monsterMoveAt:0,monsterStunUntil:0,threat:10,noise:0,battery:100,flashlight:true,lives:3,score:0,cards:0,generator:false,hidden:false,hideUntil:0,bottles:2,searches:0,hits:0,chase:false,chaseUntil:0,escaped:false,found:new Set(),cardRooms:new Set(),particles:[],shake:0,messageUntil:0,lastTick:0,lastHeartbeat:0,lastStep:0,audio:null};
  let raf=0,resizeObserver=null;

  function rand(){state.seed=(state.seed*1664525+1013904223)>>>0;return state.seed/4294967296}
  function vibrate(type='light'){try{tg?.HapticFeedback?.impactOccurred?.(type)}catch(_){}}
  async function api(path,body={}){const res=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});const data=await res.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));if(!res.ok||!data.ok)throw new Error(data.reason||'Ошибка игрового сервера.');return data}
  function goGames(){location.href='/games/?'+new URLSearchParams({...Object.fromEntries(params),chat_id:chatId}).toString()}
  function setMessage(text,seconds=2.6){caption.textContent=text;state.messageUntil=performance.now()+seconds*1000}
  function formatTime(v){v=Math.max(0,Math.ceil(v));return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0')}
  function threatLabel(){if(state.chase)return 'ПОГОНЯ';if(state.threat>78)return 'РЯДОМ';if(state.threat>50)return 'ИЩЕТ';if(state.threat>25)return 'СЛЫШИТ';return 'ТИХО'}
  function updateHud(){
    scoreEl.textContent=Math.max(0,Math.round(state.score));timerEl.textContent=formatTime(state.time);
    objectiveEl.textContent=state.generator?'ДОБЕРИСЬ ДО ЛИФТА':state.cards>=3?'ЗАПУСТИ ГЕНЕРАТОР':`КЛЮЧ-КАРТЫ ${state.cards}/3`;
    livesEl.textContent='♥'.repeat(state.lives)+'♡'.repeat(Math.max(0,3-state.lives));
    batteryEl.textContent=Math.round(state.battery)+'%';batteryBar.style.width=Math.max(0,state.battery)+'%';
    threatEl.textContent=threatLabel();threatBar.style.width=Math.min(100,state.threat)+'%';
    roomName.textContent=rooms[state.room].name;$('bottles').textContent=state.bottles;
    $('flashlight').classList.toggle('off',!state.flashlight);
    $('hide').disabled=!rooms[state.room].cover||state.hidden;$('distract').disabled=state.bottles<=0;$('burst').disabled=state.battery<14;
  }

  function resize(){
    const rect=canvas.getBoundingClientRect(),dpr=Math.min(2.5,window.devicePixelRatio||1);
    canvas.width=Math.max(2,Math.round(rect.width*dpr));canvas.height=Math.max(2,Math.round(rect.height*dpr));ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function rounded(x,y,w,h,r){ctx.beginPath();ctx.roundRect(x,y,w,h,r)}
  function drawRoom(now){
    const w=canvas.clientWidth,h=canvas.clientHeight,room=rooms[state.room],dark=state.flashlight?1:0.34;
    ctx.save();if(state.shake>0){ctx.translate((rand()-.5)*state.shake,(rand()-.5)*state.shake);state.shake*=.88}
    const bg=ctx.createLinearGradient(0,0,0,h);bg.addColorStop(0,'#091013');bg.addColorStop(1,'#010304');ctx.fillStyle=bg;ctx.fillRect(-10,-10,w+20,h+20);
    ctx.globalAlpha=.55*dark;ctx.fillStyle=room.tone;ctx.fillRect(0,0,w,h*.72);ctx.globalAlpha=1;
    const vanishingX=w*.5,vanishingY=h*.35;
    ctx.strokeStyle=`rgba(120,175,175,${.18*dark})`;ctx.lineWidth=2;
    for(let i=-4;i<=4;i++){ctx.beginPath();ctx.moveTo(vanishingX+i*18,vanishingY);ctx.lineTo(vanishingX+i*w*.22,h);ctx.stroke()}
    for(let y=vanishingY;y<h;y+=Math.max(24,(y-vanishingY)*.23+20)){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
    const doorW=Math.min(130,w*.28),doorH=Math.min(220,h*.48),doorY=h*.27;
    rooms[state.room].doors.slice(0,3).forEach((target,index)=>{
      const positions=rooms[state.room].doors.length===1?[.5]:rooms[state.room].doors.length===2?[.25,.75]:[.18,.5,.82];
      const x=w*positions[index]-doorW/2;
      ctx.fillStyle='#020607';rounded(x,doorY,doorW,doorH,8);ctx.fill();ctx.strokeStyle=`rgba(116,185,181,${.28*dark})`;ctx.lineWidth=3;ctx.stroke();
      ctx.fillStyle=`rgba(126,255,232,${.45*dark})`;ctx.font='700 10px system-ui';ctx.textAlign='center';ctx.fillText(rooms[target].name,x+doorW/2,doorY+doorH+18);
      ctx.fillStyle=target===state.monsterRoom?'#ff3658':'#6b918e';ctx.beginPath();ctx.arc(x+doorW-13,doorY+doorH*.52,4,0,Math.PI*2);ctx.fill();
    });
    if(room.cover){ctx.fillStyle='#071012';rounded(w*.05,h*.43,w*.18,h*.36,6);ctx.fill();ctx.strokeStyle='#213b3e';ctx.stroke();ctx.fillStyle='#14272a';for(let i=1;i<4;i++)ctx.fillRect(w*.06,h*.43+i*h*.08,w*.16,2)}
    drawProps(w,h,dark,now);
    const visible=state.monsterRoom===state.room&&!state.hidden&&now>state.monsterStunUntil;
    if(visible)drawMonster(w,h,now);
    if(state.flashlight&&state.battery>0){
      ctx.save();ctx.globalCompositeOperation='screen';const g=ctx.createRadialGradient(w*.5,h*.58,10,w*.5,h*.58,Math.max(w,h)*.62);g.addColorStop(0,'rgba(205,255,245,.33)');g.addColorStop(.38,'rgba(105,220,205,.12)');g.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=g;ctx.fillRect(0,0,w,h);ctx.restore();
    }else{ctx.fillStyle='rgba(0,0,0,.66)';ctx.fillRect(0,0,w,h)}
    if(state.hidden){ctx.fillStyle='rgba(0,0,0,.78)';ctx.fillRect(0,0,w,h);ctx.strokeStyle='#182528';ctx.lineWidth=18;ctx.strokeRect(-8,-8,w+16,h+16);ctx.fillStyle='#a5b5b4';ctx.font='800 11px system-ui';ctx.textAlign='center';ctx.fillText('ТЫ В УКРЫТИИ · НЕ ДВИГАЙСЯ',w/2,h*.76)}
    drawParticles(now);ctx.restore();
  }
  function drawProps(w,h,dark,now){
    ctx.globalAlpha=dark;
    if(state.room===0){ctx.fillStyle='#08171a';rounded(w*.34,h*.48,w*.32,h*.17,8);ctx.fill();ctx.fillStyle='#5bfff0';ctx.globalAlpha=.16+.08*Math.sin(now/250);ctx.fillRect(w*.39,h*.51,w*.22,h*.08)}
    if(state.room===1){ctx.fillStyle='#b8d3cf22';ctx.fillRect(w*.32,h*.58,w*.38,8);ctx.fillRect(w*.36,h*.58,7,h*.2);ctx.fillRect(w*.65,h*.58,7,h*.2)}
    if(state.room===2){ctx.fillStyle='#172326';for(let i=0;i<5;i++)ctx.fillRect(w*(.28+i*.1),h*.43,4,h*.34);for(let j=0;j<4;j++)ctx.fillRect(w*.28,h*(.46+j*.08),w*.44,4)}
    if(state.room===3){ctx.strokeStyle='#536b70';ctx.lineWidth=5;ctx.beginPath();ctx.arc(w*.5,h*.53,Math.min(w,h)*.15,0,Math.PI*2);ctx.stroke();ctx.strokeStyle='#ff3e5d';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(w*.39,h*.42);ctx.lineTo(w*.61,h*.64);ctx.stroke()}
    if(state.room===4){ctx.fillStyle='#172126';rounded(w*.37,h*.43,w*.26,h*.28,10);ctx.fill();ctx.fillStyle=state.generator?'#5dffc4':'#ffb44c';ctx.beginPath();ctx.arc(w*.5,h*.52,10,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#293d40';ctx.lineWidth=5;for(let i=0;i<5;i++){ctx.beginPath();ctx.moveTo(w*.4+i*w*.05,h*.59);ctx.lineTo(w*.4+i*w*.05,h*.68);ctx.stroke()}}
    if(state.room===5){ctx.fillStyle='#061012';ctx.fillRect(w*.38,h*.31,w*.24,h*.44);ctx.strokeStyle=state.generator?'#5dffc4':'#4e6568';ctx.lineWidth=4;ctx.strokeRect(w*.38,h*.31,w*.24,h*.44);ctx.fillStyle=state.generator?'#5dffc4':'#ff3e5d';ctx.fillRect(w*.63,h*.48,7,15)}
    ctx.globalAlpha=1;
  }
  function drawMonster(w,h,now){
    const chase=state.chase?1:0,scale=1+chase*.28+Math.sin(now/80)*.015,x=w*.5,y=h*.55;
    ctx.save();ctx.translate(x,y);ctx.scale(scale,scale);ctx.shadowColor='#000';ctx.shadowBlur=35;ctx.fillStyle='#000';ctx.beginPath();ctx.ellipse(0,45,34,82,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.ellipse(0,-38,27,35,0,0,Math.PI*2);ctx.fill();
    ctx.shadowColor='#ff2148';ctx.shadowBlur=18;ctx.fillStyle='#ff2148';ctx.beginPath();ctx.ellipse(-9,-42,4,2,0,0,Math.PI*2);ctx.ellipse(9,-42,4,2,0,0,Math.PI*2);ctx.fill();ctx.restore();
  }
  function spawnParticles(count,color='#9ffff0'){const w=canvas.clientWidth,h=canvas.clientHeight;for(let i=0;i<count;i++)state.particles.push({x:w*.5+(rand()-.5)*80,y:h*.55+(rand()-.5)*80,vx:(rand()-.5)*80,vy:(rand()-.5)*80-20,life:.5+rand(),color})}
  function drawParticles(){const dt=.016;state.particles=state.particles.filter(p=>{p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=15*dt;if(p.life<=0)return false;ctx.globalAlpha=Math.min(1,p.life*2);ctx.fillStyle=p.color;ctx.fillRect(p.x,p.y,2,2);return true});ctx.globalAlpha=1}

  function initAudio(){
    if(state.audio)return;try{const ac=new (window.AudioContext||window.webkitAudioContext)(),master=ac.createGain();master.gain.value=.09;master.connect(ac.destination);const osc=ac.createOscillator(),gain=ac.createGain();osc.type='sawtooth';osc.frequency.value=43;gain.gain.value=.05;osc.connect(gain).connect(master);osc.start();state.audio={ac,master,osc,gain}}catch(_){state.audio=null}
  }
  function tone(freq=120,duration=.12,type='sine',volume=.18){const a=state.audio;if(!a)return;const o=a.ac.createOscillator(),g=a.ac.createGain();o.type=type;o.frequency.setValueAtTime(freq,a.ac.currentTime);g.gain.setValueAtTime(volume,a.ac.currentTime);g.gain.exponentialRampToValueAtTime(.001,a.ac.currentTime+duration);o.connect(g).connect(a.master);o.start();o.stop(a.ac.currentTime+duration)}
  function footstep(){tone(55,.16,'sine',.35);setTimeout(()=>tone(43,.14,'sine',.25),90)}
  function heartbeat(){tone(62,.11,'sine',.38);setTimeout(()=>tone(52,.15,'sine',.28),130)}

  function chooseCards(){state.cardRooms.clear();const pool=[1,2,3,4];while(state.cardRooms.size<3)state.cardRooms.add(pool[Math.floor(rand()*pool.length)])}
  function addNoise(amount){state.noise=Math.min(100,state.noise+amount);state.threat=Math.min(100,state.threat+amount*.55);if(state.hidden){state.hidden=false;setMessage('Ты выдал укрытие шумом.',2)}}
  function move(direction){
    if(!state.running||state.finished)return;const exits=rooms[state.room].doors;if(!exits.length)return;
    const target=direction<0?exits[0]:exits[exits.length-1];state.room=target;state.hidden=false;addNoise(state.flashlight?18:12);state.score+=4;footstep();vibrate('light');setMessage(`Ты вошёл: ${rooms[target].name}.`,1.7);
    if(state.room===state.monsterRoom&&performance.now()>state.monsterStunUntil)beginChase('Он уже был здесь.');
    updateHud();
  }
  function searchRoom(){
    if(!state.running||state.finished||state.hidden)return;state.searches++;addNoise(22);tone(220,.08,'square',.12);state.score+=2;
    const key='r'+state.room;
    if(state.cardRooms.has(state.room)&&!state.found.has(key)){
      state.found.add(key);state.cards++;state.score+=35;spawnParticles(24,'#ffc96b');tone(640,.25,'sine',.25);vibrate('medium');setMessage(`Ключ-карта найдена. Осталось: ${3-state.cards}.`,3);
    }else if(state.room===4&&state.cards>=3&&!state.generator){
      state.generator=true;state.score+=45;state.threat=Math.max(state.threat,62);spawnParticles(35,'#70ffc0');tone(95,.7,'sawtooth',.22);setMessage('ПИТАНИЕ ВОССТАНОВЛЕНО. Охотник услышал генератор.',3.5);warning.textContent='БЕГИ К ЛИФТУ';warning.classList.add('show');setTimeout(()=>warning.classList.remove('show'),1800);state.monsterTarget=state.room;
    }else if(state.room===5&&state.generator){
      escape();return;
    }else if(!state.found.has('s'+state.room)){
      state.found.add('s'+state.room);setMessage(rooms[state.room].search,3);
      if(rand()<.3){state.battery=Math.min(100,state.battery+18);setMessage('Найдена запасная батарея. +18%.',2.5)}
    }else setMessage('Здесь больше ничего полезного.',1.8);
    if(state.room===state.monsterRoom&&performance.now()>state.monsterStunUntil)beginChase('Шорох прямо за спиной.');updateHud();
  }
  function hide(){
    if(!state.running||state.finished||!rooms[state.room].cover)return;state.hidden=true;state.hideUntil=performance.now()+4200;state.noise=Math.max(0,state.noise-18);tone(90,.1,'sine',.12);setMessage('Ты спрятался. Не нажимай кнопки.',3);updateHud();
  }
  function distract(){
    if(!state.running||state.finished||state.bottles<=0)return;state.bottles--;addNoise(8);const exits=rooms[state.room].doors;state.monsterTarget=exits[Math.floor(rand()*exits.length)]??state.room;state.monsterMoveAt=performance.now()+450;tone(480,.12,'square',.24);setTimeout(()=>tone(240,.18,'square',.18),140);setMessage('Бутылка разбилась в соседнем коридоре.',2.4);updateHud();
  }
  function burst(){
    if(!state.running||state.finished||state.battery<14)return;state.battery-=14;state.flashlight=true;spawnParticles(45,'#d8fff8');ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.clientWidth,canvas.clientHeight);tone(1000,.08,'square',.25);vibrate('heavy');
    if(state.monsterRoom===state.room){state.monsterStunUntil=performance.now()+3500;state.chase=false;state.threat=Math.max(25,state.threat-35);state.score+=18;setMessage('Охотник ослеплён. У тебя несколько секунд.',2.7)}else setMessage('Вспышка ушла в пустой коридор.',1.8);updateHud();
  }
  function toggleFlash(){if(!state.running||state.finished||state.battery<=0)return;state.flashlight=!state.flashlight;addNoise(2);tone(state.flashlight?760:260,.05,'square',.08);updateHud()}
  function beginChase(text){
    if(state.hidden){if(rand()<.72){state.threat=Math.max(15,state.threat-25);state.monsterTarget=rooms[state.room].doors[Math.floor(rand()*rooms[state.room].doors.length)]??0;setMessage('Он остановился рядом с укрытием… и ушёл.',3);return}state.hidden=false}
    state.chase=true;state.chaseUntil=performance.now()+5200;state.threat=100;state.shake=9;warning.textContent='ОН ВИДИТ ТЕБЯ';warning.classList.add('show');setTimeout(()=>warning.classList.remove('show'),1100);setMessage(text+' Беги или используй вспышку!',3);heartbeat();vibrate('heavy')
  }
  function hit(){state.hits++;state.lives--;state.chase=false;state.hidden=false;state.shake=18;state.score=Math.max(0,state.score-25);state.monsterRoom=state.room===0?4:0;state.monsterTarget=state.room;state.threat=42;spawnParticles(40,'#ff3658');tone(38,.7,'sawtooth',.38);vibrate('heavy');if(state.lives<=0){finish(false,'Охотник настиг тебя.');return}setMessage('Удар отбросил тебя в коридор. Осталось жизней: '+state.lives+'.',3);updateHud()}
  function escape(){if(state.escaped)return;state.escaped=true;state.score+=70+Math.max(0,Math.round(state.time*.45))+state.lives*12;warning.textContent='ЛИФТ ЗАКРЫВАЕТСЯ';warning.classList.add('show');tone(120,.8,'sawtooth',.22);setTimeout(()=>finish(true,'Лифт закрылся в последнюю секунду.'),1250)}

  function monsterAI(now,dt){
    state.noise=Math.max(0,state.noise-dt*(state.hidden?12:5));state.threat=Math.max(5,state.threat-dt*(state.chase?0:2.2));
    if(state.hidden&&now>state.hideUntil){state.hidden=false;setMessage('Ты осторожно вышел из укрытия.',1.8)}
    if(state.chase){state.threat=100;if(now>state.chaseUntil&&now>state.monsterStunUntil)hit();return}
    if(now<state.monsterStunUntil)return;
    const proximity=rooms[state.monsterRoom].doors.includes(state.room)?18:0;state.threat=Math.min(100,state.threat+proximity*dt*.16+state.noise*dt*.035);
    if(now>state.monsterMoveAt){
      const exits=rooms[state.monsterRoom].doors;let target=state.monsterTarget;
      if(state.noise>38||state.generator)target=state.room;
      let next=exits[Math.floor(rand()*exits.length)]??state.monsterRoom;if(exits.includes(target))next=target;
      state.monsterRoom=next;state.monsterMoveAt=now+(1700+rand()*2600)*(state.generator?.72:1);
      if(state.monsterRoom===state.room){if(state.hidden){if(rand()<.38+state.threat/250)beginChase('Дверца укрытия медленно открылась.');else setMessage('Тяжёлые шаги остановились в комнате.',2.4)}else beginChase('Силуэт появился в дверях.')}else if(rooms[state.monsterRoom].doors.includes(state.room)){setMessage(rand()<.5?'Шаги слышны совсем рядом.':'За стеной что-то медленно дышит.',2.2);footstep()}
    }
    if(state.threat>55&&now-state.lastHeartbeat>Math.max(500,1450-state.threat*9)){state.lastHeartbeat=now;heartbeat()}
  }
  function tick(now){
    if(!state.running||state.finished)return;const dt=Math.min(.05,(now-state.last)/1000||0);state.last=now;state.time-=dt;
    if(state.flashlight&&state.battery>0){state.battery=Math.max(0,state.battery-dt*(state.chase?1.9:.42));if(state.battery<=0){state.flashlight=false;setMessage('Фонарик разрядился.',2.5)}}
    monsterAI(now,dt);if(state.time<=0){finish(false,'Аварийная блокировка запечатала комплекс.');return}
    if(now>state.messageUntil&&!state.chase)caption.textContent=state.generator?'Питание работает. Ищи лифтовой холл.':state.cards>=3?'Все карты собраны. Найди генераторную.':`Найди ключ-карты: ${state.cards}/3.`;
    updateHud();drawRoom(now);raf=requestAnimationFrame(tick)
  }

  async function startGame(demo=false){
    if(state.running)return;state.demo=demo;initAudio();try{state.audio?.ac?.resume?.()}catch(_){ }
    $('intro').classList.add('hidden');state.running=true;state.finished=false;state.last=performance.now();state.monsterMoveAt=state.last+2500;chooseCards();resize();setMessage('Система: объект покинул камеру содержания.',3.5);updateHud();raf=requestAnimationFrame(tick)
  }
  async function prepare(){
    try{const data=await api('start',{game:'night-hunter'});state.sessionId=data.session_id;state.seed=Number(data.seed)||Date.now();state.time=Number(data.duration)||150;$('start').textContent='ВОЙТИ В КОМПЛЕКС';$('start').classList.remove('loading');$('start').addEventListener('click',()=>startGame(false),{once:true})}
    catch(error){state.seed=(Date.now()>>>0);$('start').classList.add('hidden');$('demo').classList.remove('hidden');$('startError').style.display='block';$('startError').textContent=error.message+' Доступен демонстрационный режим без начисления влияния.';$('demo').addEventListener('click',()=>startGame(true),{once:true})}
  }
  async function finish(success,reason){
    if(state.finished)return;state.finished=true;state.running=false;cancelAnimationFrame(raf);warning.classList.remove('show');
    const raw=Math.max(0,Math.min(300,Math.round(state.score+state.cards*12+(state.generator?22:0)+(success?38:0)-state.hits*8)));
    $('resultIcon').textContent=success?'⬆':'◉';$('resultEyebrow').textContent=success?'ЛИФТ ЗАПУЩЕН':'СВЯЗЬ ПОТЕРЯНА';$('resultTitle').textContent=success?'Ты выбрался':'Охота окончена';$('resultText').textContent=reason;$('resultScore').textContent=raw;$('resultCards').textContent=state.cards+'/3';$('resultSearches').textContent=state.searches;$('resultHits').textContent=state.hits;$('finish').classList.remove('hidden');
    if(state.demo||!state.sessionId){$('reward').textContent='Демо-режим: результат не начисляется в баланс влияния.';return}
    try{const data=await api('finish',{session_id:state.sessionId,score:raw,stats:{escaped:success,cards:state.cards,generator:state.generator,searches:state.searches,hits:state.hits,battery:Math.round(state.battery),time_left:Math.round(state.time)}});$('reward').innerHTML=data.actual_reward>0?`Начислено <b>+${data.actual_reward}</b> влияния. Баланс: <b>${data.balance}</b>.`:(data.message||'Результат сохранён, но лучшая награда дня не улучшилась.')}
    catch(error){$('reward').textContent='Результат получен, но сервер не сохранил его: '+error.message}
  }

  $('back').addEventListener('click',goGames);$('toGames').addEventListener('click',goGames);$('again').addEventListener('click',()=>location.reload());
  $('left').addEventListener('click',()=>move(-1));$('right').addEventListener('click',()=>move(1));$('search').addEventListener('click',searchRoom);$('hide').addEventListener('click',hide);$('distract').addEventListener('click',distract);$('burst').addEventListener('click',burst);$('flashlight').addEventListener('click',toggleFlash);
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&state.running&&!state.finished){state.flashlight=false;updateHud()}});
  resizeObserver=new ResizeObserver(resize);resizeObserver.observe(canvas);window.addEventListener('resize',resize);prepare();
})();
