function canMove(x,y,r=12){const pts=[[0,0],[r,0],[-r,0],[0,r],[0,-r],[r*.7,r*.7],[-r*.7,r*.7],[r*.7,-r*.7],[-r*.7,-r*.7]];return pts.every(([dx,dy])=>walkable(x+dx,y+dy)&&!blocked(x+dx,y+dy,1))}
function roomAt(x,y){return rooms.findIndex(r=>inside(r,x,y))}
function setCaption(t,s=2){$('caption').textContent=t;state.messageUntil=performance.now()+s*1000}
function banner(room,b='ЗАЧИСТКА НАЧАТА'){const el=$('waveBanner');el.querySelector('small').textContent='СЕКТОР '+(room+1);el.querySelector('b').textContent=b;el.classList.add('show');setTimeout(()=>el.classList.remove('show'),1450)}
function setWeapon(key,full=true){const d=weaponDefs[key];player.weapon=key;if(full){player.mag=d.mag;player.reserve=d.reserve}else player.mag=Math.min(player.mag,d.mag);player.reloading=false;$('weaponName').textContent=d.name;$('weaponIcon').textContent=d.icon;setCaption('Оружие сменено: '+d.name+'.',1.8)}
function weapon(){return weaponDefs[player.weapon]}
function moveVector(){let x=joy.x,y=joy.y;if(keys.has('a')||keys.has('arrowleft'))x--;if(keys.has('d')||keys.has('arrowright'))x++;if(keys.has('w')||keys.has('arrowup'))y--;if(keys.has('s')||keys.has('arrowdown'))y++;const m=Math.hypot(x,y);return m>1?{x:x/m,y:y/m,m:1}:{x,y,m}}
function movePlayer(dt,now){
 let v=moveVector(),speed=player.speed;
 if(now<player.dashUntil){v={x:player.dashX,y:player.dashY,m:1};speed*=4.1}
 if(v.m>.06){
  if(!aim.active){player.facingX=v.x;player.facingY=v.y}
  const nx=player.x+v.x*speed*dt,ny=player.y+v.y*speed*dt;
  if(canMove(nx,player.y,player.r))player.x=nx;if(canMove(player.x,ny,player.r))player.y=ny;
  player.walk+=dt*speed*.08
 }
}
function doDash(){
 const now=performance.now();if(!state.running||state.paused||now<player.dashReadyAt)return;
 const v=moveVector(),m=v.m>.1?v:{x:player.facingX,y:player.facingY,m:1};
 player.dashX=m.x;player.dashY=m.y;player.dashUntil=now+230;player.dashReadyAt=now+4000;player.invulnUntil=now+330;
 state.shake=Math.max(state.shake,3);particles(player.x,player.y,10,'#75ffe5');tone(240,.08,'sawtooth',.12);vibrate('medium')
}
function spawnPoint(roomIndex,minDistance=155){
 const r=rooms[roomIndex],side=Math.floor(rand()*4),m=28;let x,y;
 if(side===0){x=r.x+m+rand()*(r.w-m*2);y=r.y+m}else if(side===1){x=r.x+r.w-m;y=r.y+m+rand()*(r.h-m*2)}
 else if(side===2){x=r.x+m+rand()*(r.w-m*2);y=r.y+r.h-m}else{x=r.x+m;y=r.y+m+rand()*(r.h-m*2)}
 if(dist(x,y,player.x,player.y)<minDistance)return spawnPoint(roomIndex,Math.max(90,minDistance-8));return{x,y}
}
function queueSpawn(type,roomIndex=state.activeRoom,delay=.8,point=null){
 if(roomIndex<0)return;const p=point||spawnPoint(roomIndex);state.telegraphs.push({type,room:roomIndex,x:p.x,y:p.y,time:delay,total:delay})
}
function spawnEnemy(type,x,y){
 const d=enemyDefs[type],elite=type==='elite';state.enemies.push({type,x,y,hp:d.hp,maxHp:d.hp,r:d.r,speed:d.speed,damage:d.damage,score:d.score,color:d.color,
 attackAt:0,shootAt:0,chargeAt:0,hit:0,knockX:0,knockY:0,dead:false,phase:1,phaseAt:0,summonAt:0,shockAt:0,elite,telegraph:null});
 if(type==='boss'){$('bossHud').classList.remove('hidden');banner(5,'ТЯЖЁЛЫЙ ОХОТНИК');tone(48,.7,'sawtooth',.25)}
}
function startSector(i){
 if(i<0||i>=6||i<state.roomsCleared)return;
 state.activeRoom=i;state.sectorStartedAt=performance.now();state.sectorTime=0;state.spawnQueue=[];state.telegraphs=[];state.enemies=[];state.enemyBullets=[];state.pods=[];state.breakers=[];state.defenseProgress=0;state.defenseHp=100;state.nextAmbientSpawn=performance.now()+900;
 banner(i,rooms[i].objective);setCaption(sectorIntro(i),3);
 if(i===0)state.spawnQueue=[...waveSets.security];
 if(i===1){state.pods=podTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,hp:145,maxHp:145,spawnAt:performance.now()+1200+k*450,dead:false}));state.spawnQueue=[...waveSets.lab]}
 if(i===2){state.sectorTime=24;state.spawnQueue=[...waveSets.archive]}
 if(i===3){state.sectorTime=22;state.spawnQueue=[...waveSets.med]}
 if(i===4){state.breakers=breakerTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,active:false,progress:0}));state.spawnQueue=[...waveSets.generator]}
 if(i===5){state.spawnQueue=[...waveSets.boss]}
}
function sectorIntro(i){
 return [
 'Двери заблокированы. Уничтожь всех заражённых.',
 'Разбей три заражённые капсулы — они создают новых тварей.',
 'Переживи рой до конца таймера и добей остатки.',
 'Оставайся в зоне терминала и удерживай медицинский блок.',
 'Подойди к трём рубильникам и активируй их, отбиваясь от волн.',
 'Тяжёлый охотник меняет тактику по мере потери здоровья.'
 ][i]
}
function completeSector(){
 const cleared=state.activeRoom;if(cleared<0)return;state.score+=120+cleared*35;state.roomsCleared=cleared+1;state.activeRoom=-1;
 state.enemies=[];state.telegraphs=[];state.spawnQueue=[];state.enemyBullets=[];$('bossHud').classList.add('hidden');
 if(cleared===5){state.score+=450;finish(true,'Комплекс полностью зачищен.');return}
 showUpgrades(cleared)
}
function updateObjective(dt,now){
 const i=state.activeRoom;if(i<0)return;
 if(state.spawnQueue.length&&now>state.nextAmbientSpawn){queueSpawn(state.spawnQueue.shift(),i,.75);state.nextAmbientSpawn=now+520+rand()*260}
 if(i===0){if(!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector()}
 else if(i===1){
  for(const pod of state.pods)if(!pod.dead&&now>pod.spawnAt){queueSpawn(rand()<.45?'runner':'walker',i,.7,{x:pod.x+(rand()-.5)*45,y:pod.y+(rand()-.5)*45});pod.spawnAt=now+3600+rand()*1300}
  if(state.pods.every(p=>p.dead)&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector()
 }else if(i===2){
  state.sectorTime-=dt;if(state.sectorTime>0&&now>state.nextAmbientSpawn-220){if(rand()<.35)queueSpawn(rand()<.55?'runner':'walker',i,.65)}
  if(state.sectorTime<=0&&!state.telegraphs.length&&!state.enemies.length)completeSector()
 }else if(i===3){
  const inZone=dist(player.x,player.y,defensePoint.x,defensePoint.y)<defensePoint.r;
  if(inZone)state.defenseProgress+=dt;else state.defenseProgress=Math.max(0,state.defenseProgress-dt*.22);
  if(now>state.nextAmbientSpawn-260&&rand()<.28)queueSpawn(rand()<.25?'spitter':rand()<.5?'runner':'walker',i,.7);
  if(state.defenseProgress>=22&&!state.telegraphs.length&&!state.enemies.length)completeSector()
 }else if(i===4){
  for(const b of state.breakers)if(!b.active){if(dist(player.x,player.y,b.x,b.y)<48)b.progress+=dt;else b.progress=Math.max(0,b.progress-dt*.45);if(b.progress>=1.15){b.active=true;tone(680,.15,'square',.15);particles(b.x,b.y,16,'#ffbf65');setCaption('Рубильник активирован.',1.4)}}
  if(now>state.nextAmbientSpawn-250&&rand()<.27)queueSpawn(rand()<.2?'brute':rand()<.45?'spitter':'walker',i,.7);
  if(state.breakers.every(b=>b.active)&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector()
