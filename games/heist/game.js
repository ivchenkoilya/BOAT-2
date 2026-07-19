(()=>{
  "use strict";

  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.("#090710");tg?.setBackgroundColor?.("#090710");
  const params=new URLSearchParams(location.search);
  const chatId=params.get("chat_id")||"";
  const initData=tg?.initData||"";
  const headers={"Content-Type":"application/json","X-Telegram-Init-Data":initData};
  const $=id=>document.getElementById(id);
  const canvas=$("game"),ctx=canvas.getContext("2d");
  const miniCanvas=$("miniMap"),mini=miniCanvas.getContext("2d");
  const stage=$("stage"),app=$("app"),fxLayer=$("fxLayer");

  const CELL=92,COLS=10,ROWS=16,WORLD_W=COLS*CELL,WORLD_H=ROWS*CELL,WALL=10;
  const START={c:0,r:ROWS-1};
  const ZONES=["gold","tech","security","laser","broken"];
  const ZONE_META={
    gold:{floor:"#211814",line:"#704b27",accent:"#ffd76c",label:"ЗОЛОТОЙ СЕКТОР"},
    tech:{floor:"#10181b",line:"#2a4f55",accent:"#70d9e8",label:"ТЕХНИЧЕСКИЙ СЕКТОР"},
    security:{floor:"#191116",line:"#593044",accent:"#ff6f8b",label:"ПОСТ ОХРАНЫ"},
    laser:{floor:"#171012",line:"#61262e",accent:"#ff455f",label:"ЛАЗЕРНЫЙ СЕКТОР"},
    broken:{floor:"#151419",line:"#3f3b4d",accent:"#a995d6",label:"АВАРИЙНЫЙ СЕКТОР"}
  };
  const SAFE_META={
    1:{name:"МЕХАНИЧЕСКИЙ СЕЙФ",label:"ОБЫЧНЫЙ",color:"#ffd76c",method:"lockpick",difficulty:"НИЗКАЯ",size:27},
    2:{name:"ШТИФТОВЫЙ СЕЙФ",label:"УСИЛЕННЫЙ",color:"#70d9e8",method:"pins",difficulty:"СРЕДНЯЯ",size:29},
    3:{name:"КОДОВЫЙ СЕЙФ",label:"ЭЛИТНЫЙ",color:"#d986ff",method:"dial",difficulty:"ВЫСОКАЯ",size:31},
    4:{name:"ГЛАВНОЕ ХРАНИЛИЩЕ",label:"ЛЕГЕНДАРНЫЙ",color:"#ffe28c",method:"master",difficulty:"МАКСИМАЛЬНАЯ",size:36}
  };

  let dpr=1,viewW=400,viewH=620,hudSafe=126;
  let running=false,ended=false,demo=false,sessionId="",seed=1,rng=Math.random;
  let duration=165,timeLeft=duration,startedAt=0,lastFrame=0;
  let loot=0,secured=0,alarm=0,maxAlarm=0,opened=0,totalSafes=0;
  let smokeTime=0,smokeCooldown=0,moveX=0,moveY=0,shake=0,alertTier=0,bannerTimer=0,zoneTimer=0,currentZone="";
  let idleTime=0,mapCode="—",pauseStarted=0;
  const player={x:CELL/2,y:WORLD_H-CELL/2,r:10.5,vx:0,vy:0,stretch:0,bump:0,angle:0};
  const camera={x:0,y:Math.max(0,WORLD_H-viewH)};
  const exit={x:14,y:WORLD_H-76,w:60,h:60};
  let cells=[],walls=[],safes=[],cameras=[],decor=[],particles=[],trails=[],floaters=[],route=[],discovered=new Set();
  let crack={active:false,safe:null,mode:"",stages:[],stageIndex:0,durability:100,progress:0,turning:false,angle:0,targetAngle:0,tolerance:8,errorCooldown:0,pins:[],needle:0,target:0,direction:1,speed:110,round:0,rounds:3,window:18};

  function seeded(value){let s=(Number(value)||1)>>>0;return()=>((s=Math.imul(s,1664525)+1013904223>>>0)/4294967296);}
  const rand=(a,b)=>a+(b-a)*rng();
  const randInt=(a,b)=>Math.floor(rand(a,b+1));
  const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
  const normAngle=a=>{while(a>Math.PI)a-=Math.PI*2;while(a<-Math.PI)a+=Math.PI*2;return a;};
  const degDiff=(a,b)=>Math.abs((((a-b)+540)%360)-180);
  function shuffle(list){for(let i=list.length-1;i>0;i--){const j=Math.floor(rng()*(i+1));[list[i],list[j]]=[list[j],list[i]];}return list;}
  const idx=(c,r)=>r*COLS+c;
  const cellAt=(c,r)=>c>=0&&r>=0&&c<COLS&&r<ROWS?cells[idx(c,r)]:null;
  const center=(c,r)=>({x:c*CELL+CELL/2,y:r*CELL+CELL/2});
  const cellKey=(c,r)=>`${c}:${r}`;
  const manhattan=(a,b)=>Math.abs(a.c-b.c)+Math.abs(a.r-b.r);

  function buildMaze(){
    cells=Array.from({length:COLS*ROWS},(_,i)=>({c:i%COLS,r:Math.floor(i/COLS),n:true,e:true,s:true,w:true,visited:false,zone:"gold"}));
    const start=cellAt(START.c,START.r),stack=[start];start.visited=true;
    while(stack.length){
      const cur=stack[stack.length-1],choices=[];
      const n=cellAt(cur.c,cur.r-1),e=cellAt(cur.c+1,cur.r),s=cellAt(cur.c,cur.r+1),w=cellAt(cur.c-1,cur.r);
      if(n&&!n.visited)choices.push(["n",n,"s"]);if(e&&!e.visited)choices.push(["e",e,"w"]);if(s&&!s.visited)choices.push(["s",s,"n"]);if(w&&!w.visited)choices.push(["w",w,"e"]);
      if(!choices.length){stack.pop();continue;}
      const [dir,next,opposite]=choices[Math.floor(rng()*choices.length)];cur[dir]=false;next[opposite]=false;next.visited=true;stack.push(next);
    }
    for(let i=0;i<34;i++){
      const c=randInt(0,COLS-1),r=randInt(0,ROWS-1),cell=cellAt(c,r);
      if(rng()<.5&&c<COLS-1){cell.e=false;cellAt(c+1,r).w=false;}else if(r<ROWS-1){cell.s=false;cellAt(c,r+1).n=false;}
    }
    for(const cell of cells){
      const band=(Math.floor(cell.r/3)+Math.floor(cell.c/3)+(seed%5))%ZONES.length;
      cell.zone=ZONES[band];
    }
    walls=[];
    const add=(x,y,w,h)=>walls.push({x,y,w,h});
    for(const cell of cells){
      const x=cell.c*CELL,y=cell.r*CELL;
      if(cell.n)add(x,y,CELL,WALL);if(cell.w)add(x,y,WALL,CELL);
      if(cell.c===COLS-1&&cell.e)add(x+CELL-WALL,y,WALL,CELL);
      if(cell.r===ROWS-1&&cell.s)add(x,y+CELL-WALL,CELL,WALL);
    }
  }

  function buildObjects(){
    const candidates=shuffle(cells.filter(c=>manhattan(c,START)>=3));
    totalSafes=13+randInt(0,2);
    const farthest=[...candidates].sort((a,b)=>manhattan(b,START)-manhattan(a,START))[0];
    const chosen=[farthest];
    for(const cell of candidates){if(chosen.length>=totalSafes)break;if(!chosen.includes(cell))chosen.push(cell);}
    const tiers=Array(totalSafes).fill(1);tiers[0]=4;
    for(let i=1;i<Math.min(3,totalSafes);i++)tiers[i]=3;
    for(let i=3;i<Math.min(7,totalSafes);i++)tiers[i]=2;
    safes=chosen.map((cell,i)=>{
      const p=center(cell.c,cell.r),tier=tiers[i],meta=SAFE_META[tier];
      return{x:p.x+rand(-12,12),y:p.y+rand(-12,12),c:cell.c,r:cell.r,tier,value:tier===4?randInt(95,125):tier===3?randInt(48,67):tier===2?randInt(30,46):randInt(17,29),opened:false,unlocking:false,lockUntil:0,size:meta.size,id:i};
    });
    const occupied=new Set(chosen.map(c=>cellKey(c.c,c.r)));
    const camCells=shuffle(cells.filter(c=>manhattan(c,START)>=2&&!occupied.has(cellKey(c.c,c.r)))).slice(0,11+randInt(0,3));
    cameras=camCells.map((cell,i)=>{const p=center(cell.c,cell.r);return{x:p.x+rand(-12,12),y:p.y+rand(-12,12),c:cell.c,r:cell.r,angle:rand(0,Math.PI*2),speed:rand(.38,.72)*(rng()<.5?-1:1),range:rand(145,190),fov:rand(.72,.98),alert:0,state:"search",pause:rand(.1,.9),id:i};});
    decor=[];
    for(const cell of cells){
      const p=center(cell.c,cell.r),count=rng()<.55?1:2;
      for(let i=0;i<count;i++){
        const types={gold:["panel","crate","seal"],tech:["server","vent","cable"],security:["monitor","stripe","crate"],laser:["laser","stripe","cable"],broken:["crack","vent","debris"]}[cell.zone];
        decor.push({type:types[randInt(0,types.length-1)],x:p.x+rand(-26,26),y:p.y+rand(-26,26),rot:rand(0,Math.PI*2),zone:cell.zone});
      }
    }
    player.x=CELL/2;player.y=WORLD_H-CELL/2;player.vx=player.vy=0;
    camera.x=0;camera.y=Math.max(0,WORLD_H-(viewH-hudSafe));
    discovered=new Set();revealAround(START.c,START.r,1);
    particles=[];trails=[];floaters=[];route=[];
    mapCode=String(seed>>>0).slice(-4).padStart(4,"0");
    $("mapCode").textContent=`КАРТА ${mapCode}`;$("safes").textContent=`СЕЙФЫ 0/${totalSafes}`;
  }

  function revealAround(c,r,radius){for(let y=r-radius;y<=r+radius;y++)for(let x=c-radius;x<=c+radius;x++)if(cellAt(x,y))discovered.add(cellKey(x,y));}
  function playerCell(){return cellAt(clamp(Math.floor(player.x/CELL),0,COLS-1),clamp(Math.floor(player.y/CELL),0,ROWS-1));}
  function pointInWall(x,y,r=player.r){return x-r<0||y-r<0||x+r>WORLD_W||y+r>WORLD_H||walls.some(w=>x+r>w.x&&x-r<w.x+w.w&&y+r>w.y&&y-r<w.y+w.h);}
  function pointHitsWall(x,y){return walls.some(w=>x>w.x&&x<w.x+w.w&&y>w.y&&y<w.y+w.h);}
  function segmentBlocked(x1,y1,x2,y2){
    const dist=Math.hypot(x2-x1,y2-y1),steps=Math.max(2,Math.ceil(dist/5));
    for(let i=2;i<steps-1;i++){const t=i/steps,x=x1+(x2-x1)*t,y=y1+(y2-y1)*t;if(pointHitsWall(x,y))return true;}
    return false;
  }
  function rayDistance(x,y,angle,max){for(let d=8;d<=max;d+=6){if(pointHitsWall(x+Math.cos(angle)*d,y+Math.sin(angle)*d))return Math.max(8,d-5);}return max;}
  function cameraSeesPlayer(cam){
    if(smokeTime>0)return false;
    const dx=player.x-cam.x,dy=player.y-cam.y,dist=Math.hypot(dx,dy);if(dist>cam.range)return false;
    const target=Math.atan2(dy,dx);if(Math.abs(normAngle(target-cam.angle))>cam.fov/2)return false;
    return !segmentBlocked(cam.x,cam.y,player.x,player.y);
  }
  function nearestSafe(limit=52){let best=null,dist=Infinity;for(const safe of safes){if(safe.opened||performance.now()<safe.lockUntil)continue;const d=Math.hypot(player.x-safe.x,player.y-safe.y);if(d<dist){dist=d;best=safe;}}return dist<=limit?best:null;}
  function nearExit(){return player.x>exit.x-18&&player.x<exit.x+exit.w+18&&player.y>exit.y-18&&player.y<exit.y+exit.h+18;}

  function neighbors(cell){const out=[];if(!cell.n)out.push(cellAt(cell.c,cell.r-1));if(!cell.e)out.push(cellAt(cell.c+1,cell.r));if(!cell.s)out.push(cellAt(cell.c,cell.r+1));if(!cell.w)out.push(cellAt(cell.c-1,cell.r));return out.filter(Boolean);}
  function findPath(from,to){
    if(!from||!to)return[];const queue=[from],prev=new Map([[cellKey(from.c,from.r),null]]);
    while(queue.length){const cur=queue.shift();if(cur===to)break;for(const next of neighbors(cur)){const key=cellKey(next.c,next.r);if(prev.has(key))continue;prev.set(key,cur);queue.push(next);}}
    const path=[];let cur=to;if(!prev.has(cellKey(to.c,to.r)))return path;
    while(cur){path.push(center(cur.c,cur.r));cur=prev.get(cellKey(cur.c,cur.r));}return path.reverse();
  }
  function updateRoute(){
    const from=playerCell();let target=null;
    if(opened===totalSafes||timeLeft<=20)target=cellAt(START.c,START.r);
    else if(idleTime>=8){let nearest=null,d=Infinity;for(const safe of safes){if(safe.opened)continue;const cd=manhattan(from,{c:safe.c,r:safe.r});if(cd<d){d=cd;nearest=safe;}}if(nearest)target=cellAt(nearest.c,nearest.r);}
    route=target?findPath(from,target):[];
  }

  function resize(){
    const rect=canvas.getBoundingClientRect();dpr=Math.min(2,window.devicePixelRatio||1);viewW=Math.max(1,rect.width);viewH=Math.max(1,rect.height);
    hudSafe=parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--hud-safe"))||126;
    canvas.width=Math.round(viewW*dpr);canvas.height=Math.round(viewH*dpr);
    miniCanvas.width=Math.round(Math.max(1,miniCanvas.clientWidth)*dpr);miniCanvas.height=Math.round(Math.max(1,miniCanvas.clientHeight)*dpr);
  }
  addEventListener("resize",resize);

  async function api(path,body={}){
    const response=await fetch(`/games/api/${path}`,{method:"POST",headers,body:JSON.stringify({...body,chat_id:chatId})});
    const data=await response.json().catch(()=>({ok:false,reason:"Сервер не ответил."}));
    if(!response.ok||!data.ok)throw new Error(data.reason||"Ошибка сервера.");return data;
  }

  async function startGame(){
    $("startError").textContent="";$("start").disabled=true;$("start").textContent="СОЗДАЁМ НОВОЕ ХРАНИЛИЩЕ…";$("introToGames").classList.add("hidden");
    try{const data=await api("start",{game:"heist"});sessionId=data.session_id;seed=Number(data.seed)||Date.now();duration=Math.max(165,Number(data.duration)||0);demo=false;}
    catch(error){if(initData){$("startError").textContent=error.message;$("start").disabled=false;$("start").textContent="ПОПРОБОВАТЬ СНОВА";$("introToGames").classList.remove("hidden");return;}sessionId="";seed=Date.now()>>>0;duration=165;demo=true;$("startError").textContent=`Демонстрационный режим: ${error.message}`;}
    rng=seeded(seed);buildMaze();buildObjects();running=true;ended=false;startedAt=performance.now();lastFrame=startedAt;timeLeft=duration;loot=secured=alarm=maxAlarm=opened=0;smokeTime=smokeCooldown=shake=0;alertTier=bannerTimer=zoneTimer=0;idleTime=0;currentZone="";
    crack.active=false;$("loot").textContent="0";$("alarmBar").style.width="0%";$("alarmText").textContent="0%";$("hint").textContent="Исследуй хранилище и найди сейфы";$("finish").classList.add("hidden");$("result").style.display="none";$("intro").classList.add("hidden");$("minimapWrap").classList.remove("expanded");setAlertClass(0);burst(player.x,player.y,"#a76bff",20,110);requestAnimationFrame(loop);$("start").disabled=false;$("start").textContent="НАЧАТЬ ОГРАБЛЕНИЕ";
  }

  function setHint(text,pop=false){const hint=$("hint");if(hint.textContent!==text)hint.textContent=text;if(pop){hint.classList.remove("pop");void hint.offsetWidth;hint.classList.add("pop");}}
  function showBanner(text,seconds=1.5){$("alertBanner").textContent=text;$("alertBanner").classList.add("show");bannerTimer=seconds;}
  function setAlertClass(tier){stage.classList.remove("alert-medium","alert-high","alert-critical");if(tier===1)stage.classList.add("alert-medium");if(tier===2)stage.classList.add("alert-high");if(tier===3)stage.classList.add("alert-critical");}
  function alarmLevel(v){return v>=85?3:v>=60?2:v>=30?1:0;}
  function onAlarmChanged(next){setAlertClass(next);if(next===1)showBanner("ПОДОЗРИТЕЛЬНАЯ АКТИВНОСТЬ",1.8);if(next===2){showBanner("ОХРАНА ПОДНЯТА ПО ТРЕВОГЕ",2);tg?.HapticFeedback?.notificationOccurred?.("warning");}if(next===3){showBanner("БЛОКИРОВКА ХРАНИЛИЩА",2.2);tg?.HapticFeedback?.notificationOccurred?.("error");shake=.65;}}

  function openCrack(safe){
    if(crack.active)return;const meta=SAFE_META[safe.tier];crack={active:true,safe,mode:meta.method,stages:meta.method==="master"?["lockpick","pins","dial"]:[meta.method],stageIndex:0,durability:100,progress:0,turning:false,angle:0,targetAngle:0,tolerance:8,errorCooldown:0,pins:[],needle:0,target:0,direction:1,speed:110,round:0,rounds:3,window:18};
    pauseStarted=performance.now();const sx=safe.x-camera.x,sy=safe.y-camera.y+hudSafe;stage.style.setProperty("--focus-x",`${clamp(sx,40,viewW-40)}px`);stage.style.setProperty("--focus-y",`${clamp(sy,hudSafe+30,viewH-40)}px`);stage.classList.add("cracking");
    $("crackPanel").className=`crackPanel tier${safe.tier}`;$("crackType").textContent=meta.name;$("crackTitle").textContent=safe.tier===4?"Вскрытие главного хранилища":"Вскрытие сейфа";$("crackDifficulty").textContent=`СЛОЖНОСТЬ: ${meta.difficulty}`;$("crackOverlay").classList.remove("hidden");renderCrackStage();tg?.HapticFeedback?.impactOccurred?.(safe.tier>=3?"heavy":"medium");
  }
  function closeCrack(){
    if(!crack.active)return;crack.active=false;crack.turning=false;$("crackOverlay").classList.add("hidden");stage.classList.remove("cracking");if(pauseStarted)startedAt+=performance.now()-pauseStarted;pauseStarted=0;lastFrame=performance.now();
  }
  function abortCrack(){if(!crack.active)return;alarm=clamp(alarm+3,0,100);crack.safe.lockUntil=performance.now()+1800;setHint("Взлом отменён. Система заметила вмешательство.",true);closeCrack();}
  function crackError(amount,message){
    crack.durability=clamp(crack.durability-amount,0,100);alarm=clamp(alarm+(crack.safe.tier>=3?4:2.5),0,100);$("durabilityBar").style.width=`${crack.durability}%`;const msg=$("crackMessage");msg.textContent=message;msg.className="crackMessage error";const door=$("safeDoor");door.classList.remove("shake");void door.offsetWidth;door.classList.add("shake");tg?.HapticFeedback?.notificationOccurred?.("warning");if(crack.durability<=0)crackFailed();
  }
  function crackFailed(){
    crack.safe.lockUntil=performance.now()+4500;alarm=clamp(alarm+10,0,100);$("crackMessage").textContent="Инструмент сломан. Сейф временно заблокирован.";$("crackMessage").className="crackMessage error";showBanner("НЕУДАЧНЫЙ ВЗЛОМ",1.7);setTimeout(()=>{setHint("Инструмент сломан — попробуй другой сейф.",true);closeCrack();},650);
  }
  function crackStageSuccess(){
    crack.turning=false;crack.progress=1;$("crackProgressBar").style.width="100%";$("crackMessage").textContent="Механизм поддался!";$("crackMessage").className="crackMessage success";tg?.HapticFeedback?.notificationOccurred?.("success");
    if(crack.stageIndex<crack.stages.length-1){setTimeout(()=>{crack.stageIndex++;crack.progress=0;renderCrackStage();},450);return;}
    $("safeDoor").classList.add("open");setTimeout(()=>{const safe=crack.safe;closeCrack();completeSafe(safe);},650);
  }
  function renderCrackStage(){
    const mode=crack.stages[crack.stageIndex],master=crack.safe.tier===4;crack.mode=mode;crack.progress=0;crack.errorCooldown=0;$("crackProgressBar").style.width="0%";$("durabilityBar").style.width=`${crack.durability}%`;$("crackStageLabel").textContent=`ЭТАП ${crack.stageIndex+1}/${crack.stages.length}`;$("crackMessage").textContent="Работай тихо — ошибки повышают тревогу.";$("crackMessage").className="crackMessage";$("safeDoor").classList.remove("open","shake");
    if(mode==="lockpick")renderLockpick(master);if(mode==="pins")renderPins(master);if(mode==="dial")renderDial(master);
  }
  function renderLockpick(master){
    crack.angle=0;crack.targetAngle=rand(-48,48);crack.tolerance=master?5:crack.safe.tier===1?10:7;crack.turning=false;
    $("crackInstruction").textContent="Двигай отмычку. Когда механизм ослабнет — удерживай «Повернуть замок».";
    $("crackGame").innerHTML=`<div class="lockpickGame"><div class="lockVisual"><div class="sweetHint" id="sweetHint">ИЩИ ПРАВИЛЬНЫЙ УГОЛ</div><div class="pick" id="pick"></div><div class="lockTension"></div></div><input class="angleRange" id="angleRange" type="range" min="-60" max="60" value="0"><button class="turnButton" id="turnButton" type="button">УДЕРЖИВАТЬ И ПОВОРАЧИВАТЬ</button></div>`;
    const range=$("angleRange"),button=$("turnButton");
    const updateAngle=()=>{crack.angle=Number(range.value);$("pick").style.setProperty("--pick-angle",`${crack.angle}deg`);const diff=Math.abs(crack.angle-crack.targetAngle),hint=$("sweetHint");hint.textContent=diff<crack.tolerance?"МЕХАНИЗМ ОСЛАБ — ПОВОРАЧИВАЙ":diff<crack.tolerance*2?"ПОЧТИ…":"ИЩИ ПРАВИЛЬНЫЙ УГОЛ";hint.style.color=diff<crack.tolerance?"#9cffbd":diff<crack.tolerance*2?"#ffe394":"#a89c8e";};
    range.addEventListener("input",updateAngle);updateAngle();
    const down=e=>{e.preventDefault();crack.turning=true;button.classList.add("active");};const up=()=>{crack.turning=false;button.classList.remove("active");};
    button.addEventListener("pointerdown",down);button.addEventListener("pointerup",up);button.addEventListener("pointercancel",up);button.addEventListener("pointerleave",up);
  }
  function renderPins(master){
    const count=master?5:4;crack.pins=Array.from({length:count},()=>({target:randInt(1,4),current:0,locked:false}));
    $("crackInstruction").textContent="Поднимай штифты по одному до светящейся зоны. Перебор сбрасывает штифт.";
    $("crackGame").innerHTML=`<div class="pinsGame">${crack.pins.map((pin,i)=>`<button class="pinColumn" data-pin="${i}" type="button"><i class="pinTarget" style="--target:${12+pin.target*19}px"></i><i class="pinStem" style="--pin-offset:0px"></i><i class="pinHead" style="--pin-offset:0px"></i></button>`).join("")}</div>`;
    $("crackGame").querySelectorAll("[data-pin]").forEach(button=>button.addEventListener("click",()=>{
      const i=Number(button.dataset.pin),pin=crack.pins[i];if(pin.locked)return;pin.current++;
      if(pin.current===pin.target){pin.locked=true;button.classList.add("locked");tg?.HapticFeedback?.impactOccurred?.("light");}
      else if(pin.current>pin.target){pin.current=0;crackError(master?13:10,"Штифт сорвался — начинай его заново.");}
      const offset=-pin.current*19;button.querySelector(".pinStem").style.setProperty("--pin-offset",`${offset}px`);button.querySelector(".pinHead").style.setProperty("--pin-offset",`${offset}px`);
      crack.progress=crack.pins.filter(p=>p.locked).length/crack.pins.length;$("crackProgressBar").style.width=`${crack.progress*100}%`;if(crack.pins.every(p=>p.locked))crackStageSuccess();
    }));
  }
  function renderDial(master){
    crack.needle=rand(0,360);crack.target=rand(25,335);crack.direction=rng()<.5?-1:1;crack.speed=master?155:125;crack.round=0;crack.rounds=master?4:3;crack.window=master?12:17;
    $("crackInstruction").textContent="Стопори кодовый диск, когда стрелка входит в зелёный сектор.";
    $("crackGame").innerHTML=`<div class="dialGame"><div class="dialFace"><i class="dialTarget" id="dialTarget"></i><i class="dialNeedle" id="dialNeedle"></i></div><div class="dialInfo"><strong id="dialRound">1/${crack.rounds}</strong><small>Каждый успешный сектор ускоряет диск и меняет направление.</small><button class="dialTap" id="dialTap" type="button">ЗАФИКСИРОВАТЬ</button></div></div>`;
    updateDialTarget();$("dialTap").addEventListener("click",dialAttempt);
  }
  function updateDialTarget(){const start=(crack.target-crack.window/2+360)%360,end=(crack.target+crack.window/2+360)%360;const el=$("dialTarget");if(el){el.style.setProperty("--target-start",`${start}deg`);el.style.setProperty("--target-end",`${end}deg`);}const round=$("dialRound");if(round)round.textContent=`${crack.round+1}/${crack.rounds}`;}
  function dialAttempt(){
    if(degDiff(crack.needle,crack.target)<=crack.window/2){crack.round++;crack.progress=crack.round/crack.rounds;$("crackProgressBar").style.width=`${crack.progress*100}%`;tg?.HapticFeedback?.impactOccurred?.("medium");if(crack.round>=crack.rounds){crackStageSuccess();return;}crack.target=rand(25,335);crack.direction*=-1;crack.speed*=1.13;updateDialTarget();$("crackMessage").textContent="Щелчок! Следующая комбинация быстрее.";$("crackMessage").className="crackMessage success";}
    else{crackError(crack.safe.tier===4?15:11,"Промах по сектору — комбинация сбилась.");crack.round=Math.max(0,crack.round-1);crack.progress=crack.round/crack.rounds;$("crackProgressBar").style.width=`${crack.progress*100}%`;crack.target=rand(25,335);updateDialTarget();}
  }
  function updateCrack(dt){
    if(!crack.active)return;if(crack.errorCooldown>0)crack.errorCooldown-=dt;
    if(crack.mode==="lockpick"&&crack.turning){const diff=Math.abs(crack.angle-crack.targetAngle);if(diff<=crack.tolerance){crack.progress=clamp(crack.progress+dt*(crack.safe.tier===4?.58:.78),0,1);$("crackProgressBar").style.width=`${crack.progress*100}%`;$("safeDial").style.transform=`rotate(${crack.progress*72}deg)`;if(crack.progress>=1)crackStageSuccess();}
      else{crack.progress=Math.max(0,crack.progress-dt*.25);$("crackProgressBar").style.width=`${crack.progress*100}%`;crack.durability=clamp(crack.durability-dt*(crack.safe.tier===4?19:14),0,100);$("durabilityBar").style.width=`${crack.durability}%`;if(crack.errorCooldown<=0){crack.errorCooldown=.48;alarm=clamp(alarm+2.2,0,100);const door=$("safeDoor");door.classList.remove("shake");void door.offsetWidth;door.classList.add("shake");tg?.HapticFeedback?.impactOccurred?.("light");}if(crack.durability<=0)crackFailed();}}
    if(crack.mode==="dial"){crack.needle=(crack.needle+crack.direction*crack.speed*dt+360)%360;const needle=$("dialNeedle");if(needle)needle.style.setProperty("--dial-angle",`${crack.needle}deg`);}
  }

  function completeSafe(safe){
    if(safe.opened)return;safe.opened=true;opened++;const jackpot=rng()<(safe.tier===4?.34:safe.tier===3?.22:.16)?Math.round(safe.value*(safe.tier===4?.75:.55)):0;const reward=safe.value+jackpot;loot+=reward;alarm=clamp(alarm+(safe.tier===4?12:safe.tier===3?8:4),0,100);burst(safe.x,safe.y,safe.tier>=3?"#d985ff":"#ffd76c",safe.tier===4?52:30,safe.tier===4?190:140);addFloater(safe.x,safe.y-20,`+${reward}`,safe.tier>=3?"#edc2ff":"#ffe59a",1.35);flyLoot(safe,reward);if(safe.tier>=3){fxLayer.insertAdjacentHTML("beforeend",'<i class="screenFlash"></i>');setTimeout(()=>fxLayer.querySelector(".screenFlash")?.remove(),500);}if(safe.tier===4)showBanner("ГЛАВНОЕ ХРАНИЛИЩЕ ВСКРЫТО",2.2);setHint(jackpot?`🍀 Джекпот сейфа: +${reward} влияния!`:`💰 Сейф вскрыт: +${reward} влияния`,true);tg?.HapticFeedback?.notificationOccurred?.("success");idleTime=0;updateRoute();
  }
  function interact(){if(!running||crack.active)return;const safe=nearestSafe();if(safe){openCrack(safe);return;}if(nearExit()){if(loot<=0){setHint("Сначала вскрой хотя бы один сейф.",true);return;}finishGame(opened===totalSafes?"Идеальное ограбление: вынесены все сейфы":"Ты успешно покинул хранилище",1);return;}setHint("Подойди ближе к сейфу или выходу.",true);}
  function useSmoke(){if(!running||crack.active||smokeCooldown>0)return;smokeTime=5.5;smokeCooldown=22;alarm=Math.max(0,alarm-24);for(const cam of cameras){cam.alert=Math.max(0,cam.alert-.6);cam.state="search";}burst(player.x,player.y,"#d8cbed",48,170);stage.classList.add("smoke-active");$("smokeStatus").classList.remove("hidden");showBanner("КАМЕРЫ ПОТЕРЯЛИ ЦЕЛЬ",1.6);setHint("🌫 Дым скрывает тебя от камер на 5 секунд.",true);tg?.HapticFeedback?.impactOccurred?.("medium");}

  function updatePlayer(dt){
    const input=Math.hypot(moveX,moveY),oldX=player.x,oldY=player.y;
    if(input>.04){const nx=moveX/input,ny=moveY/input,speed=smokeTime>0?180:158;player.vx+=(nx*speed-player.vx)*Math.min(1,dt*11);player.vy+=(ny*speed-player.vy)*Math.min(1,dt*11);player.angle=Math.atan2(player.vy,player.vx);idleTime=0;}else{player.vx*=Math.pow(.0015,dt);player.vy*=Math.pow(.0015,dt);idleTime+=dt;}
    const dx=player.vx*dt,dy=player.vy*dt;if(!pointInWall(player.x+dx,player.y)){player.x+=dx;}else{player.vx*=-.15;player.bump=.18;shake=Math.max(shake,.1);}if(!pointInWall(player.x,player.y+dy)){player.y+=dy;}else{player.vy*=-.15;player.bump=.18;shake=Math.max(shake,.1);}
    const speed=Math.hypot(player.vx,player.vy);player.stretch+=(clamp(speed/175,0,1)-player.stretch)*Math.min(1,dt*8);player.bump=Math.max(0,player.bump-dt);
    if(Math.hypot(player.x-oldX,player.y-oldY)>1&&rng()<dt*18)trails.push({x:player.x-player.vx*.045,y:player.y-player.vy*.045,life:.48,max:.48,size:rand(3.5,7)});
    const cell=playerCell();if(cell){revealAround(cell.c,cell.r,1);if(cell.zone!==currentZone){currentZone=cell.zone;zoneTimer=1.35;$("zoneBanner").textContent=ZONE_META[cell.zone].label;$("zoneBanner").classList.add("show");}}
  }
  function updateCameras(dt){
    let detected=0,suspicious=0;
    for(const cam of cameras){cam.pause-=dt;if(cam.pause<=0&&cam.state!=="detected"){cam.angle+=cam.speed*dt;if(rng()<dt*.055){cam.pause=rand(.3,.85);cam.speed*=-1;}}const seen=cameraSeesPlayer(cam);cam.alert=clamp(cam.alert+(seen?dt*1.75:-dt*1.25),0,1);const prev=cam.state;cam.state=cam.alert>.58?"detected":cam.alert>.13?"suspicious":"search";if(cam.state==="detected")detected++;else if(cam.state==="suspicious")suspicious++;if(prev!==cam.state&&cam.state==="detected"){showBanner("КАМЕРА ЗАХВАТИЛА ЦЕЛЬ",1.2);tg?.HapticFeedback?.notificationOccurred?.("warning");}}
    if(detected)alarm+=dt*(18+detected*7);else if(suspicious)alarm+=dt*(3+suspicious*1.5);else alarm-=dt*8;alarm=clamp(alarm,0,100);maxAlarm=Math.max(maxAlarm,alarm);if(alarm>=100)finishGame("Система безопасности тебя поймала",.2);
  }
  function updateCamera(dt){const visibleH=Math.max(160,viewH-hudSafe),tx=clamp(player.x-viewW*.5,0,Math.max(0,WORLD_W-viewW)),ty=clamp(player.y-visibleH*.57,0,Math.max(0,WORLD_H-visibleH)),ease=1-Math.pow(.001,dt);camera.x+=(tx-camera.x)*ease;camera.y+=(ty-camera.y)*ease;}
  function updateEffects(dt){for(const p of particles){p.life-=dt;p.x+=p.vx*dt;p.y+=p.vy*dt;p.vy+=135*dt;}particles=particles.filter(p=>p.life>0);for(const t of trails)t.life-=dt;trails=trails.filter(t=>t.life>0);for(const f of floaters){f.life-=dt;f.y-=26*dt;}floaters=floaters.filter(f=>f.life>0);if(shake>0)shake=Math.max(0,shake-dt);if(bannerTimer>0){bannerTimer-=dt;if(bannerTimer<=0)$("alertBanner").classList.remove("show");}if(zoneTimer>0){zoneTimer-=dt;if(zoneTimer<=0)$("zoneBanner").classList.remove("show");}}
  function update(dt){
    timeLeft=Math.max(0,duration-(performance.now()-startedAt)/1000);if(smokeTime>0){smokeTime=Math.max(0,smokeTime-dt);$("smokeTimer").textContent=smokeTime.toFixed(1);if(smokeTime<=0){stage.classList.remove("smoke-active");$("smokeStatus").classList.add("hidden");}}if(smokeCooldown>0)smokeCooldown=Math.max(0,smokeCooldown-dt);
    updatePlayer(dt);updateCameras(dt);updateCamera(dt);updateEffects(dt);updateRoute();
    const next=alarmLevel(alarm);if(next!==alertTier){alertTier=next;onAlarmChanged(next);}$("loot").textContent=loot;const secs=Math.max(0,Math.ceil(timeLeft));$("timer").textContent=`${Math.floor(secs/60)}:${String(secs%60).padStart(2,"0")}`;$("safes").textContent=`СЕЙФЫ ${opened}/${totalSafes}`;$("alarmBar").style.width=`${alarm}%`;$("alarmText").textContent=`${Math.round(alarm)}%`;
    const smokeBtn=$("smoke");smokeBtn.disabled=smokeCooldown>0;smokeBtn.textContent=smokeCooldown>0?`🌫 ДЫМ: ${Math.ceil(smokeCooldown)}с`:"🌫 ДЫМОВАЯ ЗАВЕСА";
    updateActionButton();if(timeLeft<=0)finishGame("Время вышло — удалось сохранить часть добычи",.35);
  }
  function updateActionButton(){const button=$("interact"),safe=nearestSafe();button.classList.remove("ready","exit","search");if(safe){button.disabled=false;button.classList.add("ready");button.textContent=safe.tier===4?"🏛 ВСКРЫТЬ ХРАНИЛИЩЕ":safe.tier===3?"💎 ВЗЛОМАТЬ ЭЛИТНЫЙ СЕЙФ":safe.tier===2?"🧰 ВСКРЫТЬ УСИЛЕННЫЙ СЕЙФ":"🔓 ВСКРЫТЬ СЕЙФ";setHint(`Рядом ${SAFE_META[safe.tier].label.toLowerCase()} сейф — начинай взлом`);return;}if(nearExit()){button.disabled=false;button.classList.add("exit","ready");button.textContent=loot?"🚪 УЙТИ С ДОБЫЧЕЙ":"🚪 СНАЧАЛА НАЙДИ ДОБЫЧУ";return;}button.disabled=true;button.classList.add("search");button.textContent=idleTime>=8?"🧭 МАРШРУТ К ЦЕЛИ":"🔎 ПОДОЙДИ К СЕЙФУ";}

  function burst(x,y,color,count=20,power=120){for(let i=0;i<count;i++){const a=rand(0,Math.PI*2),s=rand(power*.25,power);particles.push({x,y,vx:Math.cos(a)*s,vy:Math.sin(a)*s,life:rand(.45,.9),max:1,color,size:rand(2,5)});}}
  function addFloater(x,y,text,color,life=1){floaters.push({x,y,text,color,life,max:life});}
  function flyLoot(safe,reward){const sx=safe.x-camera.x,sy=safe.y-camera.y+hudSafe;fxLayer.insertAdjacentHTML("beforeend",`<i class="lootChip" style="--sx:${sx}px;--sy:${sy}px">+${reward}</i>`);setTimeout(()=>fxLayer.querySelector(".lootChip")?.remove(),900);}

  function screen(x,y){return{x:x-camera.x,y:y-camera.y+hudSafe};}
  function rounded(c,x,y,w,h,r){r=Math.min(r,w/2,h/2);c.beginPath();c.moveTo(x+r,y);c.arcTo(x+w,y,x+w,y+h,r);c.arcTo(x+w,y+h,x,y+h,r);c.arcTo(x,y+h,x,y,r);c.arcTo(x,y,x+w,y,r);c.closePath();}
  function drawFloor(){
    const visibleH=viewH-hudSafe,minC=Math.max(0,Math.floor(camera.x/CELL)-1),maxC=Math.min(COLS-1,Math.ceil((camera.x+viewW)/CELL)),minR=Math.max(0,Math.floor(camera.y/CELL)-1),maxR=Math.min(ROWS-1,Math.ceil((camera.y+visibleH)/CELL));
    for(let r=minR;r<=maxR;r++)for(let c=minC;c<=maxC;c++){const cell=cellAt(c,r),meta=ZONE_META[cell.zone],x=c*CELL-camera.x,y=r*CELL-camera.y+hudSafe;ctx.fillStyle=meta.floor;ctx.fillRect(x,y,CELL,CELL);ctx.strokeStyle=meta.line+"55";ctx.lineWidth=1;ctx.strokeRect(x+.5,y+.5,CELL-1,CELL-1);ctx.fillStyle="#ffffff08";for(let k=14;k<CELL;k+=23)ctx.fillRect(x+k,y,1,CELL);}
  }
  function drawDecor(){for(const item of decor){const p=screen(item.x,item.y);if(p.x<-30||p.x>viewW+30||p.y<hudSafe-30||p.y>viewH+30)continue;const accent=ZONE_META[item.zone].accent;ctx.save();ctx.translate(p.x,p.y);ctx.rotate(item.rot);ctx.globalAlpha=.48;if(item.type==="server"){ctx.fillStyle="#17252a";ctx.fillRect(-17,-25,34,50);ctx.strokeStyle=accent;for(let y=-18;y<20;y+=10){ctx.strokeRect(-11,y,22,6);}}else if(item.type==="vent"){ctx.strokeStyle=accent;ctx.strokeRect(-16,-12,32,24);for(let x=-11;x<14;x+=6){ctx.beginPath();ctx.moveTo(x,-9);ctx.lineTo(x,9);ctx.stroke();}}else if(item.type==="cable"){ctx.strokeStyle=accent;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-28,12);ctx.bezierCurveTo(-8,-20,9,25,30,-8);ctx.stroke();}else if(item.type==="laser"){ctx.strokeStyle="#ff455f";ctx.shadowBlur=8;ctx.shadowColor="#ff455f";ctx.beginPath();ctx.moveTo(-32,0);ctx.lineTo(32,0);ctx.stroke();ctx.shadowBlur=0;}else if(item.type==="monitor"){ctx.fillStyle="#111";ctx.fillRect(-18,-14,36,25);ctx.strokeStyle=accent;ctx.strokeRect(-18,-14,36,25);ctx.fillStyle=accent;ctx.fillRect(-12,-8,24,3);}else if(item.type==="crate"){ctx.fillStyle="#2d251d";ctx.fillRect(-17,-17,34,34);ctx.strokeStyle=accent;ctx.strokeRect(-17,-17,34,34);ctx.beginPath();ctx.moveTo(-17,-17);ctx.lineTo(17,17);ctx.moveTo(17,-17);ctx.lineTo(-17,17);ctx.stroke();}else if(item.type==="panel"||item.type==="seal"){ctx.fillStyle=accent+"20";ctx.fillRect(-23,-11,46,22);ctx.strokeStyle=accent;ctx.strokeRect(-23,-11,46,22);}else if(item.type==="stripe"){ctx.strokeStyle=accent;ctx.setLineDash([8,6]);ctx.beginPath();ctx.moveTo(-32,0);ctx.lineTo(32,0);ctx.stroke();ctx.setLineDash([]);}else if(item.type==="crack"){ctx.strokeStyle=accent;ctx.beginPath();ctx.moveTo(-24,-18);ctx.lineTo(-6,-3);ctx.lineTo(-12,13);ctx.lineTo(8,3);ctx.lineTo(23,18);ctx.stroke();}else{ctx.fillStyle=accent+"44";for(let i=0;i<5;i++)ctx.fillRect(rand(-20,20),rand(-15,15),rand(3,8),rand(2,5));}ctx.restore();}}
  function drawExit(t){const p=screen(exit.x,exit.y),pulse=.55+.45*Math.sin(t*3.2);ctx.save();ctx.shadowBlur=20+12*pulse;ctx.shadowColor="#63f5a1";const g=ctx.createLinearGradient(p.x,p.y,p.x,p.y+exit.h);g.addColorStop(0,"#153e2b");g.addColorStop(1,"#0a2518");ctx.fillStyle=g;rounded(ctx,p.x,p.y,exit.w,exit.h,11);ctx.fill();ctx.lineWidth=3;ctx.strokeStyle="#63f5a1";ctx.stroke();ctx.shadowBlur=0;ctx.fillStyle="#b8ffd0";ctx.font="900 10px system-ui";ctx.textAlign="center";ctx.fillText("ВЫХОД",p.x+exit.w/2,p.y+36);ctx.restore();}
  function drawWalls(){for(const w of walls){const p=screen(w.x,w.y);if(p.x+w.w<0||p.x>viewW||p.y+w.h<hudSafe||p.y>viewH)continue;const g=ctx.createLinearGradient(p.x,p.y,p.x+w.w,p.y+w.h);g.addColorStop(0,"#4a3a28");g.addColorStop(.5,"#21191a");g.addColorStop(1,"#6c5130");ctx.fillStyle=g;rounded(ctx,p.x,p.y,w.w,w.h,Math.min(6,w.w/2,w.h/2));ctx.fill();ctx.strokeStyle="#c1984b66";ctx.lineWidth=1.5;ctx.stroke();}}
  function drawSafe(safe,t){const p=screen(safe.x,safe.y),meta=SAFE_META[safe.tier],s=meta.size;if(p.x<-60||p.x>viewW+60||p.y<hudSafe-60||p.y>viewH+60)return;ctx.save();ctx.translate(p.x,p.y);const pulse=.72+.28*Math.sin(t*(safe.tier+1)*1.5+safe.id);if(!safe.opened){ctx.shadowBlur=safe.tier>=3?24*pulse:12*pulse;ctx.shadowColor=meta.color;}ctx.fillStyle=safe.opened?"#151319":safe.tier===4?"#8e6325":safe.tier===3?"#4b2d64":safe.tier===2?"#28474d":"#604820";rounded(ctx,-s,-s*.8,s*2,s*1.6,8);ctx.fill();ctx.lineWidth=safe.tier===4?4:3;ctx.strokeStyle=safe.opened?"#4d4848":meta.color;ctx.stroke();ctx.shadowBlur=0;if(!safe.opened){ctx.strokeStyle="#ffffff25";ctx.strokeRect(-s+6,-s*.8+6,s*2-12,s*1.6-12);ctx.fillStyle="#0b090d";ctx.beginPath();ctx.arc(0,0,safe.tier===4?9:7,0,Math.PI*2);ctx.fill();ctx.strokeStyle=meta.color;ctx.lineWidth=2;ctx.stroke();for(const [x,y] of [[-s+7,-s*.8+7],[s-7,-s*.8+7],[-s+7,s*.8-7],[s-7,s*.8-7]]){ctx.fillStyle="#d6b978";ctx.beginPath();ctx.arc(x,y,2.5,0,Math.PI*2);ctx.fill();}if(safe.tier===4){ctx.fillStyle="#ffe394";ctx.font="900 12px system-ui";ctx.textAlign="center";ctx.fillText("VAULT",0,-s*.8-9);}}else{ctx.fillStyle="#070609";ctx.fillRect(-s+7,-s*.8+7,s*1.65,s*1.6-14);}ctx.restore();}
  function drawCamera(cam){const p=screen(cam.x,cam.y);if(p.x<-cam.range||p.x>viewW+cam.range||p.y<hudSafe-cam.range||p.y>viewH+cam.range)return;ctx.save();ctx.translate(p.x,p.y);const color=cam.state==="detected"?"#ff365d":cam.state==="suspicious"?"#ffc857":"#e34f72";if(smokeTime<=0){ctx.beginPath();ctx.moveTo(0,0);const samples=18;for(let i=0;i<=samples;i++){const a=cam.angle-cam.fov/2+cam.fov*i/samples,d=rayDistance(cam.x,cam.y,a,cam.range);ctx.lineTo(Math.cos(a)*d,Math.sin(a)*d);}ctx.closePath();const g=ctx.createRadialGradient(0,0,5,0,0,cam.range);g.addColorStop(0,color+"55");g.addColorStop(.7,color+"20");g.addColorStop(1,color+"00");ctx.fillStyle=g;ctx.fill();}ctx.shadowBlur=cam.state==="detected"?20:10;ctx.shadowColor=color;ctx.fillStyle=cam.state==="detected"?"#d92f50":"#79283d";ctx.beginPath();ctx.arc(0,0,14,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle=cam.state==="suspicious"?"#ffe28b":"#ff9bad";ctx.lineWidth=2.4;ctx.beginPath();ctx.ellipse(0,0,10.5,6.3,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle="#fff";ctx.beginPath();ctx.arc(0,0,3.3,0,Math.PI*2);ctx.fill();ctx.fillStyle="#1c0b12";ctx.beginPath();ctx.arc(0,0,1.7,0,Math.PI*2);ctx.fill();ctx.restore();}
  function drawRoute(){if(route.length<2)return;ctx.save();ctx.strokeStyle=opened===totalSafes||timeLeft<=20?"#63f5a0aa":"#ffd76c88";ctx.lineWidth=4;ctx.setLineDash([8,9]);ctx.lineCap="round";ctx.beginPath();route.forEach((p,i)=>{const s=screen(p.x,p.y);if(i===0)ctx.moveTo(s.x,s.y);else ctx.lineTo(s.x,s.y);});ctx.stroke();ctx.setLineDash([]);ctx.restore();}
  function drawPlayer(t){const p=screen(player.x,player.y),speedScale=player.stretch,bump=player.bump>0?.82:1;ctx.save();ctx.translate(p.x,p.y);ctx.rotate(player.angle);const sx=(1+speedScale*.23)*bump,sy=(1-speedScale*.13)*(2-bump);ctx.scale(sx,sy);ctx.shadowBlur=22;ctx.shadowColor=alarm>60?"#ff365d":"#a76bff";const g=ctx.createRadialGradient(-3,-4,2,0,0,player.r*1.4);g.addColorStop(0,"#d6a6ff");g.addColorStop(.45,"#a76bff");g.addColorStop(1,"#5e2aa0");ctx.fillStyle=g;ctx.beginPath();ctx.arc(0,0,player.r,0,Math.PI*2);ctx.fill();ctx.restore();ctx.save();ctx.translate(p.x,p.y-player.r-9);ctx.rotate(Math.sin(t*5)*.08+player.vx*.0008);ctx.font="19px system-ui";ctx.textAlign="center";ctx.fillText("👑",0,3);ctx.restore();if(nearestSafe(62)){ctx.strokeStyle="#ffe39477";ctx.lineWidth=2;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(p.x,p.y,29+Math.sin(t*4)*2,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);}}
  function drawEffects(){for(const tr of trails){const p=screen(tr.x,tr.y);ctx.globalAlpha=tr.life/tr.max*.35;ctx.fillStyle="#a76bff";ctx.beginPath();ctx.arc(p.x,p.y,tr.size,0,Math.PI*2);ctx.fill();}ctx.globalAlpha=1;for(const p0 of particles){const p=screen(p0.x,p0.y);ctx.globalAlpha=clamp(p0.life/p0.max,0,1);ctx.fillStyle=p0.color;ctx.fillRect(p.x,p.y,p0.size,p0.size);}ctx.globalAlpha=1;for(const f of floaters){const p=screen(f.x,f.y);ctx.globalAlpha=f.life/f.max;ctx.fillStyle=f.color;ctx.font="900 13px system-ui";ctx.textAlign="center";ctx.fillText(f.text,p.x,p.y);}ctx.globalAlpha=1;}
  function drawSmoke(){if(smokeTime<=0)return;const p=screen(player.x,player.y);ctx.save();for(let i=0;i<18;i++){const a=i/18*Math.PI*2+ticker*.25,r=18+(i%5)*8;ctx.fillStyle=`rgba(205,194,224,${.035+(i%3)*.018})`;ctx.beginPath();ctx.arc(p.x+Math.cos(a)*r,p.y+Math.sin(a)*r,18+(i%4)*4,0,Math.PI*2);ctx.fill();}ctx.restore();}
  let ticker=0;
  function draw(now=0){
    ticker=now/1000;ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,viewW,viewH);const bg=ctx.createLinearGradient(0,0,0,viewH);bg.addColorStop(0,"#1e1518");bg.addColorStop(1,"#08070c");ctx.fillStyle=bg;ctx.fillRect(0,0,viewW,viewH);ctx.save();ctx.beginPath();ctx.rect(0,hudSafe,viewW,viewH-hudSafe);ctx.clip();if(shake>0)ctx.translate(rand(-4,4)*shake,rand(-4,4)*shake);drawFloor();drawDecor();drawRoute();drawExit(ticker);for(const safe of safes)drawSafe(safe,ticker);for(const cam of cameras)drawCamera(cam);drawWalls();drawEffects();drawSmoke();drawPlayer(ticker);ctx.restore();drawMiniMap();}

  function drawMiniMap(){
    const w=Math.max(1,miniCanvas.clientWidth),h=Math.max(1,miniCanvas.clientHeight);mini.setTransform(dpr,0,0,dpr,0,0);mini.clearRect(0,0,w,h);mini.fillStyle="#060509";mini.fillRect(0,0,w,h);const pad=6,sx=(w-pad*2)/WORLD_W,sy=(h-pad*2)/WORLD_H;
    for(const cell of cells){if(!discovered.has(cellKey(cell.c,cell.r)))continue;mini.fillStyle=ZONE_META[cell.zone].floor;mini.fillRect(pad+cell.c*CELL*sx,pad+cell.r*CELL*sy,CELL*sx+.5,CELL*sy+.5);}
    mini.strokeStyle="#d3aa5a99";mini.lineWidth=1;for(const wall of walls){const c=Math.floor((wall.x+1)/CELL),r=Math.floor((wall.y+1)/CELL);if(!discovered.has(cellKey(clamp(c,0,COLS-1),clamp(r,0,ROWS-1))))continue;mini.strokeRect(pad+wall.x*sx,pad+wall.y*sy,Math.max(1,wall.w*sx),Math.max(1,wall.h*sy));}
    mini.fillStyle="#63f5a0";mini.fillRect(pad+exit.x*sx,pad+exit.y*sy,Math.max(3,exit.w*sx),Math.max(3,exit.h*sy));
    for(const safe of safes){if(safe.opened||!discovered.has(cellKey(safe.c,safe.r)))continue;mini.fillStyle=SAFE_META[safe.tier].color;const x=pad+safe.x*sx,y=pad+safe.y*sy,r=safe.tier===4?4:safe.tier===3?3:2;mini.save();mini.translate(x,y);if(safe.tier===4)mini.rotate(Math.PI/4);mini.fillRect(-r,-r,r*2,r*2);mini.restore();}
    for(const cam of cameras){if(!discovered.has(cellKey(cam.c,cam.r)))continue;mini.fillStyle=cam.state==="detected"?"#ff365d":"#df5a76";mini.beginPath();mini.arc(pad+cam.x*sx,pad+cam.y*sy,1.7,0,Math.PI*2);mini.fill();}
    const x=pad+player.x*sx,y=pad+player.y*sy;mini.save();mini.translate(x,y);mini.rotate(player.angle+Math.PI/2);mini.fillStyle="#f1c2ff";mini.beginPath();mini.moveTo(0,-5);mini.lineTo(4,4);mini.lineTo(0,2);mini.lineTo(-4,4);mini.closePath();mini.fill();mini.restore();
  }

  function loop(now){if(!running)return;const dt=Math.min(.034,(now-lastFrame)/1000||.016);lastFrame=now;if(crack.active)updateCrack(dt);else update(dt);draw(now);if(running)requestAnimationFrame(loop);}
  async function finishGame(reason,keep){
    if(ended)return;ended=true;running=false;if(crack.active)closeCrack();secured=Math.round(loot*keep);$("finish").classList.remove("hidden");$("result").style.display="block";$("resultTitle").textContent=reason;$("collected").textContent=loot;$("secured").textContent=secured;$("opened").textContent=`${opened}/${totalSafes}`;$("maxAlarm").textContent=`${Math.round(maxAlarm)}%`;$("reward").textContent=demo?"Демонстрационный режим: добыча не начисляется в баланс.":"Сохраняем результат…";
    if(!demo&&sessionId){try{const r=await api("finish",{session_id:sessionId,score:secured,stats:{collected:loot,secured,opened,total_safes:totalSafes,max_alarm:Math.round(maxAlarm),escaped:keep===1,map_code:mapCode}});$("reward").innerHTML=`Базовая награда: <b>+${r.base_run_reward}</b><br>За улучшение рекорда: <b>+${r.payable_base}</b><br>🌳 Бонус древа: <b>+${r.tree_bonus}</b><br>🏆 Получено влияния: <b>+${r.actual_reward}</b><br>Баланс: <b>${r.balance}</b><br><small>${r.message}</small>`;}catch(error){$("reward").innerHTML=`<span class="error">${error.message}</span>`;}}
  }

  const joy=$("joystick"),knob=$("knob");let joyId=null;
  function setJoy(e){const rect=joy.getBoundingClientRect(),cx=rect.left+rect.width/2,cy=rect.top+rect.height/2,dx=e.clientX-cx,dy=e.clientY-cy,len=Math.hypot(dx,dy),max=46,k=Math.min(1,max/(len||1)),x=dx*k,y=dy*k;knob.style.transform=`translate(${x}px,${y}px)`;moveX=x/max;moveY=y/max;joy.classList.add("active");}
  joy.addEventListener("pointerdown",e=>{joyId=e.pointerId;joy.setPointerCapture(e.pointerId);setJoy(e);});joy.addEventListener("pointermove",e=>{if(e.pointerId===joyId)setJoy(e);});
  function clearJoy(e){if(joyId!==null&&(e.pointerId===undefined||e.pointerId===joyId)){joyId=null;moveX=moveY=0;knob.style.transform="";joy.classList.remove("active");}}
  joy.addEventListener("pointerup",clearJoy);joy.addEventListener("pointercancel",clearJoy);
  const keys={};addEventListener("keydown",e=>{keys[e.key]=true;if(e.key==="e"||e.key==="Enter")interact();if(e.key===" ")useSmoke();syncKeys();});addEventListener("keyup",e=>{keys[e.key]=false;syncKeys();});
  function syncKeys(){moveX=(keys.ArrowRight||keys.d?1:0)-(keys.ArrowLeft||keys.a?1:0);moveY=(keys.ArrowDown||keys.s?1:0)-(keys.ArrowUp||keys.w?1:0);}

  $("interact").addEventListener("click",interact);$("smoke").addEventListener("click",useSmoke);$("start").addEventListener("click",startGame);$("again").addEventListener("click",startGame);$("crackAbort").addEventListener("click",abortCrack);$("minimapWrap").addEventListener("click",()=>$("minimapWrap").classList.toggle("expanded"));
  const goGames=()=>location.href=`/games/?${params.toString()}`;$("back").addEventListener("click",goGames);$("toGames").addEventListener("click",goGames);$("introToGames").addEventListener("click",goGames);
  resize();rng=seeded(Date.now());buildMaze();buildObjects();draw();
})();
