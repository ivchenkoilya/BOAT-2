'use strict';

const tg=window.Telegram?.WebApp;
tg?.ready();
tg?.expand();
tg?.setHeaderColor?.('#080411');
tg?.setBackgroundColor?.('#080411');

const params=new URLSearchParams(location.search);
const chatId=params.get('chat_id')||'';
const initData=tg?.initData||'';
const headers={'Content-Type':'application/json','X-Telegram-Init-Data':initData};
const $=id=>document.getElementById(id);
const canvas=$('game');
const ctx=canvas.getContext('2d',{alpha:false,desynchronized:true});

const JUMP_DURATION=.88;
const SLIDE_DURATION=.74;

let W=0,H=0,dpr=1,assets={},assetsReady=true;
let running=false,ended=false,demo=false,sessionId='',seed=1,rng=Math.random;
let startedAt=0,lastFrame=0,runDuration=60,timeLeft=60,distance=0,spawnIn=0;
let score=0,combo=0,bestCombo=0,lives=3,hits=0,lane=1,laneVisual=1;
let jump=0,slide=0,shield=0,magnet=0,power='';
let objects=[],particles=[],floating=[],rain=[],shake=0,flash=0,bossPulse=0,bossAttackIn=10,bossAlertTimer=0;
let bossTelegraph=0,bossSafeLane=-1;
let touchStart=null;

function seeded(s){return()=>{s=(s*1664525+1013904223)>>>0;return s/4294967296}}
function clamp(value,min=0,max=1){return Math.max(min,Math.min(max,value))}

function prepareGame(){
  $('start').textContent='НАЧАТЬ ЗАБЕГ';
  $('start').classList.remove('loading');
  requestAnimationFrame(()=>{if(typeof drawIdle==='function')drawIdle()});
}
prepareGame();

function resize(){
  const rect=canvas.getBoundingClientRect();
  dpr=Math.min(3,window.devicePixelRatio||1);
  W=Math.max(1,rect.width);
  H=Math.max(1,rect.height);
  canvas.width=Math.round(W*dpr);
  canvas.height=Math.round(H*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0);
  ctx.imageSmoothingEnabled=true;
  ctx.imageSmoothingQuality='high';
  if(!running&&typeof drawIdle==='function')drawIdle();
}
addEventListener('resize',resize,{passive:true});
resize();

async function api(path,body={}){
  const response=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});
  const data=await response.json().catch(()=>({ok:false,reason:'Сервер не ответил.'}));
  if(!response.ok||!data.ok)throw new Error(data.reason||'Ошибка сервера.');
  return data;
}

function reset(){
  objects=[];particles=[];floating=[];running=true;ended=false;startedAt=performance.now();lastFrame=startedAt;
  timeLeft=runDuration;distance=0;spawnIn=.5;score=0;combo=0;bestCombo=0;lives=3;hits=0;lane=1;laneVisual=1;
  jump=0;slide=0;shield=0;magnet=0;power='';shake=0;flash=0;bossPulse=0;bossAttackIn=8.5;bossAlertTimer=0;
  bossTelegraph=0;bossSafeLane=-1;
  $('score').textContent='0';
  $('power').classList.remove('show');
  $('bossAlert').classList.remove('show');
  $('ability').classList.remove('ready');
  $('ability').textContent='✨ СПОСОБНОСТЬ';
  rain=Array.from({length:Math.max(28,Math.floor(W/11))},()=>({x:rng()*W,y:rng()*H,l:12+rng()*30,s:150+rng()*210,a:.08+rng()*.20}));
}

async function startGame(){
  $('startError').textContent='';
  try{
    const data=await api('start',{game:'rooftop'});
    sessionId=data.session_id;seed=data.seed;runDuration=Number(data.duration)||60;rng=seeded(seed);demo=false;
  }catch(error){
    sessionId='';seed=Date.now()&0xffffffff;rng=seeded(seed);runDuration=60;demo=true;
    $('startError').textContent='Демонстрационный режим: '+error.message;
  }
  reset();
  $('intro').classList.add('hidden');
  requestAnimationFrame(loop);
}

function laneX(value,z=.9){
  const nz=clamp(z);
  const horizonSpread=W*.075,nearSpread=W*.285;
  return W/2+(value-1)*(horizonSpread+(nearSpread-horizonSpread)*Math.pow(nz,1.35));
}
function objectY(z){
  const horizon=H*.245;
  return horizon+(H-horizon)*Math.pow(clamp(z),1.52);
}
function objectScale(z,type='generic'){
  const nz=clamp(z);
  if(type==='orb')return .92+nz*.06;
  if(type==='gold')return .94+nz*.07;
  if(type==='power')return .91+nz*.09;
  if(type==='barrier')return .68+nz*.36;
  if(type==='vent')return .72+nz*.33;
  if(type==='drone')return .72+nz*.30;
  if(type==='wave')return .76+nz*.30;
  return .78+nz*.28;
}
function jumpArc(){
  if(jump<=0)return 0;
  const progress=clamp(1-jump/JUMP_DURATION);
  return Math.sin(progress*Math.PI);
}
function isCollectibleNear(o){return o.z>.79&&o.z<1.045&&Math.abs(o.lane-lane)<.31&&!o.hit}
function isHazardNear(o){return o.z>.90&&o.z<1.02&&Math.abs(o.lane-lane)<.21&&!o.hit&&!o.cleared}
function clearsHazard(o){
  const height=jumpArc();
  if(o.type==='barrier')return height>.20;
  if(o.type==='vent')return height>.13;
  if(o.type==='drone')return slide>.08;
  return false;
}

