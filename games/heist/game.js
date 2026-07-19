(()=>{
  "use strict";

  const tg=window.Telegram?.WebApp;
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.("#090710");
  tg?.setBackgroundColor?.("#090710");

  const params=new URLSearchParams(location.search);
  const chatId=params.get("chat_id")||"";
  const initData=tg?.initData||"";
  const headers={"Content-Type":"application/json","X-Telegram-Init-Data":initData};
  const $=id=>document.getElementById(id);

  const canvas=$("game");
  const ctx=canvas.getContext("2d");
  const miniCanvas=$("miniMap");
  const mini=miniCanvas.getContext("2d");
  const stage=$("stage");
  const app=$("app");
  const fxLayer=$("fxLayer");

  const CELL=88;
  const COLS=10;
  const ROWS=14;
  const WORLD_W=COLS*CELL;
  const WORLD_H=ROWS*CELL;
  const WALL=10;
  const START_CELL={c:0,r:ROWS-1};
  const ZONES=["gold","tech","security","laser","broken"];
  const ZONE_META={
    gold:{floor:"#211814",line:"#6d4a26",accent:"#ffd76c",label:"ЗОЛОТОЙ СЕКТОР"},
    tech:{floor:"#11171a",line:"#294a50",accent:"#70d9e8",label:"ТЕХНИЧЕСКИЙ СЕКТОР"},
    security:{floor:"#181116",line:"#543040",accent:"#ff6f8b",label:"ПОСТ ОХРАНЫ"},
    laser:{floor:"#171012",line:"#5c242c",accent:"#ff455f",label:"ЛАЗЕРНЫЙ СЕКТОР"},
    broken:{floor:"#151419",line:"#393746",accent:"#a995d6",label:"АВАРИЙНЫЙ СЕКТОР"}
  };

  let dpr=1;
  let viewW=400;
  let viewH=620;
  let running=false;
  let ended=false;
  let demo=false;
  let sessionId="";
  let seed=1;
  let rng=Math.random;
  let duration=135;
  let timeLeft=duration;
  let startedAt=0;
  let lastFrame=0;
  let loot=0;
  let secured=0;
  let alarm=0;
  let maxAlarm=0;
  let opened=0;
  let totalSafes=0;
  let smokeTime=0;
  let smokeCooldown=0;
  let moveX=0;
  let moveY=0;
  let shake=0;
  let flash=0;
  let alertTier=0;
  let bannerTimer=0;
  let zoneLabelTimer=0;
  let currentZone="";
  let activeUnlock=null;
  let activeUnlockElapsed=0;
  let route=[];
  let mapCode="—";

  const player={x:CELL/2,y:WORLD_H-CELL/2,r:12,vx:0,vy:0,stretch:0,bump:0,angle:0};
  const camera={x:0,y:Math.max(0,WORLD_H-viewH)};
  const exit={x:15,y:WORLD_H-73,w:58,h:58};
  let cells=[];
  let walls=[];
  let safes=[];
  let cameras=[];
  let particles=[];
  let trails=[];
  let floaters=[];
  let discovered=new Set();

  function seeded(value){
    let s=(Number(value)||1)>>>0;
    return()=>((s=Math.imul(s,1664525)+1013904223>>>0)/4294967296);
  }
  const rand=(a,b)=>a+(b-a)*rng();
  const randInt=(a,b)=>Math.floor(rand(a,b+1));
  function shuffle(items){
    for(let i=items.length-1;i>0;i--){
      const j=Math.floor(rng()*(i+1));
      [items[i],items[j]]=[items[j],items[i]];
    }
    return items;
  }
  const indexOf=(c,r)=>r*COLS+c;
  const cellAt=(c,r)=>c>=0&&r>=0&&c<COLS&&r<ROWS?cells[indexOf(c,r)]:null;
  const centerOf=(c,r)=>({x:c*CELL+CELL/2,y:r*CELL+CELL/2});
  const cellDistance=(a,b)=>Math.abs(a.c-b.c)+Math.abs(a.r-b.r);
  const keyOf=(c,r)=>`${c}:${r}`;
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));

  function zoneForCell(c,r){
    const band=Math.floor(r/3);
    const offset=(Math.floor(c/3)+band+(seed%ZONES.length))%ZONES.length;
    return ZONES[offset];
  }

  function buildMaze(){
    cells=Array.from({length:COLS*ROWS},(_,i)=>({
      c:i%COLS,r:Math.floor(i/COLS),visited:false,n:true,e:true,s:true,w:true,
      zone:zoneForCell(i%COLS,Math.floor(i/COLS))
    }));
    const start=cellAt(START_CELL.c,START_CELL.r);
    const stack=[start];
    start.visited=true;
    while(stack.length){
      const current=stack[stack.length-1];
      const options=[];
      const north=cellAt(current.c,current.r-1);
      const east=cellAt(current.c+1,current.r);
      const south=cellAt(current.c,current.r+1);
      const west=cellAt(current.c-1,current.r);
      if(north&&!north.visited)options.push(["n",north,"s"]);
      if(east&&!east.visited)options.push(["e",east,"w"]);
      if(south&&!south.visited)options.push(["s",south,"n"]);
      if(west&&!west.visited)options.push(["w",west,"e"]);
      if(!options.length){stack.pop();continue;}
      const [side,next,back]=options[Math.floor(rng()*options.length)];
      current[side]=false;
      next[back]=false;
      next.visited=true;
      stack.push(next);
    }
    for(let i=0;i<24;i++){
      const c=randInt(0,COLS-1);
      const r=randInt(0,ROWS-1);
      const cell=cellAt(c,r);
      if(rng()<.5&&c<COLS-1){cell.e=false;cellAt(c+1,r).w=false;}
      else if(r<ROWS-1){cell.s=false;cellAt(c,r+1).n=false;}
    }
    walls=[];
    const add=(x,y,w,h)=>walls.push({x,y,w,h});
    for(const cell of cells){
      const x=cell.c*CELL;
      const y=cell.r*CELL;
      if(cell.n)add(x,y,CELL,WALL);
      if(cell.w)add(x,y,WALL,CELL);
      if(cell.c===COLS-1&&cell.e)add(x+CELL-WALL,y,WALL,CELL);
      if(cell.r===ROWS-1&&cell.s)add(x,y+CELL-WALL,CELL,WALL);
    }
  }

  function cellNeighbors(cell){
    const out=[];
    if(!cell.n)out.push(cellAt(cell.c,cell.r-1));
    if(!cell.e)out.push(cellAt(cell.c+1,cell.r));
    if(!cell.s)out.push(cellAt(cell.c,cell.r+1));
    if(!cell.w)out.push(cellAt(cell.c-1,cell.r));
    return out.filter(Boolean);
  }

  function shortestPath(from,to){
    const queue=[from];
    const prev=new Map([[keyOf(from.c,from.r),null]]);
    while(queue.length){
      const current=queue.shift();
      if(current.c===to.c&&current.r===to.r)break;
      for(const next of cellNeighbors(current)){
        const key=keyOf(next.c,next.r);
        if(prev.has(key))continue;
        prev.set(key,current);
        queue.push(next);
      }
    }
    const result=[];
    let cursor=to;
    while(cursor){
      result.push(cursor);
      cursor=prev.get(keyOf(cursor.c,cursor.r));
    }
    return result.reverse();
  }

  function buildObjects(){
    const candidates=shuffle(cells.filter(cell=>cellDistance(cell,START_CELL)>=2));
    const farthest=[...candidates].sort((a,b)=>cellDistance(b,START_CELL)-cellDistance(a,START_CELL))[0];
    totalSafes=11+randInt(0,2);
    const selected=[farthest,...candidates.filter(c=>c!==farthest).slice(0,totalSafes-1)];
    safes=selected.map((cell,i)=>{
      const center=centerOf(cell.c,cell.r);
      const dist=cellDistance(cell,START_CELL);
      let tier=i===0?4:(dist>15||rng()>.84?3:dist>8||rng()>.5?2:1);
      const value=tier===4?randInt(70,92):tier===3?randInt(43,59):tier===2?randInt(29,42):randInt(17,28);
      return{
        x:center.x+rand(-12,12),y:center.y+rand(-12,12),cell,tier,value,
        opened:false,unlocking:false,unlockProgress:0,
        unlockDuration:tier===4?1.8:tier===3?1.18:tier===2?.9:.68,id:i
      };
    });
    const safeCells=new Set(selected.map(c=>keyOf(c.c,c.r)));
    const cameraCells=shuffle(candidates.filter(c=>!safeCells.has(keyOf(c.c,c.r)))).slice(0,9+randInt(0,2));
    cameras=cameraCells.map((cell,i)=>{
      const center=centerOf(cell.c,cell.r);
      return{
        x:center.x+rand(-10,10),y:center.y+rand(-10,10),cell,
        angle:rand(0,Math.PI*2),speed:rand(.35,.72)*(rng()<.5?-1:1),
        range:rand(120,168),fov:rand(.68,.94),alert:0,state:"search",pause:rand(0,2),id:i
      };
    });
    player.x=CELL/2;player.y=WORLD_H-CELL/2;player.vx=0;player.vy=0;
    exit.x=15;exit.y=WORLD_H-73;
    camera.x=0;camera.y=Math.max(0,WORLD_H-viewH);
    particles=[];trails=[];floaters=[];discovered=new Set();
    revealAround(START_CELL.c,START_CELL.r,1);
    mapCode=String(seed>>>0).slice(-4).padStart(4,"0");
    $("mapCode").textContent=`КАРТА ${mapCode}`;
    $("safes").textContent=`СЕЙФЫ 0/${totalSafes}`;
    updateRoute();
  }

  function revealAround(c,r,radius=1){
    for(let y=r-radius;y<=r+radius;y++)for(let x=c-radius;x<=c+radius;x++){
      if(cellAt(x,y)&&Math.abs(x-c)+Math.abs(y-r)<=radius+1)discovered.add(keyOf(x,y));
    }
  }

  function playerCell(){
    return cellAt(clamp(Math.floor(player.x/CELL),0,COLS-1),clamp(Math.floor(player.y/CELL),0,ROWS-1));
  }

  function updateRoute(){
    const current=playerCell()||cellAt(START_CELL.c,START_CELL.r);
    route=(opened===totalSafes||timeLeft<20)?shortestPath(current,cellAt(START_CELL.c,START_CELL.r)):[];
  }

  function pointInWall(x,y,r=player.r){
    if(x-r<0||y-r<0||x+r>WORLD_W||y+r>WORLD_H)return true;
    return walls.some(w=>x+r>w.x&&x-r<w.x+w.w&&y+r>w.y&&y-r<w.y+w.h);
  }

  function lineBlocked(x1,y1,x2,y2){
    const distance=Math.hypot(x2-x1,y2-y1);
    const steps=Math.max(2,Math.ceil(distance/8));
    for(let i=1;i<steps;i++){
      const t=i/steps;
      const x=x1+(x2-x1)*t;
      const y=y1+(y2-y1)*t;
      if(walls.some(w=>x>w.x&&x<w.x+w.w&&y>w.y&&y<w.y+w.h))return true;
    }
    return false;
  }

  function angleDelta(value){
    while(value>Math.PI)value-=Math.PI*2;
    while(value<-Math.PI)value+=Math.PI*2;
    return value;
  }

  function cameraSeesPlayer(cam){
    if(smokeTime>0)return false;
    const dx=player.x-cam.x;
    const dy=player.y-cam.y;
    const distance=Math.hypot(dx,dy);
    if(distance>cam.range)return false;
    const angle=Math.atan2(dy,dx);
    if(Math.abs(angleDelta(angle-cam.angle))>cam.fov/2)return false;
    return !lineBlocked(cam.x,cam.y,player.x,player.y);
  }

  function nearestSafe(){
    let found=null;
    let distance=Infinity;
    for(const safe of safes){
      if(safe.opened)continue;
      const d=Math.hypot(player.x-safe.x,player.y-safe.y);
      if(d<distance){distance=d;found=safe;}
    }
    return distance<50?found:null;
  }

  function nearExit(){
    return player.x>exit.x-18&&player.x<exit.x+exit.w+18&&player.y>exit.y-18&&player.y<exit.y+exit.h+18;
  }

  function resize(){
    const rect=canvas.getBoundingClientRect();
    dpr=Math.min(2,window.devicePixelRatio||1);
    viewW=Math.max(1,rect.width);
    viewH=Math.max(1,rect.height);
    canvas.width=Math.round(viewW*dpr);
    canvas.height=Math.round(viewH*dpr);
    miniCanvas.width=Math.round(miniCanvas.clientWidth*dpr);
    miniCanvas.height=Math.round(miniCanvas.clientHeight*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  addEventListener("resize",resize);

  async function api(path,body={}){
    const response=await fetch(`/games/api/${path}`,{
      method:"POST",headers,body:JSON.stringify({...body,chat_id:chatId})
    });
    const data=await response.json().catch(()=>({ok:false,reason:"Сервер не ответил."}));
    if(!response.ok||!data.ok)throw new Error(data.reason||"Ошибка сервера.");
    return data;
  }

  async function startGame(){
    $("startError").textContent="";
    $("start").disabled=true;
    $("start").textContent="СОЗДАЁМ НОВОЕ ХРАНИЛИЩЕ…";
    $("introToGames").classList.add("hidden");
    try{
      const data=await api("start",{game:"heist"});
      sessionId=data.session_id;
      seed=Number(data.seed)||Date.now();
      duration=Math.max(135,Number(data.duration)||0);
      demo=false;
    }catch(error){
      if(initData){
        $("startError").textContent=error.message;
        $("start").disabled=false;
        $("start").textContent="ПОПРОБОВАТЬ СНОВА";
        $("introToGames").classList.remove("hidden");
        return;
      }
      sessionId="";
      seed=Date.now()>>>0;
      duration=135;
      demo=true;
      $("startError").textContent=`Демонстрационный режим: ${error.message}`;
    }
    rng=seeded(seed);
    buildMaze();
    buildObjects();
    running=true;ended=false;startedAt=performance.now();lastFrame=startedAt;
    timeLeft=duration;loot=0;secured=0;alarm=0;maxAlarm=0;opened=0;
    smokeTime=0;smokeCooldown=0;shake=0;flash=0;alertTier=0;bannerTimer=0;
    activeUnlock=null;activeUnlockElapsed=0;currentZone="";zoneLabelTimer=0;
    $("loot").textContent="0";
    $("alarmBar").style.width="0%";
    $("alarmText").textContent="0%";
    $("hint").textContent="Исследуй хранилище и найди сейфы";
    $("finish").classList.add("hidden");
    $("result").style.display="none";
    $("intro").classList.add("hidden");
    $("minimapWrap").classList.remove("expanded");
    setAlertClass(0);
    burst(player.x,player.y,"#a76bff",20,110);
    requestAnimationFrame(loop);
    $("start").disabled=false;
    $("start").textContent="НАЧАТЬ ОГРАБЛЕНИЕ";
  }

  function setHint(text,pop=false){
    const hint=$("hint");
    if(hint.textContent!==text)hint.textContent=text;
    if(pop){
      hint.classList.remove("pop");
      void hint.offsetWidth;
      hint.classList.add("pop");
    }
  }

  function showBanner(text,durationSeconds=1.5){
    $("alertBanner").textContent=text;
    $("alertBanner").classList.add("show");
    bannerTimer=durationSeconds;
  }

  function setAlertClass(tier){
    stage.classList.remove("alert-medium","alert-high","alert-critical");
    if(tier===1)stage.classList.add("alert-medium");
    if(tier===2)stage.classList.add("alert-high");
    if(tier===3)stage.classList.add("alert-critical");
  }

  function alarmTier(value){
    if(value>=85)return 3;
    if(value>=60)return 2;
    if(value>=30)return 1;
    return 0;
  }

  function onAlarmTierChanged(next){
    setAlertClass(next);
    if(next===1)showBanner("ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ",1.8);
    if(next===2){showBanner("ОХРАНА ПОДНЯТА ПО ТРЕВОГЕ",2);tg?.HapticFeedback?.notificationOccurred?.("warning");}
    if(next===3){showBanner("БЛОКИРОВКА ХРАНИЛИЩА",2.2);tg?.HapticFeedback?.notificationOccurred?.("error");shake=.6;}
  }

  function interact(){
    if(!running||activeUnlock)return;
    const safe=nearestSafe();
    if(safe){
      activeUnlock=safe;
      activeUnlockElapsed=0;
      safe.unlocking=true;
      tg?.HapticFeedback?.impactOccurred?.(safe.tier>=3?"heavy":"medium");
      setHint(safe.tier===4?"💎 Взлом главного сейфа… не двигайся!":"🔓 Взлом замка…",true);
      return;
    }
    if(nearExit()){
      if(loot<=0){setHint("Сначала вскрой хотя бы один сейф.",true);return;}
      finishGame(opened===totalSafes?"Идеальное ограбление: вынесены все сейфы":"Ты успешно покинул хранилище",1);
      return;
    }
    setHint("Подойди ближе к сейфу или зелёному выходу.",true);
  }

  function cancelUnlock(){
    if(!activeUnlock)return;
    activeUnlock.unlocking=false;
    activeUnlock.unlockProgress=0;
    activeUnlock=null;
    activeUnlockElapsed=0;
    setHint("Взлом прерван — подойди к сейфу снова.",true);
  }

  function completeUnlock(safe){
    safe.opened=true;
    safe.unlocking=false;
    safe.unlockProgress=1;
    opened++;
    const jackpot=rng()<(safe.tier===4?.32:.17)?Math.round(safe.value*(safe.tier===4?.7:.55)):0;
    const reward=safe.value+jackpot;
    loot+=reward;
    alarm=clamp(alarm+(safe.tier===4?14:safe.tier===3?10:6),0,100);
    burst(safe.x,safe.y,safe.tier>=3?"#d985ff":"#ffd76c",safe.tier===4?46:28,safe.tier===4?185:135);
    addFloater(safe.x,safe.y-18,`+${reward}`,safe.tier>=3?"#e9b8ff":"#ffe496",1.25);
    flyLoot(safe,reward);
    if(safe.tier>=3){
      stage.classList.remove("rare-open");void stage.offsetWidth;stage.classList.add("rare-open");
      fxLayer.insertAdjacentHTML("beforeend",'<i class="screenFlash"></i>');
      setTimeout(()=>fxLayer.querySelector(".screenFlash")?.remove(),500);
      flash=.45;
    }
    if(safe.tier===4)showBanner("ЛЕГЕНДАРНАЯ ДОБЫЧА",2);
    setHint(jackpot?`🍀 Джекпот сейфа: +${reward} влияния!`:`💰 Сейф вскрыт: +${reward} влияния`,true);
    tg?.HapticFeedback?.notificationOccurred?.("success");
    activeUnlock=null;activeUnlockElapsed=0;
    updateRoute();
  }

  function useSmoke(){
    if(!running||smokeCooldown>0)return;
    smokeTime=5.5;
    smokeCooldown=22;
    alarm=Math.max(0,alarm-24);
    for(const cam of cameras){cam.alert=Math.max(0,cam.alert-.55);cam.state="search";}
    burst(player.x,player.y,"#d8cbed",48,170);
    stage.classList.add("smoke-active");
    $("smokeStatus").classList.remove("hidden");
    showBanner("КАМЕРЫ ПОТЕРЯЛИ ЦЕЛЬ",1.6);
    setHint("🌫 Дым скрывает тебя от камер на 5 секунд.",true);
    tg?.HapticFeedback?.impactOccurred?.("medium");
  }

  function updatePlayer(dt){
    const input=Math.hypot(moveX,moveY);
    const oldX=player.x;
    const oldY=player.y;
    if(activeUnlock&&input>.25){cancelUnlock();}
    if(input>.04&&!activeUnlock){
      const nx=moveX/input;
      const ny=moveY/input;
      const speed=smokeTime>0?178:155;
      player.vx+=(nx*speed-player.vx)*Math.min(1,dt*11);
      player.vy+=(ny*speed-player.vy)*Math.min(1,dt*11);
      player.angle=Math.atan2(player.vy,player.vx);
    }else{
      player.vx*=Math.pow(.0015,dt);
      player.vy*=Math.pow(.0015,dt);
    }
    const dx=player.vx*dt;
    const dy=player.vy*dt;
    if(!pointInWall(player.x+dx,player.y)){player.x+=dx;}else{player.vx*=-.16;player.bump=.18;shake=Math.max(shake,.12);}
    if(!pointInWall(player.x,player.y+dy)){player.y+=dy;}else{player.vy*=-.16;player.bump=.18;shake=Math.max(shake,.12);}
    const speed=Math.hypot(player.vx,player.vy);
    player.stretch+=(clamp(speed/170,0,1)-player.stretch)*Math.min(1,dt*8);
    player.bump=Math.max(0,player.bump-dt);
    if(Math.hypot(player.x-oldX,player.y-oldY)>1&&rng()<dt*18){
      trails.push({x:player.x-player.vx*.045,y:player.y-player.vy*.045,life:.48,max:.48,size:rand(4,8)});
    }
    const cell=playerCell();
    if(cell){
      revealAround(cell.c,cell.r,1);
      if(cell.zone!==currentZone){currentZone=cell.zone;zoneLabelTimer=1.4;}
    }
  }

  function updateUnlock(dt){
    if(!activeUnlock)return;
    const distance=Math.hypot(player.x-activeUnlock.x,player.y-activeUnlock.y);
    if(distance>55){cancelUnlock();return;}
    activeUnlockElapsed+=dt;
    activeUnlock.unlockProgress=clamp(activeUnlockElapsed/activeUnlock.unlockDuration,0,1);
    if(rng()<dt*30)particles.push({x:activeUnlock.x+rand(-18,18),y:activeUnlock.y+rand(-15,15),vx:rand(-35,35),vy:rand(-55,-15),life:.45,max:.45,color:activeUnlock.tier>=3?"#d985ff":"#ffd76c",size:rand(1.5,4)});
    if(activeUnlock.unlockProgress>=1)completeUnlock(activeUnlock);
  }

  function updateCameras(dt){
    let detected=0;
    let suspicious=0;
    for(const cam of cameras){
      cam.pause-=dt;
      if(cam.pause<=0&&cam.state!=="detected"){
        cam.angle+=cam.speed*dt;
        if(rng()<dt*.05){cam.pause=rand(.35,.9);cam.speed*=-1;}
      }
      const seen=cameraSeesPlayer(cam);
      cam.alert=clamp(cam.alert+(seen?dt*1.8:-dt*1.25),0,1);
      const previous=cam.state;
      cam.state=cam.alert>.56?"detected":cam.alert>.12?"suspicious":"search";
      if(cam.state==="detected")detected++;
      else if(cam.state==="suspicious")suspicious++;
      if(previous!==cam.state){
        if(cam.state==="suspicious"){showBanner("КАМЕРА ФИКСИРУЕТ ДВИЖЕНИЕ",1.1);tg?.HapticFeedback?.impactOccurred?.("light");}
        if(cam.state==="detected"){showBanner("ЦЕЛЬ ОБНАРУЖЕНА",1.2);shake=Math.max(shake,.3);tg?.HapticFeedback?.notificationOccurred?.("warning");}
      }
    }
    if(detected||suspicious)alarm+=dt*(detected*14+suspicious*5+8);
    else alarm-=dt*(smokeTime>0?12:8);
    alarm=clamp(alarm,0,100);
    maxAlarm=Math.max(maxAlarm,alarm);
    const tier=alarmTier(alarm);
    if(tier!==alertTier){alertTier=tier;onAlarmTierChanged(tier);}
    if(alarm>=100)finishGame("Система безопасности тебя поймала",.2);
  }

  function updateCamera(dt){
    const targetX=clamp(player.x-viewW/2,0,Math.max(0,WORLD_W-viewW));
    const targetY=clamp(player.y-viewH/2,0,Math.max(0,WORLD_H-viewH));
    const ease=1-Math.pow(.001,dt);
    camera.x+=(targetX-camera.x)*ease;
    camera.y+=(targetY-camera.y)*ease;
  }

  function updateEffects(dt){
    smokeTime=Math.max(0,smokeTime-dt);
    smokeCooldown=Math.max(0,smokeCooldown-dt);
    shake=Math.max(0,shake-dt);
    flash=Math.max(0,flash-dt);
    bannerTimer=Math.max(0,bannerTimer-dt);
    zoneLabelTimer=Math.max(0,zoneLabelTimer-dt);
    if(bannerTimer<=0)$("alertBanner").classList.remove("show");
    if(smokeTime<=0){stage.classList.remove("smoke-active");$("smokeStatus").classList.add("hidden");}
    else{$("smokeTimer").textContent=smokeTime.toFixed(1);}
    for(const p of particles){p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=110*dt;}
    particles=particles.filter(p=>p.life>0);
    for(const t of trails)t.life-=dt;
    trails=trails.filter(t=>t.life>0);
    for(const f of floaters){f.life-=dt;f.y-=24*dt;}
    floaters=floaters.filter(f=>f.life>0);
  }

  function updateUI(){
    $("loot").textContent=loot;
    const seconds=Math.max(0,Math.ceil(timeLeft));
    $("timer").textContent=`${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,"0")}`;
    $("safes").textContent=`СЕЙФЫ ${opened}/${totalSafes}`;
    $("alarmBar").style.width=`${alarm}%`;
    $("alarmText").textContent=`${Math.round(alarm)}%`;
    $("smoke").disabled=smokeCooldown>0;
    $("smoke").textContent=smokeCooldown>0?`🌫 ДЫМ: ${Math.ceil(smokeCooldown)}с`:"🌫 ДЫМОВАЯ ЗАВЕСА";

    const interactButton=$("interact");
    interactButton.classList.remove("ready");
    if(activeUnlock){
      interactButton.textContent=`🔓 ВЗЛОМ ${Math.round(activeUnlock.unlockProgress*100)}%`;
      interactButton.disabled=true;
    }else{
      const safe=nearestSafe();
      if(safe){
        interactButton.disabled=false;
        interactButton.classList.add("ready");
        interactButton.textContent=safe.tier===4?"💎 ВЗЛОМАТЬ ГЛАВНЫЙ СЕЙФ":"🔓 ВСКРЫТЬ СЕЙФ";
        setHint(`${safe.tier===4?"💎 Главный сейф":"✋ Сейф"}: примерно +${safe.value} влияния`);
      }else if(nearExit()){
        interactButton.disabled=false;
        interactButton.classList.add("ready");
        interactButton.textContent="🚪 ПОКИНУТЬ ХРАНИЛИЩЕ";
        setHint(loot?"🚪 Нажми, чтобы уйти с добычей":"🚪 Выход здесь. Сначала найди добычу.");
      }else{
        interactButton.disabled=true;
        interactButton.textContent="🔎 ИЩИ ЦЕЛЬ";
        if(opened===totalSafes)setHint("👑 Все сейфы вскрыты — следуй по зелёному маршруту!");
        else if(timeLeft<20)setHint("⏳ Мало времени — маршрут к выходу подсвечен!");
      }
    }
  }

  function update(dt){
    timeLeft=Math.max(0,duration-(performance.now()-startedAt)/1000);
    updatePlayer(dt);
    updateUnlock(dt);
    updateCameras(dt);
    updateCamera(dt);
    updateEffects(dt);
    if((opened===totalSafes||timeLeft<20)&&route.length===0)updateRoute();
    updateUI();
    if(timeLeft<=0)finishGame("Время вышло — удалось сохранить часть добычи",.35);
  }

  function roundedPath(context,x,y,w,h,r){
    const radius=Math.min(r,w/2,h/2);
    context.beginPath();context.moveTo(x+radius,y);context.arcTo(x+w,y,x+w,y+h,radius);context.arcTo(x+w,y+h,x,y+h,radius);context.arcTo(x,y+h,x,y,radius);context.arcTo(x,y,x+w,y,radius);context.closePath();
  }

  function visible(x,y,padding=100){
    const sx=x-camera.x;
    const sy=y-camera.y;
    return sx>-padding&&sy>-padding&&sx<viewW+padding&&sy<viewH+padding;
  }

  function cellNoise(c,r,salt=0){
    const value=Math.sin((c*9283+r*6271+seed*0.001+salt)*12.9898)*43758.5453;
    return value-Math.floor(value);
  }

  function drawFloor(time){
    const minC=Math.max(0,Math.floor(camera.x/CELL)-1);
    const maxC=Math.min(COLS-1,Math.ceil((camera.x+viewW)/CELL));
    const minR=Math.max(0,Math.floor(camera.y/CELL)-1);
    const maxR=Math.min(ROWS-1,Math.ceil((camera.y+viewH)/CELL));
    for(let r=minR;r<=maxR;r++)for(let c=minC;c<=maxC;c++){
      const cell=cellAt(c,r);
      const meta=ZONE_META[cell.zone];
      const x=c*CELL-camera.x;
      const y=r*CELL-camera.y;
      ctx.fillStyle=meta.floor;ctx.fillRect(x,y,CELL,CELL);
      ctx.strokeStyle=meta.line+"66";ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,CELL-1,CELL-1);
      ctx.fillStyle="rgba(255,255,255,.018)";
      for(let k=14;k<CELL;k+=22)ctx.fillRect(x+k,y,1,CELL);
      const n=cellNoise(c,r,1);
      if(cell.zone==="gold"){
        const glow=.12+.09*Math.sin(time*2+n*8);
        ctx.fillStyle=`rgba(255,205,92,${glow})`;ctx.fillRect(x+10,y+10,4,CELL-20);
      }else if(cell.zone==="tech"){
        ctx.strokeStyle="rgba(75,199,221,.18)";ctx.beginPath();ctx.moveTo(x+12,y+20);ctx.lineTo(x+CELL-14,y+20);ctx.lineTo(x+CELL-14,y+CELL-18);ctx.stroke();
      }else if(cell.zone==="security"){
        ctx.fillStyle="rgba(255,84,119,.08)";ctx.fillRect(x+9,y+CELL-15,CELL-18,4);
      }else if(cell.zone==="laser"){
        ctx.strokeStyle=`rgba(255,55,82,${.09+.08*Math.sin(time*3+n*9)})`;ctx.beginPath();ctx.moveTo(x+16,y+16);ctx.lineTo(x+CELL-16,y+CELL-16);ctx.stroke();
      }else{
        ctx.strokeStyle="rgba(177,155,221,.12)";ctx.beginPath();ctx.moveTo(x+18,y+10);ctx.lineTo(x+42,y+36);ctx.lineTo(x+29,y+68);ctx.stroke();
      }
      if(n>.78){
        ctx.fillStyle=`rgba(255,255,255,${.025+.018*Math.sin(time*1.6+n*12)})`;
        ctx.beginPath();ctx.arc(x+CELL*n,y+CELL*(1-n),1.4,0,Math.PI*2);ctx.fill();
      }
    }
  }

  function drawWalls(){
    for(const w of walls){
      const x=w.x-camera.x;
      const y=w.y-camera.y;
      if(x>viewW+20||y>viewH+20||x+w.w<-20||y+w.h<-20)continue;
      const gradient=ctx.createLinearGradient(x,y,x+w.w,y+w.h);
      gradient.addColorStop(0,"#342823");gradient.addColorStop(.5,"#181419");gradient.addColorStop(1,"#0a090d");
      ctx.fillStyle=gradient;roundedPath(ctx,x,y,w.w,w.h,Math.min(5,w.w/2,w.h/2));ctx.fill();
      ctx.strokeStyle="rgba(255,213,108,.42)";ctx.lineWidth=1.1;ctx.stroke();
      ctx.strokeStyle="rgba(255,255,255,.04)";ctx.beginPath();ctx.moveTo(x+2,y+2);ctx.lineTo(x+w.w-2,y+2);ctx.stroke();
    }
  }

  function drawRoute(time){
    if(!route.length)return;
    ctx.save();ctx.lineWidth=3;ctx.lineCap="round";ctx.setLineDash([4,10]);ctx.lineDashOffset=-time*24;ctx.strokeStyle="rgba(98,245,160,.72)";ctx.shadowBlur=12;ctx.shadowColor="#62f5a0";ctx.beginPath();
    route.forEach((cell,i)=>{
      const center=centerOf(cell.c,cell.r);const x=center.x-camera.x;const y=center.y-camera.y;
      if(i===0)ctx.moveTo(player.x-camera.x,player.y-camera.y);else ctx.lineTo(x,y);
    });
    ctx.stroke();ctx.restore();
  }

  function drawExit(time){
    const x=exit.x-camera.x;
    const y=exit.y-camera.y;
    const pulse=.55+.45*Math.sin(time*3.2);
    ctx.save();ctx.shadowBlur=20+14*pulse;ctx.shadowColor="#62f5a0";
    const gradient=ctx.createLinearGradient(x,y,x,y+exit.h);gradient.addColorStop(0,"#153e2b");gradient.addColorStop(1,"#0b2318");ctx.fillStyle=gradient;roundedPath(ctx,x,y,exit.w,exit.h,10);ctx.fill();ctx.lineWidth=3;ctx.strokeStyle="#62f5a0";ctx.stroke();ctx.shadowBlur=0;
    ctx.fillStyle="#b9ffcf";ctx.font="900 11px system-ui";ctx.textAlign="center";ctx.fillText("ВЫХОД",x+exit.w/2,y+34);ctx.restore();
  }

  function safeColors(tier){
    if(tier===4)return{body1:"#5b2f79",body2:"#1c1027",stroke:"#f5c4ff",glow:"#d985ff",name:"ГЛАВНЫЙ"};
    if(tier===3)return{body1:"#56336d",body2:"#20122b",stroke:"#e4a7ff",glow:"#c677ff",name:"ЭЛИТНЫЙ"};
    if(tier===2)return{body1:"#745522",body2:"#2f2110",stroke:"#ffe19b",glow:"#ffc95e",name:"РЕДКИЙ"};
    return{body1:"#63491e",body2:"#281c0d",stroke:"#e4bd61",glow:"#c99938",name:"ОБЫЧНЫЙ"};
  }

  function drawSafe(safe,time){
    if(!visible(safe.x,safe.y,70))return;
    const x=safe.x-camera.x;
    const y=safe.y-camera.y;
    const colors=safeColors(safe.tier);
    const pulse=safe.opened?0:.45+.35*Math.sin(time*(safe.tier+1)+safe.id);
    ctx.save();ctx.translate(x,y);
    if(!safe.opened){ctx.shadowBlur=10+18*pulse;ctx.shadowColor=colors.glow;}
    if(safe.unlocking){
      const shakeX=Math.sin(time*52)*2.5*(1-safe.unlockProgress);
      ctx.translate(shakeX,0);
    }
    const scale=safe.tier===4?1.25:safe.tier===3?1.1:1;
    ctx.scale(scale,scale);
    const gradient=ctx.createLinearGradient(-22,-18,22,18);gradient.addColorStop(0,safe.opened?"#262328":colors.body1);gradient.addColorStop(1,safe.opened?"#151317":colors.body2);ctx.fillStyle=gradient;roundedPath(ctx,-22,-18,44,36,7);ctx.fill();ctx.lineWidth=safe.tier===4?2.8:2;ctx.strokeStyle=safe.opened?"#59545d":colors.stroke;ctx.stroke();ctx.shadowBlur=0;
    ctx.fillStyle=safe.opened?"#69636e":"#120b09";ctx.beginPath();ctx.arc(0,0,5.3,0,Math.PI*2);ctx.fill();
    if(safe.unlocking){
      ctx.strokeStyle=colors.glow;ctx.lineWidth=3;ctx.beginPath();ctx.arc(0,0,11,-Math.PI/2,-Math.PI/2+Math.PI*2*safe.unlockProgress);ctx.stroke();
    }
    if(!safe.opened){ctx.fillStyle=colors.stroke;ctx.font="900 8px system-ui";ctx.textAlign="center";ctx.fillText(safe.tier===4?"◆":"●",0,-25);}
    ctx.restore();
  }

  function drawCamera(cam,time){
    if(!visible(cam.x,cam.y,cam.range+20))return;
    const x=cam.x-camera.x;
    const y=cam.y-camera.y;
    const state=cam.state;
    const search=state==="search";
    const suspicious=state==="suspicious";
    const color=search?"255,90,112":suspicious?"255,194,85":"255,44,79";
    ctx.save();ctx.translate(x,y);ctx.rotate(cam.angle);
    if(smokeTime<=0){
      const cone=ctx.createRadialGradient(0,0,5,0,0,cam.range);cone.addColorStop(0,`rgba(${color},${search?.18:suspicious?.28:.39})`);cone.addColorStop(.68,`rgba(${color},${search?.08:suspicious?.14:.2})`);cone.addColorStop(1,`rgba(${color},0)`);ctx.fillStyle=cone;ctx.beginPath();ctx.moveTo(4,0);ctx.arc(0,0,cam.range,-cam.fov/2,cam.fov/2);ctx.closePath();ctx.fill();
      if(suspicious||state==="detected"){
        ctx.strokeStyle=`rgba(${color},${state==="detected"?.75:.45})`;ctx.lineWidth=state==="detected"?2:1;ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(cam.range,0);ctx.stroke();
      }
    }
    ctx.rotate(-cam.angle);
    const pulse=state==="detected"?1+.12*Math.sin(time*14):1;
    ctx.scale(pulse,pulse);ctx.shadowBlur=state==="detected"?24:suspicious?16:9;ctx.shadowColor=`rgb(${color})`;ctx.fillStyle=search?"#6d2636":suspicious?"#8a5524":"#d92f50";ctx.beginPath();ctx.arc(0,0,13,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
    ctx.strokeStyle=search?"#ff9bad":suspicious?"#ffd088":"#fff0f3";ctx.lineWidth=2.2;ctx.beginPath();ctx.ellipse(0,0,10,state==="detected"?3.8:6,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(0,0,state==="detected"?4:3.2,0,Math.PI*2);ctx.fill();ctx.fillStyle="#231018";ctx.beginPath();ctx.arc(0,0,1.7,0,Math.PI*2);ctx.fill();
    if(suspicious){ctx.fillStyle="#ffd884";ctx.font="900 10px system-ui";ctx.textAlign="center";ctx.fillText("?",0,-19);}
    if(state==="detected"){ctx.fillStyle="#fff";ctx.font="900 10px system-ui";ctx.textAlign="center";ctx.fillText("!",0,-20);}
    ctx.restore();
  }

  function drawPlayer(time){
    const x=player.x-camera.x;
    const y=player.y-camera.y;
    for(const trail of trails){
      const alpha=trail.life/trail.max;
      ctx.fillStyle=`rgba(167,107,255,${alpha*.22})`;ctx.beginPath();ctx.arc(trail.x-camera.x,trail.y-camera.y,trail.size*alpha,0,Math.PI*2);ctx.fill();
    }
    ctx.save();ctx.translate(x,y);
    const speed=Math.hypot(player.vx,player.vy);
    const stretch=player.stretch*.16;
    ctx.rotate(player.angle||0);
    ctx.scale(1+stretch,1-stretch*.65);
    ctx.rotate(-(player.angle||0));
    if(player.bump>0)ctx.scale(.84,1.12);
    ctx.shadowBlur=22;ctx.shadowColor=smokeTime>0?"#d8cbed":"#a76bff";
    const gradient=ctx.createRadialGradient(-4,-6,2,0,0,18);gradient.addColorStop(0,"#c48cff");gradient.addColorStop(.5,"#8750d1");gradient.addColorStop(1,"#532594");ctx.fillStyle=gradient;ctx.beginPath();ctx.arc(0,0,player.r,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;
    ctx.fillStyle="rgba(233,205,255,.25)";ctx.beginPath();ctx.ellipse(-3,5,8,2.5,0,0,Math.PI*2);ctx.fill();
    ctx.restore();
    const crownBob=Math.sin(time*8+speed*.02)*1.6;
    const crownTilt=clamp(player.vx/200,-.18,.18);
    ctx.save();ctx.translate(x,y-17+crownBob);ctx.rotate(crownTilt);ctx.font="19px system-ui";ctx.textAlign="center";ctx.fillText("👑",0,0);ctx.restore();
    if(smokeTime>0){
      for(let i=0;i<9;i++){
        const angle=i/9*Math.PI*2+time*.7;
        const radius=17+(i%3)*6;
        ctx.fillStyle=`rgba(216,203,237,${.07+.04*(i%2)})`;ctx.beginPath();ctx.arc(x+Math.cos(angle)*radius,y+Math.sin(angle)*radius,12+(i%3)*4,0,Math.PI*2);ctx.fill();
      }
    }
  }

  function drawParticles(){
    for(const p of particles){
      if(!visible(p.x,p.y,30))continue;
      ctx.globalAlpha=clamp(p.life/p.max,0,1);ctx.fillStyle=p.color;ctx.beginPath();ctx.arc(p.x-camera.x,p.y-camera.y,p.size,0,Math.PI*2);ctx.fill();
    }
    ctx.globalAlpha=1;
    for(const f of floaters){
      ctx.globalAlpha=clamp(f.life/f.max,0,1);ctx.fillStyle=f.color;ctx.font="900 14px system-ui";ctx.textAlign="center";ctx.fillText(f.text,f.x-camera.x,f.y-camera.y);
    }
    ctx.globalAlpha=1;
  }

  function drawZoneLabel(){
    if(zoneLabelTimer<=0||!currentZone)return;
    const alpha=Math.min(1,zoneLabelTimer*2, (1.4-zoneLabelTimer)*4);
    const meta=ZONE_META[currentZone];
    ctx.save();ctx.globalAlpha=alpha;ctx.textAlign="center";ctx.font="900 10px system-ui";ctx.fillStyle=meta.accent;ctx.shadowBlur=10;ctx.shadowColor=meta.accent;ctx.fillText(meta.label,viewW/2,viewH-78);ctx.restore();
  }

  function draw(time){
    const shakeX=shake>0?rand(-3,3)*(shake/.6):0;
    const shakeY=shake>0?rand(-2,2)*(shake/.6):0;
    ctx.setTransform(dpr,0,0,dpr,shakeX,shakeY);
    ctx.clearRect(-10,-10,viewW+20,viewH+20);
    const bg=ctx.createLinearGradient(0,0,0,viewH);bg.addColorStop(0,"#20151a");bg.addColorStop(1,"#09080d");ctx.fillStyle=bg;ctx.fillRect(-10,-10,viewW+20,viewH+20);
    drawFloor(time);
    drawRoute(time);
    drawExit(time);
    for(const safe of safes)drawSafe(safe,time);
    for(const cam of cameras)drawCamera(cam,time);
    drawWalls();
    drawParticles();
    drawPlayer(time);
    drawZoneLabel();
    drawMinimap(time);
  }

  function drawMinimap(time){
    const width=miniCanvas.clientWidth;
    const height=miniCanvas.clientHeight;
    if(width<1||height<1)return;
    mini.setTransform(dpr,0,0,dpr,0,0);
    mini.clearRect(0,0,width,height);
    mini.fillStyle="#07060a";mini.fillRect(0,0,width,height);
    const pad=6;
    const sx=(width-pad*2)/WORLD_W;
    const sy=(height-pad*2)/WORLD_H;
    for(const cell of cells){
      const known=discovered.has(keyOf(cell.c,cell.r));
      if(!known)continue;
      const meta=ZONE_META[cell.zone];
      mini.fillStyle=meta.floor;mini.fillRect(pad+cell.c*CELL*sx,pad+cell.r*CELL*sy,CELL*sx+.5,CELL*sy+.5);
      mini.strokeStyle=meta.line+"88";mini.lineWidth=.7;mini.strokeRect(pad+cell.c*CELL*sx,pad+cell.r*CELL*sy,CELL*sx,CELL*sy);
    }
    mini.strokeStyle="rgba(255,215,108,.65)";mini.lineWidth=Math.max(.7,width/150);
    for(const w of walls){
      const c=Math.floor((w.x+1)/CELL),r=Math.floor((w.y+1)/CELL);
      if(!discovered.has(keyOf(clamp(c,0,COLS-1),clamp(r,0,ROWS-1))))continue;
      mini.strokeRect(pad+w.x*sx,pad+w.y*sy,Math.max(1,w.w*sx),Math.max(1,w.h*sy));
    }
    for(const safe of safes){
      if(!discovered.has(keyOf(safe.cell.c,safe.cell.r))||safe.opened)continue;
      mini.fillStyle=safe.tier===4?"#e99cff":safe.tier===3?"#cf7cff":"#ffd76c";mini.beginPath();mini.arc(pad+safe.x*sx,pad+safe.y*sy,safe.tier===4?3.3:2.2,0,Math.PI*2);mini.fill();
    }
    for(const cam of cameras){
      if(!discovered.has(keyOf(cam.cell.c,cam.cell.r)))continue;
      mini.fillStyle=cam.state==="detected"?"#ff365d":cam.state==="suspicious"?"#ffc65c":"#d44d6b";mini.beginPath();mini.arc(pad+cam.x*sx,pad+cam.y*sy,2,0,Math.PI*2);mini.fill();
    }
    mini.fillStyle="#62f5a0";mini.fillRect(pad+exit.x*sx,pad+exit.y*sy,Math.max(3,exit.w*sx),Math.max(3,exit.h*sy));
    mini.shadowBlur=8;mini.shadowColor="#a76bff";mini.fillStyle="#a76bff";mini.beginPath();mini.arc(pad+player.x*sx,pad+player.y*sy,3.2+.5*Math.sin(time*5),0,Math.PI*2);mini.fill();mini.shadowBlur=0;
    if(smokeTime>0){mini.fillStyle="rgba(210,198,230,.11)";for(let i=0;i<10;i++)mini.fillRect(rand(0,width),rand(0,height),rand(6,22),1);}
  }

  function burst(x,y,color,count=20,speed=120){
    for(let i=0;i<count;i++){
      const angle=rand(0,Math.PI*2);const velocity=rand(speed*.35,speed);
      particles.push({x,y,vx:Math.cos(angle)*velocity,vy:Math.sin(angle)*velocity-rand(20,80),life:rand(.45,.95),max:1,color,size:rand(1.5,5)});
    }
  }

  function addFloater(x,y,text,color,life=1){floaters.push({x,y,text,color,life,max:life});}

  function flyLoot(safe,reward){
    const rect=canvas.getBoundingClientRect();
    const sx=rect.left+(safe.x-camera.x)/viewW*rect.width;
    const sy=rect.top+(safe.y-camera.y)/viewH*rect.height;
    const chip=document.createElement("b");chip.className="lootChip";chip.textContent=`+${reward}`;chip.style.setProperty("--sx",`${sx}px`);chip.style.setProperty("--sy",`${sy}px`);fxLayer.appendChild(chip);
    setTimeout(()=>{chip.remove();$("loot").parentElement.classList.add("bump");setTimeout(()=>$("loot").parentElement.classList.remove("bump"),220);},780);
  }

  function loop(now){
    if(!running)return;
    const dt=Math.min(.034,(now-lastFrame)/1000||.016);
    lastFrame=now;
    update(dt);
    draw(now/1000);
    if(running)requestAnimationFrame(loop);
  }

  async function finishGame(reason,keep){
    if(ended)return;
    ended=true;running=false;secured=Math.round(loot*keep);
    $("finish").classList.remove("hidden");$("result").style.display="block";
    $("resultTitle").textContent=reason;$("collected").textContent=loot;$("secured").textContent=secured;$("opened").textContent=`${opened}/${totalSafes}`;$("maxAlarm").textContent=`${Math.round(maxAlarm)}%`;
    $("reward").textContent=demo?"Демонстрационный режим: добыча не начисляется в баланс.":"Сохраняем результат…";
    if(!demo&&sessionId){
      try{
        const result=await api("finish",{session_id:sessionId,score:secured,stats:{collected:loot,secured,opened,total_safes:totalSafes,max_alarm:Math.round(maxAlarm),escaped:keep===1,map_code:mapCode}});
        $("reward").innerHTML=`Базовая награда ограбления: <b>+${result.base_run_reward}</b><br>Начисляется за улучшение рекорда: <b>+${result.payable_base}</b><br>🌳 Бонус древа: <b>+${result.tree_bonus}</b><br>🏆 Получено влияния: <b>+${result.actual_reward}</b><br>Баланс: <b>${result.balance}</b><br><small>${result.message}</small>`;
      }catch(error){$("reward").innerHTML=`<span class="error">${error.message}</span>`;}
    }
  }

  const joystick=$("joystick");
  const knob=$("knob");
  let joyId=null;
  function setJoy(event){
    const rect=joystick.getBoundingClientRect();
    const cx=rect.left+rect.width/2,cy=rect.top+rect.height/2;
    const dx=event.clientX-cx,dy=event.clientY-cy;
    const length=Math.hypot(dx,dy),max=34,k=Math.min(1,max/(length||1));
    const x=dx*k,y=dy*k;
    knob.style.transform=`translate(${x}px,${y}px)`;
    moveX=x/max;moveY=y/max;
  }
  joystick.addEventListener("pointerdown",event=>{joyId=event.pointerId;joystick.setPointerCapture(event.pointerId);joystick.classList.add("active");setJoy(event);});
  joystick.addEventListener("pointermove",event=>{if(event.pointerId===joyId)setJoy(event);});
  function clearJoy(event){
    if(joyId!==null&&(event.pointerId===undefined||event.pointerId===joyId)){
      joyId=null;moveX=moveY=0;knob.style.transform="";joystick.classList.remove("active");
    }
  }
  joystick.addEventListener("pointerup",clearJoy);joystick.addEventListener("pointercancel",clearJoy);

  const keys={};
  addEventListener("keydown",event=>{keys[event.key]=true;if(event.key==="e"||event.key==="Enter")interact();if(event.key===" ")useSmoke();syncKeys();});
  addEventListener("keyup",event=>{keys[event.key]=false;syncKeys();});
  function syncKeys(){moveX=(keys.ArrowRight||keys.d?1:0)-(keys.ArrowLeft||keys.a?1:0);moveY=(keys.ArrowDown||keys.s?1:0)-(keys.ArrowUp||keys.w?1:0);}

  $("interact").addEventListener("click",interact);
  $("smoke").addEventListener("click",useSmoke);
  $("start").addEventListener("click",startGame);
  $("again").addEventListener("click",startGame);
  $("minimapWrap").addEventListener("click",()=>$("minimapWrap").classList.toggle("expanded"));
  const toGames=()=>location.href=`/games/?${params.toString()}`;
  $("back").addEventListener("click",toGames);$("toGames").addEventListener("click",toGames);$("introToGames").addEventListener("click",toGames);

  resize();
  rng=seeded(1);buildMaze();buildObjects();draw(0);
})();
