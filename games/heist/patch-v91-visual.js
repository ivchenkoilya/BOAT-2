(()=>{
  "use strict";
  (window.__heistV91Patches||(window.__heistV91Patches=[])).push((source,replaceFunction)=>{
    source=replaceFunction(source,"drawDecor","drawSecuritySystems",`  function drawDecor(){
    const time=performance.now()/1000;
    for(let index=0;index<decor.length;index++){
      const item=decor[index];
      // Оставляем меньше случайного декора и освобождаем проходы.
      if(index%3===1&&item.type!=="server"&&item.type!=="monitor")continue;
      const p=screen(item.x,item.y);if(p.x<-45||p.x>viewW+45||p.y<hudSafe-45||p.y>viewH+45)continue;
      const accent=ZONE_META[item.zone].accent;ctx.save();ctx.translate(p.x,p.y);ctx.rotate(item.rot);ctx.globalAlpha=.68;
      if(item.type==="server"){
        ctx.shadowBlur=9;ctx.shadowColor=accent+"55";const g=ctx.createLinearGradient(-18,-26,18,26);g.addColorStop(0,"#263139");g.addColorStop(.45,"#0b1014");g.addColorStop(1,"#17242a");ctx.fillStyle=g;rounded(ctx,-18,-27,36,54,5);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=accent+"88";ctx.stroke();for(let y=-19;y<21;y+=10){ctx.fillStyle="#05080a";ctx.fillRect(-12,y,24,6);ctx.fillStyle=(Math.floor(time*3+y)%3?accent:"#d58cff");ctx.globalAlpha=.45+.35*Math.sin(time*3+y);ctx.fillRect(7,y+2,3,2);}ctx.globalAlpha=.68;
      }else if(item.type==="monitor"){
        ctx.fillStyle="#07090c";rounded(ctx,-20,-15,40,28,5);ctx.fill();ctx.strokeStyle=accent;ctx.stroke();const glow=ctx.createLinearGradient(-14,-8,14,7);glow.addColorStop(0,accent+"22");glow.addColorStop(1,accent+"99");ctx.fillStyle=glow;ctx.fillRect(-14,-9,28,14);ctx.fillStyle="#d9fbff";ctx.globalAlpha=.35+.25*Math.sin(time*2+index);ctx.fillRect(-10,-5,17,2);ctx.fillRect(-10,0,11,2);
      }else if(item.type==="crate"){
        const g=ctx.createLinearGradient(-18,-18,18,18);g.addColorStop(0,item.zone==="gold"?"#78562a":"#332823");g.addColorStop(1,"#171218");ctx.fillStyle=g;ctx.fillRect(-18,-18,36,36);ctx.strokeStyle=accent+"bb";ctx.lineWidth=1.5;ctx.strokeRect(-18,-18,36,36);ctx.beginPath();ctx.moveTo(-18,-18);ctx.lineTo(18,18);ctx.moveTo(18,-18);ctx.lineTo(-18,18);ctx.stroke();if(item.zone==="gold"){ctx.fillStyle="#e4b74f";for(let i=0;i<3;i++)ctx.fillRect(-12+i*8,-4+(i%2)*5,7,4);}
      }else if(item.type==="panel"||item.type==="seal"){
        ctx.fillStyle="#100c12";rounded(ctx,-22,-12,44,24,5);ctx.fill();ctx.strokeStyle=accent+"aa";ctx.stroke();ctx.fillStyle=accent+"55";ctx.fillRect(-15,-5,30,3);ctx.fillRect(-15,2,19,3);ctx.fillStyle=accent;ctx.beginPath();ctx.arc(14,5,2.2,0,Math.PI*2);ctx.fill();
      }else if(item.type==="vent"){
        ctx.fillStyle="#15161b";ctx.fillRect(-17,-12,34,24);ctx.strokeStyle=accent+"88";ctx.strokeRect(-17,-12,34,24);for(let x=-12;x<14;x+=6){ctx.beginPath();ctx.moveTo(x,-8);ctx.lineTo(x,8);ctx.stroke();}
      }else if(item.type==="cable"){
        ctx.strokeStyle=accent+"aa";ctx.lineWidth=2.5;ctx.shadowBlur=5;ctx.shadowColor=accent;ctx.beginPath();ctx.moveTo(-27,12);ctx.bezierCurveTo(-9,-19,8,24,29,-9);ctx.stroke();ctx.shadowBlur=0;
      }else if(item.type==="laser"){
        ctx.strokeStyle="#ff4b65";ctx.lineWidth=2;ctx.shadowBlur=10;ctx.shadowColor="#ff365d";ctx.beginPath();ctx.moveTo(-31,0);ctx.lineTo(31,0);ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle="#4c1722";ctx.fillRect(-34,-5,5,10);ctx.fillRect(29,-5,5,10);
      }else if(item.type==="stripe"){
        ctx.strokeStyle=accent+"77";ctx.lineWidth=2;ctx.setLineDash([9,7]);ctx.beginPath();ctx.moveTo(-30,0);ctx.lineTo(30,0);ctx.stroke();ctx.setLineDash([]);
      }else if(item.type==="crack"||item.type==="debris"){
        ctx.strokeStyle=accent+"88";ctx.lineWidth=1.5;ctx.beginPath();ctx.moveTo(-23,-17);ctx.lineTo(-7,-3);ctx.lineTo(-13,13);ctx.lineTo(7,2);ctx.lineTo(22,17);ctx.stroke();ctx.fillStyle="#34303c";ctx.fillRect(-18,10,7,4);ctx.fillRect(8,-12,10,5);
      }
      ctx.restore();
    }
  }`);

    source=replaceFunction(source,"drawWalls","drawSafe",`  function drawWalls(front=false){
    const depth=8;
    for(let index=0;index<walls.length;index++){
      const w=walls[index],isFront=w.y+w.h*.5>player.y+player.r*.25;if(isFront!==front)continue;
      const p=screen(w.x,w.y);if(p.x+w.w+depth<0||p.x>viewW||p.y+w.h<hudSafe-depth||p.y>viewH)continue;
      ctx.save();ctx.shadowColor="rgba(0,0,0,.78)";ctx.shadowBlur=front?18:12;ctx.shadowOffsetY=front?10:6;
      const face=ctx.createLinearGradient(p.x,p.y,p.x+w.w,p.y+w.h);face.addColorStop(0,"#725331");face.addColorStop(.17,"#2b2020");face.addColorStop(.67,"#111017");face.addColorStop(1,"#79562f");ctx.fillStyle=face;rounded(ctx,p.x,p.y,w.w,w.h,Math.min(7,w.w/2,w.h/2));ctx.fill();ctx.shadowBlur=0;ctx.shadowOffsetY=0;
      ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(p.x+w.w,p.y);ctx.lineTo(p.x+w.w+depth,p.y-depth);ctx.lineTo(p.x+depth,p.y-depth);ctx.closePath();const top=ctx.createLinearGradient(p.x,p.y-depth,p.x,p.y+2);top.addColorStop(0,"#d5a75a");top.addColorStop(.34,"#815b32");top.addColorStop(1,"#21191b");ctx.fillStyle=top;ctx.fill();
      ctx.beginPath();ctx.moveTo(p.x+w.w,p.y);ctx.lineTo(p.x+w.w,p.y+w.h);ctx.lineTo(p.x+w.w+depth,p.y+w.h-depth);ctx.lineTo(p.x+w.w+depth,p.y-depth);ctx.closePath();ctx.fillStyle="#0c0a0f";ctx.fill();
      ctx.strokeStyle="#e0b76b99";ctx.lineWidth=1.4;rounded(ctx,p.x,p.y,w.w,w.h,Math.min(7,w.w/2,w.h/2));ctx.stroke();ctx.strokeStyle="#fff1bd2e";ctx.beginPath();ctx.moveTo(p.x+3,p.y+2);ctx.lineTo(p.x+w.w-3,p.y+2);ctx.stroke();
      if(index%5===0){const cx=p.x+Math.min(w.w*.5,6),cy=p.y+Math.min(w.h*.5,6);ctx.shadowBlur=12;ctx.shadowColor="#ffc85d";ctx.fillStyle="#38271d";ctx.beginPath();ctx.arc(cx,cy,7,0,Math.PI*2);ctx.fill();ctx.strokeStyle="#c89647";ctx.stroke();ctx.fillStyle="#ffd878";ctx.beginPath();ctx.arc(cx,cy,2.2,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}
      if(index%11===0&&w.w>w.h){const lx=p.x+w.w*.5,ly=p.y+4,light=.62+.38*Math.sin(performance.now()/700+index);ctx.fillStyle="#5a3d20";rounded(ctx,lx-7,ly-5,14,10,3);ctx.fill();ctx.fillStyle="rgba(255,207,105,"+light+")";ctx.shadowBlur=18;ctx.shadowColor="#ffc65e";ctx.beginPath();ctx.arc(lx,ly,3,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;}
      ctx.restore();
    }
  }`);

    source=replaceFunction(source,"draw","drawMiniMap",`  function draw(now=0){
    ticker=now/1000;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,viewW,viewH);const bg=ctx.createLinearGradient(0,0,0,viewH);bg.addColorStop(0,"#1b1218");bg.addColorStop(1,"#06060a");ctx.fillStyle=bg;ctx.fillRect(0,0,viewW,viewH);ctx.save();ctx.beginPath();ctx.rect(0,hudSafe,viewW,viewH-hudSafe);ctx.clip();if(shake>0)ctx.translate(rand(-4,4)*shake,rand(-4,4)*shake);
    drawFloor();drawDecor();drawSecuritySystems(ticker);drawRoute();drawExit(ticker);
    const vault=safes.find(safe=>safe.tier===4&&!safe.opened);if(vault){const vp=screen(vault.x,vault.y),glow=ctx.createRadialGradient(vp.x,vp.y,4,vp.x,vp.y,90);glow.addColorStop(0,"rgba(184,101,255,.18)");glow.addColorStop(.45,"rgba(255,199,82,.08)");glow.addColorStop(1,"transparent");ctx.fillStyle=glow;ctx.fillRect(vp.x-90,vp.y-90,180,180);}
    drawWalls(false);for(const safe of safes)drawSafe(safe,ticker);for(const cam of cameras)drawCamera(cam);drawEffects();drawSmoke();drawPlayer(ticker);drawWalls(true);ctx.restore();drawMiniMap();
  }`);
    return source;
  });
})();
