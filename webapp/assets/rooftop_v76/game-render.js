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
  r=Math.min(r,w/2,h/2);
  ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill()}
  if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke()}
}

function drawSky(t){
  const sky=ctx.createLinearGradient(0,0,0,H);
  sky.addColorStop(0,'#05010f');sky.addColorStop(.23,'#1c0739');sky.addColorStop(.56,'#10091f');sky.addColorStop(1,'#020309');
  ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);

  const glow=ctx.createRadialGradient(W*.50,H*.12,0,W*.50,H*.12,Math.max(W,H)*.66);
  glow.addColorStop(0,'rgba(163,55,255,.30)');glow.addColorStop(.31,'rgba(83,31,164,.15)');glow.addColorStop(1,'rgba(7,2,18,0)');
  ctx.fillStyle=glow;ctx.fillRect(0,0,W,H*.82);

  ctx.save();
  for(let i=0;i<54;i++){
    const x=hashNoise(i*7.1)*W,y=hashNoise(i*9.7+8)*H*.43,r=.4+hashNoise(i*3.7)*1.15;
    ctx.globalAlpha=.13+hashNoise(i*2.3)*.50;ctx.fillStyle=i%11===0?'#dfb8ff':'#ffffff';ctx.fillRect(x,y,r,r);
  }
  ctx.restore();

  const moonX=W*.83,moonY=H*.105,moonR=Math.min(W,H)*.046;
  ctx.save();ctx.shadowColor='#bea0ff';ctx.shadowBlur=24;ctx.fillStyle='#dcd1ff';ctx.beginPath();ctx.arc(moonX,moonY,moonR,0,Math.PI*2);ctx.fill();
  ctx.globalCompositeOperation='destination-out';ctx.beginPath();ctx.arc(moonX+moonR*.43,moonY-moonR*.10,moonR*.92,0,Math.PI*2);ctx.fill();ctx.restore();

  ctx.save();ctx.globalAlpha=.11;ctx.fillStyle='#b77aff';
  for(let i=0;i<4;i++){
    const y=H*(.18+i*.072),offset=((t*.005*(i+1))%(W*.7))-W*.34;
    ctx.beginPath();ctx.ellipse(offset+W*.42,y,W*(.18+i*.03),H*.016,0,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();
}

function drawCityLayer(t,depth,count,baseY,maxH,alpha){
  const travel=(distance*(depth===0?.16:.29)+t*(depth===0?.00055:.0011))%1;
  ctx.save();ctx.globalAlpha=alpha;
  for(let i=-2;i<count+2;i++){
    const n=i+Math.floor(travel*count),unit=W/count;
    const x=i*unit-(travel*count%1)*unit;
    const bw=unit*(.64+hashNoise(n*1.31+depth*41)*.68);
    const bh=maxH*(.30+hashNoise(n*2.17+depth*17)*.70);
    const top=baseY-bh;
    const body=ctx.createLinearGradient(x,top,x+bw,baseY);
    body.addColorStop(0,depth===0?'#171028':'#0c0918');body.addColorStop(1,depth===0?'#050711':'#03040a');
    ctx.fillStyle=body;ctx.fillRect(x,top,bw,bh);
    ctx.fillStyle=depth===0?'rgba(188,95,255,.25)':'rgba(127,68,205,.13)';ctx.fillRect(x,top,bw,1.1);
    if(hashNoise(n*6.2)>.66){ctx.fillStyle='#0e0d1b';ctx.fillRect(x+bw*.42,top-bh*.11,bw*.16,bh*.11)}
    if(depth===0){
      const cols=Math.max(2,Math.floor(bw/14)),rows=Math.max(2,Math.floor(bh/18));
      for(let cy=1;cy<rows;cy++)for(let cx=1;cx<cols;cx++){
        if(hashNoise(n*100+cy*11+cx*3)<.48)continue;
        const wx=x+cx*bw/cols-1.2,wy=top+cy*bh/rows;
        ctx.fillStyle=hashNoise(n+cy*4+cx)>.84?'rgba(255,205,105,.72)':'rgba(159,80,255,.38)';ctx.fillRect(wx,wy,2.1,3.2);
      }
    }
  }
  ctx.restore();
}

function drawNeonSigns(t){
  ctx.save();
  const pulse=.70+.20*Math.sin(t*.004);
  ctx.shadowBlur=16;ctx.font=`900 ${Math.max(9,W*.022)}px system-ui`;ctx.textAlign='center';
  const signs=[
    {x:W*.12,y:H*.36,text:'REALITY',color:'#df65ff',a:-.07},
    {x:W*.88,y:H*.42,text:'EGO',color:'#5ee6ff',a:.08}
  ];
  for(const sign of signs){
    ctx.save();ctx.translate(sign.x,sign.y);ctx.rotate(sign.a);ctx.globalAlpha=pulse;ctx.shadowColor=sign.color;
    roundedRect(-W*.09,-H*.018,W*.18,H*.036,5,'rgba(5,5,14,.88)',sign.color,1.3);
    ctx.fillStyle=sign.color;ctx.fillText(sign.text,0,H*.006);ctx.restore();
  }
  ctx.restore();
}

function drawRoofTrack(t){
  const horizonY=H*.245,leftFar=W*.43,rightFar=W*.57,leftNear=-W*.10,rightNear=W*1.10;
  const roof=ctx.createLinearGradient(0,horizonY,0,H);
  roof.addColorStop(0,'#141122');roof.addColorStop(.44,'#0b0e18');roof.addColorStop(1,'#03050a');
  polygon([[leftFar,horizonY],[rightFar,horizonY],[rightNear,H],[leftNear,H]],roof,'rgba(172,86,255,.52)',1.35);

  const edgeGlow=ctx.createLinearGradient(0,horizonY,0,H);edgeGlow.addColorStop(0,'rgba(189,95,255,.30)');edgeGlow.addColorStop(1,'rgba(73,211,255,.70)');
  ctx.save();ctx.strokeStyle=edgeGlow;ctx.lineWidth=2.4;ctx.shadowColor='#8d4eff';ctx.shadowBlur=12;
  ctx.beginPath();ctx.moveTo(leftFar,horizonY);ctx.lineTo(leftNear,H);ctx.moveTo(rightFar,horizonY);ctx.lineTo(rightNear,H);ctx.stroke();ctx.restore();

  for(let laneIndex=0;laneIndex<2;laneIndex++){
    const farX=laneX(laneIndex+.5,0),nearX=laneX(laneIndex+.5,1.18);
    ctx.strokeStyle='rgba(212,172,255,.19)';ctx.lineWidth=1.15;ctx.setLineDash([8,12]);
    ctx.beginPath();ctx.moveTo(farX,horizonY);ctx.lineTo(nearX,H);ctx.stroke();ctx.setLineDash([]);
  }

  const scroll=(distance*.027)%1;
  for(let i=0;i<17;i++){
    const z=(i/17+scroll)%1,y=objectY(z),left=laneX(-.74,z),right=laneX(2.74,z);
    ctx.strokeStyle=`rgba(178,137,213,${.028+z*.10})`;ctx.lineWidth=.65+z*1.0;
    ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
  }

  for(let i=0;i<12;i++){
    const z=((i/12)+(distance*.014)%1)%1,x=laneX(i%3,z),y=objectY(z),r=.8+z*2.8;
    ctx.fillStyle=`rgba(67,213,255,${.05+z*.15})`;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
  }

  ctx.save();ctx.globalAlpha=.74;
  const sideScroll=(distance*.014)%1;
  for(let i=0;i<9;i++){
    const z=(i/9+sideScroll)%1,y=objectY(z),s=.26+z*.88;
    const leftX=laneX(-1.05,z),rightX=laneX(3.05,z);
    ctx.fillStyle='#070a10';ctx.strokeStyle='rgba(156,79,222,.28)';ctx.lineWidth=.8+s;
    ctx.fillRect(leftX-30*s,y-20*s,40*s,20*s);ctx.strokeRect(leftX-30*s,y-20*s,40*s,20*s);
    if(i%2===0){ctx.fillRect(rightX-8*s,y-35*s,24*s,35*s);ctx.strokeRect(rightX-8*s,y-35*s,24*s,35*s)}
  }
  ctx.restore();

  ctx.save();ctx.globalAlpha=.22;ctx.strokeStyle='#af5fff';ctx.lineWidth=1;
  for(const side of [-1,1]){
    const sx=side<0?W*.03:W*.97;ctx.beginPath();ctx.moveTo(sx,H*.66);ctx.lineTo(side<0?W*.34:W*.66,H*.31);ctx.stroke();
  }
  ctx.restore();
}

function drawAttackTelegraph(t){
  if(bossTelegraph<=0||bossSafeLane<0)return;
  const progress=1-clamp01(bossTelegraph/1.18);
  const pulse=.20+.13*Math.sin(t*.026)+progress*.18;
  for(let laneIndex=0;laneIndex<3;laneIndex++){
    const safe=laneIndex===bossSafeLane;
    const farY=H*.245,nearY=H;
    const points=[
      [laneX(laneIndex-.46,0),farY],
      [laneX(laneIndex+.46,0),farY],
      [laneX(laneIndex+.46,1.15),nearY],
      [laneX(laneIndex-.46,1.15),nearY]
    ];
    const g=ctx.createLinearGradient(0,farY,0,nearY);
    if(safe){g.addColorStop(0,'rgba(56,238,255,.02)');g.addColorStop(1,'rgba(56,238,255,.10)')}
    else{g.addColorStop(0,'rgba(255,48,171,.03)');g.addColorStop(1,`rgba(255,42,152,${pulse})`)}
    polygon(points,g,safe?'rgba(79,234,255,.38)':'rgba(255,74,188,.65)',safe?1:1.8);
    if(!safe){
      ctx.save();ctx.globalAlpha=.22+progress*.38;ctx.strokeStyle='#ffd4f3';ctx.lineWidth=1.2;ctx.setLineDash([7,10]);
      ctx.beginPath();ctx.moveTo(laneX(laneIndex,0),farY);ctx.lineTo(laneX(laneIndex,1.1),nearY);ctx.stroke();ctx.setLineDash([]);ctx.restore();
    }
  }
}

function drawBackground(t){
  drawSky(t);
  drawCityLayer(t,1,13,H*.37,H*.20,.40);
  drawCityLayer(t,0,18,H*.49,H*.30,.70);
  drawNeonSigns(t);
  drawRoofTrack(t);
  drawAttackTelegraph(t);
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'rgba(3,1,9,.04)');shade.addColorStop(.68,'rgba(2,3,8,.01)');shade.addColorStop(1,'rgba(0,0,0,.38)');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
  ctx.save();ctx.strokeStyle='rgba(194,158,255,.25)';ctx.lineWidth=1;
  for(const r of rain){ctx.globalAlpha=r.a;ctx.beginPath();ctx.moveTo(r.x,r.y);ctx.lineTo(r.x-3,r.y+r.l);ctx.stroke()}
  ctx.restore();
}