function addFloat(text,x,y,color='#fff'){floating.push({text,x,y,t:1,color})}
function addBurst(x,y,color='#b76cff',count=11){for(let i=0;i<count;i++)particles.push({x,y,vx:(rng()-.5)*125,vy:-25-rng()*120,t:.65+rng()*.45,r:1.5+rng()*3,color})}
function spawnOne(type,laneValue,delay=0,kind=''){objects.push({type,lane:laneValue,z:-delay,hit:false,kind,phase:rng()*6.28,cleared:false})}

function spawnPattern(){
  const roll=rng(),target=Math.floor(rng()*3);
  if(roll<.22)spawnOne('barrier',target);
  else if(roll<.36)spawnOne('vent',target);
  else if(roll<.48)spawnOne('drone',target);
  else if(roll<.66){spawnOne('orb',target);spawnOne('orb',target,.12);spawnOne('orb',target,.24)}
  else if(roll<.76)spawnOne('gold',target);
  else if(roll<.86)spawnOne('power',target,0,['magnet','shield','flash'][Math.floor(rng()*3)]);
  else for(let i=0;i<3;i++)spawnOne('orb',i,i*.05);
  if(rng()<.40&&roll<.48)spawnOne('orb',(target+1+Math.floor(rng()*2))%3,.12);
}

function bossAttack(){
  bossSafeLane=Math.floor(rng()*3);
  bossTelegraph=1.18;
  bossPulse=1.35;
  bossAlertTimer=2.65;
  shake=3;
  $('bossAlert').classList.add('show');
  tg?.HapticFeedback?.notificationOccurred?.('warning');
}
function releaseBossAttack(){
  for(let i=0;i<3;i++)if(i!==bossSafeLane)spawnOne('wave',i,-.04);
  flash=.16;shake=9;bossPulse=1.1;
  tg?.HapticFeedback?.impactOccurred?.('heavy');
}

function move(dir){
  if(!running)return;
  lane=Math.max(0,Math.min(2,lane+dir));
  tg?.HapticFeedback?.selectionChanged?.();
}
function doJump(){
  if(running&&jump<=0&&slide<=0){jump=JUMP_DURATION;tg?.HapticFeedback?.impactOccurred?.('light')}
}
function doSlide(){
  if(running&&slide<=0&&jump<=0){slide=SLIDE_DURATION;tg?.HapticFeedback?.impactOccurred?.('light')}
}

function updatePowerCard(){
  const button=$('ability');
  if(!power){
    $('power').classList.remove('show');
    button.classList.remove('ready');
    button.textContent='✨ СПОСОБНОСТЬ';
    return;
  }
  const map={
    magnet:['🧲','МАГНИТ ГОТОВ — СОБЕРЁТ ОСКОЛКИ','🧲 АКТИВИРОВАТЬ МАГНИТ'],
    shield:['🛡','ЩИТ ГОТОВ — СПАСЁТ ОТ УДАРА','🛡 АКТИВИРОВАТЬ ЩИТ'],
    flash:['⚡','ВСПЫШКА ГОТОВА — ОЧИСТИТ ТРАССУ','⚡ ОЧИСТИТЬ ТРАССУ']
  };
  $('powerIcon').textContent=map[power][0];
  $('powerText').textContent=map[power][1];
  $('power').classList.add('show');
  button.classList.add('ready');
  button.textContent=map[power][2];
}

function useAbility(){
  if(!running||!power)return;
  if(power==='shield')shield=1;
  if(power==='magnet')magnet=7;
  if(power==='flash'){
    let removed=0;
    for(const o of objects){if(['barrier','vent','drone','wave'].includes(o.type)&&!o.hit){o.hit=true;removed++}}
    score+=removed*3+8;flash=.45;shake=4;addFloat('ТРАССА ОЧИЩЕНА',W/2,H*.62,'#ffe17b');
  }
  addBurst(laneX(lane,1),H*.81,'#d28cff',18);
  power='';updatePowerCard();
  tg?.HapticFeedback?.notificationOccurred?.('success');
}

