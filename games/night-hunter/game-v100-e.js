  if(cleared===3&&player.weapon!=='shotgun')pool[1]={t:'Дробовик',d:'7 дробин по лучу, высокий урон',weapon:'shotgun',f:()=>setWeapon('shotgun')}
 }
 const grid=$('upgradeGrid');grid.innerHTML='';
 for(const u of pool){const b=document.createElement('button');b.className='upgradeChoice'+(u.weapon?' weapon':'');b.innerHTML=`<b>${u.weapon?(u.weapon==='smg'?'▰ ':'▱ '):'✦ '}${u.t}</b><small>${u.d}</small>`;b.onclick=()=>{u.f();state.paused=false;$('upgrade').classList.add('hidden');$('grenades').textContent=player.grenades;setCaption('Следующий сектор разблокирован.',2)};grid.appendChild(b)}
 $('upgrade').classList.remove('hidden')
}
function currentObjectiveText(){
 const i=state.activeRoom;
 if(i<0)return state.roomsCleared<6?'ИДИ В СЕКТОР '+(state.roomsCleared+1)+'/6':'КОМПЛЕКС ЗАЧИЩЕН';
 if(i===0)return'ЗАРАЖЁННЫЕ: '+(state.enemies.length+state.telegraphs.length+state.spawnQueue.length);
 if(i===1)return'КАПСУЛЫ: '+state.pods.filter(p=>!p.dead).length+' · ВРАГИ: '+state.enemies.length;
 if(i===2)return'ПЕРЕЖИВИ: '+Math.max(0,Math.ceil(state.sectorTime))+' С';
 if(i===3)return'УДЕРЖАНИЕ: '+Math.min(100,Math.round(state.defenseProgress/22*100))+'%';
 if(i===4)return'РУБИЛЬНИКИ: '+state.breakers.filter(b=>b.active).length+'/3';
 return'БОСС И ЗАРАЖЁННЫЕ: '+state.enemies.length
}
function updateDirection(){
 const el=$('direction');if(state.activeRoom>=0||state.roomsCleared>=6){el.classList.add('hidden');return}
 const target=sectorCenters[state.roomsCleared],dx=target.x-player.x,dy=target.y-player.y,d=Math.hypot(dx,dy);
 el.classList.remove('hidden');el.style.setProperty('--angle',Math.atan2(dy,dx)*180/Math.PI+'deg');el.querySelector('b').textContent='СЕКТОР '+(state.roomsCleared+1);$('directionDistance').textContent=Math.round(d/10)+' м'
}
function updateHud(now){
 const ri=roomAt(player.x,player.y),w=weapon();$('roomName').textContent=ri>=0?rooms[ri].name:'СЛУЖЕБНЫЙ КОРИДОР';$('score').textContent=Math.round(state.score);$('timer').textContent=fmtTime(state.time);$('objective').textContent=currentObjectiveText();
 $('hpText').textContent=Math.ceil(player.hp)+'/'+Math.ceil(player.maxHp);$('hpBar').style.width=clamp(player.hp/player.maxHp*100,0,100)+'%';
 $('weaponName').textContent=w.name;$('weaponIcon').textContent=w.icon;$('ammoText').textContent=player.mag+' / '+player.reserve;$('ammoBar').style.width=clamp(player.mag/w.mag*100,0,100)+'%';
 $('streak').textContent='СЕРИЯ ×'+state.combo;$('streak').classList.toggle('hot',state.combo>=4);$('grenades').textContent=player.grenades;
 const dashLeft=Math.max(0,player.dashReadyAt-now);$('dashText').textContent=dashLeft>0?(dashLeft/1000).toFixed(1):'РЫВОК';$('dash').classList.toggle('cooldown',dashLeft>0);
 const boss=state.enemies.find(e=>e.type==='boss');if(boss){$('bossHud').classList.remove('hidden');$('bossBar').style.width=clamp(boss.hp/boss.maxHp*100,0,100)+'%'}else $('bossHud').classList.add('hidden');
 if(now>state.messageUntil)$('caption').textContent=state.activeRoom>=0?'Стреляй по лучу и не стой на месте.':'Следующая дверь разблокирована.';
 updateDirection()
}

