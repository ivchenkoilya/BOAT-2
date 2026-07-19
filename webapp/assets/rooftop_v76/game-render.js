function drawBackground(t){
  ctx.fillStyle='#07030d';ctx.fillRect(0,0,W,H);const sway=Math.sin(t*.00017)*4;
  if(assets.track){ctx.save();ctx.translate(sway,0);coverImage(assets.track,-5,-4,W+10,H+8,1.015+Math.sin(t*.0003)*.004);ctx.restore()}
  else{const g=ctx.createLinearGradient(0,0,0,H);g.addColorStop(0,'#2d1550');g.addColorStop(.45,'#10091d');g.addColorStop(1,'#030107');ctx.fillStyle=g;ctx.fillRect(0,0,W,H)}
  if(assets.city_far){ctx.save();ctx.globalAlpha=.13;ctx.globalCompositeOperation='screen';coverImage(assets.city_far,-8+Math.sin(t*.00008)*8,-18,W+16,H*.68,1.08);ctx.restore()}
  if(assets.city_near){ctx.save();ctx.globalAlpha=.08;ctx.globalCompositeOperation='screen';coverImage(assets.city_near,-10-Math.sin(t*.00011)*10,H*.05,W+20,H*.76,1.12);ctx.restore()}
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'rgba(6,2,14,.12)');shade.addColorStop(.52,'rgba(3,1,8,.02)');shade.addColorStop(1,'rgba(1,0,4,.38)');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  for(let i=0;i<14;i++){const z=((i/14)+(distance*.011)%1)%1,y=objectY(z),x=laneX((i%3),z),spread=9+z*32;ctx.strokeStyle=`rgba(190,112,255,${.03+z*.12})`;ctx.lineWidth=1+z*1.8;ctx.beginPath();ctx.moveTo(x,y-spread);ctx.lineTo(x,y+spread);ctx.stroke()}
  ctx.save();ctx.strokeStyle='rgba(190,150,255,.22)';ctx.lineWidth=1;for(const r of rain){ctx.globalAlpha=r.a;ctx.beginPath();ctx.moveTo(r.x,r.y);ctx.lineTo(r.x-3,r.y+r.l);ctx.stroke()}ctx.restore();
}
function drawBoss(t){
  if(!assets.boss)return;const pulse=1+Math.sin(t*.0022)*.025+bossPulse*.12,auraSize=Math.min(W*.63,H*.32)*pulse,bossW=Math.min(W*.42,H*.24)*pulse,cx=W/2,cy=H*.18;
  if(assets.aura){ctx.save();ctx.translate(cx,cy);ctx.rotate(t*.00018);ctx.globalAlpha=.52+bossPulse*.25;ctx.globalCompositeOperation='screen';ctx.drawImage(assets.aura,-auraSize/2,-auraSize/2,auraSize,auraSize);ctx.restore()}
  const ratio=assets.boss.height/assets.boss.width,bh=bossW*ratio;ctx.save();ctx.globalAlpha=.82;ctx.shadowColor='#a445ff';ctx.shadowBlur=18+bossPulse*25;ctx.drawImage(assets.boss,cx-bossW/2,cy-bh*.42,bossW,bh);ctx.restore();
  if(bossPulse>0){ctx.save();ctx.globalAlpha=bossPulse*.65;ctx.strokeStyle='#db8cff';ctx.lineWidth=2;ctx.beginPath();ctx.arc(cx,cy,auraSize*(.38+(.9-bossPulse)*.35),0,Math.PI*2);ctx.stroke();ctx.restore()}
}
function drawObject(o){
  const z=Math.max(0,o.z),x=laneX(o.lane,z),y=objectY(z),s=objectScale(z);ctx.save();ctx.translate(x,y);
  if(o.type==='orb'&&assets.crystal){const h=42*s,w=h*(assets.crystal.width/assets.crystal.height);ctx.globalAlpha=.94;ctx.shadowColor='#b755ff';ctx.shadowBlur=18*s;ctx.rotate(Math.sin(o.phase)*.09);ctx.drawImage(assets.crystal,-w/2,-h/2,w,h)}
  else if(o.type==='gold'){const r=12*s;ctx.shadowColor='#ffd45f';ctx.shadowBlur=18*s;ctx.fillStyle='#ffcc46';ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.47:r,px=Math.cos(a)*rr,py=Math.sin(a)*rr;i?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath();ctx.fill();ctx.fillStyle='#fff1a1';ctx.beginPath();ctx.arc(0,0,r*.28,0,Math.PI*2);ctx.fill()}
  else if(o.type==='barrier'&&assets.barrier){const w=125*s,h=w*(assets.barrier.height/assets.barrier.width);ctx.shadowColor='#9a44ff';ctx.shadowBlur=15*s;ctx.drawImage(assets.barrier,-w/2,-h*.82,w,h)}
  else if(o.type==='drone'&&assets.drone){const w=96*s,h=w*(assets.drone.height/assets.drone.width);ctx.translate(0,Math.sin(o.phase)*4*s-26*s);ctx.shadowColor='#c756ff';ctx.shadowBlur=18*s;ctx.drawImage(assets.drone,-w/2,-h/2,w,h)}
  else if(o.type==='power'){
    if(o.kind==='magnet'&&assets.magnet){const h=55*s,w=h*(assets.magnet.width/assets.magnet.height);ctx.shadowColor='#e69cff';ctx.shadowBlur=20*s;ctx.drawImage(assets.magnet,-w/2,-h/2,w,h)}
    else{const r=20*s;ctx.fillStyle=o.kind==='shield'?'#75dfff':'#ffd86a';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=20*s;ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.fillStyle='#25123d';ctx.font=`900 ${22*s}px system-ui`;ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(o.kind==='shield'?'◆':'⚡',0,1)}
  }else if(o.type==='vent'){const r=28*s;ctx.fillStyle='#15101d';ctx.strokeStyle='#8d51d0';ctx.lineWidth=4*s;ctx.shadowColor='#853be0';ctx.shadowBlur=12*s;ctx.beginPath();ctx.ellipse(0,0,r,r*.5,0,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.strokeStyle='#d1a2ff';ctx.lineWidth=2*s;for(let i=0;i<6;i++){ctx.rotate(Math.PI/3);ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(r*.75,0);ctx.stroke()}}
  else if(o.type==='wave'){const w=92*s,h=42*s,g=ctx.createLinearGradient(-w/2,0,w/2,0);g.addColorStop(0,'rgba(129,37,227,.1)');g.addColorStop(.5,'rgba(233,116,255,.88)');g.addColorStop(1,'rgba(129,37,227,.1)');ctx.fillStyle=g;ctx.shadowColor='#dc60ff';ctx.shadowBlur=22*s;ctx.fillRect(-w/2,-h/2,w,h);ctx.strokeStyle='#ffd4ff';ctx.lineWidth=2*s;ctx.strokeRect(-w/2,-h/2,w,h)}
  ctx.restore();
}
function drawHero(t){
  const x=laneX(laneVisual,1),baseY=H*.84,jumpProgress=jump>0?1-jump/.78:0,jumpHeight=jump>0?Math.sin(jumpProgress*Math.PI)*H*.18:0,sliding=slide>0,heroH=Math.min(168,H*.225)*(sliding?.58:1),heroW=assets.hero?heroH*(assets.hero.width/assets.hero.height):70,y=baseY-jumpHeight;
  ctx.save();ctx.globalAlpha=.55;ctx.fillStyle='#0a0411';ctx.shadowColor=shield?'#8de7ff':'#9d4bff';ctx.shadowBlur=shield?25:14;ctx.beginPath();ctx.ellipse(x,baseY+5,heroW*.32,9*(sliding?1.4:1),0,0,Math.PI*2);ctx.fill();ctx.restore();
  if(magnet>0){ctx.save();ctx.globalAlpha=.26+.08*Math.sin(t*.008);ctx.strokeStyle='#d197ff';ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(x,y-heroH*.42,heroH*(.45+i*.09),0,Math.PI*2);ctx.stroke()}ctx.restore()}
  if(shield){ctx.save();ctx.globalAlpha=.48+.12*Math.sin(t*.01);ctx.strokeStyle='#8be7ff';ctx.lineWidth=3;ctx.shadowColor='#72dfff';ctx.shadowBlur=20;ctx.beginPath();ctx.ellipse(x,y-heroH*.42,heroW*.62,heroH*.6,0,0,Math.PI*2);ctx.stroke();ctx.restore()}
  if(assets.hero){ctx.save();ctx.translate(x,y);const tilt=(lane-laneVisual)*-.22+Math.sin(t*.009)*.008;ctx.rotate(tilt);ctx.shadowColor='#9e4eff';ctx.shadowBlur=18;const bob=running&&!sliding&&jump<=0?Math.sin(t*.015)*2:0;ctx.drawImage(assets.hero,-heroW/2,-heroH+bob,heroW,heroH);ctx.restore()}
  else{ctx.fillStyle='#8b50df';ctx.fillRect(x-23,y-75,46,75)}
  if(running&&!sliding){ctx.save();ctx.globalCompositeOperation='screen';const g=ctx.createLinearGradient(x,y-15,x,baseY+60);g.addColorStop(0,'rgba(153,68,255,.28)');g.addColorStop(1,'rgba(153,68,255,0)');ctx.fillStyle=g;ctx.beginPath();ctx.moveTo(x-16,y-12);ctx.lineTo(x+16,y-12);ctx.lineTo(x+34,baseY+68);ctx.lineTo(x-34,baseY+68);ctx.closePath();ctx.fill();ctx.restore()}
}
function drawEffects(){
  for(const p of particles){ctx.save();ctx.globalAlpha=Math.max(0,p.t);ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=10;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();ctx.restore()}
  for(const f of floating){ctx.save();ctx.globalAlpha=Math.max(0,f.t);ctx.fillStyle=f.color;ctx.shadowColor='#000';ctx.shadowBlur=5;ctx.font='900 13px system-ui';ctx.textAlign='center';ctx.fillText(f.text,f.x,f.y);ctx.restore()}
  if(flash>0){ctx.save();ctx.globalAlpha=flash;ctx.fillStyle=hits?'#ff497a':'#d47aff';ctx.fillRect(0,0,W,H);ctx.restore()}
}
function draw(t){ctx.save();if(shake>0)ctx.translate((rng()-.5)*shake,(rng()-.5)*shake);drawBackground(t);drawBoss(t);for(const o of [...objects].sort((a,b)=>a.z-b.z))drawObject(o);drawHero(t);drawEffects();ctx.restore()}
function drawIdle(){if(!W||!H)return;drawBackground(performance.now());drawBoss(performance.now());drawHero(performance.now())}
function loop(now){if(!running)return;const dt=Math.min(.034,Math.max(.001,(now-lastFrame)/1000));lastFrame=now;update(dt);draw(now);if(running)requestAnimationFrame(loop)}
function formatTime(value){const seconds=Math.max(0,Math.ceil(value));return String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0')}
async function finishGame(reason){
  if(ended)return;ended=true;running=false;$('resultTitle').textContent=reason;$('resultScore').textContent=score;$('resultCombo').textContent=bestCombo;$('resultDistance').textContent=Math.round(distance)+' м';$('resultHits').textContent=hits;
  $('finish').classList.remove('hidden');$('result').style.display='block';$('reward').textContent=demo?'Демонстрационный режим: влияние не начисляется.':'Сохраняем результат на сервере…';
  if(sessionId&&!demo){
    try{const data=await api('finish',{session_id:sessionId,score,stats:{distance:Math.round(distance),best_combo:bestCombo,hits,lives_left:lives}});$('reward').innerHTML=`Базовая награда забега: <b>+${data.base_run_reward||0}</b><br>Начисляется за улучшение: <b>+${data.payable_base||0}</b><br>🌳 Бонус древа: <b>+${data.tree_bonus||0}</b><br>🏆 Получено влияния: <b>+${data.actual_reward||0}</b><br>Баланс: <b>${data.balance||0}</b><br><small>${data.message||''}</small>`}
    catch(error){$('reward').textContent='Не удалось сохранить результат: '+error.message}
  }
}
function goGames(){location.href='/games/?chat_id='+encodeURIComponent(chatId)}
$('start').onclick=startGame;
$('again').onclick=()=>{if(demo){$('finish').classList.add('hidden');$('result').style.display='none';startGame()}else{location.reload()}};
$('back').onclick=goGames;$('toGames').onclick=goGames;$('left').onclick=()=>move(-1);$('right').onclick=()=>move(1);$('ability').onclick=useAbility;
const stage=$('stage');
stage.addEventListener('pointerdown',event=>{touchStart={x:event.clientX,y:event.clientY,t:performance.now()};stage.setPointerCapture?.(event.pointerId)});
stage.addEventListener('pointerup',event=>{if(!touchStart)return;const dx=event.clientX-touchStart.x,dy=event.clientY-touchStart.y,ax=Math.abs(dx),ay=Math.abs(dy);touchStart=null;if(Math.max(ax,ay)<24){useAbility();return}if(ax>ay)move(dx>0?1:-1);else if(dy<0)doJump();else doSlide()});
document.addEventListener('keydown',event=>{if(event.key==='ArrowLeft')move(-1);if(event.key==='ArrowRight')move(1);if(event.key==='ArrowUp')doJump();if(event.key==='ArrowDown')doSlide();if(event.code==='Space')useAbility()});
