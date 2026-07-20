/* Reality 105: independent multitouch actions, darker flashlight gameplay and readable markers. */
const V105={version:'Reality 105 · Night Combat'};

/* Replace the decorative red editor-like circle in the security room with a real ventilation hatch. */
const v105SecurityBase=v101DrawSecurityRoom;
v101DrawSecurityRoom=function(r,now){
 v105SecurityBase(r,now);
 const x=r.x+18,y=r.y+r.h-112,w=105,h=92;
 ctx.save();
 const floor=ctx.createLinearGradient(x,y,x+w,y+h);floor.addColorStop(0,'#0d2429');floor.addColorStop(1,'#061317');ctx.fillStyle=floor;ctx.fillRect(x,y,w,h);
 ctx.strokeStyle='#74ffe714';ctx.lineWidth=1;for(let gx=x+8;gx<x+w;gx+=24){ctx.beginPath();ctx.moveTo(gx,y);ctx.lineTo(gx,y+h);ctx.stroke()}for(let gy=y+8;gy<y+h;gy+=24){ctx.beginPath();ctx.moveTo(x,gy);ctx.lineTo(x+w,gy);ctx.stroke()}
 ctx.fillStyle='#071014';ctx.strokeStyle='#46656b';ctx.lineWidth=3;ctx.beginPath();ctx.roundRect(x+22,y+20,62,48,8);ctx.fill();ctx.stroke();
 ctx.strokeStyle='#78909666';ctx.lineWidth=2;for(let i=0;i<5;i++){ctx.beginPath();ctx.moveTo(x+31,y+29+i*8);ctx.lineTo(x+75,y+29+i*8);ctx.stroke()}
 ctx.fillStyle='#769093';ctx.font='800 7px system-ui';ctx.textAlign='center';ctx.fillText('ВЕНТИЛЯЦИЯ',x+w/2,y+84);ctx.restore();
};

/* Current objectives use a compact diamond and a clear label instead of an unexplained yellow circle. */
v104DrawMarker=function(point,now,label){
 if(!point)return;const pulse=(Math.sin(now/160)+1)/2,txt=label||point.label||'ЦЕЛЬ';
 ctx.save();ctx.translate(point.x,point.y);
 ctx.shadowColor='#ffd36d';ctx.shadowBlur=12+pulse*8;ctx.fillStyle='#ffd36d';ctx.rotate(Math.PI/4);ctx.fillRect(-8,-8,16,16);ctx.rotate(-Math.PI/4);ctx.shadowBlur=0;
 ctx.strokeStyle=`rgba(255,220,126,${.55+pulse*.35})`;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(0,-20-pulse*4);ctx.lineTo(-7,-31-pulse*4);ctx.lineTo(7,-31-pulse*4);ctx.closePath();ctx.stroke();
 ctx.font='900 8px system-ui';const tw=Math.max(54,ctx.measureText(txt).width+18);ctx.fillStyle='rgba(20,15,5,.9)';ctx.strokeStyle='#ffd36d99';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(-tw/2,-52,tw,18,9);ctx.fill();ctx.stroke();ctx.fillStyle='#ffe6a6';ctx.textAlign='center';ctx.fillText(txt,0,-40);ctx.restore();
};

/* Telegraphs now explain themselves and disappear when the enemy appears. */
const v105TelegraphsBase=drawTelegraphs;
drawTelegraphs=function(now){
 v105TelegraphsBase(now);
 for(const t of state.telegraphs){const left=Math.max(0,t.time),pulse=(Math.sin(now/85)+1)/2;ctx.save();ctx.translate(t.x,t.y);ctx.fillStyle='rgba(35,3,9,.88)';ctx.strokeStyle=`rgba(255,68,92,${.65+pulse*.3})`;ctx.lineWidth=2;ctx.beginPath();ctx.roundRect(-31,-44,62,17,8);ctx.fill();ctx.stroke();ctx.fillStyle='#ffb3bd';ctx.font='900 7px system-ui';ctx.textAlign='center';ctx.fillText('УГРОЗА '+left.toFixed(1),0,-33);ctx.restore()}
};