function drawBoss(t){
  const attack=bossTelegraph>0?clamp01(1-bossTelegraph/1.18):0;
  const pulse=1+Math.sin(t*.0026)*.04+bossPulse*.14;
  const cx=W/2,cy=H*.158,r=Math.min(W*.155,H*.102)*pulse;

  if(bossTelegraph>0){
    ctx.save();ctx.fillStyle=`rgba(2,0,7,${.08+attack*.14})`;ctx.fillRect(0,0,W,H*.57);ctx.restore();
  }

  ctx.save();ctx.translate(cx,cy);

  for(let i=0;i<6;i++){
    const drift=Math.sin(t*.0015+i*1.7);
    ctx.globalAlpha=.08+i*.025+bossPulse*.03;
    ctx.fillStyle=i%2?'#39105f':'#13051f';
    ctx.beginPath();ctx.ellipse(drift*r*.30,r*(.35+i*.12),r*(1.6+i*.14),r*(.54+i*.08),drift*.10,0,Math.PI*2);ctx.fill();
  }

  ctx.save();ctx.globalCompositeOperation='screen';
  for(let i=0;i<4;i++){
    ctx.save();ctx.rotate(t*.00010*(i%2?1:-1)+i*.32);ctx.globalAlpha=.10+i*.055+bossPulse*.10;
    ctx.strokeStyle=i%2?'#54ddff':'#c43fff';ctx.lineWidth=1.2+i*.65;ctx.setLineDash([7+i*3,9+i*2]);
    ctx.beginPath();ctx.arc(0,0,r*(1.45+i*.27),0,Math.PI*2);ctx.stroke();ctx.restore();
  }
  ctx.restore();ctx.setLineDash([]);

  const aura=ctx.createRadialGradient(0,0,r*.08,0,0,r*2.3);
  aura.addColorStop(0,'rgba(255,195,255,.36)');aura.addColorStop(.28,'rgba(169,48,255,.24)');aura.addColorStop(1,'rgba(72,7,135,0)');
  ctx.fillStyle=aura;ctx.beginPath();ctx.arc(0,0,r*2.3,0,Math.PI*2);ctx.fill();

  ctx.shadowColor='#a431ff';ctx.shadowBlur=30+bossPulse*26;
  const silhouette=[];
  for(let i=0;i<24;i++){
    const a=-Math.PI+i*Math.PI*2/24;
    const spike=i%3===0?1.16:1;
    silhouette.push([Math.cos(a)*r*1.18*spike,Math.sin(a)*r*.82*spike]);
  }
  const body=ctx.createLinearGradient(0,-r,0,r);
  body.addColorStop(0,'#22083b');body.addColorStop(.52,'#0d0318');body.addColorStop(1,'#030007');
  polygon(silhouette,body,'#c866ff',2.1);

  ctx.strokeStyle='#ffd166';ctx.lineWidth=2.5;ctx.shadowColor='#ffd166';ctx.shadowBlur=10;
  ctx.beginPath();ctx.moveTo(-r*.92,-r*.66);ctx.lineTo(-r*.58,-r*1.48);ctx.lineTo(-r*.22,-r*.83);ctx.lineTo(0,-r*1.66);ctx.lineTo(r*.22,-r*.83);ctx.lineTo(r*.58,-r*1.48);ctx.lineTo(r*.92,-r*.66);ctx.stroke();

  const eyeOpen=.32+attack*.12+bossPulse*.04;
  const eye=ctx.createRadialGradient(-r*.08,-r*.07,1,0,0,r*.86);
  eye.addColorStop(0,'#fff');eye.addColorStop(.16,'#ffd5f8');eye.addColorStop(.44,'#d54cff');eye.addColorStop(1,'#3b075e');
  ctx.fillStyle=eye;ctx.shadowColor='#e357ff';ctx.shadowBlur=22+attack*18;
  ctx.beginPath();ctx.ellipse(0,0,r*.86,r*eyeOpen,0,0,Math.PI*2);ctx.fill();

  const pupilX=(laneVisual-1)*r*.12,pupilY=-jumpArc()*r*.05;
  ctx.fillStyle='#050008';ctx.shadowBlur=0;ctx.beginPath();ctx.ellipse(pupilX,pupilY,r*(.16+attack*.035),r*(.19+attack*.045),0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(pupilX-r*.055,pupilY-r*.07,r*.045,0,Math.PI*2);ctx.fill();

  ctx.strokeStyle='rgba(113,220,255,.50)';ctx.lineWidth=2;ctx.shadowColor='#58dfff';ctx.shadowBlur=9;
  for(const side of [-1,1]){
    ctx.beginPath();ctx.moveTo(side*r*.62,r*.52);ctx.bezierCurveTo(side*r*1.55,r*.92,side*r*.28,r*1.42,side*r*1.02,r*1.92);ctx.stroke();
    ctx.beginPath();ctx.moveTo(side*r*.82,r*.25);ctx.bezierCurveTo(side*r*1.38,r*.62,side*r*.82,r*1.02,side*r*1.52,r*1.34);ctx.stroke();
  }

  if(bossPulse>.08){
    ctx.globalAlpha=clamp01(bossPulse)*.55;ctx.strokeStyle='#f2a0ff';ctx.lineWidth=2.2;ctx.shadowColor='#e650ff';ctx.shadowBlur=18;
    ctx.beginPath();ctx.arc(0,0,r*(1.3+(1.35-bossPulse)*.58),0,Math.PI*2);ctx.stroke();
  }
  ctx.restore();
}

function drawCrystal(s){
  const h=42*s,w=24*s;ctx.shadowColor='#c66cff';ctx.shadowBlur=17*s;
  const g=ctx.createLinearGradient(-w/2,-h/2,w/2,h/2);g.addColorStop(0,'#fff0ff');g.addColorStop(.25,'#d78aff');g.addColorStop(.66,'#7a29d0');g.addColorStop(1,'#31065e');
  polygon([[0,-h/2],[w/2,-h*.13],[w*.32,h*.42],[0,h/2],[-w*.32,h*.42],[-w/2,-h*.13]],g,'#f6d6ff',1.15*s);
  ctx.strokeStyle='rgba(255,255,255,.58)';ctx.lineWidth=.8*s;ctx.beginPath();ctx.moveTo(0,-h/2);ctx.lineTo(0,h/2);ctx.moveTo(-w/2,-h*.13);ctx.lineTo(w*.32,h*.42);ctx.stroke();
}
function drawGold(s){
  const r=13*s;ctx.shadowColor='#ffd45f';ctx.shadowBlur=18*s;ctx.fillStyle='#ffcc46';ctx.beginPath();
  for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.47:r,px=Math.cos(a)*rr,py=Math.sin(a)*rr;i?ctx.lineTo(px,py):ctx.moveTo(px,py)}
  ctx.closePath();ctx.fill();ctx.fillStyle='#fff1a1';ctx.beginPath();ctx.arc(0,0,r*.28,0,Math.PI*2);ctx.fill();
}
function drawBarrier(s){
  const w=108*s,h=46*s;ctx.shadowColor='#b02fff';ctx.shadowBlur=16*s;
  roundedRect(-w/2,-h*.82,w,h,7*s,'#100b19','#dc78ff',2*s);
  ctx.save();ctx.beginPath();ctx.rect(-w/2+4*s,-h*.82+4*s,w-8*s,h-8*s);ctx.clip();ctx.strokeStyle='#ffd260';ctx.lineWidth=7*s;
  for(let x=-w;x<w;x+=23*s){ctx.beginPath();ctx.moveTo(x,-h);ctx.lineTo(x+55*s,h);ctx.stroke()}
  ctx.restore();
  ctx.fillStyle='#633092';ctx.fillRect(-w*.38,h*.18,w*.12,h*.34);ctx.fillRect(w*.26,h*.18,w*.12,h*.34);
  ctx.fillStyle='#ff4aa8';ctx.shadowColor='#ff4aa8';ctx.shadowBlur=10;ctx.beginPath();ctx.arc(-w*.39,-h*.60,3.2*s,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(w*.39,-h*.60,3.2*s,0,Math.PI*2);ctx.fill();
}
function drawDrone(s,phase){
  const w=80*s,h=29*s;ctx.translate(0,Math.sin(phase)*3*s-25*s);ctx.shadowColor='#52dfff';ctx.shadowBlur=18*s;
  roundedRect(-w*.29,-h*.46,w*.58,h*.92,h*.3,'#0c0d16','#7be8ff',1.5*s);
  ctx.strokeStyle='#a15cff';ctx.lineWidth=3*s;ctx.beginPath();ctx.moveTo(-w*.22,0);ctx.lineTo(-w*.48,-h*.12);ctx.moveTo(w*.22,0);ctx.lineTo(w*.48,-h*.12);ctx.stroke();
  for(const dir of [-1,1]){ctx.strokeStyle='#dfd6ff';ctx.lineWidth=1*s;ctx.beginPath();ctx.ellipse(dir*w*.5,-h*.15,w*.18,h*.08,0,0,Math.PI*2);ctx.stroke()}
  ctx.fillStyle='#ff3f91';ctx.shadowColor='#ff3f91';ctx.shadowBlur=12;ctx.beginPath();ctx.arc(0,h*.06,4*s,0,Math.PI*2);ctx.fill();
}
function drawPower(kind,s){
  const r=21*s,main=kind==='shield'?'#79e5ff':kind==='magnet'?'#d77aff':'#ffd86a';
  ctx.shadowColor=main;ctx.shadowBlur=20*s;ctx.fillStyle='rgba(7,6,18,.96)';ctx.strokeStyle=main;ctx.lineWidth=2*s;ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.strokeStyle=main;ctx.fillStyle=main;ctx.lineWidth=4*s;ctx.lineCap='round';
  if(kind==='magnet'){ctx.beginPath();ctx.arc(0,-2*s,10*s,.05*Math.PI,.95*Math.PI);ctx.stroke();ctx.fillRect(-13*s,-6*s,5*s,9*s);ctx.fillRect(8*s,-6*s,5*s,9*s)}
  else if(kind==='shield')polygon([[0,-12*s],[10*s,-7*s],[8*s,6*s],[0,13*s],[-8*s,6*s],[-10*s,-7*s]],'rgba(121,229,255,.3)',main,2*s);
  else polygon([[3*s,-13*s],[-7*s,2*s],[0,2*s],[-3*s,13*s],[9*s,-4*s],[2*s,-4*s]],main,null);
}
function drawVent(s){
  const r=27*s;ctx.shadowColor='#853be0';ctx.shadowBlur=12*s;ctx.fillStyle='#090b11';ctx.strokeStyle='#a45ee8';ctx.lineWidth=3*s;ctx.beginPath();ctx.ellipse(0,0,r,r*.47,0,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.strokeStyle='#d5a4ff';ctx.lineWidth=1.5*s;for(let i=0;i<6;i++){const x=-r*.65+i*r*.26;ctx.beginPath();ctx.moveTo(x,-r*.32);ctx.lineTo(x+r*.2,r*.32);ctx.stroke()}
}
function drawWave(s){
  const w=92*s,h=43*s,g=ctx.createLinearGradient(-w/2,0,w/2,0);g.addColorStop(0,'rgba(86,31,187,.04)');g.addColorStop(.5,'rgba(246,71,201,.92)');g.addColorStop(1,'rgba(60,204,255,.05)');
  ctx.shadowColor='#ff42c9';ctx.shadowBlur=25*s;ctx.fillStyle=g;ctx.fillRect(-w/2,-h/2,w,h);ctx.strokeStyle='#ffd4f6';ctx.lineWidth=1.8*s;ctx.strokeRect(-w/2,-h/2,w,h);
  ctx.strokeStyle='rgba(255,255,255,.54)';for(let i=-2;i<=2;i++){ctx.beginPath();ctx.moveTo(i*w*.15,-h/2);ctx.lineTo((i+1)*w*.15,h/2);ctx.stroke()}
}
function drawObject(o){
  const rawZ=o.z,z=Math.max(0,rawZ),x=laneX(o.lane,z),y=objectY(z),s=objectScale(z,o.type);
  ctx.save();ctx.translate(x,y);ctx.globalAlpha=clamp01((rawZ+.14)/.14);
  if(o.type==='orb'){ctx.rotate(Math.sin(o.phase)*.08);drawCrystal(s)}
  else if(o.type==='gold')drawGold(s);
  else if(o.type==='barrier')drawBarrier(s);
  else if(o.type==='drone')drawDrone(s,o.phase);
  else if(o.type==='power')drawPower(o.kind||'magnet',s);
  else if(o.type==='vent')drawVent(s);
  else if(o.type==='wave')drawWave(s);
  ctx.restore();
}

function drawHero(t){
  const x=laneX(laneVisual,1),baseY=H*.84,jumpRatio=jumpArc(),jumpHeight=jumpRatio*H*.19,sliding=slide>0,y=baseY-jumpHeight;
  const scale=Math.min(1.34,H/760)*(.96+Math.min(W,430)/430*.10),runPhase=t*.014;

  ctx.save();ctx.globalAlpha=.55-jumpRatio*.22;ctx.fillStyle='#010207';ctx.shadowColor=shield?'#8de7ff':'#9d4bff';ctx.shadowBlur=shield?25:14;
  ctx.beginPath();ctx.ellipse(x,baseY+5,(31-jumpRatio*8)*scale,(9-jumpRatio*2)*(sliding?1.5:1)*scale,0,0,Math.PI*2);ctx.fill();ctx.restore();

  if(magnet>0){ctx.save();ctx.globalAlpha=.27+.08*Math.sin(t*.008);ctx.strokeStyle='#d197ff';ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(x,y-54*scale,55*scale+i*10*scale,0,Math.PI*2);ctx.stroke()}ctx.restore()}
  if(shield){ctx.save();ctx.globalAlpha=.48+.12*Math.sin(t*.01);ctx.strokeStyle='#8be7ff';ctx.lineWidth=3;ctx.shadowColor='#72dfff';ctx.shadowBlur=20;ctx.beginPath();ctx.ellipse(x,y-54*scale,43*scale,68*scale,0,0,Math.PI*2);ctx.stroke();ctx.restore()}

  ctx.save();ctx.translate(x,y);ctx.rotate((lane-laneVisual)*-.22+jumpRatio*.04);
  ctx.lineCap='round';ctx.lineJoin='round';ctx.shadowColor='#9e4eff';ctx.shadowBlur=18;

  if(sliding){
    ctx.strokeStyle='#f2e7ff';ctx.lineWidth=8*scale;ctx.beginPath();ctx.moveTo(-30*scale,-18*scale);ctx.lineTo(20*scale,-29*scale);ctx.lineTo(37*scale,-12*scale);ctx.stroke();
    roundedRect(-31*scale,-42*scale,56*scale,25*scale,10*scale,'#141020','#c06cff',2*scale);
    ctx.fillStyle='#d4b4a7';ctx.beginPath();ctx.arc(-27*scale,-49*scale,11*scale,0,Math.PI*2);ctx.fill();
  }else{
    const airborne=jumpRatio>.06;
    const leg=airborne?19*scale:Math.sin(runPhase)*16*scale;
    const arm=airborne?14*scale:Math.sin(runPhase+Math.PI)*12*scale;
    const bob=airborne?0:Math.sin(runPhase*2)*2*scale;
    ctx.translate(0,bob);

    ctx.strokeStyle='#eeeaf5';ctx.lineWidth=8*scale;ctx.beginPath();
    ctx.moveTo(-5*scale,-42*scale);ctx.lineTo(-13*scale,-18*scale);ctx.lineTo(-13*scale+leg,airborne?-5*scale:0);
    ctx.moveTo(4*scale,-41*scale);ctx.lineTo(12*scale,-18*scale);ctx.lineTo(12*scale-leg,airborne?-11*scale:0);ctx.stroke();

    ctx.strokeStyle='#d9cdec';ctx.lineWidth=6*scale;ctx.beginPath();
    ctx.moveTo(-14*scale,-80*scale);ctx.lineTo(-25*scale,-56*scale);ctx.lineTo(-25*scale+arm,-43*scale);
    ctx.moveTo(14*scale,-79*scale);ctx.lineTo(25*scale,-58*scale);ctx.lineTo(25*scale-arm,-43*scale);ctx.stroke();

    const jacket=ctx.createLinearGradient(-22*scale,-94*scale,22*scale,-39*scale);jacket.addColorStop(0,'#24103e');jacket.addColorStop(.48,'#8540d8');jacket.addColorStop(1,'#140b22');
    polygon([[-18*scale,-92*scale],[17*scale,-92*scale],[22*scale,-49*scale],[7*scale,-39*scale],[-14*scale,-43*scale],[-22*scale,-63*scale]],jacket,'#cf85ff',1.7*scale);
    ctx.fillStyle='#d8b6a5';ctx.beginPath();ctx.arc(0,-107*scale,13*scale,0,Math.PI*2);ctx.fill();
    ctx.fillStyle='#100c16';ctx.beginPath();ctx.arc(-2*scale,-111*scale,13*scale,Math.PI,Math.PI*2);ctx.fill();
    ctx.fillStyle='#65e6ff';ctx.shadowColor='#65e6ff';ctx.shadowBlur=9;ctx.fillRect(6*scale,-108*scale,5*scale,2*scale);

    const cape=ctx.createLinearGradient(-40*scale,-80*scale,-15*scale,-42*scale);cape.addColorStop(0,'rgba(192,70,255,.02)');cape.addColorStop(1,'rgba(192,70,255,.42)');
    polygon([[-18*scale,-83*scale],[-45*scale,-61*scale],[-18*scale,-44*scale]],cape,'rgba(208,117,255,.18)',1);
  }
  ctx.restore();

  if(running&&!sliding){
    ctx.save();ctx.globalCompositeOperation='screen';const trail=ctx.createLinearGradient(x,y-15,x,baseY+68);
    trail.addColorStop(0,'rgba(185,89,255,.36)');trail.addColorStop(.45,'rgba(79,220,255,.18)');trail.addColorStop(1,'rgba(72,204,255,0)');
    ctx.fillStyle=trail;ctx.beginPath();ctx.moveTo(x-16,y-14);ctx.lineTo(x+16,y-14);ctx.lineTo(x+40,baseY+72);ctx.lineTo(x-40,baseY+72);ctx.closePath();ctx.fill();ctx.restore();
  }
}

function drawEffects(t){
  if(running){
    ctx.save();ctx.strokeStyle='rgba(158,105,255,.12)';ctx.lineWidth=1;
    for(let i=0;i<8;i++){
      const phase=(i/8+(distance*.012)%1)%1,x=laneX((i%3)-.2,phase),y=objectY(phase);
      ctx.globalAlpha=.04+phase*.15;ctx.beginPath();ctx.moveTo(x,y-6-phase*18);ctx.lineTo(x,y+7+phase*26);ctx.stroke();
    }
    ctx.restore();
  }
  for(const p of particles){ctx.save();ctx.globalAlpha=Math.max(0,p.t);ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=10;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,Math.PI*2);ctx.fill();ctx.restore()}
  for(const f of floating){ctx.save();ctx.globalAlpha=Math.max(0,f.t);ctx.fillStyle=f.color;ctx.shadowColor='#000';ctx.shadowBlur=5;ctx.font='900 13px system-ui';ctx.textAlign='center';ctx.fillText(f.text,f.x,f.y);ctx.restore()}
  if(flash>0){ctx.save();ctx.globalAlpha=flash;ctx.fillStyle=hits?'#ff497a':'#d47aff';ctx.fillRect(0,0,W,H);ctx.restore()}
  const vignette=ctx.createRadialGradient(W/2,H*.55,Math.min(W,H)*.2,W/2,H*.55,Math.max(W,H)*.72);
  vignette.addColorStop(0,'rgba(0,0,0,0)');vignette.addColorStop(1,'rgba(0,0,0,.31)');ctx.fillStyle=vignette;ctx.fillRect(0,0,W,H);
}

