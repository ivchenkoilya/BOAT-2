}
function updateEffects(dt){
 for(const p of [...state.particles]){p.x+=p.vx*dt;p.y+=p.vy*dt;p.vx*=.955;p.vy*=.955;p.life-=dt;if(p.life<=0)state.particles.splice(state.particles.indexOf(p),1)}
 for(const c of [...state.casings]){c.x+=c.vx*dt;c.y+=c.vy*dt;c.vx*=.94;c.vy*=.94;c.life-=dt;if(c.life<=0)state.casings.splice(state.casings.indexOf(c),1)}
 for(const s of [...state.smoke]){s.x+=s.vx*dt;s.y+=s.vy*dt;s.life-=dt;if(s.life<=0)state.smoke.splice(state.smoke.indexOf(s),1)}
 for(const f of [...state.floaters]){f.y-=28*dt;f.life-=dt;if(f.life<=0)state.floaters.splice(state.floaters.indexOf(f),1)}
 for(const c of [...state.corpses]){c.life-=dt;if(c.life<=0)state.corpses.splice(state.corpses.indexOf(c),1)}
 if(performance.now()>state.comboUntil)state.combo=0
}
function particles(x,y,n,color){for(let i=0;i<n;i++)state.particles.push({x,y,vx:(rand()-.5)*185,vy:(rand()-.5)*185,life:.32+rand()*.58,color})}

function moveEnemy(e,tx,ty,dt,mult=1){
 let dx=tx-e.x,dy=ty-e.y,d=Math.hypot(dx,dy)||1;dx/=d;dy/=d;
 let vx=dx*e.speed*mult+e.knockX,vy=dy*e.speed*mult+e.knockY;e.knockX*=.82;e.knockY*=.82;
 const nx=e.x+vx*dt,ny=e.y+vy*dt;
 if(canMove(nx,e.y,e.r*.65))e.x=nx;else if(canMove(e.x-dy*e.speed*dt,e.y+dx*e.speed*dt,e.r*.65)){e.x-=dy*e.speed*dt;e.y+=dx*e.speed*dt}
 if(canMove(e.x,ny,e.r*.65))e.y=ny
}
function fireEnemy(e,now,spread=0){
 const d=dist(e.x,e.y,player.x,player.y)||1,a=Math.atan2(player.y-e.y,player.x-e.x)+(rand()-.5)*spread;
 state.enemyBullets.push({x:e.x,y:e.y,vx:Math.cos(a)*230,vy:Math.sin(a)*230,life:2.6,damage:e.damage});e.shootAt=now+1350+rand()*500;tone(82,.08,'triangle',.07)
}
function updateBoss(e,dt,now){
 const ratio=e.hp/e.maxHp,phase=ratio>.66?1:ratio>.32?2:3;if(phase!==e.phase){e.phase=phase;state.bossPhase=phase;banner(5,'ФАЗА '+phase);tone(45,.45,'sawtooth',.25);state.shake=8}
 $('bossPhase').textContent='ТЯЖЁЛЫЙ ОХОТНИК · ФАЗА '+phase;
 if(phase===1){
  moveEnemy(e,player.x,player.y,dt,1.05);
  if(dist(e.x,e.y,player.x,player.y)<e.r+player.r+12&&now>e.attackAt){damagePlayer(e.damage);e.attackAt=now+900;state.shake=7}
 }else if(phase===2){
  if(!e.telegraph&&now>e.chargeAt){const d=dist(e.x,e.y,player.x,player.y)||1;e.telegraph={x:e.x,y:e.y,dx:(player.x-e.x)/d,dy:(player.y-e.y)/d,time:.72};e.chargeAt=now+2700}
  if(e.telegraph){e.telegraph.time-=dt;if(e.telegraph.time<=0){const ox=e.x,oy=e.y,nx=e.x+e.telegraph.dx*390*dt*4,ny=e.y+e.telegraph.dy*390*dt*4;if(canMove(nx,ny,e.r*.5)){e.x=nx;e.y=ny}else{e.x=ox;e.y=oy;e.telegraph=null}if(dist(e.x,e.y,player.x,player.y)<62)damagePlayer(24);if(e.telegraph&&e.telegraph.time<-.27)e.telegraph=null}}
  else moveEnemy(e,player.x,player.y,dt,.8)
  if(now>e.summonAt){queueSpawn(rand()<.5?'runner':'walker',5,.6);e.summonAt=now+3500}
 }else{
  moveEnemy(e,player.x,player.y,dt,1.2);
  if(now>e.shockAt){state.shockwaves.push({x:e.x,y:e.y,r:18,speed:175,life:1.75,damage:18,hit:false});e.shockAt=now+2200;tone(52,.28,'sine',.2)}
  if(now>e.summonAt){queueSpawn(rand()<.35?'spitter':rand()<.6?'runner':'brute',5,.55);e.summonAt=now+2300}
  if(dist(e.x,e.y,player.x,player.y)<e.r+player.r+10&&now>e.attackAt){damagePlayer(27);e.attackAt=now+720}
 }
}
function updateEnemies(dt,now){
 for(const e of [...state.enemies]){
  if(e.dead){state.enemies.splice(state.enemies.indexOf(e),1);continue}
  e.hit=Math.max(0,e.hit-dt);
  if(e.type==='boss'){updateBoss(e,dt,now);continue}
  let targetX=player.x,targetY=player.y;
  if(state.activeRoom===3&&rand()<.008){targetX=defensePoint.x;targetY=defensePoint.y}
  const d=dist(e.x,e.y,targetX,targetY);
  if(e.type==='spitter'){
   if(d>220)moveEnemy(e,targetX,targetY,dt,.8);else if(d<145)moveEnemy(e,e.x-(targetX-e.x),e.y-(targetY-e.y),dt,.65);
   if(now>e.shootAt&&dist(e.x,e.y,player.x,player.y)<430)fireEnemy(e,now,.12)
  }else if(e.type==='runner'){
   const sway=Math.sin(now/180+e.x*.02)*32;moveEnemy(e,targetX+(targetY-e.y)/(d||1)*sway,targetY-(targetX-e.x)/(d||1)*sway,dt,1.08)
  }else if(e.type==='brute'){
   if(now>e.chargeAt&&d<320){e.chargeAt=now+2600;e.phaseAt=now+480;e.telegraph={dx:(targetX-e.x)/(d||1),dy:(targetY-e.y)/(d||1)}}
   if(now<e.phaseAt&&e.telegraph)moveEnemy(e,e.x+e.telegraph.dx*300,e.y+e.telegraph.dy*300,dt,2.4);else moveEnemy(e,targetX,targetY,dt,.78)
  }else if(e.type==='elite'){
   moveEnemy(e,targetX,targetY,dt,1.06);for(const other of state.enemies)if(other!==e&&dist(e.x,e.y,other.x,other.y)<125)other.speed=Math.min(enemyDefs[other.type].speed*1.25,other.speed+.02)
  }else moveEnemy(e,targetX,targetY,dt,1);
  if(d<e.r+player.r+8&&now>e.attackAt){damagePlayer(e.damage);e.attackAt=now+(e.type==='runner'?650:900);const q=d||1;e.knockX=-(player.x-e.x)/q*95;e.knockY=-(player.y-e.y)/q*95}
  if(state.activeRoom===3&&dist(e.x,e.y,defensePoint.x,defensePoint.y)<35&&now>e.attackAt){state.defenseHp-=e.damage*.6;e.attackAt=now+850;if(state.defenseHp<=0)finish(false,'Медицинский терминал уничтожен.')}
 }
 if(state.turret&&now>state.turret.fireAt){let best=null,bd=280;for(const e of state.enemies){const d=dist(state.turret.x,state.turret.y,e.x,e.y);if(d<bd){bd=d;best=e}}if(best){const d=bd||1;state.bullets.push({x:state.turret.x,y:state.turret.y,px:state.turret.x,py:state.turret.y,vx:(best.x-state.turret.x)/d*600,vy:(best.y-state.turret.y)/d*600,life:.6,damage:12,pierce:0,color:'#78c9ff'});state.turret.fireAt=now+420}}
}

