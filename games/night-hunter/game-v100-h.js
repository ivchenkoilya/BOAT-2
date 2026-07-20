  if(state.breakers.every(b=>b.active)&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector();return
 }
 if(i===5&& !state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector()
}
updateObjective=updateObjectiveV100;

function reset(){
 Object.assign(player,{x:260,y:225,r:14,facingX:1,facingY:0,hp:100,maxHp:100,speed:155,weapon:'pistol',mag:12,reserve:84,reloading:false,reloadEnd:0,lastShot:0,damageBonus:0,fireRateBonus:0,pierce:0,grenades:2,vamp:0,invulnUntil:0,dashUntil:0,dashReadyAt:0,dashX:1,dashY:0,muzzle:0,recoil:0,walk:0});
 Object.assign(state,{running:false,finished:false,paused:false,time:240,last:performance.now(),score:0,kills:0,shots:0,hits:0,roomsCleared:0,activeRoom:-1,unlockedThrough:0,spawnQueue:[],telegraphs:[],enemies:[],bullets:[],enemyBullets:[],grenadeObjs:[],pickups:[],particles:[],casings:[],smoke:[],corpses:[],floaters:[],messageUntil:0,shake:0,flash:0,combo:0,comboUntil:0,sectorTime:0,sectorStartedAt:0,pods:[],breakers:[],defenseProgress:0,defenseHp:100,nextQueueSpawn:0,nextExtraSpawn:0,bossPhase:1,chargeTelegraph:null,shockwaves:[],turret:null,shieldUntil:0});
 fireHeld=false;aim.active=false;aim.id=null;joy.x=joy.y=0;$('bossHud').classList.add('hidden');$('upgrade').classList.add('hidden');$('finish').classList.add('hidden');$('reloadText').classList.add('hidden');$('grenades').textContent='2';setWeapon('pistol',true)
}
function tick(now){
 if(!state.running||state.finished)return;const dt=Math.min(.04,(now-state.last)/1000||0);state.last=now;
 if(!state.paused){
  state.time-=dt;movePlayer(dt,now);if(fireHeld)shoot(now);if(player.reloading&&now>=player.reloadEnd)finishReload();
  updateTelegraphs(dt);updateEnemies(dt,now);updateBullets(dt);updatePickups(dt);updateEffects(dt);updateObjective(dt,now);
  const ri=roomAt(player.x,player.y);if(state.activeRoom<0&&ri===state.roomsCleared&&ri<6)startSector(ri);
  if(state.time<=0)finish(false,'Время операции истекло.')
 }
 updateHud(now);render(now);raf=requestAnimationFrame(tick)
}
function startGame(demo=false){
 state.demo=demo;initAudio();try{audio?.ac?.resume?.()}catch(_){}$('intro').classList.add('hidden');reset();state.running=true;startSector(0);setCaption('Левый джойстик — движение. Веди пальцем по кнопке огня — направляй луч и стреляй.',4);resize();raf=requestAnimationFrame(tick)
}
async function prepare(){
 try{const d=await api('start',{game:'night-hunter'});state.sessionId=d.session_id;state.seed=Number(d.seed)||Date.now();state.time=Number(d.duration)||240;$('start').textContent='НАЧАТЬ ЗАЧИСТКУ';$('start').classList.remove('loading');$('start').onclick=()=>startGame(false)}
 catch(e){state.seed=Date.now()>>>0;$('start').classList.add('hidden');$('demo').classList.remove('hidden');$('demo').onclick=()=>startGame(true);$('startError').style.display='block';$('startError').textContent=e.message+' Доступен демонстрационный режим.'}
}
async function finish(success,reason){
 if(state.finished)return;state.finished=true;state.running=false;cancelAnimationFrame(raf);fireHeld=false;
 const accuracy=state.shots?Math.min(100,Math.round(state.hits/state.shots*100)):0;
 const raw=Math.max(0,Math.round(state.score+state.roomsCleared*70+(success?320:0)+player.hp*1.5));
 $('resultIcon').textContent=success?'☑':'☣';$('resultEyebrow').textContent=success?'КОМПЛЕКС ЗАЧИЩЕН':'ОПЕРАЦИЯ ПРОВАЛЕНА';$('resultTitle').textContent=success?'Зачистка завершена':'Отряд потерян';$('resultText').textContent=reason;
 $('resultScore').textContent=raw;$('resultKills').textContent=state.kills;$('resultRooms').textContent=state.roomsCleared+'/6';$('resultAccuracy').textContent=accuracy+'%';$('finish').classList.remove('hidden');
 if(state.demo||!state.sessionId){$('reward').textContent='Демо-режим: результат не начисляется.';return}
 try{const d=await api('finish',{session_id:state.sessionId,score:raw,stats:{cleared:success,kills:state.kills,rooms:state.roomsCleared,shots:state.shots,hits:state.hits,accuracy,hp:Math.round(player.hp),time_left:Math.round(state.time),weapon:player.weapon}});$('reward').innerHTML=d.actual_reward>0?`Начислено <b>+${d.actual_reward}</b> влияния. Баланс: <b>${d.balance}</b>.`:(d.message||'Результат сохранён.')}
 catch(e){$('reward').textContent='Сервер не сохранил результат: '+e.message}
}