function collect(o,value,color='#c176ff'){
  if(o.hit)return;
  o.hit=true;combo++;bestCombo=Math.max(bestCombo,combo);
  const mult=combo>=35?3:combo>=20?2:combo>=10?1.5:1,gained=Math.round(value*mult);score+=gained;
  const x=laneX(o.lane,o.z),y=objectY(o.z);addBurst(x,y,color,12);addFloat('+'+gained,x,y-10,color);
  tg?.HapticFeedback?.impactOccurred?.('soft');
}
function collide(o){
  if(o.hit)return;
  o.hit=true;
  if(shield){shield=0;flash=.2;shake=3;addFloat('ЩИТ СПАС',laneX(lane,1),H*.7,'#9de9ff');addBurst(laneX(lane,1),H*.78,'#8ee7ff',20);return}
  hits++;lives--;combo=0;shake=13;flash=.4;
  tg?.HapticFeedback?.notificationOccurred?.('error');
  if(lives<=0)finishGame('Центр Вселенной остановил забег');
}

function update(dt){
  timeLeft=Math.max(0,runDuration-(performance.now()-startedAt)/1000);
  distance+=dt*28;
  laneVisual+=(lane-laneVisual)*Math.min(1,dt*13);

  spawnIn-=dt;
  if(spawnIn<=0){spawnPattern();spawnIn=Math.max(.42,.78-distance/2400)}

  bossAttackIn-=dt;
  if(bossAttackIn<=0&&bossTelegraph<=0){bossAttack();bossAttackIn=13+rng()*5}
  if(bossTelegraph>0){
    const before=bossTelegraph;
    bossTelegraph=Math.max(0,bossTelegraph-dt);
    if(before>0&&bossTelegraph===0)releaseBossAttack();
  }
  if(bossAlertTimer>0){bossAlertTimer-=dt;if(bossAlertTimer<=0)$('bossAlert').classList.remove('show')}

  if(jump>0)jump=Math.max(0,jump-dt);
  if(slide>0)slide=Math.max(0,slide-dt);
  if(magnet>0)magnet=Math.max(0,magnet-dt);
  bossPulse=Math.max(0,bossPulse-dt*.82);
  flash=Math.max(0,flash-dt*1.6);
  shake=Math.max(0,shake-dt*22);

  const speed=.285+Math.min(.18,distance/3000);
  for(const o of objects){
    o.z+=speed*dt;o.phase+=dt*3;
    if(magnet>0&&['orb','gold'].includes(o.type)&&o.z>.42&&Math.abs(o.lane-lane)<=1)o.lane+=(lane-o.lane)*Math.min(1,dt*6);

    if(isCollectibleNear(o)){
      if(o.type==='orb')collect(o,3);
      else if(o.type==='gold')collect(o,12,'#ffd86a');
      else if(o.type==='power'){
        o.hit=true;power=o.kind||'magnet';updatePowerCard();
        addFloat('УСИЛЕНИЕ',laneX(o.lane,o.z),objectY(o.z)-15,'#ffe17b');
      }
    }

    if(isHazardNear(o)&&['barrier','vent','drone','wave'].includes(o.type)){
      if(clearsHazard(o)){
        if(!o.cleared){o.cleared=true;addFloat(o.type==='drone'?'ИДЕАЛЬНЫЙ ПОДКАТ':'ЧИСТЫЙ ПРЫЖОК',laneX(o.lane,o.z),objectY(o.z)-24,'#9eefff')}
      }else collide(o);
    }
  }

  objects=objects.filter(o=>o.z<1.16&&!o.hit);
  for(const p of particles){p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=90*dt;p.t-=dt}
  particles=particles.filter(p=>p.t>0);
  for(const f of floating){f.y-=34*dt;f.t-=dt}
  floating=floating.filter(f=>f.t>0);
  for(const r of rain){r.y+=r.s*dt;r.x-=r.s*.08*dt;if(r.y>H+30){r.y=-30;r.x=rng()*W}}

  $('score').textContent=score;
  $('timer').textContent=formatTime(timeLeft);
  const multiplier=combo>=35?3:combo>=20?2:combo>=10?1.5:1;
  $('combo').textContent='СЕРИЯ ×'+multiplier;
  $('combo').classList.toggle('hot',multiplier>1);
  $('lives').textContent='❤'.repeat(Math.max(0,lives))+'♡'.repeat(Math.max(0,3-lives));
  if(timeLeft<=0)finishGame('Время забега закончилось');
}

function coverImage(image,x,y,w,h,zoom=1){
  if(!image)return;
  const ir=image.width/image.height,rr=w/h;let sw,sh,sx,sy;
  if(ir>rr){sh=image.height;sw=sh*rr;sx=(image.width-sw)/2;sy=0}else{sw=image.width;sh=sw/rr;sx=0;sy=(image.height-sh)/2}
  const zw=sw/zoom,zh=sh/zoom;sx+=(sw-zw)/2;sy+=(sh-zh)/2;ctx.drawImage(image,sx,sy,zw,zh,x,y,w,h);
}
