'use strict';

function clamp01(value){return Math.max(0,Math.min(1,value))}
function hashNoise(value){
  const x=Math.sin(value*12.9898+seed*0.0001)*43758.5453;
  return x-Math.floor(x);
}
function polygon(points,fill,stroke,lineWidth=1){
  if(!points.length)return;
  ctx.beginPath();ctx.moveTo(points[0][0],points[0][1]);
  for(let i=1;i<points.length;i++)ctx.lineTo(points[i][0],points[i][1]);
  ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill()}
  if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke()}
}
function roundedRect(x,y,w,h,r,fill,stroke,lineWidth=1){
  r=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill()}
  if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke()}
}
function drawSky(t){
  const sky=ctx.createLinearGradient(0,0,0,H);
  sky.addColorStop(0,'#09031a');sky.addColorStop(.28,'#241044');sky.addColorStop(.62,'#100a22');sky.addColorStop(1,'#03040b');
  ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);

  const glow=ctx.createRadialGradient(W*.54,H*.12,0,W*.54,H*.12,Math.max(W,H)*.62);
  glow.addColorStop(0,'rgba(178,78,255,.30)');glow.addColorStop(.32,'rgba(101,44,184,.13)');glow.addColorStop(1,'rgba(8,2,20,0)');
  ctx.fillStyle=glow;ctx.fillRect(0,0,W,H*.8);

  ctx.save();
  for(let i=0;i<42;i++){
    const x=hashNoise(i*7.1)*W,y=hashNoise(i*9.7+8)*H*.43,r=.45+hashNoise(i*3.7)*1.25;
    ctx.globalAlpha=.18+hashNoise(i*2.3)*.55;ctx.fillStyle=i%9===0?'#e8c8ff':'#ffffff';ctx.fillRect(x,y,r,r);
  }
  ctx.restore();

  const moonX=W*.82,moonY=H*.105,moonR=Math.min(W,H)*.048;
  ctx.save();ctx.shadowColor='#d9b7ff';ctx.shadowBlur=28;ctx.fillStyle='#e8dcff';ctx.beginPath();ctx.arc(moonX,moonY,moonR,0,Math.PI*2);ctx.fill();
  ctx.globalCompositeOperation='destination-out';ctx.beginPath();ctx.arc(moonX+moonR*.42,moonY-moonR*.12,moonR*.92,0,Math.PI*2);ctx.fill();ctx.restore();

  ctx.save();ctx.globalAlpha=.18;ctx.fillStyle='#b77aff';
  for(let i=0;i<4;i++){
    const y=H*(.18+i*.075),offset=((t*.006*(i+1))%(W*.65))-W*.3;
    ctx.beginPath();ctx.ellipse(offset+W*.4,y,W*(.18+i*.025),H*.018,0,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();
}
function drawCityLayer(t,depth,count,baseY,maxH,alpha){
  const travel=(distance*(depth===0?0.18:0.34)+t*(depth===0?.0008:.0015))%1;
  ctx.save();ctx.globalAlpha=alpha;
  for(let i=-2;i<count+2;i++){
    const n=i+Math.floor(travel*count),unit=W/count;
    const x=i*unit-(travel*count%1)*unit;
    const bw=unit*(.62+hashNoise(n*1.31+depth*41)*.72);
    const bh=maxH*(.28+hashNoise(n*2.17+depth*17)*.72);
    const top=baseY-bh;
    const body=ctx.createLinearGradient(x,top,x+bw,baseY);
    body.addColorStop(0,depth===0?'#19112f':'#100b20');body.addColorStop(1,depth===0?'#080914':'#05060e');
    ctx.fillStyle=body;ctx.fillRect(x,top,bw,bh);
    ctx.fillStyle=depth===0?'rgba(185,103,255,.24)':'rgba(140,78,210,.16)';ctx.fillRect(x,top,bw,1.2);
    if(hashNoise(n*6.2)> .66){ctx.fillStyle='#121022';ctx.fillRect(x+bw*.42,top-bh*.11,bw*.16,bh*.11)}
    if(depth===0){
      const cols=Math.max(2,Math.floor(bw/14)),rows=Math.max(2,Math.floor(bh/19));
      for(let cy=1;cy<rows;cy++)for(let cx=1;cx<cols;cx++){
        if(hashNoise(n*100+cy*11+cx*3)<.46)continue;
        const wx=x+cx*bw/cols-1.2,wy=top+cy*bh/rows;
        ctx.fillStyle=hashNoise(n+cy*4+cx)>.82?'rgba(255,214,105,.70)':'rgba(166,96,255,.38)';ctx.fillRect(wx,wy,2.2,3.4);
      }
    }
  }
  ctx.restore();
}
function trackPoint(laneValue,z){return [laneX(laneValue,z),objectY(z)]}
function drawRoofTrack(t){
  const horizonY=H*.245,leftFar=W*.43,rightFar=W*.57,leftNear=-W*.12,rightNear=W*1.12;
  const roof=ctx.createLinearGradient(0,horizonY,0,H);
  roof.addColorStop(0,'#151225');roof.addColorStop(.46,'#0e101b');roof.addColorStop(1,'#070910');
  polygon([[leftFar,horizonY],[rightFar,horizonY],[rightNear,H],[leftNear,H]],roof,'rgba(176,102,255,.48)',1.3);

  const edgeGlow=ctx.createLinearGradient(0,horizonY,0,H);edgeGlow.addColorStop(0,'rgba(190,116,255,.28)');edgeGlow.addColorStop(1,'rgba(89,205,255,.62)');
  ctx.save();ctx.strokeStyle=edgeGlow;ctx.lineWidth=2.2;ctx.shadowColor='#8d4eff';ctx.shadowBlur=10;
  ctx.beginPath();ctx.moveTo(leftFar,horizonY);ctx.lineTo(leftNear,H);ctx.moveTo(rightFar,horizonY);ctx.lineTo(rightNear,H);ctx.stroke();ctx.restore();

  for(let laneIndex=0;laneIndex<2;laneIndex++){
    const farX=laneX(laneIndex+.5,0),nearX=laneX(laneIndex+.5,1.18);
    ctx.strokeStyle='rgba(201,163,255,.22)';ctx.lineWidth=1.3;ctx.setLineDash([8,11]);ctx.beginPath();ctx.moveTo(farX,horizonY);ctx.lineTo(nearX,H);ctx.stroke();ctx.setLineDash([]);
  }

  const scroll=(distance*.028)%1;
  for(let i=0;i<15;i++){
    const z=(i/15+scroll)%1,y=objectY(z),left=laneX(-.72,z),right=laneX(2.72,z);
    ctx.strokeStyle=`rgba(179,139,216,${.035+z*.12})`;ctx.lineWidth=.7+z*1.2;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
  }

  for(let i=0;i<9;i++){
    const z=((i/9)+(distance*.016)%1)%1,x=laneX(i%3,z),y=objectY(z),r=1+z*4;
    ctx.fillStyle=`rgba(89,210,255,${.07+z*.18})`;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
  }

  ctx.save();ctx.globalAlpha=.7;
  const sideScroll=(distance*.015)%1;
  for(let i=0;i<8;i++){
    const z=(i/8+sideScroll)%1,y=objectY(z),s=.25+z*1.2;
    const leftX=laneX(-1.05,z),rightX=laneX(3.05,z);
    ctx.fillStyle='#0b0d15';ctx.strokeStyle='rgba(155,88,222,.30)';ctx.lineWidth=1+s;
    ctx.fillRect(leftX-30*s,y-20*s,40*s,20*s);ctx.strokeRect(leftX-30*s,y-20*s,40*s,20*s);
    if(i%2===0){ctx.fillRect(rightX-8*s,y-35*s,24*s,35*s);ctx.strokeRect(rightX-8*s,y-35*s,24*s,35*s)}
  }
  ctx.restore();

  const railY=H*.66;
  ctx.save();ctx.globalAlpha=.25;ctx.strokeStyle='#b16cff';ctx.lineWidth=1;
  for(let side of [-1,1]){
    const sx=side<0?W*.03:W*.97;ctx.beginPath();ctx.moveTo(sx,railY);ctx.lineTo(side<0?W*.34:W*.66,H*.31);ctx.stroke();
  }
  ctx.restore();
}
function drawNeonSigns(t){
  ctx.save();
  const pulse=.72+.18*Math.sin(t*.004);
  ctx.shadowBlur=14;ctx.font=`900 ${Math.max(9,W*.022)}px system-ui`;ctx.textAlign='center';
  const signs=[{x:W*.12,y:H*.36,text:'REALITY',color:'#cf70ff',a:-.07},{x:W*.88,y:H*.42,text:'EGO',color:'#69ddff',a:.08}];
  for(const sign of signs){ctx.save();ctx.translate(sign.x,sign.y);ctx.rotate(sign.a);ctx.globalAlpha=pulse;ctx.shadowColor=sign.color;roundedRect(-W*.09,-H*.018,W*.18,H*.036,5,'rgba(7,6,16,.82)',sign.color,1.2);ctx.fillStyle=sign.color;ctx.fillText(sign.text,0,H*.006);ctx.restore()}
  ctx.restore();
}
function drawBackground(t){
  drawSky(t);drawCityLayer(t,1,13,H*.37,H*.20,.42);drawCityLayer(t,0,18,H*.49,H*.30,.72);drawNeonSigns(t);drawRoofTrack(t);
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'rgba(3,1,9,.05)');shade.addColorStop(.68,'rgba(2,3,8,.02)');shade.addColorStop(1,'rgba(0,0,0,.36)');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  ctx.save();ctx.strokeStyle='rgba(194,158,255,.25)';ctx.lineWidth=1;for(const r of rain){ctx.globalAlpha=r.a;ctx.beginPath();ctx.moveTo(r.x,r.y);ctx.lineTo(r.x-3,r.y+r.l);ctx.stroke()}ctx.restore();
}
function drawBoss(t){
  const pulse=1+Math.sin(t*.0025)*.035+bossPulse*.12,cx=W/2,cy=H*.17,r=Math.min(W*.11,H*.075)*pulse;
  ctx.save();ctx.translate(cx,cy);ctx.globalCompositeOperation='screen';
  for(let i=0;i<4;i++){ctx.rotate((t*.00012)*(i%2?1:-1));ctx.globalAlpha=.12+i*.06+bossPulse*.12;ctx.strokeStyle=i%2?'#6edbff':'#c663ff';ctx.lineWidth=1.2+i*.7;ctx.setLineDash([6+i*3,8+i*2]);ctx.beginPath();ctx.arc(0,0,r*(1.45+i*.26),0,Math.PI*2);ctx.stroke()}ctx.setLineDash([]);
  const aura=ctx.createRadialGradient(0,0,r*.15,0,0,r*2.1);aura.addColorStop(0,'rgba(242,197,255,.42)');aura.addColorStop(.35,'rgba(162,68,255,.25)');aura.addColorStop(1,'rgba(94,23,174,0)');ctx.fillStyle=aura;ctx.beginPath();ctx.arc(0,0,r*2.1,0,Math.PI*2);ctx.fill();
  ctx.globalCompositeOperation='source-over';ctx.shadowColor='#b64dff';ctx.shadowBlur=22+bossPulse*25;ctx.fillStyle='#10051f';ctx.strokeStyle='#d28aff';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(0,0,r*1.08,r*.76,0,0,Math.PI*2);ctx.fill();ctx.stroke();
  const eye=ctx.createRadialGradient(0,0,1,0,0,r*.72);eye.addColorStop(0,'#ffffff');eye.addColorStop(.18,'#e9bcff');eye.addColorStop(.48,'#b64eff');eye.addColorStop(1,'#41116d');ctx.fillStyle=eye;ctx.beginPath();ctx.ellipse(0,0,r*.72,r*.32,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#0a0313';ctx.beginPath();ctx.arc(0,0,r*.16,0,Math.PI*2);ctx.fill();ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(-r*.05,-r*.06,r*.045,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#ffd67a';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-r*.62,-r*.66);ctx.lineTo(-r*.30,-r*1.08);ctx.lineTo(0,-r*.70);ctx.lineTo(r*.30,-r*1.08);ctx.lineTo(r*.62,-r*.66);ctx.stroke();
  ctx.restore();
}
function drawCrystal(s){
  const h=43*s,w=25*s;ctx.shadowColor='#c66cff';ctx.shadowBlur=18*s;
  const g=ctx.createLinearGradient(-w/2,-h/2,w/2,h/2);g.addColorStop(0,'#f2d5ff');g.addColorStop(.32,'#c06dff');g.addColorStop(.7,'#7123c8');g.addColorStop(1,'#3a0b78');
  polygon([[0,-h/2],[w/2,-h*.12],[w*.32,h*.42],[0,h/2],[-w*.32,h*.42],[-w/2,-h*.12]],g,'#efd8ff',1.2*s);
  ctx.strokeStyle='rgba(255,255,255,.55)';ctx.lineWidth=.8*s;ctx.beginPath();ctx.moveTo(0,-h/2);ctx.lineTo(0,h/2);ctx.moveTo(-w/2,-h*.12);ctx.lineTo(w*.32,h*.42);ctx.stroke();
}
function drawGold(s){
  const r=13*s;ctx.shadowColor='#ffd45f';ctx.shadowBlur=18*s;ctx.fillStyle='#ffcc46';ctx.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.47:r,px=Math.cos(a)*rr,py=Math.sin(a)*rr;i?ctx.lineTo(px,py):ctx.moveTo(px,py)}ctx.closePath();ctx.fill();ctx.fillStyle='#fff1a1';ctx.beginPath();ctx.arc(0,0,r*.28,0,Math.PI*2);ctx.fill();
}
function drawBarrier(s){
  const w=112*s,h=48*s;ctx.shadowColor='#a84cff';ctx.shadowBlur=14*s;roundedRect(-w/2,-h*.82,w,h,7*s,'#161020','#b86cff',2*s);
  ctx.save();ctx.beginPath();ctx.rect(-w/2+4*s,-h*.82+4*s,w-8*s,h-8*s);ctx.clip();ctx.strokeStyle='#ffd66a';ctx.lineWidth=8*s;for(let x=-w;x<w;x+=24*s){ctx.beginPath();ctx.moveTo(x,-h);ctx.lineTo(x+55*s,h);ctx.stroke()}ctx.restore();
  ctx.fillStyle='#6f3baa';ctx.fillRect(-w*.38,h*.18,w*.12,h*.35);ctx.fillRect(w*.26,h*.18,w*.12,h*.35);
}
function drawDrone(s,phase){
  const w=82*s,h=30*s;ctx.translate(0,Math.sin(phase)*4*s-25*s);ctx.shadowColor='#6edcff';ctx.shadowBlur=18*s;roundedRect(-w*.28,-h*.45,w*.56,h*.9,h*.3,'#151324','#7de5ff',1.5*s);
  ctx.strokeStyle='#9d68ff';ctx.lineWidth=3*s;ctx.beginPath();ctx.moveTo(-w*.22,0);ctx.lineTo(-w*.48,-h*.12);ctx.moveTo(w*.22,0);ctx.lineTo(w*.48,-h*.12);ctx.stroke();
  for(const dir of [-1,1]){ctx.strokeStyle='#d8c6ff';ctx.lineWidth=1*s;ctx.beginPath();ctx.ellipse(dir*w*.5,-h*.15,w*.18,h*.08,0,0,Math.PI*2);ctx.stroke()}
  ctx.fillStyle='#ff4b9a';ctx.beginPath();ctx.arc(0,h*.06,4*s,0,Math.PI*2);ctx.fill();
}
function drawPower(kind,s){
  const r=21*s,main=kind==='shield'?'#79e5ff':kind==='magnet'?'#d77aff':'#ffd86a';ctx.shadowColor=main;ctx.shadowBlur=20*s;ctx.fillStyle='rgba(11,8,24,.94)';ctx.strokeStyle=main;ctx.lineWidth=2*s;ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.strokeStyle=main;ctx.fillStyle=main;ctx.lineWidth=4*s;ctx.lineCap='round';
  if(kind==='magnet'){ctx.beginPath();ctx.arc(0,-2*s,10*s,.05*Math.PI,.95*Math.PI);ctx.stroke();ctx.fillRect(-13*s,-6*s,5*s,9*s);ctx.fillRect(8*s,-6*s,5*s,9*s)}
  else if(kind==='shield'){polygon([[0,-12*s],[10*s,-7*s],[8*s,6*s],[0,13*s],[-8*s,6*s],[-10*s,-7*s]],'rgba(121,229,255,.3)',main,2*s)}
  else{polygon([[3*s,-13*s],[-7*s,2*s],[0,2*s],[-3*s,13*s],[9*s,-4*s],[2*s,-4*s]],main,null)}
}
function drawVent(s){
  const r=28*s;ctx.shadowColor='#853be0';ctx.shadowBlur=12*s;ctx.fillStyle='#11121b';ctx.strokeStyle='#9a5adc';ctx.lineWidth=3*s;ctx.beginPath();ctx.ellipse(0,0,r,r*.48,0,0,Math.PI*2);ctx.fill();ctx.stroke();ctx.strokeStyle='#d1a2ff';ctx.lineWidth=1.6*s;for(let i=0;i<6;i++){const x=-r*.65+i*r*.26;ctx.beginPath();ctx.moveTo(x,-r*.32);ctx.lineTo(x+r*.2,r*.32);ctx.stroke()}
}
function drawWave(s){
  const w=95*s,h=45*s,g=ctx.createLinearGradient(-w/2,0,w/2,0);g.addColorStop(0,'rgba(104,47,213,.06)');g.addColorStop(.5,'rgba(231,112,255,.88)');g.addColorStop(1,'rgba(72,191,255,.06)');ctx.shadowColor='#dc60ff';ctx.shadowBlur=24*s;ctx.fillStyle=g;ctx.fillRect(-w/2,-h/2,w,h);ctx.strokeStyle='#f5d5ff';ctx.lineWidth=1.8*s;ctx.strokeRect(-w/2,-h/2,w,h);ctx.strokeStyle='rgba(255,255,255,.55)';for(let i=-2;i<=2;i++){ctx.beginPath();ctx.moveTo(i*w*.15,-h/2);ctx.lineTo((i+1)*w*.15,h/2);ctx.stroke()}
}
function drawObject(o){
  const z=Math.max(0,o.z),x=laneX(o.lane,z),y=objectY(z),s=objectScale(z);ctx.save();ctx.translate(x,y);
  if(o.type==='orb'){ctx.rotate(Math.sin(o.phase)*.09);drawCrystal(s)}
  else if(o.type==='gold')drawGold(s);
  else if(o.type==='barrier')drawBarrier(s);
  else if(o.type==='drone')drawDrone(s,o.phase);
  else if(o.type==='power')drawPower(o.kind||'magnet',s);
  else if(o.type==='vent')drawVent(s);
  else if(o.type==='wave')drawWave(s);
  ctx.restore();
}
function drawHero(t){
  const x=laneX(laneVisual,1),baseY=H*.84,jumpProgress=jump>0?1-jump/.78:0,jumpHeight=jump>0?Math.sin(jumpProgress*Math.PI)*H*.18:0,sliding=slide>0,y=baseY-jumpHeight;
  const scale=Math.min(1.25,H/760)*(.92+Math.min(W,430)/430*.08),runPhase=t*.014;
  ctx.save();ctx.globalAlpha=.55;ctx.fillStyle='#02030a';ctx.shadowColor=shield?'#8de7ff':'#9d4bff';ctx.shadowBlur=shield?25:14;ctx.beginPath();ctx.ellipse(x,baseY+5,31*scale,9*(sliding?1.5:1)*scale,0,0,Math.PI*2);ctx.fill();ctx.restore();
  if(magnet>0){ctx.save();ctx.globalAlpha=.28+.08*Math.sin(t*.008);ctx.strokeStyle='#d197ff';ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(x,y-54*scale,55*scale+i*10*scale,0,Math.PI*2);ctx.stroke()}ctx.restore()}
  if(shield){ctx.save();ctx.globalAlpha=.5+.12*Math.sin(t*.01);ctx.strokeStyle='#8be7ff';ctx.lineWidth=3;ctx.shadowColor='#72dfff';ctx.shadowBlur=20;ctx.beginPath();ctx.ellipse(x,y-54*scale,43*scale,68*scale,0,0,Math.PI*2);ctx.stroke();ctx.restore()}

  ctx.save();ctx.translate(x,y);ctx.rotate((lane-laneVisual)*-.22);
  if(sliding){
    ctx.shadowColor='#9e4eff';ctx.shadowBlur=16;ctx.strokeStyle='#f2e7ff';ctx.lineWidth=8*scale;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-30*scale,-18*scale);ctx.lineTo(20*scale,-29*scale);ctx.lineTo(37*scale,-12*scale);ctx.stroke();
    ctx.fillStyle='#181024';ctx.strokeStyle='#b76cff';ctx.lineWidth=2*scale;roundedRect(-31*scale,-42*scale,56*scale,25*scale,10*scale,'#181024','#b76cff',2*scale);
    ctx.fillStyle='#d4b4a7';ctx.beginPath();ctx.arc(-27*scale,-49*scale,11*scale,0,Math.PI*2);ctx.fill();
  }else{
    const leg=Math.sin(runPhase)*16*scale,arm=Math.sin(runPhase+Math.PI)*12*scale,bob=Math.sin(runPhase*2)*2*scale;
    ctx.translate(0,bob);ctx.lineCap='round';ctx.lineJoin='round';ctx.shadowColor='#9e4eff';ctx.shadowBlur=18;
    ctx.strokeStyle='#ede8f5';ctx.lineWidth=8*scale;ctx.beginPath();ctx.moveTo(-5*scale,-42*scale);ctx.lineTo(-13*scale,-18*scale);ctx.lineTo(-13*scale+leg,0);ctx.moveTo(4*scale,-41*scale);ctx.lineTo(12*scale,-18*scale);ctx.lineTo(12*scale-leg,0);ctx.stroke();
    ctx.strokeStyle='#d9cdec';ctx.lineWidth=6*scale;ctx.beginPath();ctx.moveTo(-14*scale,-80*scale);ctx.lineTo(-25*scale,-56*scale);ctx.lineTo(-25*scale+arm,-43*scale);ctx.moveTo(14*scale,-79*scale);ctx.lineTo(25*scale,-58*scale);ctx.lineTo(25*scale-arm,-43*scale);ctx.stroke();
    const jacket=ctx.createLinearGradient(-22*scale,-94*scale,22*scale,-39*scale);jacket.addColorStop(0,'#30174d');jacket.addColorStop(.5,'#7f3ed0');jacket.addColorStop(1,'#1b102d');polygon([[-18*scale,-92*scale],[17*scale,-92*scale],[22*scale,-49*scale],[7*scale,-39*scale],[-14*scale,-43*scale],[-22*scale,-63*scale]],jacket,'#c286ff',1.7*scale);
    ctx.fillStyle='#d8b6a5';ctx.beginPath();ctx.arc(0,-107*scale,13*scale,0,Math.PI*2);ctx.fill();ctx.fillStyle='#15101d';ctx.beginPath();ctx.arc(-2*scale,-111*scale,13*scale,Math.PI,Math.PI*2);ctx.fill();
    ctx.fillStyle='#70dfff';ctx.shadowColor='#70dfff';ctx.shadowBlur=8;ctx.fillRect(6*scale,-108*scale,5*scale,2*scale);
    ctx.fillStyle='rgba(174,77,255,.22)';ctx.beginPath();ctx.moveTo(-18*scale,-82*scale);ctx.lineTo(-38*scale,-60*scale);ctx.lineTo(-17*scale,-47*scale);ctx.closePath();ctx.fill();
  }
  ctx.restore();

  if(running&&!sliding){ctx.save();ctx.globalCompositeOperation='screen';const trail=ctx.createLinearGradient(x,y-15,x,baseY+62);trail.addColorStop(0,'rgba(153,68,255,.25)');trail.addColorStop(1,'rgba(72,204,255,0)');ctx.fillStyle=trail;ctx.beginPath();ctx.moveTo(x-16,y-14);ctx.lineTo(x+16,y-14);ctx.lineTo(x+38,baseY+70);ctx.lineTo(x-38,baseY+70);ctx.closePath();ctx.fill();ctx.restore()}
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