function joyUpdate(e){
 const r=$('joystick').getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,dx=e.clientX-cx,dy=e.clientY-cy,max=r.width*.34,m=Math.hypot(dx,dy)||1,s=Math.min(1,max/m),x=dx*s,y=dy*s;
 joy.x=x/max;joy.y=y/max;$('joystickKnob').style.transform=`translate(calc(-50% + ${x}px),calc(-50% + ${y}px))`
}
function joyReset(){joy.id=null;joy.x=joy.y=0;$('joystickKnob').style.transform='translate(-50%,-50%)'}
function aimUpdate(e){
 const r=$('fire').getBoundingClientRect(),cx=r.left+r.width/2,cy=r.top+r.height/2,dx=e.clientX-cx,dy=e.clientY-cy,m=Math.hypot(dx,dy);
 if(m>8){aim.x=dx/m;aim.y=dy/m;player.facingX=aim.x;player.facingY=aim.y}
}
$('joystick').addEventListener('pointerdown',e=>{e.preventDefault();joy.id=e.pointerId;$('joystick').setPointerCapture?.(e.pointerId);joyUpdate(e)});
$('joystick').addEventListener('pointermove',e=>{if(e.pointerId===joy.id)joyUpdate(e)});
$('joystick').addEventListener('pointerup',joyReset);$('joystick').addEventListener('pointercancel',joyReset);

const fire=$('fire');
fire.addEventListener('pointerdown',e=>{e.preventDefault();fireHeld=true;aim.active=true;aim.id=e.pointerId;aimUpdate(e);fire.classList.add('firing');fire.setPointerCapture?.(e.pointerId)});
fire.addEventListener('pointermove',e=>{if(e.pointerId===aim.id)aimUpdate(e)});
const stopFire=e=>{if(e&&aim.id!==null&&e.pointerId!==aim.id)return;fireHeld=false;aim.active=false;aim.id=null;fire.classList.remove('firing')};
fire.addEventListener('pointerup',stopFire);fire.addEventListener('pointercancel',stopFire);fire.addEventListener('pointerleave',e=>{if(e.buttons===0)stopFire(e)});

$('reload').onclick=reload;$('grenade').onclick=throwGrenade;$('dash').onclick=doDash;$('back').onclick=goGames;$('toGames').onclick=goGames;$('again').onclick=()=>location.reload();
window.addEventListener('keydown',e=>{keys.add(e.key.toLowerCase());if(e.code==='Space'){fireHeld=true;aim.active=true;e.preventDefault()}if(e.key.toLowerCase()==='r')reload();if(e.key.toLowerCase()==='shift')doDash()});
window.addEventListener('keyup',e=>{keys.delete(e.key.toLowerCase());if(e.code==='Space'){fireHeld=false;aim.active=false}});
document.addEventListener('visibilitychange',()=>{if(document.hidden){fireHeld=false;aim.active=false;joyReset()}});
new ResizeObserver(resize).observe(canvas);window.addEventListener('resize',resize);prepare();
})();