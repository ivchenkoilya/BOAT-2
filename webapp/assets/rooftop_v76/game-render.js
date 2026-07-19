'use strict';

function clamp01(value){return Math.max(0,Math.min(1,value))}
function lerp(a,b,t){return a+(b-a)*t}
function hashNoise(value){const x=Math.sin(value*12.9898+seed*.0001)*43758.5453;return x-Math.floor(x)}
function polygon(points,fill,stroke,lineWidth=1){
  if(!points.length)return;
  ctx.beginPath();ctx.moveTo(points[0][0],points[0][1]);
  for(let i=1;i<points.length;i++)ctx.lineTo(points[i][0],points[i][1]);
  ctx.closePath();if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke()}
}
function roundedRect(x,y,w,h,r,fill,stroke,lineWidth=1){
  r=Math.min(r,w/2,h/2);ctx.beginPath();ctx.moveTo(x+r,y);ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
  if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=lineWidth;ctx.stroke()}
}
function drawLightPool(x,y,rx,ry,color,alpha=.3){
  ctx.save();ctx.translate(x,y);ctx.scale(1,ry/rx);
  const g=ctx.createRadialGradient(0,0,0,0,0,rx);g.addColorStop(0,color);g.addColorStop(.42,color.replace(/[^,]+\)$/,'0.12)'));g.addColorStop(1,'rgba(0,0,0,0)');
  ctx.globalAlpha=alpha;ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,rx,0,Math.PI*2);ctx.fill();ctx.restore();
}

