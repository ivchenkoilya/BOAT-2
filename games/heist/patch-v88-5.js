(()=>{
  "use strict";
  (window.__heistV88Patches||(window.__heistV88Patches=[])).push((source,replaceFunction)=>{
    source=source
      .replace('let idleTime=0,mapCode="—",pauseStarted=0;','let idleTime=0,mapCode="—",pauseStarted=0,baitCharges=1,baitTime=0,baitX=0,baitY=0,securityDisabledUntil=0;')
      .replace('let cells=[],walls=[],safes=[],cameras=[],decor=[],particles=[],trails=[],floaters=[],route=[],discovered=new Set();','let cells=[],walls=[],safes=[],cameras=[],decor=[],terminals=[],securityDoors=[],particles=[],trails=[],floaters=[],route=[],discovered=new Set();')
      .replace('    decor=[];','    for(const cam of cameras){cam.baseX=cam.x;cam.baseY=cam.y;cam.railAxis=rng()<.5?"x":"y";cam.railPhase=rand(0,Math.PI*2);}\n    const terminalCells=shuffle(cells.filter(c=>manhattan(c,START)>3&&(c.zone==="tech"||c.zone==="security")&&!occupied.has(cellKey(c.c,c.r)))).slice(0,3);terminals=terminalCells.map((c,i)=>{const p=center(c.c,c.r);return{x:p.x+rand(-16,16),y:p.y+rand(-16,16),c:c.c,r:c.r,type:i%2?"reveal":"disable",used:false};});\n    securityDoors=[];for(const c of shuffle(cells.filter(c=>manhattan(c,START)>4&&!occupied.has(cellKey(c.c,c.r))))){if(securityDoors.length>=5)break;if(!c.e&&c.c<COLS-1)securityDoors.push({x:(c.c+1)*CELL-WALL/2,y:c.r*CELL+18,w:WALL,h:CELL-36,phase:rand(0,6),disabled:false});else if(!c.s&&c.r<ROWS-1)securityDoors.push({x:c.c*CELL+18,y:(c.r+1)*CELL-WALL/2,w:CELL-36,h:WALL,phase:rand(0,6),disabled:false});}\n    decor=[];')
      .replace('escapeMode=false;stage.classList.remove("escape-mode");','escapeMode=false;baitCharges=1;baitTime=0;securityDisabledUntil=0;stage.classList.remove("escape-mode");document.dispatchEvent(new CustomEvent("heist:bait-state",{detail:{charges:baitCharges}}));')
      .replace('timeLeft=Math.max(0,duration-(performance.now()-startedAt)/1000);if(smokeTime>0)','timeLeft=Math.max(0,duration-(performance.now()-startedAt)/1000);if(baitTime>0)baitTime=Math.max(0,baitTime-dt);if(smokeTime>0)')
      .replace('drawFloor();drawDecor();drawRoute();drawExit(ticker);','drawFloor();drawDecor();drawSecuritySystems(ticker);drawRoute();drawExit(ticker);')
      .replace('const x=pad+player.x*sx,y=pad+player.y*sy;','for(const term of terminals){if(term.used||!discovered.has(cellKey(term.c,term.r)))continue;mini.fillStyle=term.type==="disable"?"#70d9e8":"#a995d6";mini.fillRect(pad+term.x*sx-2,pad+term.y*sy-2,4,4);}const x=pad+player.x*sx,y=pad+player.y*sy;');

    source=replaceFunction(source,"pointInWall","pointHitsWall",`  function doorClosed(d){
    if(performance.now()<securityDisabledUntil)return false;const px=player.x,py=player.y;if(px>d.x-18&&px<d.x+d.w+18&&py>d.y-18&&py<d.y+d.h+18)return false;return (escapeMode||alarm>=42)&&Math.sin(performance.now()/650+d.phase)>.05;
  }
  function pointInWall(x,y,r=player.r){return x-r<0||y-r<0||x+r>WORLD_W||y+r>WORLD_H||walls.some(w=>x+r>w.x&&x-r<w.x+w.w&&y+r>w.y&&y-r<w.y+w.h)||securityDoors.some(d=>doorClosed(d)&&x+r>d.x&&x-r<d.x+d.w&&y+r>d.y&&y-r<d.y+d.h);}`);

    source=replaceFunction(source,"interact","useSmoke",`  function nearestTerminal(limit=62){let best=null,d=Infinity;for(const t of terminals){if(t.used)continue;const n=Math.hypot(player.x-t.x,player.y-t.y);if(n<d){d=n;best=t;}}return d<=limit?best:null;}
  function useTerminal(term){term.used=true;if(term.type==="disable"){securityDisabledUntil=performance.now()+12000;for(const cam of cameras){cam.alert=0;cam.state="search";}alarm=Math.max(0,alarm-18);showBanner("ОХРАНА ОТКЛЮЧЕНА НА 12 СЕКУНД",1.8);setHint("💻 Камеры и охранные двери временно отключены.",true);}else{for(const c of cells)discovered.add(cellKey(c.c,c.r));showBanner("КАРТА ХРАНИЛИЩА ЗАГРУЖЕНА",1.6);setHint("🗺 Все помещения открыты на мини-карте.",true);}tg?.HapticFeedback?.notificationOccurred?.("success");}
  function useBait(){if(!running||crack.active||baitCharges<=0)return;const tx=player.x+Math.cos(player.angle)*72,ty=player.y+Math.sin(player.angle)*72;baitX=pointInWall(tx,ty,8)?player.x:tx;baitY=pointInWall(tx,ty,8)?player.y:ty;baitTime=6.5;baitCharges--;for(const cam of cameras){if(Math.hypot(cam.x-baitX,cam.y-baitY)<380){cam.alert=Math.max(0,cam.alert-.25);cam.angle=Math.atan2(baitY-cam.y,baitX-cam.x);}}burst(baitX,baitY,"#70d9e8",34,120);showBanner("ПРИМАНКА СОЗДАЛА ЛОЖНЫЙ ШУМ",1.5);setHint("📡 Камеры рядом повернулись к приманке.",true);document.dispatchEvent(new CustomEvent("heist:bait-state",{detail:{charges:baitCharges}}));tg?.HapticFeedback?.impactOccurred?.("medium");}
  document.addEventListener("heist:bait",useBait);
  function interact(){if(!running||crack.active)return;const term=nearestTerminal();if(term){useTerminal(term);return;}const safe=nearestSafe();if(safe){openCrack(safe);return;}if(nearExit()){if(loot<=0){setHint("Сначала вскрой хотя бы один сейф.",true);return;}finishGame(opened===totalSafes?"Идеальное ограбление: вынесены все сейфы":"Ты успешно покинул хранилище",1);return;}setHint("Подойди ближе к сейфу, терминалу или выходу.",true);}`);

    source=replaceFunction(source,"updateActionButton","burst",`  function updateActionButton(){const button=$("interact"),term=nearestTerminal(),safe=nearestSafe();button.classList.remove("ready","exit","search");if(term){button.disabled=false;button.classList.add("ready");button.textContent=term.type==="disable"?"💻 ОТКЛЮЧИТЬ ОХРАНУ":"🗺 СКАЧАТЬ КАРТУ";setHint(term.type==="disable"?"Рядом терминал охраны":"Рядом картографический терминал");return;}if(safe){button.disabled=false;button.classList.add("ready");button.textContent=safe.tier===4?"🏛 ВСКРЫТЬ ХРАНИЛИЩЕ":safe.tier===3?"💎 ВЗЛОМАТЬ ЭЛИТНЫЙ СЕЙФ":safe.tier===2?"🧰 ВСКРЫТЬ УСИЛЕННЫЙ СЕЙФ":"🔓 ВСКРЫТЬ СЕЙФ";setHint("Рядом "+SAFE_META[safe.tier].label.toLowerCase()+" сейф — начинай взлом");return;}if(nearExit()){button.disabled=false;button.classList.add("exit","ready");button.textContent=loot?"🚪 УЙТИ С ДОБЫЧЕЙ":"🚪 СНАЧАЛА НАЙДИ ДОБЫЧУ";return;}button.disabled=true;button.classList.add("search");button.textContent=idleTime>=7?"🧭 МАРШРУТ К ЦЕЛИ":"🔎 ПОДОЙДИ К ЦЕЛИ";}`);

    source=replaceFunction(source,"updateCameras","updateCamera",`  function updateCameras(dt){
    let detectedVisible=0,suspiciousVisible=0;const modeMult=escapeMode?1.12:1,disabled=performance.now()<securityDisabledUntil;
    for(const cam of cameras){
      if(!cam.baseX){cam.baseX=cam.x;cam.baseY=cam.y;cam.railAxis=rng()<.5?"x":"y";cam.railPhase=rand(0,6);}
      if(disabled){cam.alert=0;cam.state="search";continue;}
      const lure=baitTime>0&&Math.hypot(cam.x-baitX,cam.y-baitY)<380&&!segmentBlocked(cam.x,cam.y,baitX,baitY);
      const seen=!lure&&cameraSeesPlayer(cam);
      cam.pause-=dt;
      if(lure){const target=Math.atan2(baitY-cam.y,baitX-cam.x);cam.angle+=normAngle(target-cam.angle)*Math.min(1,dt*4.2);cam.alert=Math.max(0,cam.alert-dt*2.4);}
      else if(seen){const target=Math.atan2(player.y-cam.y,player.x-cam.x);cam.angle+=normAngle(target-cam.angle)*Math.min(1,dt*(cam.state==="detected"?3.6:2.6));}
      else if(cam.pause<=0){cam.angle+=cam.speed*dt*modeMult;if(rng()<dt*.065){cam.pause=rand(.2,.55);cam.speed*=-1;}}
      if(!seen&&cam.state!=="detected"){const rail=Math.sin(performance.now()/1100+cam.railPhase)*14;cam.x=cam.baseX+(cam.railAxis==="x"?rail:0);cam.y=cam.baseY+(cam.railAxis==="y"?rail:0);}
      cam.alert=clamp(cam.alert+(seen?dt*1.55:-dt*2.8),0,1);
      const prev=cam.state;
      cam.state=seen?(cam.alert>.72?"detected":cam.alert>.18?"suspicious":"search"):(cam.alert>.22?"suspicious":"search");
      if(seen&&cam.state==="detected")detectedVisible++;else if(seen&&cam.state==="suspicious")suspiciousVisible++;
      if(prev!==cam.state&&cam.state==="suspicious"&&seen){showBanner("КАМЕРА ЗАМЕТИЛА ДВИЖЕНИЕ",.85);tg?.HapticFeedback?.impactOccurred?.("light");}
      if(prev!==cam.state&&cam.state==="detected"&&seen){showBanner("КАМЕРА ЗАХВАТИЛА ЦЕЛЬ",1.1);shake=Math.max(shake,.24);tg?.HapticFeedback?.notificationOccurred?.("warning");}
    }
    if(detectedVisible)alarm+=dt*(18+detectedVisible*6.5)*modeMult;
    else if(suspiciousVisible)alarm+=dt*(4+suspiciousVisible*1.4)*modeMult;
    else alarm-=dt*(escapeMode?2.5:5.5);
    alarm=clamp(alarm,0,100);maxAlarm=Math.max(maxAlarm,alarm);if(alarm>=100)finishGame("Система безопасности тебя поймала",.2);
  }`);

    source=source.replace('  function drawExit(t){',`  function drawSecuritySystems(t){
    for(const term of terminals){if(term.used)continue;const p=screen(term.x,term.y),color=term.type==="disable"?"#70d9e8":"#a995d6";ctx.save();ctx.shadowBlur=18;ctx.shadowColor=color;ctx.fillStyle="#091318";rounded(ctx,p.x-18,p.y-15,36,30,7);ctx.fill();ctx.strokeStyle=color;ctx.lineWidth=2;ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle=color;ctx.font="900 13px system-ui";ctx.textAlign="center";ctx.fillText(term.type==="disable"?"⌁":"⌖",p.x,p.y+5);ctx.restore();}
    for(const d of securityDoors){const closed=doorClosed(d),p=screen(d.x,d.y);ctx.save();ctx.globalAlpha=closed?1:.18;ctx.fillStyle=closed?"#7d172b":"#27333a";ctx.shadowBlur=closed?16:0;ctx.shadowColor="#ff365d";rounded(ctx,p.x,p.y,d.w,d.h,3);ctx.fill();ctx.strokeStyle=closed?"#ff5572":"#70d9e8";ctx.stroke();ctx.restore();}
    if(baitTime>0){const p=screen(baitX,baitY),pulse=.7+.3*Math.sin(t*12);ctx.save();ctx.strokeStyle="#70d9e8";ctx.lineWidth=2;ctx.globalAlpha=pulse;ctx.shadowBlur=18;ctx.shadowColor="#70d9e8";for(let r=10;r<=28;r+=9){ctx.beginPath();ctx.arc(p.x,p.y,r+(1-pulse)*5,0,Math.PI*2);ctx.stroke();}ctx.fillStyle="#d9fbff";ctx.font="16px system-ui";ctx.textAlign="center";ctx.fillText("📡",p.x,p.y+5);ctx.restore();}
  }
  function drawExit(t){`);
    return source;
  });
})();