const upgrades=[
{t:'Усиленные пули',d:'+7 к урону любого оружия',f:()=>player.damageBonus+=7},
{t:'Быстрый затвор',d:'Скорострельность +15%',f:()=>player.fireRateBonus+=35},
{t:'Бронепластины',d:'+25 максимального HP и лечение',f:()=>{player.maxHp+=25;player.hp=Math.min(player.maxHp,player.hp+40)}},
{t:'Адреналин',d:'+18 к скорости движения',f:()=>player.speed+=18},
{t:'Пробивающие пули',d:'Пуля пробивает ещё одну цель',f:()=>player.pierce++},
{t:'Вампирический модуль',d:'+3 HP за убийство',f:()=>player.vamp+=3},
{t:'Подсумок',d:'+1 граната и большой запас патронов',f:()=>{player.grenades++;player.reserve+=45}},
{t:'Импульсный щит',d:'8 секунд неуязвимости после выбора',f:()=>state.shieldUntil=performance.now()+8000},
{t:'Автотурель',d:'Стационарная турель сопровождает зачистку',f:()=>state.turret={x:player.x-25,y:player.y+25,fireAt:0}}
];
function showUpgrades(cleared){
 state.paused=true;fireHeld=false;aim.active=false;
 let pool;
 if(cleared===0)pool=[
  {t:'Пистолет-пулемёт',d:'30 патронов, высокая скорострельность',weapon:'smg',f:()=>setWeapon('smg')},
  {t:'Дробовик',d:'7 дробин по лучу, мощный ближний бой',weapon:'shotgun',f:()=>setWeapon('shotgun')},
  upgrades[2]
 ];else{
  pool=[...upgrades].sort(()=>rand()-.5).slice(0,3);
  if(cleared===2&&player.weapon==='pistol')pool[0]={t:'Пистолет-пулемёт',d:'30 патронов, высокая скорострельность',weapon:'smg',f:()=>setWeapon('smg')};