function draw(t){
  ctx.save();
  if(shake>0)ctx.translate(Math.sin(t*.073)*shake*.52,Math.cos(t*.091)*shake*.42);
  drawBackground(t);drawBoss(t);
  for(const o of [...objects].sort((a,b)=>a.z-b.z))drawObject(o);
  drawHero(t);drawEffects(t);ctx.restore();
}
function drawIdle(){if(!W||!H)return;const now=performance.now();drawBackground(now);drawBoss(now);drawHero(now);drawEffects(now)}
function loop(now){if(!running)return;const dt=Math.min(.034,Math.max(.001,(now-lastFrame)/1000));lastFrame=now;update(dt);draw(now);if(running)requestAnimationFrame(loop)}
function formatTime(value){const seconds=Math.max(0,Math.ceil(value));return String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0')}

async function finishGame(reason){
  if(ended)return;
  ended=true;running=false;
  $('resultTitle').textContent=reason;$('resultScore').textContent=score;$('resultCombo').textContent=bestCombo;$('resultDistance').textContent=Math.round(distance)+' м';$('resultHits').textContent=hits;
  $('finish').classList.remove('hidden');$('result').style.display='block';$('reward').textContent=demo?'Демонстрационный режим: влияние не начисляется.':'Сохраняем результат на сервере…';
  if(sessionId&&!demo){
    try{
      const data=await api('finish',{session_id:sessionId,score,stats:{distance:Math.round(distance),best_combo:bestCombo,hits,lives_left:lives}});
      $('reward').innerHTML=`Базовая награда забега: <b>+${data.base_run_reward||0}</b><br>Начисляется за улучшение: <b>+${data.payable_base||0}</b><br>🌳 Бонус древа: <b>+${data.tree_bonus||0}</b><br>🏆 Получено влияния: <b>+${data.actual_reward||0}</b><br>Баланс: <b>${data.balance||0}</b><br><small>${data.message||''}</small>`;
    }catch(error){$('reward').textContent='Не удалось сохранить результат: '+error.message}
  }
}
function goGames(){location.href='/games/?chat_id='+encodeURIComponent(chatId)}

$('start').onclick=startGame;
$('again').onclick=()=>{if(demo){$('finish').classList.add('hidden');$('result').style.display='none';startGame()}else location.reload()};
$('back').onclick=goGames;
$('toGames').onclick=goGames;
$('ability').onclick=useAbility;

const stage=$('stage');
stage.addEventListener('pointerdown',event=>{
  event.preventDefault();touchStart={x:event.clientX,y:event.clientY,t:performance.now()};stage.setPointerCapture?.(event.pointerId);
});
stage.addEventListener('pointerup',event=>{
  event.preventDefault();
  if(!touchStart)return;
  const dx=event.clientX-touchStart.x,dy=event.clientY-touchStart.y,ax=Math.abs(dx),ay=Math.abs(dy);
  touchStart=null;
  if(Math.max(ax,ay)<18){useAbility();return}
  if(ax>ay*1.04)move(dx>0?1:-1);
  else if(dy<0)doJump();
  else doSlide();
});
stage.addEventListener('pointercancel',()=>{touchStart=null});
document.addEventListener('keydown',event=>{
  if(event.key==='ArrowLeft')move(-1);if(event.key==='ArrowRight')move(1);if(event.key==='ArrowUp')doJump();if(event.key==='ArrowDown')doSlide();if(event.code==='Space')useAbility();
});
requestAnimationFrame(()=>{resize();drawIdle()});