function drawSky(t){
  const sky=ctx.createLinearGradient(0,0,0,H);
  sky.addColorStop(0,'#030008');sky.addColorStop(.20,'#16042f');sky.addColorStop(.50,'#0d0a1b');sky.addColorStop(1,'#010207');
  ctx.fillStyle=sky;ctx.fillRect(0,0,W,H);

  const glow=ctx.createRadialGradient(W*.50,H*.105,0,W*.50,H*.105,Math.max(W,H)*.70);
  glow.addColorStop(0,'rgba(171,52,255,.34)');glow.addColorStop(.28,'rgba(79,27,155,.16)');glow.addColorStop(1,'rgba(5,1,14,0)');
  ctx.fillStyle=glow;ctx.fillRect(0,0,W,H*.84);

  ctx.save();ctx.globalCompositeOperation='screen';
  for(let i=0;i<5;i++){
    const y=H*(.13+i*.068),shift=Math.sin(t*.00018+i)*W*.12;
    const band=ctx.createLinearGradient(0,y,W,y);
    band.addColorStop(0,'rgba(90,35,170,0)');band.addColorStop(.38,'rgba(179,73,255,.10)');band.addColorStop(.60,'rgba(74,213,255,.06)');band.addColorStop(1,'rgba(90,35,170,0)');
    ctx.globalAlpha=.55;ctx.fillStyle=band;ctx.beginPath();ctx.ellipse(W*.5+shift,y,W*(.29+i*.02),H*(.014+i*.003),0,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();

  ctx.save();
  for(let i=0;i<64;i++){
    const x=hashNoise(i*7.1)*W,y=hashNoise(i*9.7+8)*H*.42,r=.35+hashNoise(i*3.7)*1.15;
    const twinkle=.35+.65*Math.sin(t*.0017+i*2.1)*.5+.35;
    ctx.globalAlpha=(.08+hashNoise(i*2.3)*.45)*twinkle;ctx.fillStyle=i%13===0?'#e3bcff':'#ffffff';ctx.fillRect(x,y,r,r);
  }
  ctx.restore();

  const moonX=W*.84,moonY=H*.10,moonR=Math.min(W,H)*.043;
  ctx.save();
  const halo=ctx.createRadialGradient(moonX,moonY,moonR*.2,moonX,moonY,moonR*2.8);halo.addColorStop(0,'rgba(218,204,255,.34)');halo.addColorStop(1,'rgba(124,88,255,0)');ctx.fillStyle=halo;ctx.beginPath();ctx.arc(moonX,moonY,moonR*2.8,0,Math.PI*2);ctx.fill();
  ctx.shadowColor='#c3a9ff';ctx.shadowBlur=24;ctx.fillStyle='#ddd4ff';ctx.beginPath();ctx.arc(moonX,moonY,moonR,0,Math.PI*2);ctx.fill();
  ctx.globalCompositeOperation='destination-out';ctx.beginPath();ctx.arc(moonX+moonR*.43,moonY-moonR*.10,moonR*.92,0,Math.PI*2);ctx.fill();ctx.restore();
}

function drawCityLayer(t,depth,count,baseY,maxH,alpha){
  const travel=(distance*(depth===0?.15:depth===1?.08:.035)+t*(depth===0?.00046:depth===1?.00025:.00012))%1;
  ctx.save();ctx.globalAlpha=alpha;
  for(let i=-2;i<count+2;i++){
    const n=i+Math.floor(travel*count),unit=W/count,x=i*unit-(travel*count%1)*unit;
    const bw=unit*(.63+hashNoise(n*1.31+depth*41)*.68),bh=maxH*(.28+hashNoise(n*2.17+depth*17)*.72),top=baseY-bh;
    const body=ctx.createLinearGradient(x,top,x+bw,baseY);
    const topColor=depth===0?'#181027':depth===1?'#0c0a17':'#070710';
    const bottomColor=depth===0?'#03060d':depth===1?'#02040a':'#010207';
    body.addColorStop(0,topColor);body.addColorStop(1,bottomColor);ctx.fillStyle=body;ctx.fillRect(x,top,bw,bh);
    ctx.fillStyle=depth===0?'rgba(191,90,255,.22)':'rgba(110,67,190,.10)';ctx.fillRect(x,top,bw,1);

    if(hashNoise(n*6.2)>.64){
      const antennaH=bh*(.08+hashNoise(n*2.6)*.13);ctx.fillStyle='#090914';ctx.fillRect(x+bw*.46,top-antennaH,bw*.08,antennaH);
      ctx.strokeStyle=depth===0?'rgba(99,220,255,.35)':'rgba(153,99,222,.18)';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x+bw*.5,top-antennaH);ctx.lineTo(x+bw*.5,top-antennaH-bh*.05);ctx.stroke();
      if(depth===0&&hashNoise(n*4.9)>.55){ctx.fillStyle='#ff4ca8';ctx.shadowColor='#ff4ca8';ctx.shadowBlur=8;ctx.beginPath();ctx.arc(x+bw*.5,top-antennaH-bh*.052,1.5,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0}
    }

    if(depth===0){
      const cols=Math.max(2,Math.floor(bw/13)),rows=Math.max(2,Math.floor(bh/17));
      for(let cy=1;cy<rows;cy++)for(let cx=1;cx<cols;cx++){
        const flicker=hashNoise(n*100+cy*11+cx*3+Math.floor(t*.0007));
        if(flicker<.51)continue;
        const wx=x+cx*bw/cols-1.1,wy=top+cy*bh/rows;
        ctx.fillStyle=flicker>.88?'rgba(255,211,112,.72)':'rgba(154,81,255,.34)';ctx.fillRect(wx,wy,2,3);
      }
    }
  }
  ctx.restore();
}

function drawNeonSigns(t){
  ctx.save();ctx.font=`900 ${Math.max(9,W*.021)}px system-ui`;ctx.textAlign='center';
  const signs=[
    {x:W*.12,y:H*.36,text:'REALITY',color:'#e260ff',a:-.07,phase:0},
    {x:W*.88,y:H*.42,text:'EGO',color:'#5ee8ff',a:.08,phase:1.7}
  ];
  for(const sign of signs){
    const pulse=.64+.25*Math.sin(t*.004+sign.phase),glitch=Math.sin(t*.021+sign.phase)>.965?3:0;
    ctx.save();ctx.translate(sign.x+glitch,sign.y);ctx.rotate(sign.a);ctx.globalAlpha=pulse;ctx.shadowColor=sign.color;ctx.shadowBlur=18;
    roundedRect(-W*.088,-H*.017,W*.176,H*.034,5,'rgba(4,4,12,.91)',sign.color,1.25);
    ctx.fillStyle=sign.color;ctx.fillText(sign.text,0,H*.0055);ctx.restore();
  }
  ctx.restore();
}

function roofQuad(laneIndex,z1,z2,pad=.47){
  return [[laneX(laneIndex-pad,z1),objectY(z1)],[laneX(laneIndex+pad,z1),objectY(z1)],[laneX(laneIndex+pad,z2),objectY(z2)],[laneX(laneIndex-pad,z2),objectY(z2)]];
}

function drawRoofTrack(t){
  const horizonY=H*.245,leftFar=W*.43,rightFar=W*.57,leftNear=-W*.10,rightNear=W*1.10;
  const roof=ctx.createLinearGradient(0,horizonY,0,H);
  roof.addColorStop(0,'#151324');roof.addColorStop(.42,'#090d17');roof.addColorStop(1,'#020408');
  polygon([[leftFar,horizonY],[rightFar,horizonY],[rightNear,H],[leftNear,H]],roof,'rgba(175,86,255,.56)',1.4);

  ctx.save();ctx.clip();
  const wet=ctx.createLinearGradient(W*.25,0,W*.75,H);wet.addColorStop(0,'rgba(187,85,255,0)');wet.addColorStop(.48,'rgba(155,75,255,.045)');wet.addColorStop(.64,'rgba(82,219,255,.075)');wet.addColorStop(1,'rgba(82,219,255,0)');ctx.fillStyle=wet;ctx.fillRect(0,horizonY,W,H-horizonY);

  const panelScroll=(distance*.020)%1;
  for(let band=0;band<12;band++){
    const z1=(band/12+panelScroll)%1,z2=Math.min(1,z1+.075);
    if(z2<=z1)continue;
    for(let laneIndex=0;laneIndex<3;laneIndex++){
      const a=.015+((band+laneIndex)%2)*.013;
      polygon(roofQuad(laneIndex,z1,z2),`rgba(${laneIndex===1?'102,72,138':'48,72,89'},${a})`,'rgba(171,132,214,.045)',.55);
    }
  }

  for(let i=0;i<8;i++){
    const z=.30+((i*.113+distance*.004)%.68),x=laneX((i%3)+hashNoise(i*4.2)*.25-.12,z),y=objectY(z);
    const rx=8+z*22,ry=2+z*5;
    ctx.save();ctx.globalAlpha=.07+z*.05;ctx.fillStyle=i%2?'#72dfff':'#bc68ff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=10;ctx.beginPath();ctx.ellipse(x,y,rx,ry,0,0,Math.PI*2);ctx.fill();ctx.restore();
  }
  ctx.restore();

  const edgeGlow=ctx.createLinearGradient(0,horizonY,0,H);edgeGlow.addColorStop(0,'rgba(194,95,255,.34)');edgeGlow.addColorStop(1,'rgba(67,220,255,.76)');
  ctx.save();ctx.strokeStyle=edgeGlow;ctx.lineWidth=2.5;ctx.shadowColor='#8d4eff';ctx.shadowBlur=13;
  ctx.beginPath();ctx.moveTo(leftFar,horizonY);ctx.lineTo(leftNear,H);ctx.moveTo(rightFar,horizonY);ctx.lineTo(rightNear,H);ctx.stroke();ctx.restore();

  for(let laneIndex=0;laneIndex<2;laneIndex++){
    const farX=laneX(laneIndex+.5,0),nearX=laneX(laneIndex+.5,1.18);
    ctx.strokeStyle='rgba(211,174,255,.17)';ctx.lineWidth=1.05;ctx.setLineDash([8,13]);ctx.beginPath();ctx.moveTo(farX,horizonY);ctx.lineTo(nearX,H);ctx.stroke();ctx.setLineDash([]);
  }

  const seamScroll=(distance*.027)%1;
  for(let i=0;i<18;i++){
    const z=(i/18+seamScroll)%1,y=objectY(z),left=laneX(-.74,z),right=laneX(2.74,z);
    ctx.strokeStyle=`rgba(177,138,211,${.026+z*.095})`;ctx.lineWidth=.6+z*.9;ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
  }

  for(let i=0;i<13;i++){
    const z=((i/13)+(distance*.014)%1)%1,x=laneX(i%3,z),y=objectY(z),r=.7+z*2.4;
    ctx.fillStyle=`rgba(62,218,255,${.04+z*.13})`;ctx.shadowColor='#5de2ff';ctx.shadowBlur=6;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
  }

  ctx.save();ctx.globalAlpha=.76;
  const sideScroll=(distance*.013)%1;
  for(let i=0;i<9;i++){
    const z=(i/9+sideScroll)%1,y=objectY(z),s=.25+z*.84,leftX=laneX(-1.05,z),rightX=laneX(3.05,z);
    ctx.fillStyle='#05080d';ctx.strokeStyle='rgba(158,80,224,.26)';ctx.lineWidth=.8+s;
    ctx.fillRect(leftX-30*s,y-20*s,40*s,20*s);ctx.strokeRect(leftX-30*s,y-20*s,40*s,20*s);
    if(i%2===0){ctx.fillRect(rightX-8*s,y-35*s,24*s,35*s);ctx.strokeRect(rightX-8*s,y-35*s,24*s,35*s)}
  }
  ctx.restore();
}

function drawAttackTelegraph(t){
  if(bossTelegraph<=0||bossSafeLane<0)return;
  const progress=1-clamp01(bossTelegraph/1.28),pulse=.16+.12*Math.sin(t*.028)+progress*.22;
  for(let laneIndex=0;laneIndex<3;laneIndex++){
    const safe=laneIndex===bossSafeLane,farY=H*.245,nearY=H,points=roofQuad(laneIndex,0,1.15,.46),g=ctx.createLinearGradient(0,farY,0,nearY);
    if(safe){g.addColorStop(0,'rgba(55,235,255,.01)');g.addColorStop(1,'rgba(55,235,255,.10)')}
    else{g.addColorStop(0,'rgba(255,47,166,.02)');g.addColorStop(1,`rgba(255,40,149,${pulse})`)}
    polygon(points,g,safe?'rgba(80,237,255,.42)':'rgba(255,72,188,.72)',safe?1.1:1.9);
    if(!safe){
      ctx.save();ctx.globalAlpha=.18+progress*.45;ctx.strokeStyle='#ffd1f2';ctx.lineWidth=1.1;ctx.setLineDash([7,10]);
      ctx.beginPath();ctx.moveTo(laneX(laneIndex,0),farY);ctx.lineTo(laneX(laneIndex,1.1),nearY);ctx.stroke();ctx.setLineDash([]);
      for(let i=0;i<5;i++){
        const z=.22+i*.16,x=laneX(laneIndex,z),y=objectY(z),w=6+z*16;
        ctx.beginPath();ctx.moveTo(x-w,y);ctx.lineTo(x,y+4+z*5);ctx.lineTo(x+w,y);ctx.stroke();
      }
      ctx.restore();
    }
  }
}

function drawAtmosphere(t){
  ctx.save();
  for(let i=0;i<18;i++){
    const z=(i/18+(distance*.004)%1)%1,x=laneX((i%5)*.75-.5,z)+Math.sin(t*.0007+i)*18,y=objectY(z)-20-z*45,r=1+z*3;
    ctx.globalAlpha=.025+z*.065;ctx.fillStyle=i%3?'#ae76ff':'#6bdfff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=9;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();

  ctx.save();ctx.strokeStyle='rgba(204,177,255,.23)';ctx.lineWidth=1;
  for(const r of rain){ctx.globalAlpha=r.a;ctx.beginPath();ctx.moveTo(r.x,r.y);ctx.lineTo(r.x-3,r.y+r.l);ctx.stroke()}
  ctx.restore();
}

function drawBackground(t){
  drawSky(t);
  drawCityLayer(t,2,9,H*.34,H*.16,.20);
  drawCityLayer(t,1,13,H*.39,H*.22,.38);
  drawCityLayer(t,0,18,H*.50,H*.31,.72);
  drawNeonSigns(t);drawRoofTrack(t);drawAttackTelegraph(t);drawAtmosphere(t);
  const shade=ctx.createLinearGradient(0,0,0,H);shade.addColorStop(0,'rgba(3,1,9,.01)');shade.addColorStop(.67,'rgba(2,3,8,0)');shade.addColorStop(1,'rgba(0,0,0,.30)');ctx.fillStyle=shade;ctx.fillRect(0,0,W,H);
}

function drawBoss(t){
  const attack=bossTelegraph>0?clamp01(1-bossTelegraph/1.28):0,pulse=1+Math.sin(t*.0025)*.035+bossPulse*.12;
  const cx=W/2,cy=H*.157,r=Math.min(W*.175,H*.112)*pulse;

  if(bossTelegraph>0){ctx.save();ctx.fillStyle=`rgba(1,0,5,${.06+attack*.17})`;ctx.fillRect(0,0,W,H*.58);ctx.restore()}

  ctx.save();ctx.translate(cx,cy);

  const backGlow=ctx.createRadialGradient(0,0,r*.08,0,0,r*2.45);backGlow.addColorStop(0,'rgba(213,70,255,.32)');backGlow.addColorStop(.38,'rgba(95,27,182,.18)');backGlow.addColorStop(1,'rgba(15,2,30,0)');ctx.fillStyle=backGlow;ctx.beginPath();ctx.arc(0,0,r*2.45,0,Math.PI*2);ctx.fill();

  for(let i=0;i<7;i++){
    const drift=Math.sin(t*.0014+i*1.4),rise=((t*.00005+i*.15)%1);
    ctx.globalAlpha=.07+i*.018;ctx.fillStyle=i%2?'#48106f':'#160321';
    ctx.beginPath();ctx.ellipse(drift*r*.34,r*(.38+i*.11-rise*.20),r*(1.52+i*.13),r*(.47+i*.07),drift*.09,0,Math.PI*2);ctx.fill();
  }

  ctx.save();ctx.globalCompositeOperation='screen';
  for(let i=0;i<5;i++){
    ctx.save();ctx.rotate(t*.000095*(i%2?1:-1)+i*.31);ctx.globalAlpha=.09+i*.04+bossPulse*.08;
    ctx.strokeStyle=i%2?'#55e4ff':'#d13fff';ctx.lineWidth=1.1+i*.55;ctx.setLineDash([7+i*3,10+i*2]);ctx.beginPath();ctx.arc(0,0,r*(1.34+i*.24),0,Math.PI*2);ctx.stroke();ctx.restore();
  }
  ctx.restore();ctx.setLineDash([]);

  ctx.shadowColor='#a42aff';ctx.shadowBlur=34+bossPulse*28;
  const silhouette=[];
  for(let i=0;i<32;i++){
    const a=-Math.PI+i*Math.PI*2/32,spike=i%4===0?1.15:1;
    silhouette.push([Math.cos(a)*r*1.12*spike,Math.sin(a)*r*.78*spike]);
  }
  const body=ctx.createLinearGradient(0,-r,0,r);body.addColorStop(0,'#260640');body.addColorStop(.48,'#090111');body.addColorStop(1,'#010003');
  polygon(silhouette,body,'#cf65ff',2.2);

  const shoulders=ctx.createLinearGradient(0,0,0,r*1.8);shoulders.addColorStop(0,'rgba(17,2,28,.96)');shoulders.addColorStop(1,'rgba(2,0,5,0)');
  polygon([[-r*.75,r*.42],[-r*1.72,r*.86],[-r*1.22,r*1.55],[0,r*1.18],[r*1.22,r*1.55],[r*1.72,r*.86],[r*.75,r*.42]],shoulders,'rgba(185,70,255,.28)',1.4);

  ctx.strokeStyle='#ffd166';ctx.lineWidth=2.6;ctx.shadowColor='#ffd166';ctx.shadowBlur=11;
  ctx.beginPath();ctx.moveTo(-r*.92,-r*.64);ctx.lineTo(-r*.60,-r*1.48);ctx.lineTo(-r*.22,-r*.82);ctx.lineTo(0,-r*1.68);ctx.lineTo(r*.22,-r*.82);ctx.lineTo(r*.60,-r*1.48);ctx.lineTo(r*.92,-r*.64);ctx.stroke();

  const eyeOpen=.31+attack*.16+bossPulse*.035,eye=ctx.createRadialGradient(-r*.08,-r*.07,1,0,0,r*.91);
  eye.addColorStop(0,'#fff');eye.addColorStop(.14,'#ffd6f8');eye.addColorStop(.42,'#dd45ff');eye.addColorStop(.74,'#7b169e');eye.addColorStop(1,'#21002f');
  ctx.fillStyle=eye;ctx.shadowColor='#ef4cff';ctx.shadowBlur=26+attack*22;ctx.beginPath();ctx.ellipse(0,0,r*.91,r*eyeOpen,0,0,Math.PI*2);ctx.fill();

  const pupilX=(laneVisual-1)*r*.14,pupilY=-jumpArc()*r*.055;
  ctx.fillStyle='#020003';ctx.shadowBlur=0;ctx.beginPath();ctx.ellipse(pupilX,pupilY,r*(.17+attack*.045),r*(.22+attack*.055),0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle='#fff';ctx.beginPath();ctx.arc(pupilX-r*.058,pupilY-r*.078,r*.047,0,Math.PI*2);ctx.fill();

  if(attack>0){
    ctx.save();ctx.globalCompositeOperation='screen';
    for(let i=0;i<18;i++){
      const a=i/18*Math.PI*2+t*.0012,radius=r*(1.55-attack*.72+hashNoise(i*4.1)*.35),px=Math.cos(a)*radius,py=Math.sin(a)*radius*.68;
      ctx.globalAlpha=.12+attack*.55;ctx.fillStyle=i%2?'#ff70d7':'#7beaff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=12;ctx.beginPath();ctx.arc(px,py,1.2+attack*2.4,0,Math.PI*2);ctx.fill();
    }
    ctx.restore();
  }

  ctx.strokeStyle='rgba(103,226,255,.54)';ctx.lineWidth=2;ctx.shadowColor='#58dfff';ctx.shadowBlur=9;
  for(const side of [-1,1]){
    ctx.beginPath();ctx.moveTo(side*r*.58,r*.50);ctx.bezierCurveTo(side*r*1.65,r*.90,side*r*.26,r*1.46,side*r*1.08,r*2.02);ctx.stroke();
    ctx.beginPath();ctx.moveTo(side*r*.82,r*.22);ctx.bezierCurveTo(side*r*1.48,r*.58,side*r*.78,r*1.10,side*r*1.62,r*1.42);ctx.stroke();
  }

  for(let i=0;i<10;i++){
    const a=t*.0004+i*.63,or=r*(1.30+hashNoise(i)*.48),px=Math.cos(a)*or,py=Math.sin(a)*or*.68;
    ctx.globalAlpha=.20+hashNoise(i*2.7)*.30;ctx.fillStyle=i%3?'#c85cff':'#69e5ff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=10;ctx.beginPath();ctx.arc(px,py,1.2+hashNoise(i*4.2)*2.1,0,Math.PI*2);ctx.fill();
  }

  if(bossPulse>.08){ctx.globalAlpha=clamp01(bossPulse)*.58;ctx.strokeStyle='#f4a5ff';ctx.lineWidth=2.2;ctx.shadowColor='#e650ff';ctx.shadowBlur=18;ctx.beginPath();ctx.arc(0,0,r*(1.28+(1.42-bossPulse)*.55),0,Math.PI*2);ctx.stroke()}
  ctx.restore();
}

function drawObjectBase(x,y,s,color,wide=1){
  ctx.save();ctx.translate(x,y);ctx.globalAlpha=.52;ctx.fillStyle='rgba(0,0,0,.78)';ctx.shadowColor=color;ctx.shadowBlur=16*s;ctx.beginPath();ctx.ellipse(0,3*s,26*s*wide,7*s,0,0,Math.PI*2);ctx.fill();ctx.globalAlpha=.20;ctx.fillStyle=color;ctx.beginPath();ctx.ellipse(0,1*s,34*s*wide,10*s,0,0,Math.PI*2);ctx.fill();ctx.restore();
}

function drawCrystal(s,phase,t){
  const h=35*s,w=21*s,shimmer=.65+.35*Math.sin(t*.007+phase*2.1);
  ctx.save();ctx.globalCompositeOperation='screen';
  for(let i=0;i<5;i++){
    const a=t*.0015+phase+i*1.26,rr=18*s+Math.sin(t*.002+i)*3*s,px=Math.cos(a)*rr,py=Math.sin(a)*rr*.65;
    ctx.globalAlpha=.16+.16*shimmer;ctx.fillStyle=i%2?'#f4c7ff':'#74e7ff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=9;ctx.beginPath();ctx.arc(px,py,1.1+i%2*.5,0,Math.PI*2);ctx.fill();
  }
  ctx.restore();
  ctx.shadowColor='#ca63ff';ctx.shadowBlur=20*s;
  const g=ctx.createLinearGradient(-w/2,-h/2,w/2,h/2);g.addColorStop(0,'#fff5ff');g.addColorStop(.22,'#e8a4ff');g.addColorStop(.58,'#963ddc');g.addColorStop(1,'#31045b');
  polygon([[0,-h/2],[w/2,-h*.12],[w*.32,h*.42],[0,h/2],[-w*.32,h*.42],[-w/2,-h*.12]],g,'#f9dcff',1.1*s);
  ctx.globalAlpha=.28+.42*shimmer;ctx.fillStyle='#fff';polygon([[-w*.08,-h*.40],[w*.28,-h*.12],[w*.12,h*.08],[-w*.04,-h*.04]],'#fff',null);ctx.globalAlpha=1;
  ctx.strokeStyle='rgba(255,255,255,.58)';ctx.lineWidth=.75*s;ctx.beginPath();ctx.moveTo(0,-h/2);ctx.lineTo(0,h/2);ctx.moveTo(-w/2,-h*.12);ctx.lineTo(w*.32,h*.42);ctx.stroke();
}
function drawGold(s,phase,t){
  const r=11.5*s,pulse=.92+.09*Math.sin(t*.008+phase);
  ctx.save();ctx.scale(pulse,pulse);ctx.rotate(Math.sin(t*.002+phase)*.08);ctx.shadowColor='#ffd45f';ctx.shadowBlur=20*s;ctx.fillStyle='#ffcd47';ctx.beginPath();
  for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,rr=i%2?r*.47:r,px=Math.cos(a)*rr,py=Math.sin(a)*rr;i?ctx.lineTo(px,py):ctx.moveTo(px,py)}
  ctx.closePath();ctx.fill();ctx.fillStyle='#fff2ad';ctx.beginPath();ctx.arc(0,0,r*.27,0,Math.PI*2);ctx.fill();ctx.restore();
}
function drawBarrier(s,phase,t){
  const w=102*s,h=43*s,blink=.45+.55*(Math.sin(t*.014+phase)>0);
  ctx.shadowColor='#b02fff';ctx.shadowBlur=16*s;roundedRect(-w/2,-h*.82,w,h,7*s,'#090b11','#dd76ff',2*s);
  const metal=ctx.createLinearGradient(-w/2,0,w/2,0);metal.addColorStop(0,'rgba(255,255,255,.02)');metal.addColorStop(.45,'rgba(255,255,255,.13)');metal.addColorStop(.56,'rgba(255,255,255,.02)');metal.addColorStop(1,'rgba(0,0,0,.22)');ctx.fillStyle=metal;roundedRect(-w/2+3*s,-h*.82+3*s,w-6*s,h-6*s,5*s,metal,null);
  ctx.save();ctx.beginPath();ctx.rect(-w/2+5*s,-h*.82+5*s,w-10*s,h-10*s);ctx.clip();ctx.strokeStyle='#ffd25f';ctx.lineWidth=7*s;
  for(let x=-w;x<w;x+=23*s){ctx.beginPath();ctx.moveTo(x,-h);ctx.lineTo(x+54*s,h);ctx.stroke()}
  ctx.restore();
  ctx.fillStyle='#552675';ctx.fillRect(-w*.38,h*.18,w*.12,h*.34);ctx.fillRect(w*.26,h*.18,w*.12,h*.34);
  for(const side of [-1,1]){ctx.globalAlpha=blink;ctx.fillStyle='#ff3f9e';ctx.shadowColor='#ff3f9e';ctx.shadowBlur=12;ctx.beginPath();ctx.arc(side*w*.39,-h*.60,3*s,0,Math.PI*2);ctx.fill()}
  ctx.globalAlpha=1;ctx.shadowBlur=0;ctx.fillStyle='rgba(230,201,255,.55)';for(const side of [-1,1])for(const yy of [-.56,-.12]){ctx.beginPath();ctx.arc(side*w*.44,h*yy,1.1*s,0,Math.PI*2);ctx.fill()}
}
function drawDrone(s,phase,t){
  const w=74*s,h=27*s,bob=Math.sin(phase)*3*s;ctx.translate(0,bob-23*s);
  ctx.save();ctx.globalAlpha=.28;ctx.strokeStyle='#7cecff';ctx.shadowColor='#7cecff';ctx.shadowBlur=14;ctx.lineWidth=2*s;
  for(const dir of [-1,1]){ctx.beginPath();ctx.ellipse(dir*w*.50,-h*.15,w*(.24+.04*Math.sin(t*.02+phase)),h*.10,0,0,Math.PI*2);ctx.stroke()}
  ctx.restore();
  ctx.shadowColor='#52dfff';ctx.shadowBlur=19*s;roundedRect(-w*.30,-h*.47,w*.60,h*.94,h*.30,'#070a10','#80edff',1.5*s);
  const shell=ctx.createLinearGradient(-w*.3,-h*.3,w*.3,h*.3);shell.addColorStop(0,'rgba(143,237,255,.18)');shell.addColorStop(.5,'rgba(99,69,165,.08)');shell.addColorStop(1,'rgba(0,0,0,.34)');ctx.fillStyle=shell;roundedRect(-w*.26,-h*.38,w*.52,h*.70,h*.25,shell,null);
  ctx.strokeStyle='#a55eff';ctx.lineWidth=3*s;ctx.beginPath();ctx.moveTo(-w*.22,0);ctx.lineTo(-w*.48,-h*.12);ctx.moveTo(w*.22,0);ctx.lineTo(w*.48,-h*.12);ctx.stroke();
  ctx.fillStyle='#ff3f91';ctx.shadowColor='#ff3f91';ctx.shadowBlur=13;ctx.beginPath();ctx.arc(0,h*.06,4*s,0,Math.PI*2);ctx.fill();
  ctx.save();ctx.globalAlpha=.30;ctx.fillStyle='#65e8ff';ctx.shadowColor='#65e8ff';ctx.shadowBlur=10;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc((i-1)*7*s,h*.58+Math.sin(t*.012+i)*3*s,1.4*s,0,Math.PI*2);ctx.fill()}ctx.restore();
}
function drawPower(kind,s,t){
  const r=18*s,main=kind==='shield'?'#79e5ff':kind==='magnet'?'#d77aff':'#ffd86a',pulse=.94+.08*Math.sin(t*.008);
  ctx.save();ctx.scale(pulse,pulse);ctx.rotate(t*.0007);ctx.globalAlpha=.35;ctx.strokeStyle=main;ctx.shadowColor=main;ctx.shadowBlur=15;ctx.lineWidth=1.4;ctx.setLineDash([4,7]);ctx.beginPath();ctx.arc(0,0,r*1.38,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.restore();
  ctx.shadowColor=main;ctx.shadowBlur=20*s;ctx.fillStyle='rgba(5,5,15,.96)';ctx.strokeStyle=main;ctx.lineWidth=2*s;ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.fill();ctx.stroke();
  ctx.strokeStyle=main;ctx.fillStyle=main;ctx.lineWidth=4*s;ctx.lineCap='round';
  if(kind==='magnet'){ctx.beginPath();ctx.arc(0,-2*s,9*s,.05*Math.PI,.95*Math.PI);ctx.stroke();ctx.fillRect(-12*s,-6*s,5*s,9*s);ctx.fillRect(7*s,-6*s,5*s,9*s)}
  else if(kind==='shield')polygon([[0,-11*s],[9*s,-6*s],[7*s,6*s],[0,12*s],[-7*s,6*s],[-9*s,-6*s]],'rgba(121,229,255,.3)',main,2*s);
  else polygon([[3*s,-12*s],[-6*s,2*s],[0,2*s],[-3*s,12*s],[8*s,-4*s],[2*s,-4*s]],main,null);
}
function drawVent(s,phase,t){
  const r=24*s;ctx.shadowColor='#853be0';ctx.shadowBlur=13*s;ctx.fillStyle='#06080d';ctx.strokeStyle='#a95fe8';ctx.lineWidth=3*s;ctx.beginPath();ctx.ellipse(0,0,r,r*.46,0,0,Math.PI*2);ctx.fill();ctx.stroke();
  const metal=ctx.createRadialGradient(-r*.2,-r*.15,1,0,0,r);metal.addColorStop(0,'rgba(210,188,255,.17)');metal.addColorStop(1,'rgba(0,0,0,0)');ctx.fillStyle=metal;ctx.beginPath();ctx.ellipse(0,0,r*.88,r*.37,0,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#d7a8ff';ctx.lineWidth=1.4*s;for(let i=0;i<6;i++){const x=-r*.65+i*r*.26;ctx.beginPath();ctx.moveTo(x,-r*.30);ctx.lineTo(x+r*.2,r*.30);ctx.stroke()}
  ctx.save();ctx.globalAlpha=.12+.08*Math.sin(t*.004+phase);ctx.fillStyle='#83e5ff';for(let i=0;i<3;i++){const x=(i-1)*7*s+Math.sin(t*.001+i)*3*s,y=-r*.55-((t*.018+i*7)%18)*s;ctx.beginPath();ctx.arc(x,y,3.5*s+i*s,0,Math.PI*2);ctx.fill()}ctx.restore();
}
function drawWave(s,phase,t){
  const w=88*s,h=40*s,g=ctx.createLinearGradient(-w/2,0,w/2,0);g.addColorStop(0,'rgba(86,31,187,.03)');g.addColorStop(.5,'rgba(247,64,196,.93)');g.addColorStop(1,'rgba(60,204,255,.04)');
  ctx.shadowColor='#ff42c9';ctx.shadowBlur=26*s;ctx.fillStyle=g;ctx.fillRect(-w/2,-h/2,w,h);ctx.strokeStyle='#ffd4f6';ctx.lineWidth=1.7*s;ctx.strokeRect(-w/2,-h/2,w,h);
  ctx.strokeStyle='rgba(255,255,255,.54)';for(let i=-2;i<=2;i++){const drift=Math.sin(t*.01+phase+i)*4*s;ctx.beginPath();ctx.moveTo(i*w*.15+drift,-h/2);ctx.lineTo((i+1)*w*.15+drift,h/2);ctx.stroke()}
}

function drawObject(o,t){
  const rawZ=o.z,z=Math.max(0,rawZ),x=laneX(o.lane,z),baseY=objectY(z),s=objectScale(z,o.type),floatY=(o.type==='orb'||o.type==='gold'||o.type==='power')?Math.sin(t*.003+o.phase)*4*s:0,y=baseY+floatY;
  const color=o.type==='gold'?'rgba(255,210,76,.95)':o.type==='drone'?'rgba(87,228,255,.95)':o.type==='barrier'||o.type==='wave'?'rgba(238,72,193,.94)':'rgba(185,91,255,.92)';
  drawObjectBase(x,baseY,s,color,o.type==='barrier'||o.type==='wave'?1.55:o.type==='vent'?1.15:1);
  ctx.save();ctx.translate(x,y);ctx.globalAlpha=clamp01((rawZ+.14)/.14);
  if(o.type==='orb')drawCrystal(s,o.phase,t);
  else if(o.type==='gold')drawGold(s,o.phase,t);
  else if(o.type==='barrier')drawBarrier(s,o.phase,t);
  else if(o.type==='drone')drawDrone(s,o.phase,t);
  else if(o.type==='power')drawPower(o.kind||'magnet',s,t);
  else if(o.type==='vent')drawVent(s,o.phase,t);
  else if(o.type==='wave')drawWave(s,o.phase,t);
  ctx.restore();
}

function drawHeroFigure(t,x,y,scale,sliding,jumpRatio,alpha=1,ghost=false){
  ctx.save();ctx.globalAlpha=alpha;ctx.translate(x,y);ctx.rotate((lane-laneVisual)*-.20+jumpRatio*.035);ctx.lineCap='round';ctx.lineJoin='round';
  ctx.shadowColor=ghost?'#67dbff':'#a54cff';ctx.shadowBlur=ghost?14:20;

  if(sliding){
    ctx.strokeStyle=ghost?'#7ce6ff':'#f2edff';ctx.lineWidth=8*scale;ctx.beginPath();ctx.moveTo(-30*scale,-18*scale);ctx.lineTo(20*scale,-29*scale);ctx.lineTo(37*scale,-12*scale);ctx.stroke();
    roundedRect(-31*scale,-42*scale,56*scale,25*scale,10*scale,ghost?'rgba(74,205,255,.18)':'#100b1a',ghost?'#79e5ff':'#ca74ff',2*scale);
    if(!ghost){ctx.fillStyle='#d8b8aa';ctx.beginPath();ctx.arc(-27*scale,-49*scale,11*scale,0,Math.PI*2);ctx.fill()}
  }else{
    const airborne=jumpRatio>.06,runPhase=t*.014,leg=airborne?19*scale:Math.sin(runPhase)*16*scale,arm=airborne?14*scale:Math.sin(runPhase+Math.PI)*12*scale,bob=airborne?0:Math.sin(runPhase*2)*2*scale;
    ctx.translate(0,bob);

    ctx.strokeStyle=ghost?'rgba(105,226,255,.72)':'#f1edf8';ctx.lineWidth=8*scale;ctx.beginPath();
    ctx.moveTo(-5*scale,-42*scale);ctx.lineTo(-13*scale,-18*scale);ctx.lineTo(-13*scale+leg,airborne?-5*scale:0);
    ctx.moveTo(4*scale,-41*scale);ctx.lineTo(12*scale,-18*scale);ctx.lineTo(12*scale-leg,airborne?-11*scale:0);ctx.stroke();

    ctx.strokeStyle=ghost?'rgba(190,112,255,.65)':'#dcd2e9';ctx.lineWidth=6*scale;ctx.beginPath();
    ctx.moveTo(-14*scale,-80*scale);ctx.lineTo(-25*scale,-56*scale);ctx.lineTo(-25*scale+arm,-43*scale);
    ctx.moveTo(14*scale,-79*scale);ctx.lineTo(25*scale,-58*scale);ctx.lineTo(25*scale-arm,-43*scale);ctx.stroke();

    const jacket=ctx.createLinearGradient(-24*scale,-95*scale,24*scale,-38*scale);
    if(ghost){jacket.addColorStop(0,'rgba(100,225,255,.10)');jacket.addColorStop(1,'rgba(181,77,255,.24)')}
    else{jacket.addColorStop(0,'#1d0b35');jacket.addColorStop(.42,'#8e42e0');jacket.addColorStop(.72,'#54218e');jacket.addColorStop(1,'#0d0715')}
    polygon([[-19*scale,-93*scale],[18*scale,-93*scale],[24*scale,-63*scale],[20*scale,-47*scale],[7*scale,-38*scale],[-15*scale,-42*scale],[-24*scale,-63*scale]],jacket,ghost?'rgba(101,225,255,.35)':'#db91ff',1.8*scale);

    if(!ghost){
      ctx.fillStyle='#2a1741';polygon([[-19*scale,-88*scale],[-27*scale,-78*scale],[-18*scale,-69*scale]],'#2a1741','#b965ff',1.2*scale);polygon([[18*scale,-88*scale],[27*scale,-78*scale],[18*scale,-69*scale]],'#2a1741','#b965ff',1.2*scale);
      ctx.fillStyle='#d9b7a9';ctx.beginPath();ctx.arc(0,-108*scale,13*scale,0,Math.PI*2);ctx.fill();
      ctx.fillStyle='#0c0912';ctx.beginPath();ctx.arc(-2*scale,-112*scale,13*scale,Math.PI,Math.PI*2);ctx.fill();
      const visor=ctx.createLinearGradient(3*scale,-111*scale,12*scale,-105*scale);visor.addColorStop(0,'#80f0ff');visor.addColorStop(1,'#a569ff');ctx.fillStyle=visor;ctx.shadowColor='#69e8ff';ctx.shadowBlur=10;roundedRect(3*scale,-111*scale,10*scale,4*scale,2*scale,visor,null);
      ctx.fillStyle='#ffd96a';ctx.shadowColor='#ffd96a';ctx.shadowBlur=8;polygon([[0,-77*scale],[5*scale,-70*scale],[0,-63*scale],[-5*scale,-70*scale]],'#ffd96a',null);
      const cape=ctx.createLinearGradient(-46*scale,-82*scale,-14*scale,-41*scale);cape.addColorStop(0,'rgba(87,222,255,.02)');cape.addColorStop(.48,'rgba(124,92,255,.20)');cape.addColorStop(1,'rgba(205,74,255,.48)');polygon([[-18*scale,-84*scale],[-48*scale,-62*scale],[-18*scale,-42*scale]],cape,'rgba(209,118,255,.20)',1);
    }
  }
  ctx.restore();
}

function drawHero(t){
  const x=laneX(laneVisual,1),baseY=H*.84,jumpRatio=jumpArc(),jumpHeight=jumpRatio*H*.19,sliding=slide>0,y=baseY-jumpHeight;
  const scale=Math.min(1.30,H/760)*(.96+Math.min(W,430)/430*.10),delta=lane-laneVisual;

  ctx.save();ctx.globalAlpha=.50-jumpRatio*.20;ctx.fillStyle='#010207';ctx.shadowColor=shield?'#8de7ff':'#9d4bff';ctx.shadowBlur=shield?25:16;ctx.beginPath();ctx.ellipse(x,baseY+5,(31-jumpRatio*8)*scale,(9-jumpRatio*2)*(sliding?1.5:1)*scale,0,0,Math.PI*2);ctx.fill();ctx.restore();
  drawLightPool(x,baseY+3,54*scale,14*scale,'rgba(115,209,255,0.48)',.55-jumpRatio*.25);

  if(Math.abs(delta)>.025){
    for(let i=2;i>=1;i--){const ghostX=x-delta*W*(.055*i);drawHeroFigure(t,ghostX,y,scale,sliding,jumpRatio,.075*i,true)}
  }

  if(magnet>0){ctx.save();ctx.globalAlpha=.23+.08*Math.sin(t*.008);ctx.strokeStyle='#d197ff';ctx.lineWidth=2;for(let i=0;i<3;i++){ctx.beginPath();ctx.arc(x,y-54*scale,54*scale+i*10*scale,0,Math.PI*2);ctx.stroke()}ctx.restore()}
  if(shield){ctx.save();ctx.globalAlpha=.46+.12*Math.sin(t*.01);ctx.strokeStyle='#8be7ff';ctx.lineWidth=3;ctx.shadowColor='#72dfff';ctx.shadowBlur=22;ctx.beginPath();ctx.ellipse(x,y-54*scale,44*scale,68*scale,0,0,Math.PI*2);ctx.stroke();ctx.restore()}

  drawHeroFigure(t,x,y,scale,sliding,jumpRatio,1,false);

  if(running&&!sliding){
    ctx.save();ctx.globalCompositeOperation='screen';const trail=ctx.createLinearGradient(x,y-15,x,baseY+72);
    trail.addColorStop(0,'rgba(196,92,255,.40)');trail.addColorStop(.42,'rgba(79,226,255,.20)');trail.addColorStop(1,'rgba(72,204,255,0)');
    ctx.fillStyle=trail;ctx.beginPath();ctx.moveTo(x-15,y-14);ctx.lineTo(x+15,y-14);ctx.lineTo(x+42,baseY+74);ctx.lineTo(x-42,baseY+74);ctx.closePath();ctx.fill();ctx.restore();

    ctx.save();ctx.globalCompositeOperation='screen';
    for(let i=0;i<7;i++){
      const phase=t*.006+i*1.7,px=x+Math.sin(phase)*18*scale,py=baseY+5-((t*.045+i*17)%62)*scale;
      ctx.globalAlpha=.08+(i%3)*.05;ctx.fillStyle=i%2?'#bd6cff':'#69e6ff';ctx.shadowColor=ctx.fillStyle;ctx.shadowBlur=9;ctx.beginPath();ctx.arc(px,py,1.2+(i%2),0,Math.PI*2);ctx.fill();
    }
    ctx.restore();
  }
}

function drawEffects(t){
  if(running){
    ctx.save();ctx.strokeStyle='rgba(158,105,255,.105)';ctx.lineWidth=1;
    for(let i=0;i<9;i++){
      const phase=(i/9+(distance*.012)%1)%1,x=laneX((i%3)-.2,phase),y=objectY(phase);
      ctx.globalAlpha=.035+phase*.13;ctx.beginPath();ctx.moveTo(x,y-6-phase*18);ctx.lineTo(x,y+7+phase*26);ctx.stroke();
    }
    ctx.restore();
  }

  for(const ring of rings){
    const a=clamp01(ring.t/ring.maxT);ctx.save();ctx.globalAlpha=a*.72;ctx.strokeStyle=ring.color;ctx.shadowColor=ring.color;ctx.shadowBlur=15;ctx.lineWidth=1.2+2*a;ctx.beginPath();ctx.ellipse(ring.x,ring.y,ring.r,ring.r*.32,0,0,Math.PI*2);ctx.stroke();ctx.restore();
  }

  for(const p of particles){
    const a=clamp01(p.t/p.maxT);ctx.save();ctx.translate(p.x,p.y);ctx.rotate(p.rot);ctx.globalAlpha=a;
    if(p.kind==='shard'){
      ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=11;polygon([[0,-p.length*.5],[p.r,p.length*.1],[0,p.length*.5],[-p.r,p.length*.1]],p.color,null);
    }else if(p.kind==='trail'){
      ctx.strokeStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=9;ctx.lineWidth=Math.max(.8,p.r);ctx.beginPath();ctx.moveTo(-p.length*.5,0);ctx.lineTo(p.length*.5,0);ctx.stroke();
    }else if(p.kind==='smoke'){
      ctx.globalAlpha=a*.18;ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=p.r;ctx.beginPath();ctx.arc(0,0,p.r*(1.3-a*.3),0,Math.PI*2);ctx.fill();
    }else{
      ctx.fillStyle=p.color;ctx.shadowColor=p.color;ctx.shadowBlur=10;ctx.beginPath();ctx.arc(0,0,p.r,0,Math.PI*2);ctx.fill();
    }
    ctx.restore();
  }

  for(const f of floating){
    const a=clamp01(f.t/f.maxT);ctx.save();ctx.globalAlpha=a;ctx.fillStyle=f.color;ctx.shadowColor=f.color;ctx.shadowBlur=8;ctx.font='900 13px system-ui';ctx.textAlign='center';ctx.fillText(f.text,f.x,f.y);ctx.restore();
  }

  if(flash>0){ctx.save();ctx.globalAlpha=flash;ctx.fillStyle=hits?'#ff497a':'#d47aff';ctx.fillRect(0,0,W,H);ctx.restore()}

  const vignette=ctx.createRadialGradient(W/2,H*.55,Math.min(W,H)*.20,W/2,H*.55,Math.max(W,H)*.74);
  vignette.addColorStop(0,'rgba(0,0,0,0)');vignette.addColorStop(.72,'rgba(0,0,0,.04)');vignette.addColorStop(1,'rgba(0,0,0,.36)');ctx.fillStyle=vignette;ctx.fillRect(0,0,W,H);

  ctx.save();ctx.globalAlpha=.026;ctx.fillStyle='#fff';const frame=Math.floor(t/90);
  for(let i=0;i<50;i++){const x=hashNoise(i*11.7+frame)*W,y=hashNoise(i*8.3+frame*2)*H;ctx.fillRect(x,y,1,1)}
  ctx.restore();
}

function draw(t){
  ctx.save();if(shake>0)ctx.translate(Math.sin(t*.073)*shake*.52,Math.cos(t*.091)*shake*.42);
  drawBackground(t);drawBoss(t);for(const o of [...objects].sort((a,b)=>a.z-b.z))drawObject(o,t);drawHero(t);drawEffects(t);ctx.restore();
}
function drawIdle(){if(!W||!H)return;const now=performance.now();drawBackground(now);drawBoss(now);drawHero(now);drawEffects(now)}
function loop(now){if(!running)return;const dt=Math.min(.034,Math.max(.001,(now-lastFrame)/1000));lastFrame=now;update(dt);draw(now);if(running)requestAnimationFrame(loop)}
function formatTime(value){const seconds=Math.max(0,Math.ceil(value));return String(Math.floor(seconds/60)).padStart(2,'0')+':'+String(seconds%60).padStart(2,'0')}

async function finishGame(reason){
  if(ended)return;ended=true;running=false;
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
$('back').onclick=goGames;$('toGames').onclick=goGames;$('ability').onclick=useAbility;

const stage=$('stage');
stage.addEventListener('pointerdown',event=>{event.preventDefault();touchStart={x:event.clientX,y:event.clientY,t:performance.now()};stage.setPointerCapture?.(event.pointerId)});
stage.addEventListener('pointerup',event=>{
  event.preventDefault();if(!touchStart)return;
  const dx=event.clientX-touchStart.x,dy=event.clientY-touchStart.y,ax=Math.abs(dx),ay=Math.abs(dy);touchStart=null;
  if(Math.max(ax,ay)<18){useAbility();return}if(ax>ay*1.04)move(dx>0?1:-1);else if(dy<0)doJump();else doSlide();
});
stage.addEventListener('pointercancel',()=>{touchStart=null});
document.addEventListener('keydown',event=>{if(event.key==='ArrowLeft')move(-1);if(event.key==='ArrowRight')move(1);if(event.key==='ArrowUp')doJump();if(event.key==='ArrowDown')doSlide();if(event.code==='Space')useAbility()});
requestAnimationFrame(()=>{resize();drawIdle()});