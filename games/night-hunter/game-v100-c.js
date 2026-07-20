 }else if(i===5){if(!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector()}
}

function aimAngle(){return Math.atan2(player.facingY,player.facingX)}
function inBeam(x,y,max=620,half=.25){
 const dx=x-player.x,dy=y-player.y,d=Math.hypot(dx,dy);if(d>max||d<1)return false;
 const dot=(dx/d)*player.facingX+(dy/d)*player.facingY;return dot>Math.cos(half)
}
function shoot(now){
 if(player.reloading)return;const w=weapon();const delay=Math.max(55,w.delay-player.fireRateBonus);
 if(now-player.lastShot<delay)return;if(player.mag<=0){reload();return}
 player.lastShot=now;player.mag--;state.shots++;player.muzzle=.12;player.recoil=w.recoil;state.flash=.09;state.shake=Math.max(state.shake,w.recoil);
 const base=aimAngle();
 for(let i=0;i<w.pellets;i++){
  const a=base+(rand()-.5)*w.spread,ax=Math.cos(a),ay=Math.sin(a);
  state.bullets.push({x:player.x+ax*25,y:player.y+ay*25,px:player.x,py:player.y,vx:ax*w.speed,vy:ay*w.speed,life:.92,damage:w.damage+player.damageBonus,pierce:player.pierce,color:w.color})
 }
 const sideX=-player.facingY,sideY=player.facingX;state.casings.push({x:player.x+sideX*8,y:player.y+sideY*8,vx:sideX*80+(rand()-.5)*30,vy:sideY*80+(rand()-.5)*30,life:.7});
 state.smoke.push({x:player.x+player.facingX*28,y:player.y+player.facingY*28,vx:player.facingX*16,vy:player.facingY*16,life:.45});
 tone(player.weapon==='shotgun'?92:player.weapon==='smg'?185:145,player.weapon==='shotgun'?.09:.045,'square',player.weapon==='shotgun'?.24:.16);vibrate(player.weapon==='shotgun'?'medium':'light');
 if(player.mag===0&&player.reserve>0)setTimeout(reload,110)
}
function reload(){
 if(player.reloading||player.mag>=weapon().mag||player.reserve<=0||!state.running||state.paused)return;
 player.reloading=true;player.reloadEnd=performance.now()+(player.weapon==='shotgun'?1450:1100);$('reloadText').classList.remove('hidden');tone(235,.07,'square',.08)
}
function finishReload(){
 const w=weapon(),need=w.mag-player.mag,take=Math.min(need,player.reserve);player.mag+=take;player.reserve-=take;player.reloading=false;$('reloadText').classList.add('hidden');tone(520,.06,'square',.09)
}
function throwGrenade(){
 if(!state.running||state.paused||player.grenades<=0)return;player.grenades--;$('grenades').textContent=player.grenades;
 state.grenadeObjs.push({x:player.x,y:player.y,vx:player.facingX*330,vy:player.facingY*330,time:.72});tone(180,.08,'triangle',.1)
}
function explode(g){
 state.shake=Math.max(state.shake,11);state.flash=.45;particles(g.x,g.y,42,'#ffb35a');tone(58,.35,'sawtooth',.32);vibrate('heavy');
 for(const e of [...state.enemies]){const d=dist(g.x,g.y,e.x,e.y);if(d<155)damageEnemy(e,Math.max(25,150-d*.65),(e.x-g.x)/(d||1),(e.y-g.y)/(d||1))}
 for(const pod of state.pods){if(!pod.dead&&dist(g.x,g.y,pod.x,pod.y)<145)damagePod(pod,90)}
}
function damagePod(pod,amount){
 if(pod.dead)return;pod.hp-=amount;particles(pod.x,pod.y,5,'#8ea5ff');floatText(pod.x,pod.y-24,Math.round(amount),'#b8c5ff');
 if(pod.hp<=0){pod.dead=true;state.score+=85;particles(pod.x,pod.y,24,'#9aaeff');tone(86,.22,'sawtooth',.18)}
}
function damageEnemy(e,amount,kx=0,ky=0){
 if(e.dead)return;e.hp-=amount;e.hit=.11;e.knockX+=kx*125;e.knockY+=ky*125;state.hits++;floatText(e.x,e.y-e.r-8,Math.round(amount),amount>45?'#ffd06e':'#f1ffff');
 particles(e.x,e.y,3,e.type==='spitter'?'#86ff83':'#ff526b');
 if(e.hp<=0)killEnemy(e)
}
function killEnemy(e){
 if(e.dead)return;e.dead=true;state.kills++;state.combo++;state.comboUntil=performance.now()+2600;state.score+=e.score*(1+Math.min(1.5,state.combo*.04));
 if(player.vamp)player.hp=Math.min(player.maxHp,player.hp+player.vamp);
 state.corpses.push({type:e.type,x:e.x,y:e.y,r:e.r,angle:Math.atan2(e.knockY,e.knockX),life:7});
 particles(e.x,e.y,e.type==='boss'?50:14,e.type==='spitter'?'#75ff72':'#d13b55');tone(e.type==='boss'?42:75,.16,'sawtooth',e.type==='boss'?.3:.12);
 if(rand()<.16&&e.type!=='boss')state.pickups.push({type:rand()<.58?'ammo':'med',x:e.x,y:e.y,life:12});
 if(state.combo===2)setCaption('ДВОЙНОЕ УБИЙСТВО!',1.2);else if(state.combo===3)setCaption('ТРОЙНОЕ УБИЙСТВО!',1.2);else if(state.combo===5)setCaption('СЕРИЯ ×5!',1.2);else if(state.combo===8)setCaption('БЕЗУПРЕЧНАЯ ЗАЧИСТКА!',1.5);if(e.type==='boss')state.score+=600
}
function floatText(x,y,text,color){state.floaters.push({x,y,text:String(text),color,life:.7})}
function damagePlayer(amount){
 const now=performance.now();if(now<player.invulnUntil||now<state.shieldUntil)return;
 player.hp-=amount;player.invulnUntil=now+520;state.shake=Math.max(state.shake,7);$('damageFx').classList.remove('show');void $('damageFx').offsetWidth;$('damageFx').classList.add('show');tone(63,.18,'sawtooth',.18);vibrate('heavy');
 if(player.hp<=0){player.hp=0;finish(false,'Герой погиб во время зачистки.')}
}
function updateTelegraphs(dt){
 for(const t of [...state.telegraphs]){t.time-=dt;if(t.time<=0){spawnEnemy(t.type,t.x,t.y);state.telegraphs.splice(state.telegraphs.indexOf(t),1)}}
}
function updateBullets(dt){
 for(const b of [...state.bullets]){
  b.px=b.x;b.py=b.y;b.x+=b.vx*dt;b.y+=b.vy*dt;b.life-=dt;let removed=false;
  for(const pod of state.pods)if(!pod.dead&&dist(b.x,b.y,pod.x,pod.y)<28){damagePod(pod,b.damage);b.pierce--;if(b.pierce<0){removed=true;break}}
  if(!removed)for(const e of [...state.enemies])if(!e.dead&&dist(b.x,b.y,e.x,e.y)<e.r+4){const d=Math.hypot(b.vx,b.vy)||1;damageEnemy(e,b.damage,b.vx/d,b.vy/d);b.pierce--;if(b.pierce<0){removed=true;break}}
  if(removed||b.life<=0||!walkable(b.x,b.y)||blocked(b.x,b.y,-3))state.bullets.splice(state.bullets.indexOf(b),1)
 }
 for(const b of [...state.enemyBullets]){
  b.x+=b.vx*dt;b.y+=b.vy*dt;b.life-=dt;if(dist(b.x,b.y,player.x,player.y)<player.r+6){damagePlayer(b.damage);b.life=0}
  if(b.life<=0||!walkable(b.x,b.y))state.enemyBullets.splice(state.enemyBullets.indexOf(b),1)
 }
 for(const g of [...state.grenadeObjs]){g.x+=g.vx*dt;g.y+=g.vy*dt;g.vx*=.968;g.vy*=.968;g.time-=dt;if(g.time<=0){explode(g);state.grenadeObjs.splice(state.grenadeObjs.indexOf(g),1)}}
 for(const s of [...state.shockwaves]){s.r+=s.speed*dt;s.life-=dt;if(!s.hit&&Math.abs(dist(s.x,s.y,player.x,player.y)-s.r)<18){s.hit=true;damagePlayer(s.damage)}if(s.life<=0)state.shockwaves.splice(state.shockwaves.indexOf(s),1)}
}
function updatePickups(dt){
 for(const p of [...state.pickups]){p.life-=dt;if(dist(player.x,player.y,p.x,p.y)<29){if(p.type==='ammo'){player.reserve=Math.min(260,player.reserve+(player.weapon==='shotgun'?10:30));setCaption('Подобраны патроны.',1.3)}else{player.hp=Math.min(player.maxHp,player.hp+28);setCaption('Аптечка восстановила 28 HP.',1.3)}state.pickups.splice(state.pickups.indexOf(p),1);tone(650,.08,'sine',.1)}else if(p.life<=0)state.pickups.splice(state.pickups.indexOf(p),1)}
