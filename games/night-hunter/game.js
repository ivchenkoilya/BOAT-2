(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#020608');tg?.setBackgroundColor?.('#020608');
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const chatId=params.get('chat_id')||'';
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const canvas=$('game'),ctx=canvas.getContext('2d',{alpha:false});
  const minimap=$('minimap'),mctx=minimap.getContext('2d');
  const lightCanvas=document.createElement('canvas'),lctx=lightCanvas.getContext('2d');
  const roomName=$('roomName'),scoreEl=$('score'),timerEl=$('timer'),objectiveEl=$('objective'),livesEl=$('lives');
  const batteryEl=$('battery'),batteryBar=$('batteryBar'),threatEl=$('threat'),threatBar=$('threatBar');
  const caption=$('caption'),warning=$('warning'),interactButton=$('interact'),interactLabel=$('interactLabel');
  const progressBox=$('interactionProgress'),progressBar=$('interactionBar'),progressText=$('interactionText'),contextHint=$('contextHint');
  const joystick=$('joystick'),joystickKnob=$('joystickKnob');

  const WORLD={w:1200,h:900};
  const rooms=[
    {id:'security',name:'ПОСТ ОХРАНЫ',x:40,y:40,w:330,h:280,color:'#17383d'},
    {id:'lab',name:'ЛАБОРАТОРИЯ',x:435,y:40,w:330,h:280,color:'#252d48'},
    {id:'archive',name:'АРХИВ',x:830,y:40,w:330,h:280,color:'#3b3422'},
    {id:'med',name:'МЕДИЦИНСКИЙ БЛОК',x:40,y:580,w:330,h:280,color:'#21403b'},
    {id:'elevator',name:'ЛИФТОВОЙ ХОЛЛ',x:435,y:580,w:330,h:280,color:'#28383d'},
    {id:'generator',name:'ГЕНЕРАТОРНАЯ',x:830,y:580,w:330,h:280,color:'#44331f'}
  ];
  const corridors=[
    {x:350,y:145,w:105,h:72},{x:745,y:145,w:105,h:72},
    {x:350,y:685,w:105,h:72},{x:745,y:685,w:105,h:72},
    {x:165,y:300,w:82,h:300},{x:559,y:300,w:82,h:300},{x:954,y:300,w:82,h:300},
    {x:165,y:414,w:871,h:78}
  ];
  const walkZones=[...rooms,...corridors];

  const solids=[
    {id:'sec-desk',type:'desk',x:112,y:93,w:185,h:58},
    {id:'sec-locker',type:'locker',x:64,y:205,w:52,h:86},
    {id:'sec-cabinet',type:'cabinet',x:302,y:70,w:39,h:96},
    {id:'lab-capsule',type:'capsule',x:545,y:78,w:112,h:153},
    {id:'lab-console-a',type:'console',x:458,y:244,w:88,h:38},
    {id:'lab-console-b',type:'console',x:666,y:244,w:76,h:38},
    {id:'archive-shelf-a',type:'shelf',x:866,y:79,w:236,h:31},
    {id:'archive-shelf-b',type:'shelf',x:866,y:151,w:236,h:31},
    {id:'archive-shelf-c',type:'shelf',x:866,y:223,w:172,h:31},
    {id:'archive-locker',type:'locker',x:1091,y:211,w:48,h:80},
    {id:'med-bed-a',type:'bed',x:139,y:628,w:164,h:47},
    {id:'med-bed-b',type:'bed',x:139,y:754,w:164,h:47},
    {id:'med-locker',type:'locker',x:63,y:686,w:51,h:87},
    {id:'med-cabinet',type:'cabinet',x:305,y:608,w:38,h:96},
    {id:'generator-main',type:'generator',x:900,y:630,w:182,h:111},
    {id:'generator-locker',type:'locker',x:1087,y:748,w:50,h:85},
    {id:'generator-crate',type:'crate',x:850,y:785,w:74,h:48},
    {id:'elevator-console',type:'elevatorConsole',x:684,y:711,w:38,h:68}
  ];

  const covers=[
    {id:'sec-locker',x:123,y:249,label:'ШКАФ ПОСТА ОХРАНЫ'},
    {id:'archive-locker',x:1080,y:251,label:'АРХИВНЫЙ ШКАФ'},
    {id:'med-locker',x:123,y:730,label:'МЕДИЦИНСКИЙ ШКАФ'},
    {id:'generator-locker',x:1076,y:788,label:'ТЕХНИЧЕСКИЙ ШКАФ'}
  ];

  const searchables=[
    {id:'security-terminal',x:205,y:166,label:'ТЕРМИНАЛ',group:'a'},
    {id:'lab-console',x:500,y:299,label:'КОНСОЛЬ ЛАБОРАТОРИИ',group:'a'},
    {id:'lab-cabinet',x:710,y:118,label:'ШКАФ С ОБРАЗЦАМИ',group:'a'},
    {id:'archive-shelf',x:930,y:126,label:'АРХИВНЫЙ СТЕЛЛАЖ',group:'b'},
    {id:'archive-box',x:1070,y:278,label:'КОРОБ С ДОКУМЕНТАМИ',group:'b'},
    {id:'med-cabinet',x:288,y:649,label:'МЕДИЦИНСКИЙ ШКАФ',group:'c'},
    {id:'med-cart',x:314,y:786,label:'ТЕЛЕЖКА',group:'c'},
    {id:'generator-toolbox',x:864,y:768,label:'ЯЩИК С ИНСТРУМЕНТАМИ',group:'c'}
  ];

  const generatorTarget={id:'generator',x:992,y:765,label:'ЗАПУСТИТЬ ГЕНЕРАТОР'};
  const elevatorTarget={id:'elevator',x:600,y:804,label:'ВЫЗВАТЬ ЛИФТ'};
  const patrolPoints=[
    {x:205,y:190},{x:710,y:190},{x:1120,y:130},
    {x:205,y:720},{x:600,y:690},{x:1120,y:650}
  ];

  const state={
    running:false,finished:false,demo:false,sessionId:null,seed:1,time:150,last:0,
    battery:100,flashlight:true,lives:3,score:0,cards:0,generator:false,escaped:false,
    bottles:2,searches:0,hits:0,noise:0,threat:7,interaction:null,hidden:false,hideTarget:null,
    searched:new Set(),cardIds:new Set(),visited:new Set(),particles:[],messageUntil:0,
    flashAlpha:0,shake:0,distance:0,lastStepAt:0,lastHeartbeat:0,lastRoom:'security',
    audio:null,invulnerableUntil:0,hideCheckAt:0
  };
  const player={x:205,y:190,r:13,facingX:1,facingY:0,walk:0};
  const monster={
    x:1120,y:650,r:15,mode:'patrol',targetX:1120,targetY:650,path:[],pathIndex:0,
    repathAt:0,stunnedUntil:0,chaseLostAt:0,lastSeenX:0,lastSeenY:0,lastStepAt:0,
    patrolIndex:5
  };
  const camera={x:0,y:0};
  const joystickState={pointerId:null,x:0,y:0,magnitude:0};
  const keys=new Set();
  let raf=0,resizeObserver=null,viewW=1,viewH=1,dpr=1;

  function rand(){state.seed=(state.seed*1664525+1013904223)>>>0;return state.seed/4294967296}
  function clamp(value,min,max){return Math.max(min,Math.min(max,value))}
  function distance(ax,ay,bx,by){return Math.hypot(bx-ax,by-ay)}
  function vibrate(type='light'){try{tg?.HapticFeedback?.impactOccurred?.(type)}catch(_){}}
  async function api(path,body={}){const res=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});const data=await res.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));if(!res.ok||!data.ok)throw new Error(data.reason||'Ошибка игрового сервера.');return data}
  function goGames(){location.href='/games/?'+new URLSearchParams({...Object.fromEntries(params),chat_id:chatId}).toString()}
  function setMessage(text,seconds=2.6){caption.textContent=text;state.messageUntil=performance.now()+seconds*1000}
  function formatTime(value){value=Math.max(0,Math.ceil(value));return String(Math.floor(value/60)).padStart(2,'0')+':'+String(value%60).padStart(2,'0')}
  function pointInRect(x,y,rect,pad=0){return x>=rect.x-pad&&x<=rect.x+rect.w+pad&&y>=rect.y-pad&&y<=rect.y+rect.h+pad}
  function pointInWalkZone(x,y){return walkZones.some(zone=>pointInRect(x,y,zone))}
  function pointInSolid(x,y,pad=0){return solids.some(item=>pointInRect(x,y,item,pad))}
  function canOccupy(x,y,r=12){
    const samples=[[0,0],[r,0],[-r,0],[0,r],[0,-r],[r*.72,r*.72],[-r*.72,r*.72],[r*.72,-r*.72],[-r*.72,-r*.72]];
    return samples.every(([dx,dy])=>pointInWalkZone(x+dx,y+dy)&&!pointInSolid(x+dx,y+dy,1));
  }
  function roomAt(x,y){return rooms.find(room=>pointInRect(x,y,room))||null}
  function lineOfSight(ax,ay,bx,by){
    const steps=Math.ceil(distance(ax,ay,bx,by)/18);
    for(let i=1;i<steps;i++){const t=i/steps,x=ax+(bx-ax)*t,y=ay+(by-ay)*t;if(!pointInWalkZone(x,y)||pointInSolid(x,y,2))return false}
    return true;
  }

  const GRID=40,COLS=Math.ceil(WORLD.w/GRID),ROWS=Math.ceil(WORLD.h/GRID);
  let navWalkable=[];
  function navIndex(cx,cy){return cy*COLS+cx}
  function rebuildNavigation(){
    navWalkable=new Array(COLS*ROWS).fill(false);
    for(let cy=0;cy<ROWS;cy++)for(let cx=0;cx<COLS;cx++){
      const x=cx*GRID+GRID/2,y=cy*GRID+GRID/2;
      navWalkable[navIndex(cx,cy)]=canOccupy(x,y,11);
    }
  }
  function nearestNavCell(x,y){
    const baseX=clamp(Math.floor(x/GRID),0,COLS-1),baseY=clamp(Math.floor(y/GRID),0,ROWS-1);
    for(let radius=0;radius<7;radius++)for(let dy=-radius;dy<=radius;dy++)for(let dx=-radius;dx<=radius;dx++){
      if(Math.abs(dx)!==radius&&Math.abs(dy)!==radius)continue;
      const cx=baseX+dx,cy=baseY+dy;if(cx<0||cy<0||cx>=COLS||cy>=ROWS)continue;
      if(navWalkable[navIndex(cx,cy)])return {cx,cy,index:navIndex(cx,cy)};
    }
    return null;
  }
  function buildPath(sx,sy,tx,ty){
    const start=nearestNavCell(sx,sy),goal=nearestNavCell(tx,ty);if(!start||!goal)return [];
    if(start.index===goal.index)return [{x:tx,y:ty}];
    const previous=new Int32Array(COLS*ROWS);previous.fill(-2);previous[start.index]=-1;
    const queue=new Int32Array(COLS*ROWS);let head=0,tail=0;queue[tail++]=start.index;
    const directions=[[1,0],[-1,0],[0,1],[0,-1]];
    while(head<tail){
      const current=queue[head++];if(current===goal.index)break;
      const cx=current%COLS,cy=Math.floor(current/COLS);
      for(const [dx,dy] of directions){const nx=cx+dx,ny=cy+dy;if(nx<0||ny<0||nx>=COLS||ny>=ROWS)continue;const ni=navIndex(nx,ny);if(!navWalkable[ni]||previous[ni]!==-2)continue;previous[ni]=current;queue[tail++]=ni}
    }
    if(previous[goal.index]===-2)return [];
    const reversed=[];let current=goal.index;
    while(current!==-1){const cx=current%COLS,cy=Math.floor(current/COLS);reversed.push({x:cx*GRID+GRID/2,y:cy*GRID+GRID/2});current=previous[current]}
    reversed.reverse();reversed.shift();reversed.push({x:tx,y:ty});return reversed;
  }

  function initAudio(){
    if(state.audio)return;
    try{
      const ac=new (window.AudioContext||window.webkitAudioContext)(),master=ac.createGain();master.gain.value=.1;master.connect(ac.destination);
      const ambient=ac.createOscillator(),ambientGain=ac.createGain();ambient.type='sawtooth';ambient.frequency.value=39;ambientGain.gain.value=.035;ambient.connect(ambientGain).connect(master);ambient.start();
      state.audio={ac,master,ambient,ambientGain};
    }catch(_){state.audio=null}
  }
  function tone(freq=120,duration=.12,type='sine',volume=.18,pan=0){
    const audio=state.audio;if(!audio)return;
    const oscillator=audio.ac.createOscillator(),gain=audio.ac.createGain();oscillator.type=type;oscillator.frequency.setValueAtTime(freq,audio.ac.currentTime);gain.gain.setValueAtTime(Math.max(.001,volume),audio.ac.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audio.ac.currentTime+duration);
    let node=gain;if(audio.ac.createStereoPanner){const panner=audio.ac.createStereoPanner();panner.pan.value=clamp(pan,-1,1);gain.connect(panner);node=panner}
    oscillator.connect(gain);node.connect(audio.master);oscillator.start();oscillator.stop(audio.ac.currentTime+duration);
  }
  function heartbeat(){tone(61,.1,'sine',.36);setTimeout(()=>tone(49,.14,'sine',.28),125)}
  function monsterFootstep(){const pan=clamp((monster.x-player.x)/260,-1,1);tone(monster.mode==='chase'?47:55,.16,'sine',monster.mode==='chase'?.42:.27,pan);setTimeout(()=>tone(38,.13,'sine',.2,pan),85)}
  function playerFootstep(intensity){tone(intensity>.75?84:68,.045,'triangle',.045+intensity*.035,0)}

  function chooseCardLocations(){
    state.cardIds.clear();
    for(const group of ['a','b','c']){const options=searchables.filter(item=>item.group===group);state.cardIds.add(options[Math.floor(rand()*options.length)].id)}
  }
  function emitNoise(x,y,radius,kind='step'){
    state.noise=Math.max(state.noise,clamp(radius/5,0,100));
    const heard=distance(monster.x,monster.y,x,y)<=radius;
    if(heard||kind==='generator'){
      if(monster.mode!=='chase'){monster.mode='investigate';monster.targetX=x;monster.targetY=y;monster.path=[];monster.repathAt=0}
      if(kind!=='step')setMessage(kind==='bottle'?'Звук разбитого стекла разнёсся по этажу.':'Охотник услышал шум.',1.8);
    }
  }

  function inputVector(){
    let x=joystickState.x,y=joystickState.y;
    if(keys.has('arrowleft')||keys.has('a'))x-=1;if(keys.has('arrowright')||keys.has('d'))x+=1;if(keys.has('arrowup')||keys.has('w'))y-=1;if(keys.has('arrowdown')||keys.has('s'))y+=1;
    const magnitude=Math.hypot(x,y);if(magnitude>1){x/=magnitude;y/=magnitude}
    return {x,y,magnitude:Math.min(1,magnitude)};
  }
  function movePlayer(dt,now){
    const input=inputVector();
    if(state.hidden||state.interaction){player.walk=0;if(state.interaction&&input.magnitude>.18)cancelInteraction('Действие прервано.');return}
    if(input.magnitude<.08){player.walk=0;return}
    player.facingX=input.x/input.magnitude;player.facingY=input.y/input.magnitude;player.walk=input.magnitude;
    const speed=52+input.magnitude*108,dx=player.facingX*speed*dt,dy=player.facingY*speed*dt;
    const beforeX=player.x,beforeY=player.y;
    if(canOccupy(player.x+dx,player.y,player.r))player.x+=dx;
    if(canOccupy(player.x,player.y+dy,player.r))player.y+=dy;
    const travelled=distance(beforeX,beforeY,player.x,player.y);state.distance+=travelled;state.score+=travelled*.006;
    const stepDelay=clamp(560-input.magnitude*300,230,520);
    if(now-state.lastStepAt>stepDelay&&travelled>.3){
      state.lastStepAt=now;playerFootstep(input.magnitude);
      const radius=70+input.magnitude*175;emitNoise(player.x,player.y,radius,'step');
    }
  }

  function nearestContext(){
    if(state.hidden)return {kind:'exitHide',label:'ВЫЙТИ ИЗ УКРЫТИЯ',duration:.2,target:state.hideTarget};
    let best=null,bestDistance=Infinity;
    const consider=(context,x,y,range=62)=>{const d=distance(player.x,player.y,x,y);if(d<range&&d<bestDistance){best=context;bestDistance=d}};
    for(const cover of covers)consider({kind:'hide',label:'СПРЯТАТЬСЯ',duration:.45,target:cover},cover.x,cover.y,54);
    for(const item of searchables)if(!state.searched.has(item.id))consider({kind:'search',label:'ОБЫСКАТЬ '+item.label,duration:1.45,target:item},item.x,item.y,62);
    consider({kind:'generator',label:state.cards>=3?'ЗАПУСТИТЬ ГЕНЕРАТОР':'НУЖНО 3 КЛЮЧ-КАРТЫ',duration:2.15,target:generatorTarget},generatorTarget.x,generatorTarget.y,72);
    consider({kind:'elevator',label:state.generator?'ВЫЗВАТЬ ЛИФТ':'ЛИФТ БЕЗ ПИТАНИЯ',duration:1.7,target:elevatorTarget},elevatorTarget.x,elevatorTarget.y,70);
    return best;
  }
  function beginInteraction(){
    if(!state.running||state.finished||state.interaction)return;
    const context=nearestContext();if(!context){setMessage('Рядом нет объекта для взаимодействия.',1.5);return}
    if(context.kind==='generator'&&state.cards<3){setMessage(`Не хватает ключ-карт: ${state.cards}/3.`,2);return}
    if(context.kind==='elevator'&&!state.generator){setMessage('Сначала восстанови питание в генераторной.',2);return}
    if(context.kind==='exitHide'){exitHide();return}
    state.interaction={...context,started:performance.now(),progress:0};
    progressText.textContent=context.label;progressBar.style.width='0%';progressBox.classList.remove('hidden');
    emitNoise(player.x,player.y,context.kind==='search'?235:context.kind==='generator'?520:95,context.kind==='generator'?'generator':'action');
    tone(context.kind==='generator'?92:205,.12,'square',.13);vibrate('light');
  }
  function cancelInteraction(message='Действие отменено.'){
    if(!state.interaction)return;state.interaction=null;progressBox.classList.add('hidden');progressBar.style.width='0%';setMessage(message,1.4)
  }
  function completeInteraction(){
    const interaction=state.interaction;if(!interaction)return;state.interaction=null;progressBox.classList.add('hidden');progressBar.style.width='0%';
    if(interaction.kind==='hide'){enterHide(interaction.target);return}
    if(interaction.kind==='search'){completeSearch(interaction.target);return}
    if(interaction.kind==='generator'){activateGenerator();return}
    if(interaction.kind==='elevator'){escape();return}
  }
  function updateInteraction(now){
    if(!state.interaction)return;
    const elapsed=(now-state.interaction.started)/1000;state.interaction.progress=clamp(elapsed/state.interaction.duration,0,1);progressBar.style.width=Math.round(state.interaction.progress*100)+'%';
    if(state.interaction.progress>=1)completeInteraction();
  }
  function completeSearch(item){
    state.searched.add(item.id);state.searches++;state.score+=5;tone(300,.08,'square',.11);
    if(state.cardIds.has(item.id)){
      state.cards++;state.score+=38;spawnParticles(item.x,item.y,28,'#ffc96b');tone(690,.28,'sine',.25);vibrate('medium');setMessage(`Ключ-карта найдена. Осталось: ${3-state.cards}.`,3);
    }else{
      const roll=rand();
      if(roll<.4){state.battery=Math.min(100,state.battery+24);spawnParticles(item.x,item.y,18,'#7fffe9');setMessage('Найдена батарея. Заряд +24%.',2.5)}
      else if(roll<.64){state.bottles=Math.min(4,state.bottles+1);setMessage('Найдена стеклянная колба. Можно отвлечь охотника.',2.5)}
      else{state.score+=12;setMessage('Найдена запись эксперимента. +12 очков.',2.5)}
    }
  }
  function enterHide(cover){
    state.hidden=true;state.hideTarget=cover;state.flashlight=false;state.noise=Math.max(0,state.noise-22);state.hideCheckAt=performance.now()+1200;player.x=cover.x;player.y=cover.y;tone(74,.12,'sine',.12);setMessage('Ты спрятался. Не включай свет и не двигайся.',3);vibrate('light')
  }
  function exitHide(){state.hidden=false;const cover=state.hideTarget;state.hideTarget=null;player.x+=(cover?.x<600?34:-34);if(!canOccupy(player.x,player.y,player.r))player.x=clamp(player.x,140,1060);emitNoise(player.x,player.y,180,'action');setMessage('Ты осторожно вышел из укрытия.',1.8)}
  function activateGenerator(){
    if(state.generator)return;state.generator=true;state.score+=48;state.threat=75;spawnParticles(generatorTarget.x,generatorTarget.y,42,'#70ffc0');tone(88,.8,'sawtooth',.23);warning.textContent='ПИТАНИЕ ВОССТАНОВЛЕНО';warning.classList.add('show');setTimeout(()=>warning.classList.remove('show'),1600);setMessage('Генератор ожил. Охотник идёт на шум. Доберись до лифта!',3.8);emitNoise(generatorTarget.x,generatorTarget.y,1200,'generator');monster.mode='chase';monster.chaseLostAt=performance.now()+7000;monster.lastSeenX=player.x;monster.lastSeenY=player.y;monster.repathAt=0
  }
  function escape(){
    if(state.escaped)return;state.escaped=true;state.score+=75+Math.round(state.time*.4)+state.lives*12;warning.textContent='ЛИФТ ЗАКРЫВАЕТСЯ';warning.classList.add('show');tone(120,.8,'sawtooth',.22);setTimeout(()=>finish(true,'Лифт закрылся, когда охотник уже вошёл в холл.'),1200)
  }

  function throwBottle(){
    if(!state.running||state.finished||state.hidden||state.bottles<=0)return;
    state.bottles--;
    let tx=player.x+player.facingX*190,ty=player.y+player.facingY*190;
    for(let step=0;step<10&&!pointInWalkZone(tx,ty);step++){tx=player.x+player.facingX*(180-step*16);ty=player.y+player.facingY*(180-step*16)}
    state.bottle={x:tx,y:ty,until:performance.now()+1300};spawnParticles(tx,ty,24,'#9fffe9');tone(520,.08,'square',.2,clamp((tx-player.x)/180,-1,1));setTimeout(()=>tone(185,.22,'square',.25,clamp((tx-player.x)/180,-1,1)),80);emitNoise(tx,ty,560,'bottle');vibrate('medium')
  }
  function toggleFlashlight(){
    if(!state.running||state.finished||state.hidden||state.battery<=0)return;state.flashlight=!state.flashlight;tone(state.flashlight?770:245,.05,'square',.08);if(state.flashlight)emitNoise(player.x,player.y,70,'switch')
  }
  function burst(){
    if(!state.running||state.finished||state.hidden||state.battery<18)return;
    state.battery-=18;state.flashlight=true;state.flashAlpha=1;tone(1100,.09,'square',.25);vibrate('heavy');
    const dx=monster.x-player.x,dy=monster.y-player.y,dist=Math.hypot(dx,dy),dot=(dx*player.facingX+dy*player.facingY)/(dist||1);
    if(dist<265&&dot>.56&&lineOfSight(player.x,player.y,monster.x,monster.y)){
      monster.stunnedUntil=performance.now()+3600;monster.mode='investigate';monster.targetX=monster.x;monster.targetY=monster.y;monster.path=[];state.threat=Math.max(22,state.threat-42);state.score+=18;spawnParticles(monster.x,monster.y,36,'#d8fff8');setMessage('Вспышка попала в охотника. Беги!',2.7)
    }else setMessage('Свет ударил в пустоту. Охотник не был перед тобой.',2);
  }

  function planMonsterPath(targetX,targetY){monster.path=buildPath(monster.x,monster.y,targetX,targetY);monster.pathIndex=0;monster.repathAt=performance.now()+420}
  function choosePatrol(){monster.patrolIndex=(monster.patrolIndex+1+Math.floor(rand()*3))%patrolPoints.length;const target=patrolPoints[monster.patrolIndex];monster.targetX=target.x;monster.targetY=target.y;planMonsterPath(target.x,target.y)}
  function triggerChase(text='Он увидел тебя.'){
    if(state.hidden)return;monster.mode='chase';monster.chaseLostAt=performance.now()+2700;monster.lastSeenX=player.x;monster.lastSeenY=player.y;monster.repathAt=0;state.threat=100;state.shake=7;warning.textContent='ОН ВИДИТ ТЕБЯ';warning.classList.add('show');setTimeout(()=>warning.classList.remove('show'),1000);setMessage(text+' Беги или развернись и используй вспышку!',3);heartbeat();vibrate('heavy')
  }
  function hitPlayer(){
    const now=performance.now();if(now<state.invulnerableUntil||state.hidden)return;
    if(state.interaction){state.interaction=null;progressBox.classList.add('hidden');progressBar.style.width='0%'}
    state.hits++;state.lives--;state.score=Math.max(0,state.score-28);state.shake=18;state.flashAlpha=.55;spawnParticles(player.x,player.y,44,'#ff3658');tone(36,.72,'sawtooth',.4);vibrate('heavy');
    if(state.lives<=0){finish(false,'Охотник настиг тебя в коридоре.');return}
    player.x=205;player.y=190;monster.x=1120;monster.y=650;monster.mode='patrol';monster.path=[];monster.repathAt=0;state.invulnerableUntil=now+2600;state.hidden=false;state.hideTarget=null;state.threat=38;setMessage(`Ты очнулся на посту охраны. Осталось жизней: ${state.lives}.`,3)
  }
  function updateMonster(now,dt){
    if(now<monster.stunnedUntil){state.threat=Math.max(8,state.threat-dt*20);return}
    const dist=distance(monster.x,monster.y,player.x,player.y);
    const detectionRange=(state.flashlight?285:190)+(state.generator?28:0);
    const sees=!state.hidden&&dist<detectionRange&&lineOfSight(monster.x,monster.y,player.x,player.y);
    if(sees){if(monster.mode!=='chase')triggerChase('Существо заметило свет.');monster.chaseLostAt=now+2700;monster.lastSeenX=player.x;monster.lastSeenY=player.y}
    if(monster.mode==='chase'){
      if(sees){monster.targetX=player.x;monster.targetY=player.y}else{monster.targetX=monster.lastSeenX;monster.targetY=monster.lastSeenY}
      if(now>monster.repathAt)planMonsterPath(monster.targetX,monster.targetY);
      if(!sees&&now>monster.chaseLostAt){monster.mode='investigate';monster.targetX=monster.lastSeenX;monster.targetY=monster.lastSeenY;planMonsterPath(monster.targetX,monster.targetY);setMessage('Охотник потерял тебя, но продолжает искать.',2)}
    }else if(monster.mode==='investigate'){
      if(now>monster.repathAt&&monster.pathIndex>=monster.path.length)planMonsterPath(monster.targetX,monster.targetY);
      if(distance(monster.x,monster.y,monster.targetX,monster.targetY)<34){monster.mode='patrol';choosePatrol()}
    }else if(monster.path.length===0||monster.pathIndex>=monster.path.length){choosePatrol()}

    if(state.hidden&&dist<62&&now>state.hideCheckAt){
      state.hideCheckAt=now+2500;const chance=(state.generator?.56:.31)+(state.noise>55?.18:0);
      if(rand()<chance){state.hidden=false;state.hideTarget=null;triggerChase('Дверца укрытия медленно открылась.')}else{setMessage('Охотник остановился рядом с укрытием… и прошёл мимо.',3);monster.mode='patrol';choosePatrol()}
    }

    let target=monster.path[monster.pathIndex];
    if(target){
      const dx=target.x-monster.x,dy=target.y-monster.y,len=Math.hypot(dx,dy);
      if(len<8){monster.pathIndex++;target=monster.path[monster.pathIndex]}
      if(target){const vx=(target.x-monster.x),vy=(target.y-monster.y),length=Math.hypot(vx,vy)||1;const speed=monster.mode==='chase'?(state.generator?128:108):monster.mode==='investigate'?82:59;monster.x+=vx/length*speed*dt;monster.y+=vy/length*speed*dt}
    }

    const updatedDist=distance(monster.x,monster.y,player.x,player.y);
    const proximity=clamp(100-updatedDist*.2,5,92);state.threat+=((monster.mode==='chase'?100:proximity)-state.threat)*Math.min(1,dt*3.2);state.noise=Math.max(0,state.noise-dt*7);
    const stepDelay=monster.mode==='chase'?280:monster.mode==='investigate'?470:690;if(now-monster.lastStepAt>stepDelay){monster.lastStepAt=now;monsterFootstep()}
    if(state.threat>58&&now-state.lastHeartbeat>Math.max(480,1450-state.threat*9)){state.lastHeartbeat=now;heartbeat()}
    if(updatedDist<28&&!state.hidden)hitPlayer();
  }

  function updateRoom(){
    const room=roomAt(player.x,player.y),id=room?.id||'corridor';roomName.textContent=room?.name||'СЛУЖЕБНЫЙ КОРИДОР';
    if(id!==state.lastRoom){state.lastRoom=id;if(room&&!state.visited.has(id)){state.visited.add(id);state.score+=7;setMessage(`Ты вошёл: ${room.name}.`,1.8)}}
  }
  function threatLabel(){if(monster.mode==='chase')return 'ПОГОНЯ';if(state.threat>78)return 'РЯДОМ';if(state.threat>52)return 'ИЩЕТ';if(state.threat>27)return 'СЛЫШИТ';return 'ТИХО'}
  function updateHud(){
    scoreEl.textContent=Math.max(0,Math.round(state.score));timerEl.textContent=formatTime(state.time);
    objectiveEl.textContent=state.generator?'ДОБЕРИСЬ ДО ЛИФТА':state.cards>=3?'ЗАПУСТИ ГЕНЕРАТОР':`КЛЮЧ-КАРТЫ ${state.cards}/3`;
    livesEl.textContent='♥'.repeat(state.lives)+'♡'.repeat(Math.max(0,3-state.lives));batteryEl.textContent=Math.round(state.battery)+'%';batteryBar.style.width=Math.max(0,state.battery)+'%';threatEl.textContent=threatLabel();threatBar.style.width=Math.min(100,state.threat)+'%';$('bottles').textContent=state.bottles;
    $('flashlight').classList.toggle('off',!state.flashlight);$('flashlight').disabled=state.hidden||state.battery<=0;$('distract').disabled=state.hidden||state.bottles<=0;$('burst').disabled=state.hidden||state.battery<18;
    const context=nearestContext();interactButton.disabled=!context;interactButton.classList.toggle('pulse',!!context);interactLabel.textContent=context?.label||'ДЕЙСТВИЕ';
    if(context){contextHint.textContent=context.label;contextHint.classList.remove('hidden')}else contextHint.classList.add('hidden');
  }

  function resize(){
    const rect=canvas.getBoundingClientRect();dpr=Math.min(2.25,window.devicePixelRatio||1);viewW=Math.max(2,rect.width);viewH=Math.max(2,rect.height);
    canvas.width=Math.round(viewW*dpr);canvas.height=Math.round(viewH*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
    lightCanvas.width=canvas.width;lightCanvas.height=canvas.height;lctx.setTransform(dpr,0,0,dpr,0,0);
    const miniRect=minimap.getBoundingClientRect();minimap.width=Math.max(2,Math.round(miniRect.width*dpr));minimap.height=Math.max(2,Math.round(miniRect.height*dpr));mctx.setTransform(dpr,0,0,dpr,0,0)
  }
  function roundedPath(context,x,y,w,h,r){context.beginPath();context.roundRect(x,y,w,h,r)}
  function drawFloorZone(zone,color){
    ctx.fillStyle=color;ctx.fillRect(zone.x,zone.y,zone.w,zone.h);ctx.strokeStyle='#385357';ctx.lineWidth=10;ctx.strokeRect(zone.x,zone.y,zone.w,zone.h);
    ctx.save();ctx.beginPath();ctx.rect(zone.x,zone.y,zone.w,zone.h);ctx.clip();ctx.strokeStyle='#90d8ce0b';ctx.lineWidth=1;for(let x=zone.x;x<zone.x+zone.w;x+=38){ctx.beginPath();ctx.moveTo(x,zone.y);ctx.lineTo(x,zone.y+zone.h);ctx.stroke()}for(let y=zone.y;y<zone.y+zone.h;y+=38){ctx.beginPath();ctx.moveTo(zone.x,y);ctx.lineTo(zone.x+zone.w,y);ctx.stroke()}ctx.restore()
  }
  function drawWorld(now){
    ctx.fillStyle='#010405';ctx.fillRect(0,0,WORLD.w,WORLD.h);
    for(const room of rooms){const gradient=ctx.createLinearGradient(room.x,room.y,room.x,room.y+room.h);gradient.addColorStop(0,room.color);gradient.addColorStop(1,'#081012');drawFloorZone(room,gradient);ctx.fillStyle='#b4d8d416';ctx.font='900 20px system-ui';ctx.textAlign='center';ctx.fillText(room.name,room.x+room.w/2,room.y+room.h-22)}
    for(const corridor of corridors){ctx.fillStyle='#101c20';ctx.fillRect(corridor.x,corridor.y,corridor.w,corridor.h);ctx.strokeStyle='#243d42';ctx.lineWidth=3;ctx.strokeRect(corridor.x,corridor.y,corridor.w,corridor.h)}
    drawDoorFrames();drawProps(now);drawSearchables(now);drawObjectives(now);
    if(state.bottle&&performance.now()<state.bottle.until){ctx.fillStyle='#aafff3';ctx.beginPath();ctx.arc(state.bottle.x,state.bottle.y,5,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#aafff355';ctx.beginPath();ctx.arc(state.bottle.x,state.bottle.y,18+Math.sin(now/80)*4,0,Math.PI*2);ctx.stroke()}
    drawParticles();drawMonster(now);drawPlayer(now)
  }
  function drawDoorFrames(){
    const frames=[
      [370,145,0,72],[435,145,0,72],[765,145,0,72],[830,145,0,72],
      [370,685,0,72],[435,685,0,72],[765,685,0,72],[830,685,0,72],
      [165,320,82,0],[165,580,82,0],[559,320,82,0],[559,580,82,0],[954,320,82,0],[954,580,82,0]
    ];
    ctx.strokeStyle='#668f91';ctx.lineWidth=5;for(const [x,y,w,h] of frames){ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+w,y+h);ctx.stroke();ctx.strokeStyle='#7fffe928';ctx.lineWidth=11;ctx.stroke();ctx.strokeStyle='#668f91';ctx.lineWidth=5}
  }
  function drawProps(now){
    for(const item of solids){
      ctx.save();
      if(item.type==='desk'){ctx.fillStyle='#0b171a';roundedPath(ctx,item.x,item.y,item.w,item.h,8);ctx.fill();ctx.strokeStyle='#284145';ctx.stroke();ctx.fillStyle='#4effe222';ctx.fillRect(item.x+38,item.y+10,78,26)}
      else if(item.type==='locker'||item.type==='cabinet'){ctx.fillStyle='#0a1417';roundedPath(ctx,item.x,item.y,item.w,item.h,5);ctx.fill();ctx.strokeStyle='#365156';ctx.lineWidth=3;ctx.stroke();ctx.fillStyle='#68898a';ctx.fillRect(item.x+item.w-10,item.y+item.h*.48,3,8)}
      else if(item.type==='console'){ctx.fillStyle='#0b1518';roundedPath(ctx,item.x,item.y,item.w,item.h,5);ctx.fill();ctx.fillStyle='#70ffe51f';ctx.fillRect(item.x+8,item.y+7,item.w-16,item.h-14)}
      else if(item.type==='capsule'){ctx.fillStyle='#071012';roundedPath(ctx,item.x,item.y,item.w,item.h,46);ctx.fill();ctx.strokeStyle='#63868c';ctx.lineWidth=5;ctx.stroke();ctx.strokeStyle='#ff435f88';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(item.x+18,item.y+20);ctx.lineTo(item.x+item.w-12,item.y+item.h-18);ctx.stroke()}
      else if(item.type==='shelf'){ctx.fillStyle='#10191b';ctx.fillRect(item.x,item.y,item.w,item.h);ctx.strokeStyle='#405355';ctx.strokeRect(item.x,item.y,item.w,item.h);for(let x=item.x+20;x<item.x+item.w;x+=28){ctx.fillStyle=['#3d3325','#26343a','#44332e'][Math.floor((x/28)%3)];ctx.fillRect(x,item.y+5,12,item.h-10)}}
      else if(item.type==='bed'){ctx.fillStyle='#182b2d';roundedPath(ctx,item.x,item.y,item.w,item.h,9);ctx.fill();ctx.fillStyle='#b9d4d21b';ctx.fillRect(item.x+10,item.y+8,item.w-20,item.h-16);ctx.strokeStyle='#557174';ctx.stroke()}
      else if(item.type==='generator'){ctx.fillStyle='#10191c';roundedPath(ctx,item.x,item.y,item.w,item.h,12);ctx.fill();ctx.strokeStyle='#5e7274';ctx.lineWidth=4;ctx.stroke();ctx.fillStyle=state.generator?'#66ffc6':'#ffbd62';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=state.generator?18:7;ctx.beginPath();ctx.arc(item.x+item.w*.5,item.y+item.h*.38,10,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle='#293d40';ctx.lineWidth=5;for(let x=item.x+22;x<item.x+item.w-15;x+=28){ctx.beginPath();ctx.moveTo(x,item.y+item.h*.62);ctx.lineTo(x,item.y+item.h-15);ctx.stroke()}}
      else if(item.type==='crate'){ctx.fillStyle='#342b20';ctx.fillRect(item.x,item.y,item.w,item.h);ctx.strokeStyle='#756246';ctx.strokeRect(item.x,item.y,item.w,item.h);ctx.beginPath();ctx.moveTo(item.x,item.y);ctx.lineTo(item.x+item.w,item.y+item.h);ctx.moveTo(item.x+item.w,item.y);ctx.lineTo(item.x,item.y+item.h);ctx.stroke()}
      else if(item.type==='elevatorConsole'){ctx.fillStyle='#0a1417';roundedPath(ctx,item.x,item.y,item.w,item.h,5);ctx.fill();ctx.fillStyle=state.generator?'#70ffc0':'#ff435f';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=12;ctx.beginPath();ctx.arc(item.x+item.w/2,item.y+17,5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0}
      ctx.restore();
    }
    ctx.fillStyle='#05090a';ctx.fillRect(505,818,190,28);ctx.strokeStyle=state.generator?'#70ffc0':'#51686a';ctx.lineWidth=4;ctx.strokeRect(505,818,190,28);ctx.fillStyle=state.generator?'#70ffc055':'#ff435f22';ctx.fillRect(518,824,164,15)
  }
  function drawSearchables(now){
    for(const item of searchables){
      if(state.searched.has(item.id))continue;const near=distance(player.x,player.y,item.x,item.y)<85,pulse=.55+.25*Math.sin(now/240);
      ctx.save();ctx.fillStyle=near?`rgba(127,255,233,${pulse})`:'#71918f';ctx.shadowColor='#7fffe9';ctx.shadowBlur=near?18:0;ctx.beginPath();ctx.arc(item.x,item.y,5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=near?'#7fffe977':'#526d6d55';ctx.beginPath();ctx.arc(item.x,item.y,near?15:10,0,Math.PI*2);ctx.stroke();ctx.restore()
    }
  }
  function drawObjectives(now){
    if(state.cards>=3&&!state.generator){ctx.strokeStyle=`rgba(112,255,192,${.5+.3*Math.sin(now/180)})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(generatorTarget.x,generatorTarget.y,24,0,Math.PI*2);ctx.stroke()}
    if(state.generator){ctx.strokeStyle=`rgba(112,255,192,${.55+.3*Math.sin(now/160)})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(elevatorTarget.x,elevatorTarget.y,26,0,Math.PI*2);ctx.stroke()}
  }
  function drawPlayer(now){
    if(state.hidden)return;ctx.save();ctx.translate(player.x,player.y);ctx.rotate(Math.atan2(player.facingY,player.facingX));const bob=Math.sin(now/95)*player.walk*2;ctx.translate(0,bob);ctx.fillStyle='#071014';ctx.strokeStyle='#8ad9cf';ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,12,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.fillStyle='#a9fff2';ctx.beginPath();ctx.arc(5,-3,4,0,Math.PI*2);ctx.fill();ctx.fillStyle='#31595a';ctx.fillRect(-10,-8,7,16);ctx.fillStyle='#d9fff8';ctx.fillRect(9,-2,12,4);ctx.restore()
  }
  function drawMonster(now){
    ctx.save();ctx.translate(monster.x,monster.y);const targetAngle=Math.atan2(player.y-monster.y,player.x-monster.x);ctx.rotate(targetAngle);const stride=Math.sin(now/(monster.mode==='chase'?70:125));ctx.shadowColor='#000';ctx.shadowBlur=25;ctx.fillStyle='#010203';ctx.beginPath();ctx.ellipse(0,0,18,29,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(11,0,13,0,Math.PI*2);ctx.fill();ctx.lineWidth=8;ctx.strokeStyle='#010203';ctx.beginPath();ctx.moveTo(-4,-16);ctx.lineTo(-23,-28-stride*5);ctx.moveTo(-4,16);ctx.lineTo(-23,28+stride*5);ctx.stroke();ctx.shadowColor='#ff2148';ctx.shadowBlur=16;ctx.fillStyle='#ff2148';ctx.beginPath();ctx.ellipse(14,-5,3,1.5,0,0,Math.PI*2);ctx.ellipse(14,5,3,1.5,0,0,Math.PI*2);ctx.fill();ctx.restore()
  }
  function spawnParticles(x,y,count,color='#9ffff0'){for(let i=0;i<count;i++)state.particles.push({x:x+(rand()-.5)*30,y:y+(rand()-.5)*30,vx:(rand()-.5)*85,vy:(rand()-.5)*85,life:.5+rand(),color})}
  function drawParticles(){const dt=.016;state.particles=state.particles.filter(p=>{p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vx*=.98;p.vy*=.98;if(p.life<=0)return false;ctx.globalAlpha=Math.min(1,p.life*2);ctx.fillStyle=p.color;ctx.fillRect(p.x,p.y,3,3);return true});ctx.globalAlpha=1}
  function drawLighting(){
    lctx.clearRect(0,0,viewW,viewH);lctx.globalCompositeOperation='source-over';lctx.fillStyle=state.hidden?'rgba(0,0,0,.94)':state.flashlight?'rgba(0,0,0,.79)':'rgba(0,0,0,.93)';lctx.fillRect(0,0,viewW,viewH);
    const px=player.x-camera.x,py=player.y-camera.y;lctx.globalCompositeOperation='destination-out';
    let radial=lctx.createRadialGradient(px,py,6,px,py,state.hidden?28:state.flashlight?68:42);radial.addColorStop(0,'rgba(0,0,0,.92)');radial.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=radial;lctx.beginPath();lctx.arc(px,py,state.hidden?30:state.flashlight?72:45,0,Math.PI*2);lctx.fill();
    if(state.flashlight&&!state.hidden&&state.battery>0){
      const angle=Math.atan2(player.facingY,player.facingX);lctx.save();lctx.translate(px,py);lctx.rotate(angle);lctx.filter='blur(10px)';const beam=lctx.createLinearGradient(0,0,350,0);beam.addColorStop(0,'rgba(0,0,0,.88)');beam.addColorStop(.72,'rgba(0,0,0,.43)');beam.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=beam;lctx.beginPath();lctx.moveTo(0,-12);lctx.lineTo(360,-135);lctx.lineTo(360,135);lctx.lineTo(0,12);lctx.closePath();lctx.fill();lctx.restore()
    }
    lctx.globalCompositeOperation='source-over';ctx.drawImage(lightCanvas,0,0,viewW,viewH);
    if(state.hidden){ctx.fillStyle='#a9c0be';ctx.font='900 10px system-ui';ctx.textAlign='center';ctx.fillText('ТЫ В УКРЫТИИ · СЛУШАЙ ШАГИ',viewW/2,viewH*.58)}
    if(state.flashAlpha>0){ctx.fillStyle=`rgba(255,255,255,${state.flashAlpha})`;ctx.fillRect(0,0,viewW,viewH)}
  }
  function drawMinimap(){
    const width=minimap.clientWidth,height=minimap.clientHeight,sx=width/WORLD.w,sy=height/WORLD.h;mctx.clearRect(0,0,width,height);mctx.fillStyle='#03090b';mctx.fillRect(0,0,width,height);
    for(const corridor of corridors){mctx.fillStyle='#1d3034';mctx.fillRect(corridor.x*sx,corridor.y*sy,corridor.w*sx,corridor.h*sy)}
    for(const room of rooms){mctx.fillStyle=state.visited.has(room.id)?'#315b59':'#17282c';mctx.fillRect(room.x*sx,room.y*sy,room.w*sx,room.h*sy);mctx.strokeStyle='#4c7473';mctx.strokeRect(room.x*sx,room.y*sy,room.w*sx,room.h*sy)}
    mctx.fillStyle=state.generator?'#70ffc0':'#ffc96b';mctx.beginPath();mctx.arc((state.generator?elevatorTarget.x:generatorTarget.x)*sx,(state.generator?elevatorTarget.y:generatorTarget.y)*sy,2.8,0,Math.PI*2);mctx.fill();mctx.fillStyle='#9ffff0';mctx.beginPath();mctx.arc(player.x*sx,player.y*sy,3,0,Math.PI*2);mctx.fill();
    if(state.threat>82){mctx.fillStyle='#ff435f88';mctx.beginPath();mctx.arc(monster.x*sx,monster.y*sy,2.5,0,Math.PI*2);mctx.fill()}
  }
  function render(now){
    const maxX=Math.max(0,WORLD.w-viewW),maxY=Math.max(0,WORLD.h-viewH),targetX=clamp(player.x-viewW/2,0,maxX),targetY=clamp(player.y-viewH/2,0,maxY);camera.x+=(targetX-camera.x)*.12;camera.y+=(targetY-camera.y)*.12;
    const shakeX=state.shake>0?(rand()-.5)*state.shake:0,shakeY=state.shake>0?(rand()-.5)*state.shake:0;state.shake*=.87;state.flashAlpha=Math.max(0,state.flashAlpha-.08);
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle='#010405';ctx.fillRect(0,0,viewW,viewH);ctx.save();ctx.translate(-camera.x+shakeX,-camera.y+shakeY);drawWorld(now);ctx.restore();drawLighting();drawMinimap()
  }

  function tick(now){
    if(!state.running||state.finished)return;const dt=Math.min(.045,(now-state.last)/1000||0);state.last=now;state.time-=dt;
    movePlayer(dt,now);updateInteraction(now);updateMonster(now,dt);updateRoom();
    if(state.flashlight&&!state.hidden&&state.battery>0){state.battery=Math.max(0,state.battery-dt*(monster.mode==='chase'?.9:.34));if(state.battery<=0){state.flashlight=false;setMessage('Фонарик разрядился. Ищи батарею.',2.4)}}
    if(state.time<=0){finish(false,'Аварийная блокировка запечатала комплекс.');return}
    if(now>state.messageUntil&&monster.mode!=='chase')caption.textContent=state.generator?'Питание восстановлено. Лифтовой холл отмечен на карте.':state.cards>=3?'Все карты собраны. Иди в генераторную.':`Свободно исследуй комнаты. Найдено карт: ${state.cards}/3.`;
    updateHud();render(now);raf=requestAnimationFrame(tick)
  }

  function resetGameState(){
    player.x=205;player.y=190;player.facingX=1;player.facingY=0;player.walk=0;monster.x=1120;monster.y=650;monster.mode='patrol';monster.path=[];monster.pathIndex=0;monster.repathAt=0;monster.stunnedUntil=0;monster.patrolIndex=5;
    state.battery=100;state.flashlight=true;state.lives=3;state.score=0;state.cards=0;state.generator=false;state.escaped=false;state.bottles=2;state.searches=0;state.hits=0;state.noise=0;state.threat=7;state.interaction=null;state.hidden=false;state.hideTarget=null;state.searched.clear();state.visited.clear();state.visited.add('security');state.particles=[];state.flashAlpha=0;state.shake=0;state.distance=0;state.lastStepAt=0;state.lastHeartbeat=0;state.lastRoom='security';state.invulnerableUntil=0;chooseCardLocations();choosePatrol()
  }
  async function startGame(demo=false){
    if(state.running)return;state.demo=demo;initAudio();try{state.audio?.ac?.resume?.()}catch(_){}
    $('intro').classList.add('hidden');resetGameState();state.running=true;state.finished=false;state.last=performance.now();resize();setMessage('Система: объект покинул камеру содержания. Управляй героем джойстиком.',4);updateHud();raf=requestAnimationFrame(tick)
  }
  async function prepare(){
    try{const data=await api('start',{game:'night-hunter'});state.sessionId=data.session_id;state.seed=Number(data.seed)||Date.now();state.time=Number(data.duration)||150;$('start').textContent='ВОЙТИ В КОМПЛЕКС';$('start').classList.remove('loading');$('start').addEventListener('click',()=>startGame(false),{once:true})}
    catch(error){state.seed=Date.now()>>>0;$('start').classList.add('hidden');$('demo').classList.remove('hidden');$('startError').style.display='block';$('startError').textContent=error.message+' Доступен демонстрационный режим без начисления влияния.';$('demo').addEventListener('click',()=>startGame(true),{once:true})}
  }
  async function finish(success,reason){
    if(state.finished)return;state.finished=true;state.running=false;cancelAnimationFrame(raf);warning.classList.remove('show');
    const raw=Math.max(0,Math.min(300,Math.round(state.score+state.cards*11+(state.generator?24:0)+(success?40:0)-state.hits*8)));
    $('resultIcon').textContent=success?'⬆':'◉';$('resultEyebrow').textContent=success?'ЛИФТ ЗАПУЩЕН':'СВЯЗЬ ПОТЕРЯНА';$('resultTitle').textContent=success?'Ты выбрался':'Охота окончена';$('resultText').textContent=reason;$('resultScore').textContent=raw;$('resultCards').textContent=state.cards+'/3';$('resultSearches').textContent=state.searches;$('resultHits').textContent=state.hits;$('finish').classList.remove('hidden');
    if(state.demo||!state.sessionId){$('reward').textContent='Демо-режим: результат не начисляется в баланс влияния.';return}
    try{const data=await api('finish',{session_id:state.sessionId,score:raw,stats:{escaped:success,cards:state.cards,generator:state.generator,searches:state.searches,hits:state.hits,battery:Math.round(state.battery),time_left:Math.round(state.time),distance:Math.round(state.distance)}});$('reward').innerHTML=data.actual_reward>0?`Начислено <b>+${data.actual_reward}</b> влияния. Баланс: <b>${data.balance}</b>.`:(data.message||'Результат сохранён, но лучшая награда дня не улучшилась.')}
    catch(error){$('reward').textContent='Результат получен, но сервер не сохранил его: '+error.message}
  }

  function updateJoystick(event){
    const rect=joystick.getBoundingClientRect(),cx=rect.left+rect.width/2,cy=rect.top+rect.height/2,dx=event.clientX-cx,dy=event.clientY-cy,max=rect.width*.31,len=Math.hypot(dx,dy)||1,scale=Math.min(1,max/len);const nx=dx*scale,ny=dy*scale;
    joystickState.x=nx/max;joystickState.y=ny/max;joystickState.magnitude=Math.min(1,Math.hypot(joystickState.x,joystickState.y));joystickKnob.style.transform=`translate(calc(-50% + ${nx}px),calc(-50% + ${ny}px))`
  }
  function resetJoystick(){joystickState.pointerId=null;joystickState.x=0;joystickState.y=0;joystickState.magnitude=0;joystickKnob.style.transform='translate(-50%,-50%)'}
  joystick.addEventListener('pointerdown',event=>{event.preventDefault();joystickState.pointerId=event.pointerId;joystick.setPointerCapture?.(event.pointerId);updateJoystick(event)});
  joystick.addEventListener('pointermove',event=>{if(event.pointerId!==joystickState.pointerId)return;event.preventDefault();updateJoystick(event)});
  joystick.addEventListener('pointerup',event=>{if(event.pointerId===joystickState.pointerId)resetJoystick()});joystick.addEventListener('pointercancel',resetJoystick);
  window.addEventListener('keydown',event=>{keys.add(event.key.toLowerCase());if(['arrowup','arrowdown','arrowleft','arrowright',' '].includes(event.key.toLowerCase()))event.preventDefault()});window.addEventListener('keyup',event=>keys.delete(event.key.toLowerCase()));

  $('back').addEventListener('click',goGames);$('toGames').addEventListener('click',goGames);$('again').addEventListener('click',()=>location.reload());interactButton.addEventListener('click',beginInteraction);$('distract').addEventListener('click',throwBottle);$('burst').addEventListener('click',burst);$('flashlight').addEventListener('click',toggleFlashlight);
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&state.running&&!state.finished){state.flashlight=false;resetJoystick();updateHud()}});
  rebuildNavigation();resizeObserver=new ResizeObserver(resize);resizeObserver.observe(canvas);window.addEventListener('resize',resize);prepare();
})();