/* Strong darkness outside the flashlight, with only small local emergency lights. */
drawLight=function(now){
 lctx.setTransform(dpr,0,0,dpr,0,0);lctx.clearRect(0,0,vw,vh);lctx.fillStyle='rgba(0,0,0,.66)';lctx.fillRect(0,0,vw,vh);
 const px=player.x-camera.x,py=player.y-camera.y,ang=aimAngle()+player.recoil*.0015*Math.sin(now/22);
 lctx.globalCompositeOperation='destination-out';
 const local=[
  {x:140,y:85,r:52,a:.24},{x:375,y:85,r:52,a:.2},{x:855,y:155,r:66,a:.2},
  {x:1430,y:770,r:58,a:.17},{x:855,y:770,r:62,a:.18},{x:280,y:770,r:54,a:.15}
 ];
 for(const q of local){const sx=q.x-camera.x,sy=q.y-camera.y;if(sx<-q.r||sy<-q.r||sx>vw+q.r||sy>vh+q.r)continue;const g=lctx.createRadialGradient(sx,sy,2,sx,sy,q.r);g.addColorStop(0,`rgba(0,0,0,${q.a})`);g.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=g;lctx.beginPath();lctx.arc(sx,sy,q.r,0,Math.PI*2);lctx.fill()}
 const ambient=lctx.createRadialGradient(px,py,6,px,py,88);ambient.addColorStop(0,'rgba(0,0,0,.78)');ambient.addColorStop(.5,'rgba(0,0,0,.28)');ambient.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=ambient;lctx.beginPath();lctx.arc(px,py,88,0,Math.PI*2);lctx.fill();
 lctx.save();lctx.translate(px,py);lctx.rotate(ang);const beam=lctx.createLinearGradient(0,0,585,0);beam.addColorStop(0,'rgba(0,0,0,1)');beam.addColorStop(.48,'rgba(0,0,0,.96)');beam.addColorStop(.8,'rgba(0,0,0,.64)');beam.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=beam;lctx.beginPath();lctx.moveTo(0,-13);lctx.quadraticCurveTo(260,-68,585,-118);lctx.lineTo(585,118);lctx.quadraticCurveTo(260,68,0,13);lctx.closePath();lctx.fill();
 if(player.muzzle>0){const flash=lctx.createRadialGradient(30,0,2,30,0,120);flash.addColorStop(0,'rgba(0,0,0,.9)');flash.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=flash;lctx.beginPath();lctx.arc(30,0,120,0,Math.PI*2);lctx.fill()}lctx.restore();
 lctx.globalCompositeOperation='source-over';ctx.drawImage(light,0,0,vw,vh);
 ctx.save();ctx.translate(px,py);ctx.rotate(ang);const glow=ctx.createLinearGradient(18,0,360,0);glow.addColorStop(0,'rgba(205,255,248,.12)');glow.addColorStop(.65,'rgba(160,235,228,.045)');glow.addColorStop(1,'rgba(205,255,248,0)');ctx.fillStyle=glow;ctx.beginPath();ctx.moveTo(18,-8);ctx.lineTo(360,-54);ctx.lineTo(360,54);ctx.lineTo(18,8);ctx.closePath();ctx.fill();ctx.restore();
};

/* Independent pointer handlers: movement keeps running while reloading, dashing or throwing. */
function v105BindAction(id,action){
 const el=$(id);if(!el)return;el.onclick=null;
 const down=e=>{if(e.pointerType==='mouse'&&e.button!==0)return;e.preventDefault();e.stopPropagation();el.classList.add('pressed');action()};
 const up=e=>{e.preventDefault();e.stopPropagation();el.classList.remove('pressed')};
 el.addEventListener('pointerdown',down,{passive:false});el.addEventListener('pointerup',up,{passive:false});el.addEventListener('pointercancel',up,{passive:false});el.addEventListener('contextmenu',e=>e.preventDefault());
}
v105BindAction('reload',reload);v105BindAction('grenade',throwGrenade);v105BindAction('dash',doDash);

/* Shorter labels and clear action identity. */
const v105Reload=$('reload'),v105Grenade=$('grenade'),v105Dash=$('dash'),v105Fire=$('fire');
if(v105Reload)v105Reload.innerHTML='<span>↻</span><b>МАГАЗИН</b><small>ПЕРЕЗАРЯДКА</small>';
if(v105Grenade)v105Grenade.innerHTML='<span>●</span><b id="grenades">'+player.grenades+'</b><small>ГРАНАТА</small>';
if(v105Dash)v105Dash.innerHTML='<span>➤</span><b id="dashText">РЫВОК</b><small>УКЛОНЕНИЕ</small>';
if(v105Fire)v105Fire.innerHTML='<span>✹</span><b>ОГОНЬ</b><small>ВЕДИ ПАЛЬЦЕМ</small>';

const v105HudBase=updateHud;
updateHud=function(now){
 v105HudBase(now);
 const dashPct=player.dashReadyAt<=now?1:clamp(1-(player.dashReadyAt-now)/4000,0,1);
 const reloadPct=player.reloading?clamp(1-(player.reloadEnd-now)/(player.weapon==='shotgun'?1450:1100),0,1):1;
 if(v105Dash){v105Dash.style.setProperty('--cool-angle',dashPct.toFixed(3)+'turn');v105Dash.classList.toggle('cooldown',dashPct<.999)}
 if(v105Reload){v105Reload.style.setProperty('--cool-angle',reloadPct.toFixed(3)+'turn');v105Reload.classList.toggle('cooldown',player.reloading)}
 if(v105Grenade){v105Grenade.style.setProperty('--cool-angle',(player.grenades>0?'1turn':'0turn'));v105Grenade.classList.toggle('cooldown',player.grenades<=0)}
};