function drawCorridor(c,now){
 ctx.fillStyle='#12242a';ctx.fillRect(c.x,c.y,c.w,c.h);ctx.strokeStyle='#40616a';ctx.lineWidth=4;ctx.strokeRect(c.x,c.y,c.w,c.h);
 ctx.save();ctx.beginPath();ctx.rect(c.x,c.y,c.w,c.h);ctx.clip();ctx.strokeStyle='#a7fff010';ctx.lineWidth=1;
 if(c.dir==='h'){for(let x=c.x+12;x<c.x+c.w;x+=22){ctx.beginPath();ctx.moveTo(x,c.y);ctx.lineTo(x,c.y+c.h);ctx.stroke()}}
 else{for(let y=c.y+12;y<c.y+c.h;y+=22){ctx.beginPath();ctx.moveTo(c.x,y);ctx.lineTo(c.x+c.w,y);ctx.stroke()}}
 ctx.fillStyle='#ffc96518';const pulse=(Math.sin(now/240)+1)/2;if(c.dir==='h'){ctx.fillRect(c.x,c.y+8,c.w,5);ctx.fillRect(c.x,c.y+c.h-13,c.w,5)}else{ctx.fillRect(c.x+8,c.y,5,c.h);ctx.fillRect(c.x+c.w-13,c.y,5,c.h)}
 ctx.fillStyle=`rgba(255,210,100,${.12+pulse*.12})`;ctx.font='800 12px system-ui';ctx.textAlign='center';ctx.fillText(c.label,c.x+c.w/2,c.y+c.h/2+4);ctx.restore()
}
function drawRoom(r,i,now){
 const grad=ctx.createLinearGradient(r.x,r.y,r.x,r.y+r.h);grad.addColorStop(0,r.color);grad.addColorStop(1,'#071014');ctx.fillStyle=grad;ctx.fillRect(r.x,r.y,r.w,r.h);
 ctx.strokeStyle=r.accent+'66';ctx.lineWidth=5;ctx.strokeRect(r.x,r.y,r.w,r.h);ctx.strokeStyle='#bafff00c';ctx.lineWidth=1;
 for(let x=r.x+18;x<r.x+r.w;x+=34){ctx.beginPath();ctx.moveTo(x,r.y);ctx.lineTo(x,r.y+r.h);ctx.stroke()}
 for(let y=r.y+18;y<r.y+r.h;y+=34){ctx.beginPath();ctx.moveTo(r.x,y);ctx.lineTo(r.x+r.w,y);ctx.stroke()}
 ctx.fillStyle=r.accent+'12';ctx.font='900 28px system-ui';ctx.textAlign='center';ctx.fillText(r.name,r.x+r.w/2,r.y+r.h-24);
 drawDecor(r,i,now)
}
function box3d(x,y,w,h,top='#17272b',side='#091014',edge='#4d6c72'){
 ctx.fillStyle=side;ctx.fillRect(x+7,y+8,w,h);ctx.fillStyle=top;ctx.fillRect(x,y,w,h);ctx.strokeStyle=edge;ctx.lineWidth=2;ctx.strokeRect(x,y,w,h)
}
function drawDecor(r,i,now){
 ctx.save();
 if(i===0){
  for(let k=0;k<4;k++){box3d(r.x+42+k*94,r.y+48,76,58,'#0a181c','#03080a','#315158');ctx.fillStyle=k%2?r.accent+'55':'#305a5d';ctx.fillRect(r.x+50+k*94,r.y+56,60,28);ctx.fillStyle='#8affef18';ctx.fillRect(r.x+54+k*94,r.y+60,24,3)}
  box3d(r.x+90,r.y+248,250,38,'#112328','#071014','#29494f');ctx.fillStyle='#d7fff122';ctx.fillRect(r.x+150,r.y+257,55,7)
 }else if(i===1){
  for(const q of podTemplate){ctx.strokeStyle='#9ab0ff77';ctx.lineWidth=5;ctx.beginPath();ctx.ellipse(q.x,q.y,37,72,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#6c83ff17';ctx.fill()}
  for(let k=0;k<3;k++)box3d(r.x+40+k*145,r.y+295,105,24,'#11182b','#080b14','#485482')
 }else if(i===2){
  for(let k=0;k<4;k++){box3d(r.x+42+k*102,r.y+48,75,230,'#211b10','#0d0a06','#8b7040');for(let s=0;s<5;s++){ctx.fillStyle=s%2?'#b58b4130':'#d7bb6b22';ctx.fillRect(r.x+49+k*102,r.y+65+s*39,61,13)}}
 }else if(i===3){
  for(let k=0;k<2;k++){box3d(r.x+62,r.y+66+k*150,250,58,'#15312c','#07110f','#5a8d83');ctx.fillStyle='#d8fff022';ctx.fillRect(r.x+82,r.y+78+k*150,160,34);ctx.fillStyle='#8ffff02a';ctx.fillRect(r.x+325,r.y+66+k*150,24,58)}
  ctx.strokeStyle='#83ffe955';ctx.setLineDash([6,6]);ctx.beginPath();ctx.arc(defensePoint.x,defensePoint.y,defensePoint.r,0,Math.PI*2);ctx.stroke();ctx.setLineDash([])
 }else if(i===4){
  box3d(r.x+110,r.y+75,250,145,'#36230d','#160d05','#a66a2d');for(let k=0;k<3;k++){ctx.fillStyle='#ffb75d'+(Math.sin(now/190+k)>0?'55':'20');ctx.beginPath();ctx.arc(r.x+160+k*72,r.y+145,16,0,Math.PI*2);ctx.fill()}
  ctx.strokeStyle='#ffb75d30';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(r.x+40,r.y+285);ctx.bezierCurveTo(r.x+150,r.y+230,r.x+280,r.y+335,r.x+420,r.y+270);ctx.stroke()
 }else{
  box3d(r.x+76,r.y+72,315,142,'#17282d','#081014','#72929a');ctx.fillStyle='#86ffe530';ctx.fillRect(r.x+205,r.y+230,55,70);ctx.fillStyle='#ff3f5c22';ctx.fillRect(r.x+96,r.y+90,275,8)
