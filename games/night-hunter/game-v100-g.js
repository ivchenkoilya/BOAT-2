 for(const b of state.enemyBullets){ctx.fillStyle='#9cff75';ctx.shadowColor='#6dff55';ctx.shadowBlur=10;ctx.beginPath();ctx.arc(b.x,b.y,5,0,Math.PI*2);ctx.fill()}
 ctx.shadowBlur=0;
 for(const g of state.grenadeObjs){ctx.fillStyle='#2f3635';ctx.beginPath();ctx.arc(g.x,g.y,7,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#ffd06e';ctx.stroke()}
 for(const c of state.casings){ctx.fillStyle='#ffd06e';ctx.save();ctx.translate(c.x,c.y);ctx.rotate(c.life*9);ctx.fillRect(-2,-1,5,2);ctx.restore()}
 for(const s of state.smoke){ctx.globalAlpha=clamp(s.life/.45,0,.35);ctx.fillStyle='#cdd9d9';ctx.beginPath();ctx.arc(s.x,s.y,7+(1-s.life/.45)*12,0,Math.PI*2);ctx.fill();ctx.globalAlpha=1}
 for(const p of state.particles){ctx.globalAlpha=clamp(p.life/.45,0,1);ctx.fillStyle=p.color;ctx.fillRect(p.x-2,p.y-2,4,4)}ctx.globalAlpha=1;
 for(const f of state.floaters){ctx.globalAlpha=clamp(f.life/.7,0,1);ctx.fillStyle=f.color;ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText(f.text,f.x,f.y)}ctx.globalAlpha=1;
 for(const s of state.shockwaves){ctx.strokeStyle='#ff4b6355';ctx.lineWidth=8;ctx.beginPath();ctx.arc(s.x,s.y,s.r,0,Math.PI*2);ctx.stroke()}
}
function drawWorld(now){
 ctx.fillStyle='#020507';ctx.fillRect(0,0,WORLD.w,WORLD.h);
 for(const c of corridors)drawCorridor(c,now);rooms.forEach((r,i)=>drawRoom(r,i,now));drawDoors();drawObjectives(now);
 for(const s of solids){ctx.strokeStyle='#5b777d33';ctx.strokeRect(s.x,s.y,s.w,s.h)}
 for(const c of state.corpses)drawCorpse(c);drawTelegraphs(now);drawPickups(now);
 for(const e of state.enemies)drawEnemy(e,now);drawPlayer(now);drawEffects();
 if(state.turret){ctx.fillStyle='#78c9ff';ctx.beginPath();ctx.arc(state.turret.x,state.turret.y,12,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#d8f1ff';ctx.beginPath();ctx.moveTo(state.turret.x,state.turret.y);ctx.lineTo(state.turret.x+18,state.turret.y);ctx.stroke()}
}
function drawLight(now){
 lctx.setTransform(dpr,0,0,dpr,0,0);lctx.clearRect(0,0,vw,vh);lctx.fillStyle='rgba(0,0,0,.37)';lctx.fillRect(0,0,vw,vh);
 const px=player.x-camera.x,py=player.y-camera.y,ang=aimAngle()+player.recoil*.002*Math.sin(now/25);
 lctx.globalCompositeOperation='destination-out';
 const rad=lctx.createRadialGradient(px,py,8,px,py,120);rad.addColorStop(0,'rgba(0,0,0,.98)');rad.addColorStop(1,'rgba(0,0,0,0)');
 lctx.fillStyle=rad;lctx.beginPath();lctx.arc(px,py,122,0,Math.PI*2);lctx.fill();
 lctx.save();lctx.translate(px,py);lctx.rotate(ang);const beam=lctx.createLinearGradient(0,0,520,0);beam.addColorStop(0,'rgba(0,0,0,.98)');beam.addColorStop(.67,'rgba(0,0,0,.78)');beam.addColorStop(1,'rgba(0,0,0,0)');
 lctx.fillStyle=beam;lctx.beginPath();lctx.moveTo(0,-16);lctx.lineTo(520,-130);lctx.lineTo(520,130);lctx.lineTo(0,16);lctx.closePath();lctx.fill();lctx.restore();
 lctx.globalCompositeOperation='source-over';ctx.drawImage(light,0,0,vw,vh);
 ctx.save();ctx.translate(px,py);ctx.rotate(ang);ctx.strokeStyle='#d8fff766';ctx.lineWidth=1;ctx.setLineDash([3,7]);ctx.beginPath();ctx.moveTo(38,0);ctx.lineTo(290,0);ctx.stroke();ctx.setLineDash([]);ctx.strokeStyle='#ffdf8b88';ctx.beginPath();ctx.arc(290,0,9,0,Math.PI*2);ctx.stroke();ctx.restore()
}
function render(now){
 const maxX=Math.max(0,WORLD.w-vw),maxY=Math.max(0,WORLD.h-vh),tx=clamp(player.x-vw/2,0,maxX),ty=clamp(player.y-vh/2,0,maxY);camera.x+=(tx-camera.x)*.13;camera.y+=(ty-camera.y)*.13;
 const sx=(rand()-.5)*state.shake,sy=(rand()-.5)*state.shake;state.shake*=.83;state.flash=Math.max(0,state.flash-.022);player.muzzle=Math.max(0,player.muzzle-.035);player.recoil*=.72;
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vw,vh);ctx.save();ctx.translate(-camera.x+sx,-camera.y+sy);drawWorld(now);ctx.restore();drawLight(now);
 if(state.flash>0){ctx.fillStyle=`rgba(255,235,180,${state.flash})`;ctx.fillRect(0,0,vw,vh)}
}

function startSectorV100(i){
 if(i<0||i>=6||i<state.roomsCleared)return;
 state.activeRoom=i;state.sectorStartedAt=performance.now();state.sectorTime=0;state.spawnQueue=[];state.telegraphs=[];state.enemies=[];state.enemyBullets=[];state.pods=[];state.breakers=[];state.defenseProgress=0;state.defenseHp=100;
 state.nextQueueSpawn=performance.now()+450;state.nextExtraSpawn=performance.now()+1500;banner(i,rooms[i].objective);setCaption(sectorIntro(i),3);
 if(i===0)state.spawnQueue=[...waveSets.security];
 if(i===1){state.pods=podTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,hp:145,maxHp:145,spawnAt:performance.now()+1400+k*500,dead:false}));state.spawnQueue=[...waveSets.lab]}
 if(i===2){state.sectorTime=24;state.spawnQueue=[...waveSets.archive]}
 if(i===3){state.sectorTime=22;state.spawnQueue=[...waveSets.med]}
 if(i===4){state.breakers=breakerTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,active:false,progress:0}));state.spawnQueue=[...waveSets.generator]}
 if(i===5)state.spawnQueue=[...waveSets.boss]
}
startSector=startSectorV100;
function updateObjectiveV100(dt,now){
 const i=state.activeRoom;if(i<0)return;
 if(state.spawnQueue.length&&now>state.nextQueueSpawn){queueSpawn(state.spawnQueue.shift(),i,.75);state.nextQueueSpawn=now+520+rand()*250}
 if(i===0){if(!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector();return}
 if(i===1){
  for(const pod of state.pods)if(!pod.dead&&now>pod.spawnAt){queueSpawn(rand()<.45?'runner':'walker',i,.72,{x:pod.x+(rand()-.5)*45,y:pod.y+(rand()-.5)*45});pod.spawnAt=now+3600+rand()*1200}
  if(state.pods.every(p=>p.dead)&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector();return
 }
 if(i===2){
  state.sectorTime=Math.max(0,state.sectorTime-dt);
  if(state.sectorTime>0&&now>state.nextExtraSpawn){queueSpawn(rand()<.5?'runner':rand()<.75?'walker':'spitter',i,.65);state.nextExtraSpawn=now+900+rand()*500}
  if(state.sectorTime<=0&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector();return
 }
 if(i===3){
  const inZone=dist(player.x,player.y,defensePoint.x,defensePoint.y)<defensePoint.r;
  if(inZone)state.defenseProgress=Math.min(22,state.defenseProgress+dt);else state.defenseProgress=Math.max(0,state.defenseProgress-dt*.18);
  if(state.defenseProgress<22&&now>state.nextExtraSpawn){queueSpawn(rand()<.2?'spitter':rand()<.55?'runner':'walker',i,.7);state.nextExtraSpawn=now+1050+rand()*550}
  if(state.defenseProgress>=22&&!state.spawnQueue.length&&!state.telegraphs.length&&!state.enemies.length)completeSector();return
 }
 if(i===4){
  for(const b of state.breakers)if(!b.active){if(dist(player.x,player.y,b.x,b.y)<48)b.progress+=dt;else b.progress=Math.max(0,b.progress-dt*.4);if(b.progress>=1.15){b.active=true;tone(680,.15,'square',.15);particles(b.x,b.y,16,'#ffbf65');setCaption('Рубильник активирован.',1.4)}}
  if(!state.breakers.every(b=>b.active)&&now>state.nextExtraSpawn){queueSpawn(rand()<.18?'brute':rand()<.48?'spitter':'walker',i,.72);state.nextExtraSpawn=now+1100+rand()*600}
