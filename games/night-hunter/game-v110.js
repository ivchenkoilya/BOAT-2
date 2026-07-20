(async()=>{
'use strict';
const error=document.getElementById('startError'),startButton=document.getElementById('start');
try{
 const [legacyLoader,engine]=await Promise.all([
  fetch('/games/night-hunter/game-v109.js?v=109',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('не загружена модель рабочего');return r.text()}),
  fetch('/games/night-hunter/game-v108.js?v=110',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('не загружен игровой движок');return r.text()})
 ]);
 const spriteMatch=legacyLoader.match(/hero\.src='(data:image\/webp;base64,[^']+)'/);
 if(!spriteMatch)throw new Error('не найден спрайт рабочего');
 const hero=new Image();hero.decoding='async';hero.src=spriteMatch[1];try{await hero.decode()}catch(_){}window.__NH_HERO_SPRITE=hero;
 let source=engine;
 const swap=(start,end,body)=>{const a=source.indexOf(start),b=source.indexOf(end,a);if(a<0||b<0)throw new Error('не найден визуальный блок: '+start);source=source.slice(0,a)+body+source.slice(b)};
 source=source.replace("function setTask(clock,objective,location,caption){state.clock=clock;state.objective=objective;if(location)$('location').textContent=location;if(caption)showCaption(caption,4)}",`function setTask(clock,objective,location,caption){
  state.clock=clock;state.objective=objective;if(location)$('location').textContent=location;
  const detail=$('objectiveDetail');if(detail)detail.textContent=caption||'';
  if(caption)showCaption(caption,4)
 }`);
 const helpers=`
const v110Puddles=[{x:180,y:330,rx:82,ry:20},{x:510,y:565,rx:68,ry:17},{x:765,y:360,rx:52,ry:14}];
function v110RoundRect(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.stroke()}}
function v110Lamp(x,y,on=true,warm=false){ctx.save();ctx.translate(x,y);ctx.fillStyle='#11191b';ctx.fillRect(-10,-5,20,10);if(on){const g=ctx.createRadialGradient(0,5,2,0,5,95);g.addColorStop(0,warm?'rgba(255,223,143,.34)':'rgba(178,235,224,.24)');g.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=g;ctx.fillRect(-100,-10,200,130);ctx.fillStyle=warm?'#ffe29a':'#c9fff3';ctx.fillRect(-7,0,14,3)}ctx.restore()}
function v110Crate(x,y,w=48,h=34){ctx.fillStyle='#191e20';ctx.fillRect(x+5,y+7,w,h);v110RoundRect(x,y,w,h,4,'#574631','#88704e');ctx.strokeStyle='#251d14';ctx.beginPath();ctx.moveTo(x+7,y+7);ctx.lineTo(x+w-7,y+h-7);ctx.moveTo(x+w-7,y+7);ctx.lineTo(x+7,y+h-7);ctx.stroke()}
function v110Worker(x,y,phase=0){const step=Math.sin(phase)*3;ctx.save();ctx.translate(x,y);ctx.fillStyle='#07101288';ctx.beginPath();ctx.ellipse(0,15,15,7,0,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#172124';ctx.lineWidth=6;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-4,8);ctx.lineTo(-6-step,23);ctx.moveTo(5,8);ctx.lineTo(7+step,23);ctx.stroke();ctx.fillStyle='#314b4b';ctx.beginPath();ctx.roundRect(-11,-12,22,28,7);ctx.fill();ctx.fillStyle='#d0a07e';ctx.beginPath();ctx.arc(0,-15,7,0,Math.PI*2);ctx.fill();ctx.restore()}
function v110Machine(x,y,w,h,label,active,now,accent='#5f7b7c'){
 ctx.save();ctx.fillStyle='#03070899';ctx.beginPath();ctx.roundRect(x+11,y+13,w,h,13);ctx.fill();
 const metal=ctx.createLinearGradient(x,y,x+w,y+h);metal.addColorStop(0,'#536264');metal.addColorStop(.45,'#27383b');metal.addColorStop(1,'#111a1c');v110RoundRect(x,y,w,h,13,metal,'#71898b');
 ctx.fillStyle='#0a1214';ctx.beginPath();ctx.roundRect(x+16,y+18,w-48,h*.5,7);ctx.fill();ctx.strokeStyle='#425b5e';ctx.stroke();
 ctx.fillStyle=active?'#f1b94e':'#5b786f';ctx.beginPath();ctx.arc(x+w-22,y+25,6,0,Math.PI*2);ctx.fill();if(active){ctx.shadowColor='#ffb13b';ctx.shadowBlur=16;ctx.fill();ctx.shadowBlur=0}
 ctx.fillStyle='#11191b';ctx.fillRect(x+w-38,y+45,25,70);ctx.fillStyle=active?'#78e7d6':'#355355';ctx.fillRect(x+w-33,y+51,15,19);
 ctx.strokeStyle='#bb914d';ctx.lineWidth=3;ctx.strokeRect(x-8,y+h*.68,w+16,h*.32+8);
 ctx.fillStyle='#d6e4e0';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText(label,x+w*.46,y+h-16);
 if(active){ctx.strokeStyle='#ffbc56';ctx.lineWidth=2;for(let i=0;i<5;i++){const a=now/180+i*1.2,r=18+i*4;ctx.beginPath();ctx.moveTo(x+w*.47,y+h*.34);ctx.lineTo(x+w*.47+Math.cos(a)*r,y+h*.34+Math.sin(a)*r);ctx.stroke()}}
 ctx.restore()
}
function v110Steam(x,y,now,scale=1){ctx.save();ctx.globalAlpha=.18;for(let i=0;i<5;i++){const t=(now*.018+i*23)%95;ctx.fillStyle='rgba(215,235,228,'+(1-t/110)+')';ctx.beginPath();ctx.arc(x+Math.sin((now+i*200)/420)*10*scale,y-t*scale,10+6*Math.sin(i),0,Math.PI*2);ctx.fill()}ctx.restore()}
function v110Sparks(x,y,now){if(Math.floor(now/650)%4!==0)return;ctx.save();ctx.strokeStyle='#ffc35e';ctx.lineWidth=2;for(let i=0;i<8;i++){const a=-1.5+i*.38+(now%200)/900,r=15+(i*7)%42;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+Math.cos(a)*r,y+Math.sin(a)*r);ctx.stroke()}ctx.restore()}
function v110Noise(g,w,h,amount=85){for(let i=0;i<amount;i++){g.fillStyle='rgba(225,255,248,'+(Math.random()*.09)+')';g.fillRect(Math.random()*w,Math.random()*h,Math.random()*3+1,1)}}
function v110CameraHeader(g,id,name,w){g.fillStyle='#d7ebe6';g.font='900 21px monospace';g.fillText('CAM '+String(id).padStart(2,'0')+' · '+name,24,34);g.fillStyle='#ff536b';g.font='900 15px monospace';g.fillText('● REC',w-95,34)}
`;
 source=source.replace('function drawPlayer(now){',helpers+'\nfunction drawPlayer(now){');
 swap('function drawPlayer(now){','\nfunction drawOutside(now){',`function drawPlayer(now){
  const image=window.__NH_HERO_SPRITE,moving=Math.hypot(joy.x,joy.y)>.08||keys.size>0;
  const raw=Math.atan2(player.facingY,player.facingX),snap=Math.round(raw/(Math.PI/4))*(Math.PI/4),bob=moving?Math.sin(player.walk*1.7)*.8:Math.sin(now/650)*.35;
  ctx.save();ctx.translate(player.x,player.y);
  ctx.fillStyle='#02070888';ctx.beginPath();ctx.ellipse(0,18,19,8,0,0,Math.PI*2);ctx.fill();
  ctx.rotate(snap+Math.PI/2);ctx.translate(0,bob);
  if(image?.complete){ctx.filter=state.scene==='factory'?'brightness(.83) saturate(.82) contrast(1.08)':'brightness(.98) saturate(.92)';ctx.drawImage(image,-31,-50,62,78);ctx.filter='none'}
  else{ctx.fillStyle='#25443f';ctx.beginPath();ctx.roundRect(-15,-23,30,46,9);ctx.fill()}
  if(state.flashlightUnlocked){ctx.strokeStyle='#cbd7d3';ctx.lineWidth=5;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(9,-8);ctx.lineTo(29,-8);ctx.stroke();ctx.fillStyle=state.flashlight?'#fff0a5':'#596767';ctx.fillRect(27,-12,10,8);if(state.flashlight){ctx.shadowColor='#ffe6a0';ctx.shadowBlur=12;ctx.fillRect(29,-10,5,4);ctx.shadowBlur=0}}
  ctx.restore()
 }`);
 swap('function drawOutside(now){','\nfunction machine(',`function drawOutside(now){
  const W=OUTSIDE.w,H=OUTSIDE.h;
  const sky=ctx.createLinearGradient(0,0,0,260);sky.addColorStop(0,'#eb9a53');sky.addColorStop(.5,'#d9b77a');sky.addColorStop(1,'#81979a');ctx.fillStyle=sky;ctx.fillRect(0,0,W,260);
  const sun=ctx.createRadialGradient(125,78,8,125,78,250);sun.addColorStop(0,'rgba(255,248,198,.95)');sun.addColorStop(.24,'rgba(255,214,126,.35)');sun.addColorStop(1,'rgba(255,170,80,0)');ctx.fillStyle=sun;ctx.fillRect(0,0,500,360);
  ctx.fillStyle='#2b3335';ctx.fillRect(0,0,W,210);ctx.fillStyle='#3a4345';ctx.fillRect(0,0,W,28);
  ctx.strokeStyle='#e7d697aa';ctx.lineWidth=5;ctx.setLineDash([54,34]);ctx.beginPath();ctx.moveTo(0,112);ctx.lineTo(W,112);ctx.stroke();ctx.setLineDash([]);
  for(let i=0;i<4;i++){const x=((now*.035+i*340)%1500)-230,y=i%2?145:54;ctx.fillStyle=i%2?'#7a4b43':'#385a68';ctx.beginPath();ctx.roundRect(x,y,108,44,12);ctx.fill();ctx.fillStyle='#cce3e577';ctx.fillRect(x+20,y+7,52,14);ctx.fillStyle='#090d0e';ctx.beginPath();ctx.arc(x+24,y+44,9,0,Math.PI*2);ctx.arc(x+83,y+44,9,0,Math.PI*2);ctx.fill()}
  ctx.fillStyle='#8d8270';ctx.fillRect(0,210,W,490);ctx.fillStyle='#a89a7d';ctx.fillRect(0,245,W,455);
  for(const p of v110Puddles){const g=ctx.createRadialGradient(p.x,p.y,2,p.x,p.y,p.rx);g.addColorStop(0,'rgba(199,225,220,.38)');g.addColorStop(1,'rgba(40,55,57,0)');ctx.save();ctx.scale(1,p.ry/p.rx);ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y*p.rx/p.ry,p.rx,0,Math.PI*2);ctx.fill();ctx.restore()}
  ctx.strokeStyle='#d8ccaa22';ctx.lineWidth=1;for(let y=270;y<H;y+=74){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(W,y);ctx.stroke()}for(let x=30;x<W;x+=115){ctx.beginPath();ctx.moveTo(x,245);ctx.lineTo(x,H);ctx.stroke()}
  ctx.fillStyle='#192427';ctx.fillRect(790,135,310,565);ctx.fillStyle='#33474a';ctx.fillRect(805,155,295,545);
  ctx.fillStyle='#6d929255';for(let y=190;y<520;y+=72)for(let x=830;x<1080;x+=62)ctx.fillRect(x,y,45,48);
  ctx.fillStyle='#10181a';ctx.fillRect(855,325,190,260);ctx.fillStyle='#89c6bc55';ctx.fillRect(880,352,140,185);ctx.strokeStyle='#bde9dc99';ctx.lineWidth=3;ctx.strokeRect(880,352,140,185);
  ctx.fillStyle='#e7cb7d';ctx.font='900 22px system-ui';ctx.textAlign='center';ctx.fillText('ОРФЕЙ',945,270);ctx.font='800 9px system-ui';ctx.fillText('МАШИНОСТРОИТЕЛЬНЫЙ ЗАВОД',945,293);
  ctx.fillStyle='#192224';ctx.fillRect(735,360,110,180);ctx.fillStyle='#2d3b3e';ctx.fillRect(748,379,84,135);ctx.fillStyle='#e7d598';ctx.font='800 9px system-ui';ctx.fillText('ПРОХОДНАЯ',790,350);
  ctx.fillStyle='#222c2e';ctx.fillRect(815,543,230,16);ctx.strokeStyle='#b7463e';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(820,551);ctx.lineTo(990,551);ctx.stroke();
  const fenceY=595;ctx.strokeStyle='#263638';ctx.lineWidth=5;for(let x=700;x<1100;x+=32){ctx.beginPath();ctx.moveTo(x,fenceY);ctx.lineTo(x,700);ctx.stroke()}ctx.beginPath();ctx.moveTo(700,fenceY);ctx.lineTo(1100,fenceY);ctx.stroke();
  for(let i=0;i<4;i++)v110Worker(650+i*45,420+(i%2)*22,now/300+i);
  for(const [x,y,s] of [[120,435,1],[360,600,.85],[600,390,.78]]){ctx.fillStyle='#4a3424';ctx.fillRect(x-6,y,12,42*s);ctx.fillStyle='#2f5a43';for(let i=0;i<5;i++){ctx.beginPath();ctx.arc(x+Math.sin(now/900+i)*4,y-15-i*4,20-i*2,0,Math.PI*2);ctx.fill()}}
  v110Lamp(775,342,true,true);v110Lamp(1038,335,true,true);
  const pulse=(Math.sin(now/180)+1)/2;ctx.strokeStyle='rgba(247,211,126,'+(.35+pulse*.45)+')';ctx.lineWidth=2;ctx.beginPath();ctx.arc(points.gate.x,points.gate.y,24+pulse*4,0,Math.PI*2);ctx.stroke();
  drawPlayer(now)
 }`);
 swap('function machine(','\nfunction drawFactory(now){',`function machine(x,y,w,h,label,color='#30484d',active=false,now=0){v110Machine(x,y,w,h,label,active,now,color)}`);
 swap('function drawFactory(now){','\nfunction drawFlashlight(){',`function drawFactory(now){
  const night=state.phase>=3,W=FACTORY.w,H=FACTORY.h;
  const floor=ctx.createLinearGradient(0,0,W,H);floor.addColorStop(0,night?'#182528':'#899997');floor.addColorStop(.5,night?'#0d1719':'#6f807d');floor.addColorStop(1,night?'#05090a':'#455557');ctx.fillStyle=floor;ctx.fillRect(0,0,W,H);
  ctx.fillStyle='rgba(0,0,0,.16)';for(let x=0;x<W;x+=100)ctx.fillRect(x,0,2,H);for(let y=0;y<H;y+=100)ctx.fillRect(0,y,W,2);
  for(let i=0;i<55;i++){const x=(i*179)%W,y=(i*83)%H,r=12+(i%6)*5;ctx.fillStyle='rgba(9,14,15,'+(night?.22:.12)+')';ctx.beginPath();ctx.ellipse(x,y,r,r*.35,(i%4)*.4,0,Math.PI*2);ctx.fill()}
  ctx.strokeStyle=night?'#d1fff01d':'#f3dda94a';ctx.lineWidth=5;ctx.setLineDash([30,20]);ctx.beginPath();ctx.moveTo(420,450);ctx.lineTo(1505,450);ctx.moveTo(395,855);ctx.lineTo(1425,855);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#101b1d';ctx.beginPath();ctx.roundRect(50,52,370,272,14);ctx.fill();ctx.strokeStyle='#5b8b8788';ctx.lineWidth=4;ctx.stroke();
  const postGrad=ctx.createLinearGradient(60,60,400,310);postGrad.addColorStop(0,'#304f51');postGrad.addColorStop(1,'#142527');ctx.fillStyle=postGrad;ctx.beginPath();ctx.roundRect(66,66,338,238,12);ctx.fill();
  ctx.fillStyle='#071013';ctx.beginPath();ctx.roundRect(88,82,296,100,7);ctx.fill();for(let i=0;i<4;i++){ctx.fillStyle=i===2&&state.phase>=3?'#642032':'#173b3f';ctx.fillRect(103+i*67,98,54,50);ctx.fillStyle='#79cfc31e';ctx.fillRect(109+i*67,104,30,5)}
  ctx.fillStyle='#33281d';ctx.fillRect(105,211,250,55);ctx.fillStyle='#d6be77';ctx.fillRect(140,225,110,8);ctx.fillStyle='#72898a';ctx.fillRect(275,222,42,18);ctx.fillStyle='#e4efe9';ctx.font='900 14px system-ui';ctx.textAlign='center';ctx.fillText('ПОСТ ДЕЖУРНОГО',235,200);
  v110Lamp(160,62,true,true);v110Lamp(330,62,true,false);
  v110Machine(480,105,260,250,'СТАНОК №3',false,now);v110Machine(800,105,260,250,'СТАНОК №4',state.phase===2,now);v110Machine(1120,105,260,250,'СТАНОК №5',state.phase>=7&&Math.floor(now/550)%2===0,now);
  v110Machine(465,520,340,200,'ЛАЗЕРНЫЙ УЧАСТОК',state.phase>=4,now,'#3b4749');v110Machine(855,515,275,205,'ГИБОЧНЫЙ ПРЕСС',state.phase>=5&&Math.floor(now/420)%2===0,now,'#47463d');
  ctx.fillStyle='#182023';ctx.beginPath();ctx.roundRect(1180,485,270,250,15);ctx.fill();ctx.strokeStyle='#806343';ctx.lineWidth=4;ctx.stroke();for(let i=0;i<4;i++){ctx.fillStyle='#4c5b5c';ctx.beginPath();ctx.arc(1240+i*56,570,24,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#c79852';ctx.stroke()}ctx.fillStyle='#273438';ctx.beginPath();ctx.arc(1320,645,70,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#b97f43';ctx.lineWidth=8;ctx.stroke();ctx.fillStyle='#e1c77e';ctx.font='900 12px system-ui';ctx.fillText('КОМПРЕССОРНАЯ',1318,706);v110Steam(1215,520,now,1.1);
  ctx.fillStyle='#1c2628';ctx.beginPath();ctx.roundRect(1440,680,285,210,12);ctx.fill();ctx.strokeStyle='#65797a';ctx.lineWidth=3;ctx.stroke();for(let i=0;i<12;i++){ctx.fillStyle=i<6&&state.phase===4?'#8b283b':'#2d514c';ctx.fillRect(1465+(i%6)*39,710+Math.floor(i/6)*77,25,50);if(i<6&&state.phase===4&&i%2===0){ctx.shadowColor='#ff4761';ctx.shadowBlur=12;ctx.fillRect(1470+(i%6)*39,718,15,8);ctx.shadowBlur=0}}ctx.fillStyle='#d9e6e2';ctx.fillText('ГЛАВНЫЙ ЩИТ',1580,865);if(state.phase===4)v110Sparks(1710,760,now);
  ctx.fillStyle='#2d3b3e';ctx.fillRect(1148,55,125,125);ctx.strokeStyle='#697d80';ctx.strokeRect(1148,55,125,125);ctx.fillStyle='#d2be7c';ctx.font='900 9px system-ui';ctx.fillText('ШКАФЧИК МАСТЕРА',1210,122);
  ctx.fillStyle='#06090a';ctx.fillRect(1520,75,240,355);ctx.strokeStyle=state.oldShopOpen?'#e8c66e':'#6c2637';ctx.lineWidth=5;ctx.strokeRect(1520,75,240,355);ctx.fillStyle=state.oldShopOpen?'#e8c66e':'#ff526b';ctx.font='900 13px system-ui';ctx.fillText(state.oldShopOpen?'СЕКТОР 0 · ОТКРЫТ':'СТАРЫЙ ЦЕХ · ЗАКРЫТ',1640,463);
  if(state.oldShopOpen){v110Machine(1540,95,200,290,'СТАНОК №0',state.phase>=9,now,'#201317');ctx.fillStyle='#ff3d5b14';ctx.fillRect(1540,95,200,290)}
  for(const n of optionalNotes){if(state.notes.has(n.id))continue;ctx.save();ctx.translate(n.x,n.y);ctx.rotate(-.12);ctx.shadowColor='#f7d98a';ctx.shadowBlur=12;ctx.fillStyle='#ead8a8';ctx.fillRect(-14,-18,28,36);ctx.shadowBlur=0;ctx.fillStyle='#725936';ctx.fillRect(-8,-8,16,2);ctx.fillRect(-8,-2,16,2);ctx.restore()}
  const t=getMainTarget();if(t){const pulse=(Math.sin(now/170)+1)/2;ctx.strokeStyle='rgba(243,210,126,'+(.32+pulse*.5)+')';ctx.lineWidth=2;ctx.beginPath();ctx.arc(t.x,t.y,23+pulse*4,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#efd486';ctx.font='900 8px system-ui';ctx.fillText(t.label,t.x,t.y-34)}
  for(const [x,y,warm] of [[445,430,false],[780,430,false],[1120,430,false],[1450,430,false],[430,835,true],[920,835,false],[1390,835,false]])v110Lamp(x,y,!night||Math.floor((now+x)/1700)%4!==0,warm);
  v110Steam(1120,760,now,.8);if(state.phase>=4)v110Steam(760,520,now,.55);
  if(state.shadow.visible){ctx.save();ctx.translate(state.shadow.x,state.shadow.y);ctx.globalAlpha=.8;ctx.fillStyle='#010304';ctx.beginPath();ctx.ellipse(0,13,22,48,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(0,-38,17,0,Math.PI*2);ctx.fill();ctx.fillStyle='#ff3e58';ctx.beginPath();ctx.arc(-5,-40,2.5,0,Math.PI*2);ctx.arc(5,-40,2.5,0,Math.PI*2);ctx.fill();ctx.restore()}
  drawPlayer(now)
 }`);
 swap('function drawFlashlight(){','\nfunction render(now){',`function drawFlashlight(){
  if(state.scene!=='factory'||state.phase<2)return;const darkness=state.flashlight?.58:.76;lctx.setTransform(dpr,0,0,dpr,0,0);lctx.clearRect(0,0,vw,vh);lctx.fillStyle='rgba(1,5,6,'+darkness+')';lctx.fillRect(0,0,vw,vh);
  const px=player.x-camera.x,py=player.y-camera.y,a=Math.atan2(player.facingY,player.facingX);lctx.globalCompositeOperation='destination-out';
  const amb=lctx.createRadialGradient(px,py,3,px,py,state.flashlight?105:52);amb.addColorStop(0,'rgba(0,0,0,.92)');amb.addColorStop(.55,'rgba(0,0,0,.5)');amb.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=amb;lctx.beginPath();lctx.arc(px,py,state.flashlight?108:55,0,Math.PI*2);lctx.fill();
  if(state.flashlight){lctx.save();lctx.translate(px,py);lctx.rotate(a);const beam=lctx.createLinearGradient(0,0,620,0);beam.addColorStop(0,'rgba(0,0,0,1)');beam.addColorStop(.7,'rgba(0,0,0,.82)');beam.addColorStop(1,'rgba(0,0,0,0)');lctx.fillStyle=beam;lctx.beginPath();lctx.moveTo(4,-17);lctx.quadraticCurveTo(260,-68,620,-132);lctx.lineTo(620,132);lctx.quadraticCurveTo(260,68,4,17);lctx.closePath();lctx.fill();lctx.restore()}
  lctx.globalCompositeOperation='source-over';ctx.drawImage(light,0,0,vw,vh)
 }`);
 swap('function drawCamera(id){','\nfunction drawCameraPerson',`function drawCamera(id){
  const c=$('cameraFeed'),g=c.getContext('2d'),w=c.width,h=c.height,name=cameraDefs.find(q=>q.id===id)?.name||'';g.clearRect(0,0,w,h);
  const bg=g.createLinearGradient(0,0,w,h);bg.addColorStop(0,'#26383a');bg.addColorStop(1,'#05090a');g.fillStyle=bg;g.fillRect(0,0,w,h);v110CameraHeader(g,id,name,w);
  g.save();g.translate(0,46);
  if(id===1){g.fillStyle='#6f766b';g.fillRect(0,0,w,h);g.fillStyle='#253438';g.fillRect(540,50,360,390);g.fillStyle='#91b8b24d';g.fillRect(615,110,180,245);g.fillStyle='#172022';g.fillRect(85,210,400,20);g.strokeStyle='#9a713f';g.lineWidth=5;g.strokeRect(85,230,400,175);g.fillStyle='#d5bd73';g.fillRect(110,260,150,10);if(state.cameraMode==='zero'){drawCameraPerson(g,455,350,true);g.fillStyle='#ff6075';g.font='900 18px monospace';g.fillText('СОТРУДНИК УЖЕ НА ТЕРРИТОРИИ',415,470)}}
  else if(id===2){g.fillStyle='#172426';g.fillRect(0,0,w,h);for(let i=0;i<3;i++){g.fillStyle='#34484b';g.beginPath();g.roundRect(75+i*285,120,230,250,10);g.fill();g.fillStyle=i===1&&state.phase>=3?'#c84256':'#6d8a85';g.fillRect(260+i*285,145,16,16);g.fillStyle='#081012';g.fillRect(95+i*285,145,150,100)}g.strokeStyle='#bea052';g.setLineDash([24,18]);g.beginPath();g.moveTo(30,420);g.lineTo(920,420);g.stroke();g.setLineDash([]);if(state.cameraMode==='anomaly')drawCameraPerson(g,785,340,false)}
  else if(id===3){g.fillStyle='#1c2b2e';g.fillRect(0,0,w,h);g.fillStyle='#405659';g.beginPath();g.roundRect(235,70,500,355,14);g.fill();g.fillStyle='#071113';g.fillRect(285,120,340,160);g.fillStyle='#d74157';g.beginPath();g.arc(675,110,12,0,Math.PI*2);g.fill();g.fillStyle='#e7d092';g.font='900 26px monospace';g.fillText('ОШИБКА ОХЛАЖДЕНИЯ',270,460)}
  else if(id===4){g.fillStyle='#122022';g.fillRect(0,0,w,h);for(let i=0;i<4;i++){g.fillStyle='#3c4b4c';g.beginPath();g.arc(185+i*190,250,78,0,Math.PI*2);g.fill();g.strokeStyle='#a77743';g.lineWidth=12;g.stroke();g.fillStyle='#d8c78c';g.font='900 18px monospace';g.fillText(i===2?'0 BAR':'5.2',155+i*190,255)}v110Noise(g,w,h,35)}
  else if(id===5){g.fillStyle='#11191a';g.fillRect(0,0,w,h);for(let i=0;i<10;i++){g.fillStyle=i<5?'#7f2839':'#294d48';g.fillRect(105+(i%5)*155,105+Math.floor(i/5)*170,90,120)}g.fillStyle='#ff667a';g.font='900 22px monospace';g.fillText('ПЕРЕГРУЗКА ЛИНИИ 047',280,455)}
  else if(id===6){g.fillStyle='#050708';g.fillRect(0,0,w,h);for(let i=0;i<6;i++){g.fillStyle='#172123';g.fillRect(80+i*135,80,95,350)}g.fillStyle='#9b263a';g.fillRect(410,75,140,360);g.fillStyle='#ff596f';g.font='900 24px monospace';g.fillText(state.cameraMode==='zero'?'ДВЕРЬ ОТКРЫТА':'НЕТ СИГНАЛА',350,255);if(state.cameraMode==='zero')drawCameraPerson(g,520,380,false)}
  else if(id===7){g.fillStyle='#091113';g.fillRect(0,0,w,h);g.fillStyle='#263b3d';g.fillRect(110,80,740,330);g.fillStyle='#0d181a';g.fillRect(165,120,620,220);drawCameraPerson(g,505,350,false);g.fillStyle='#ff5a70';g.font='900 21px monospace';g.fillText('ОБЪЕКТ СМОТРИТ В КАМЕРУ',290,455)}
  else{g.fillStyle='#080607';g.fillRect(0,0,w,h);g.strokeStyle='#6e2435';g.lineWidth=6;g.strokeRect(180,45,600,405);g.fillStyle='#231217';g.beginPath();g.roundRect(300,100,360,290,14);g.fill();g.fillStyle='#ff425e';g.font='900 40px monospace';g.fillText('СТАНОК №0',350,230);g.font='900 22px monospace';g.fillText('ОПЕРАТОР: И. ИВЧЕНКОВ',280,430)}
  g.restore();v110Noise(g,w,h,120)
 }`);
 const setup=`
 document.body.classList.add('reality110');
 const objectiveBox=$('objective');if(objectiveBox&&$('objectiveDetail'))$('objectiveDetail').textContent='Тёплый вечер. Дневная смена покидает территорию.';
 document.addEventListener('contextmenu',e=>e.preventDefault());
 const journal=$('journalModal'),cameraModal=$('cameraModal');
 $('confirmSignature')?.addEventListener('click',()=>{journal?.classList.add('stamping');setTimeout(()=>journal?.classList.remove('stamping'),900)});
 const originalOpenCameras=openCameras;openCameras=function(mode){cameraModal?.classList.add('opening');originalOpenCameras(mode);setTimeout(()=>cameraModal?.classList.remove('opening'),650)};
`;
 source=source.replace("new ResizeObserver(resize).observe(canvas);",setup+"\nnew ResizeObserver(resize).observe(canvas);");
 (0,eval)(source);
}catch(e){if(error){error.textContent='Reality 110 не загрузилась: '+e.message;error.style.display='block'}if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}}
})();
