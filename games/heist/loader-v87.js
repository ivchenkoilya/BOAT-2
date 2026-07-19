(()=>{
  "use strict";
  const VERSION="87";
  const loadScript=src=>new Promise((resolve,reject)=>{
    const s=document.createElement("script");
    s.src=`${src}?v=${VERSION}`;
    s.onload=resolve;
    s.onerror=reject;
    document.body.appendChild(s);
  });
  const installPost=async()=>{
    for(const src of ["/games/heist/enhance-v83.js","/games/heist/ui-v86.js","/games/heist/polish-v87.js"]){
      try{await loadScript(src)}catch(error){console.error("Heist post-script failed",src,error)}
    }
  };
  const replaceFunction=(source,name,nextName,replacement)=>{
    const pattern=new RegExp(`  function ${name}\\([^]*?\\n  function ${nextName}`);
    const match=source.match(pattern);
    if(!match){console.warn(`Heist v87: function ${name} not patched`);return source}
    return source.replace(pattern,`${replacement}\n  function ${nextName}`);
  };
  const boot=async()=>{
    try{
      const response=await fetch(`/games/heist/game.js?v=${VERSION}`,{cache:"no-store"});
      if(!response.ok)throw new Error(`HTTP ${response.status}`);
      let source=await response.text();

      source=source
        .replace(".slice(0,11+randInt(0,3));",".slice(0,14+randInt(0,3));")
        .replace("speed:rand(.38,.72)","speed:rand(.56,1.02)")
        .replace("range:rand(145,190)","range:rand(190,245)")
        .replace("fov:rand(.72,.98)","fov:rand(1.02,1.32)");

      source=replaceFunction(source,"renderDial","updateDialTarget",`  function renderDial(master){
    crack.needle=rand(0,360);crack.target=rand(48,312);crack.direction=rng()<.5?-1:1;crack.speed=master?112:92;crack.round=0;crack.rounds=master?4:3;crack.window=master?54:62;crack.nearTick=false;
    $("crackInstruction").textContent="Стопори кодовый диск, когда стрелка находится внутри широкой зелёной зоны.";
    $("crackGame").innerHTML=\`<div class="dialGame"><div class="dialFace"><i class="dialTarget" id="dialTarget"></i><i class="dialNeedle" id="dialNeedle"></i></div><div class="dialInfo"><strong id="dialRound">1/\${crack.rounds}</strong><small>Зелёная зона полностью совпадает с реальной областью попадания. Финальный сектор дополнительно упрощён.</small><button class="dialTap" id="dialTap" type="button">ЗАФИКСИРОВАТЬ</button></div></div>\`;
    updateDialTarget();$("dialTap").addEventListener("click",dialAttempt);
  }`);

      source=replaceFunction(source,"dialAttempt","updateCrack",`  function dialAttempt(){
    const diff=degDiff(crack.needle,crack.target),finalRound=crack.round===crack.rounds-1,assist=finalRound?16:9;
    if(diff<=crack.window/2+assist){
      crack.round++;crack.progress=crack.round/crack.rounds;$("crackProgressBar").style.width=\`\${crack.progress*100}%\`;tg?.HapticFeedback?.impactOccurred?.("heavy");
      if(crack.round>=crack.rounds){crackStageSuccess();return;}
      crack.target=rand(48,312);crack.direction*=-1;crack.speed*=1.035;if(crack.round===crack.rounds-1)crack.speed*=.76;crack.nearTick=false;updateDialTarget();
      $("crackMessage").textContent=crack.round===crack.rounds-1?"Последний сектор замедлен — попади внутрь зелёной зоны.":"Точное попадание! Следующий сектор немного быстрее.";$("crackMessage").className="crackMessage success";
    }else{
      crackError(crack.safe.tier===4?11:8,\`Промах на \${Math.round(diff)}° — попади внутрь подсвеченного сектора.\`);crack.round=Math.max(0,crack.round-1);crack.progress=crack.round/crack.rounds;$("crackProgressBar").style.width=\`\${crack.progress*100}%\`;crack.target=rand(48,312);crack.speed=Math.max(82,crack.speed*.9);crack.nearTick=false;updateDialTarget();
    }
  }`);

      source=source.replace(
        'if(crack.mode==="dial"){crack.needle=(crack.needle+crack.direction*crack.speed*dt+360)%360;const needle=$("dialNeedle");if(needle)needle.style.setProperty("--dial-angle",`${crack.needle}deg`);}',
        'if(crack.mode==="dial"){crack.needle=(crack.needle+crack.direction*crack.speed*dt+360)%360;const needle=$("dialNeedle"),tap=$("dialTap"),diff=degDiff(crack.needle,crack.target),near=diff<=crack.window/2+13;if(needle)needle.style.setProperty("--dial-angle",`${crack.needle}deg`);tap?.classList.toggle("dial-near",near);if(near&&!crack.nearTick){crack.nearTick=true;tg?.HapticFeedback?.impactOccurred?.("light");}if(!near)crack.nearTick=false;}'
      );

      source=replaceFunction(source,"updateCameras","updateCamera",`  function updateCameras(dt){
    let detected=0,suspicious=0;
    for(const cam of cameras){
      cam.pause-=dt;const seen=cameraSeesPlayer(cam);
      if(seen){const target=Math.atan2(player.y-cam.y,player.x-cam.x);cam.angle+=normAngle(target-cam.angle)*Math.min(1,dt*(cam.state==="detected"?4.2:2.8));}
      else if(cam.pause<=0){cam.angle+=cam.speed*dt;if(rng()<dt*.075){cam.pause=rand(.16,.5);cam.speed*=-1;}}
      cam.alert=clamp(cam.alert+(seen?dt*3.45:-dt*.68),0,1);const prev=cam.state;cam.state=cam.alert>.4?"detected":cam.alert>.07?"suspicious":"search";
      if(cam.state==="detected")detected++;else if(cam.state==="suspicious")suspicious++;
      if(prev!==cam.state&&cam.state==="suspicious"){showBanner("КАМЕРА ЗАМЕТИЛА ДВИЖЕНИЕ",.85);tg?.HapticFeedback?.impactOccurred?.("light");}
      if(prev!==cam.state&&cam.state==="detected"){showBanner("КАМЕРА ЗАХВАТИЛА ЦЕЛЬ",1.25);shake=Math.max(shake,.32);tg?.HapticFeedback?.notificationOccurred?.("warning");}
    }
    if(detected)alarm+=dt*(32+detected*13);else if(suspicious)alarm+=dt*(8+suspicious*3.5);else alarm-=dt*2.6;
    alarm=clamp(alarm,0,100);maxAlarm=Math.max(maxAlarm,alarm);if(alarm>=100)finishGame("Система безопасности тебя поймала",.2);
  }`);

      source=replaceFunction(source,"drawSafe","drawCamera",`  function drawSafe(safe,t){
    const p=screen(safe.x,safe.y),meta=SAFE_META[safe.tier],s=meta.size;if(p.x<-70||p.x>viewW+70||p.y<hudSafe-70||p.y>viewH+70)return;
    ctx.save();ctx.globalAlpha=.5;ctx.fillStyle="#000";ctx.beginPath();ctx.ellipse(p.x,p.y+s*.72,s*.84,s*.28,0,0,Math.PI*2);ctx.fill();ctx.restore();
    if(!safe.opened&&safe.tier>=3){ctx.save();ctx.translate(p.x,p.y);ctx.rotate(t*.55+safe.id);for(let i=0;i<(safe.tier===4?8:5);i++){const a=i/((safe.tier===4?8:5))*Math.PI*2,r=s+9+(i%2)*4;ctx.fillStyle=meta.color;ctx.globalAlpha=.25+.3*Math.sin(t*3+i);ctx.shadowBlur=10;ctx.shadowColor=meta.color;ctx.beginPath();ctx.arc(Math.cos(a)*r,Math.sin(a)*r,1.5+(i%2),0,Math.PI*2);ctx.fill();}ctx.restore();}
    ctx.save();ctx.translate(p.x,p.y);const pulse=.72+.28*Math.sin(t*(safe.tier+1)*1.5+safe.id);if(!safe.opened){ctx.shadowBlur=safe.tier>=3?32*pulse:16*pulse;ctx.shadowColor=meta.color;}ctx.fillStyle=safe.opened?"#151319":safe.tier===4?"#8e6325":safe.tier===3?"#4b2d64":safe.tier===2?"#28474d":"#604820";rounded(ctx,-s,-s*.8,s*2,s*1.6,8);ctx.fill();ctx.lineWidth=safe.tier===4?4:3;ctx.strokeStyle=safe.opened?"#4d4848":meta.color;ctx.stroke();ctx.shadowBlur=0;
    if(!safe.opened){ctx.save();rounded(ctx,-s+3,-s*.8+3,s*2-6,s*1.6-6,6);ctx.clip();const shine=((t*.55+safe.id*.21)%1)*(s*3)-s*1.5;const grad=ctx.createLinearGradient(shine-18,0,shine+18,0);grad.addColorStop(0,"transparent");grad.addColorStop(.5,"rgba(255,255,255,.2)");grad.addColorStop(1,"transparent");ctx.fillStyle=grad;ctx.fillRect(-s,-s,s*2,s*2);ctx.restore();ctx.strokeStyle="#ffffff25";ctx.strokeRect(-s+6,-s*.8+6,s*2-12,s*1.6-12);ctx.fillStyle="#0b090d";ctx.beginPath();ctx.arc(0,0,safe.tier===4?9:7,0,Math.PI*2);ctx.fill();ctx.strokeStyle=meta.color;ctx.lineWidth=2;ctx.stroke();for(const [x,y] of [[-s+7,-s*.8+7],[s-7,-s*.8+7],[-s+7,s*.8-7],[s-7,s*.8-7]]){ctx.fillStyle="#d6b978";ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();}if(safe.tier===4){ctx.fillStyle="#ffe394";ctx.font="900 12px system-ui";ctx.textAlign="center";ctx.fillText("VAULT",0,-s*.8-9);}}
    else{ctx.fillStyle="#070609";ctx.fillRect(-s+7,-s*.8+7,s*1.65,s*1.6-14);}ctx.restore();
  }`);

      source=replaceFunction(source,"drawCamera","drawRoute",`  function drawCamera(cam){
    const p=screen(cam.x,cam.y);if(p.x<-cam.range||p.x>viewW+cam.range||p.y<hudSafe-cam.range||p.y>viewH+cam.range)return;ctx.save();ctx.translate(p.x,p.y);const color=cam.state==="detected"?"#ff203f":cam.state==="suspicious"?"#ffbd3d":"#ef416d",pulse=.72+.28*Math.sin(ticker*7+cam.id);
    if(smokeTime<=0){ctx.beginPath();ctx.moveTo(0,0);const samples=24;for(let i=0;i<=samples;i++){const a=cam.angle-cam.fov/2+cam.fov*i/samples,d=rayDistance(cam.x,cam.y,a,cam.range);ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d);}ctx.closePath();const g=ctx.createRadialGradient(0,0,3,0,0,cam.range);g.addColorStop(0,color+"a8");g.addColorStop(.58,color+"48");g.addColorStop(1,color+"00");ctx.fillStyle=g;ctx.fill();}
    ctx.save();ctx.rotate(-ticker*.8*cam.speed);ctx.strokeStyle=color;ctx.globalAlpha=.38+.3*pulse;ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(0,0,24,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.restore();ctx.shadowBlur=cam.state==="detected"?38:20;ctx.shadowColor=color;ctx.fillStyle=cam.state==="detected"?"#e91f43":"#8d2946";ctx.beginPath();ctx.arc(0,0,18,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=cam.state==="suspicious"?"#ffe28b":"#ffb0c1";ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(0,0,14,8.5,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(0,0,4.8,0,Math.PI*2);ctx.fill();ctx.fillStyle="#16060c";ctx.beginPath();ctx.arc(0,0,2.5,0,Math.PI*2);ctx.fill();
    if(cam.state==="detected"&&!segmentBlocked(cam.x,cam.y,player.x,player.y)){const pp=screen(player.x,player.y);ctx.strokeStyle="#ff2449";ctx.lineWidth=2;ctx.globalAlpha=.72+.25*pulse;ctx.shadowBlur=10;ctx.shadowColor="#ff2449";ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(pp.x-p.x,pp.y-p.y);ctx.stroke();}
    ctx.restore();
  }`);

      source=replaceFunction(source,"drawPlayer","drawEffects",`  function drawPlayer(t){
    const p=screen(player.x,player.y),speedScale=player.stretch,bump=player.bump>0?.82:1;ctx.save();ctx.globalAlpha=.5;ctx.fillStyle="#000";ctx.beginPath();ctx.ellipse(p.x,p.y+14,16,7,0,0,Math.PI*2);ctx.fill();ctx.restore();ctx.save();ctx.translate(p.x,p.y);ctx.rotate(player.angle);const sx=(1+speedScale*.23)*bump,sy=(1-speedScale*.13)*(2-bump);ctx.scale(sx,sy);ctx.shadowBlur=alarm>60?30:25;ctx.shadowColor=alarm>60?"#ff365d":"#a76bff";const g=ctx.createRadialGradient(-3,-4,2,0,0,player.r*1.55);g.addColorStop(0,"#e4c2ff");g.addColorStop(.42,"#b177ff");g.addColorStop(1,"#55258f");ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,player.r,0,Math.PI*2);ctx.fill();ctx.restore();ctx.save();ctx.translate(p.x,p.y-player.r-9-Math.sin(t*5)*1.5);ctx.rotate(Math.sin(t*5)*.1+player.vx*.0008);ctx.font="20px system-ui";ctx.textAlign="center";ctx.shadowBlur=10;ctx.shadowColor="#ffd76c";ctx.fillText("👑",0,3);ctx.restore();if(nearestSafe(62)){ctx.strokeStyle="#ffe394aa";ctx.lineWidth=2.2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(p.x,p.y,29+Math.sin(t*4)*3,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}if(alarm>35){ctx.strokeStyle=\`rgba(255,54,93,\${.18+alarm/180})\`;ctx.lineWidth=2;ctx.beginPath();ctx.arc(p.x,p.y,22+Math.sin(t*8)*2,0,Math.PI*2);ctx.stroke();}
  }`);

      const blob=new Blob([source],{type:"text/javascript"}),url=URL.createObjectURL(blob),script=document.createElement("script");
      script.src=url;script.onload=async()=>{URL.revokeObjectURL(url);await installPost()};script.onerror=async error=>{console.error("Heist transformed game failed",error);URL.revokeObjectURL(url);await loadScript("/games/heist/game.js");await installPost()};document.body.appendChild(script);
    }catch(error){console.error("Heist v87 loader failed",error);await loadScript("/games/heist/game.js");await installPost()}
  };
  boot();
})();
