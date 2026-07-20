 }
 ctx.restore()
}
function drawDoors(){
 for(const d of doors){const closed=doorClosed(d);ctx.fillStyle=closed?'#291016':'#102428';ctx.strokeStyle=closed?'#ff4c6377':'#75ffe555';ctx.lineWidth=3;ctx.fillRect(d.x,d.y,d.w,d.h);ctx.strokeRect(d.x,d.y,d.w,d.h);if(closed){ctx.fillStyle='#ff4868';ctx.beginPath();ctx.arc(d.x+d.w/2,d.y+d.h/2,5,0,Math.PI*2);ctx.fill()}}
}
function drawObjectives(now){
 if(state.activeRoom===1)for(const pod of state.pods){if(pod.dead)continue;const p=pod.hp/pod.maxHp;ctx.strokeStyle='#aebcff';ctx.lineWidth=5;ctx.beginPath();ctx.ellipse(pod.x,pod.y,34,68,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#8c9fff22';ctx.fill();ctx.fillStyle='#111827';ctx.fillRect(pod.x-31,pod.y-84,62,6);ctx.fillStyle='#859cff';ctx.fillRect(pod.x-31,pod.y-84,62*p,6)}
 if(state.activeRoom===3){const pct=clamp(state.defenseProgress/22,0,1);ctx.strokeStyle='#75ffe5';ctx.lineWidth=6;ctx.beginPath();ctx.arc(defensePoint.x,defensePoint.y,defensePoint.r,-Math.PI/2,-Math.PI/2+Math.PI*2*pct);ctx.stroke();ctx.fillStyle='#75ffe518';ctx.beginPath();ctx.arc(defensePoint.x,defensePoint.y,42,0,Math.PI*2);ctx.fill();ctx.fillStyle='#d9fff3';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText(Math.round(pct*100)+'%',defensePoint.x,defensePoint.y+4)}
 if(state.activeRoom===4)for(const b of state.breakers){ctx.fillStyle=b.active?'#75ffe5':'#3d2914';ctx.strokeStyle=b.active?'#bafff3':'#ffbf65';ctx.lineWidth=3;ctx.fillRect(b.x-17,b.y-24,34,48);ctx.strokeRect(b.x-17,b.y-24,34,48);if(!b.active&&b.progress>0){ctx.strokeStyle='#ffcf74';ctx.lineWidth=5;ctx.beginPath();ctx.arc(b.x,b.y,29,-Math.PI/2,-Math.PI/2+Math.PI*2*clamp(b.progress/1.15,0,1));ctx.stroke()}}
}
function drawTelegraphs(now){
 for(const t of state.telegraphs){const p=clamp(t.time/t.total,0,1),pulse=(Math.sin(now/65)+1)/2;ctx.strokeStyle=`rgba(255,61,88,${.45+pulse*.45})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(t.x,t.y,18+36*(1-p),0,Math.PI*2);ctx.stroke();ctx.fillStyle=`rgba(255,42,72,${.08+.14*(1-p)})`;ctx.beginPath();ctx.arc(t.x,t.y,24,0,Math.PI*2);ctx.fill();ctx.fillStyle='#ff5570';ctx.font='900 10px system-ui';ctx.textAlign='center';ctx.fillText('!',t.x,t.y+3)}
}
function drawCorpse(c){
 ctx.save();ctx.translate(c.x,c.y);ctx.rotate(c.angle||0);ctx.globalAlpha=clamp(c.life/2,0,.5);ctx.fillStyle=c.type==='spitter'?'#274329':'#35141c';ctx.beginPath();ctx.ellipse(0,0,c.r*1.25,c.r*.58,0,0,Math.PI*2);ctx.fill();ctx.restore()
}
function drawEnemy(e,now){
 ctx.save();ctx.translate(e.x,e.y);const hit=e.hit>0;ctx.shadowColor=hit?'#fff':'transparent';ctx.shadowBlur=hit?14:0;
 if(e.elite){ctx.strokeStyle='#c884ff88';ctx.lineWidth=3;ctx.beginPath();ctx.arc(0,0,e.r+8+Math.sin(now/120)*2,0,Math.PI*2);ctx.stroke()}
 if(e.type==='walker'){
  ctx.fillStyle=hit?'#fff':e.color;ctx.beginPath();ctx.ellipse(0,4,11,17,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(0,-13,8,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#6d7e80';ctx.lineWidth=5;ctx.beginPath();ctx.moveTo(-7,0);ctx.lineTo(-15,13);ctx.moveTo(7,0);ctx.lineTo(15,13);ctx.stroke()
 }else if(e.type==='runner'){
  ctx.strokeStyle=hit?'#fff':'#623145';ctx.lineWidth=5;for(let a=-1;a<=1;a+=2){ctx.beginPath();ctx.moveTo(a*5,0);ctx.lineTo(a*18,-13);ctx.moveTo(a*5,5);ctx.lineTo(a*20,16);ctx.stroke()}ctx.fillStyle=hit?'#fff':e.color;ctx.beginPath();ctx.ellipse(0,0,12,9,0,0,Math.PI*2);ctx.fill()
 }else if(e.type==='spitter'){
  ctx.fillStyle=hit?'#fff':'#355b35';ctx.beginPath();ctx.arc(0,3,15,0,Math.PI*2);ctx.fill();ctx.fillStyle='#91ff77';ctx.beginPath();ctx.arc(0,-7,7,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#68bf57';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(-12,10);ctx.lineTo(-18,18);ctx.moveTo(12,10);ctx.lineTo(18,18);ctx.stroke()
 }else if(e.type==='brute'){
  ctx.fillStyle=hit?'#fff':'#55313a';ctx.beginPath();ctx.moveTo(-23,-9);ctx.lineTo(-13,-22);ctx.lineTo(13,-22);ctx.lineTo(23,-9);ctx.lineTo(18,19);ctx.lineTo(-18,19);ctx.closePath();ctx.fill();ctx.fillStyle='#1b0d11';ctx.beginPath();ctx.arc(0,-20,10,0,Math.PI*2);ctx.fill()
 }else if(e.type==='elite'){
  ctx.fillStyle=hit?'#fff':'#4c365f';ctx.beginPath();ctx.ellipse(0,3,14,20,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#c884ff';ctx.lineWidth=4;ctx.beginPath();ctx.moveTo(-8,-5);ctx.lineTo(-20,-18);ctx.moveTo(8,-5);ctx.lineTo(20,-18);ctx.stroke()
 }else{
  ctx.fillStyle=hit?'#fff':'#260a10';ctx.beginPath();ctx.ellipse(0,8,31,43,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#6e1d2d';ctx.lineWidth=9;ctx.beginPath();ctx.moveTo(-20,-6);ctx.lineTo(-45,24);ctx.moveTo(20,-6);ctx.lineTo(45,24);ctx.stroke();ctx.fillStyle='#100205';ctx.beginPath();ctx.arc(0,-34,20,0,Math.PI*2);ctx.fill()
 }
 ctx.fillStyle='#ff334f';ctx.beginPath();ctx.arc(-4,-10,2.7,0,Math.PI*2);ctx.arc(4,-10,2.7,0,Math.PI*2);ctx.fill();
 const ratio=clamp(e.hp/e.maxHp,0,1);ctx.fillStyle='#2a1017';ctx.fillRect(-e.r,-e.r-15,e.r*2,5);ctx.fillStyle=e.type==='boss'?'#ff3558':'#e64d66';ctx.fillRect(-e.r,-e.r-15,e.r*2*ratio,5);
 if(e.telegraph&&e.type==='boss'){ctx.strokeStyle='#ff4b5f99';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(e.telegraph.dx*280,e.telegraph.dy*280);ctx.stroke()}
 ctx.restore()
}

function drawPlayer(now){
 ctx.save();ctx.translate(player.x,player.y);ctx.rotate(aimAngle());const bob=Math.sin(player.walk)*1.8;
 ctx.shadowColor='#75ffe555';ctx.shadowBlur=14;ctx.fillStyle='#071014';ctx.beginPath();ctx.ellipse(-5,5,19,13,0,0,Math.PI*2);ctx.fill();
 ctx.fillStyle=performance.now()<state.shieldUntil?'#9dc7ff':'#3ba88f';ctx.beginPath();ctx.roundRect(-13,-15+bob,28,31,9);ctx.fill();
 ctx.fillStyle='#f1b38f';ctx.beginPath();ctx.arc(1,-17+bob,10,0,Math.PI*2);ctx.fill();
 ctx.fillStyle='#0b1114';ctx.fillRect(-17,-9+bob,9,22);ctx.fillRect(-10,13+bob,7,13);ctx.fillRect(6,13+bob,7,13);
 ctx.fillStyle='#d7e2e0';ctx.fillRect(8,-5+bob,26,8);ctx.fillStyle='#657579';ctx.fillRect(27,-3+bob,13,7);
 if(player.muzzle>0){ctx.fillStyle='#fff7b0';ctx.beginPath();ctx.moveTo(40,0);ctx.lineTo(55,-9);ctx.lineTo(51,0);ctx.lineTo(55,9);ctx.closePath();ctx.fill();ctx.shadowColor='#ffbb4d';ctx.shadowBlur=25}
 ctx.restore()
}
function drawPickups(now){
 for(const p of state.pickups){const bob=Math.sin(now/160+p.x)*3;ctx.save();ctx.translate(p.x,p.y+bob);ctx.fillStyle=p.type==='ammo'?'#ffd06e':'#75ffc0';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=14;ctx.beginPath();ctx.arc(0,0,11,0,Math.PI*2);ctx.fill();ctx.fillStyle='#061014';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText(p.type==='ammo'?'▰':'+',0,4);ctx.restore()}
}
function drawEffects(){
 for(const b of state.bullets){ctx.strokeStyle=b.color;ctx.lineWidth=2.2;ctx.beginPath();ctx.moveTo(b.px,b.py);ctx.lineTo(b.x,b.y);ctx.stroke()}
