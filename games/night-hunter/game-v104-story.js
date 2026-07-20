/* Reality 104: free-roam story campaign, survivor escort and swept bullet hit registration. */
const V104={version:'Reality 104 · Open Story'};
const v104BaseReset=reset,v104BaseStartGame=startGame,v104BaseMoveEnemy=moveEnemy,v104BaseUpdateEnemies=updateEnemies,v104BaseDrawWorld=drawWorld,v104BaseDrawObjectives=drawObjectives,v104BaseHud=updateHud;
const v104Path=[
 {x:280,y:220},{x:568,y:220},{x:855,y:220},{x:1143,y:220},{x:1430,y:220},
 {x:1430,y:495},{x:1430,y:770},{x:1143,y:770},{x:855,y:770},{x:568,y:770},{x:280,y:770}
];
const v104Points={terminal:{x:370,y:255,label:'ТЕРМИНАЛ ОХРАНЫ'},generator:{x:855,y:770,label:'ГЕНЕРАТОРНАЯ'},survivor:{x:1430,y:785,label:'ВЫЖИВШАЯ'},card:{x:1510,y:355,label:'КАРТА ЛИФТА'},sample:{x:855,y:250,label:'ОБРАЗЕЦ'},elevator:{x:280,y:875,label:'ЭВАКУАЦИЯ'}};
let v104EnemyId=1,v104PodId=1,v104MapLast=0;

function v104StoryState(){return state.story}
function v104InitStory(){
 state.story={active:true,phase:0,progress:0,nextSpawn:performance.now()+1200,lastRadioAt:0,choice:null,choiceOpen:false,bossSpawned:false,
 survivor:{x:v104Points.survivor.x,y:v104Points.survivor.y,hp:80,maxHp:80,rescued:false,attackAt:0},extractProgress:0,radioText:'',radioSpeaker:'АННА'};
 state.activeRoom=99;state.roomsCleared=0;state.unlockedThrough=6;state.breakers=[];state.pods=[];state.spawnQueue=[];state.telegraphs=[];state.enemies=[];state.enemyBullets=[];
 doorClosed=()=>false;
 for(const spec of [{t:'walker',r:0},{t:'runner',r:1},{t:'spitter',r:2},{t:'walker',r:3},{t:'brute',r:4}])queueSpawn(spec.t,spec.r,.55+rand()*.8);
 v104Radio('АННА','Если кто-нибудь слышит… я заперта в медицинском блоке. Найди терминал охраны.');
}
reset=function(){const wanted=Math.max(360,Number(state.time)||0);v104BaseReset();state.time=wanted;v104InitStory()};
startSector=function(){state.activeRoom=99};
startGame=function(demo=false){v104BaseStartGame(demo);setTimeout(()=>v104Radio('АННА','Я вижу сигнал твоего фонаря. Сначала включи терминал охраны.'),120)};
doorClosed=()=>false;
updateDirection=function(){const el=$('direction');if(el)el.classList.add('hidden')};

function v104Radio(speaker,text){
 const s=v104StoryState();if(!s)return;s.radioSpeaker=speaker;s.radioText=text;s.lastRadioAt=performance.now();
 const panel=$('radioHud');if(panel){panel.classList.add('show');$('radioSpeaker').textContent=speaker;$('radioText').textContent=text;const hp=$('survivorHp');if(hp)hp.textContent=s.survivor.rescued?'АННА '+Math.max(0,Math.ceil(s.survivor.hp))+'/'+s.survivor.maxHp:'СИГНАЛ ПО РАЦИИ'}
 setCaption(speaker+': '+text,4.6);tone(speaker==='СИСТЕМА'?420:610,.07,'sine',.07)
}
function v104Phase(next,speaker,text,score=110){const s=v104StoryState();s.phase=next;s.progress=0;state.roomsCleared=Math.min(6,next);state.score+=score;v104Radio(speaker,text)}
function v104Objective(){
 const s=v104StoryState();if(!s)return'СИСТЕМА ЗАГРУЖАЕТСЯ';
 if(s.phase===0)return'АКТИВИРУЙ ТЕРМИНАЛ ОХРАНЫ';
 if(s.phase===1)return'ПИТАНИЕ: '+state.breakers.filter(b=>b.active).length+'/3';
 if(s.phase===2)return'НАЙДИ ВЫЖИВШУЮ В МЕДБЛОКЕ';
 if(s.phase===3)return'ЗАБЕРИ КАРТУ ЛИФТА В АРХИВЕ';
 if(s.phase===4)return'ДОБЕРИСЬ ДО ОБРАЗЦА В ЛАБОРАТОРИИ';
 if(s.phase===5)return'СОПРОВОДИ АННУ К ЛИФТУ';
 if(s.phase===6){const boss=state.enemies.find(e=>e.type==='boss');return boss?'ТЯЖЁЛЫЙ ОХОТНИК: '+Math.max(0,Math.ceil(boss.hp)):'ЗАЩИТИ ЛИФТ'}
 if(s.phase===7)return'ЭВАКУАЦИЯ: '+Math.round(Math.min(100,s.extractProgress/5*100))+'%';
 return'ВЫХОД ОТКРЫТ'
}
currentObjectiveText=v104Objective;
function v104Target(){const s=v104StoryState();if(!s)return null;if(s.phase===0)return v104Points.terminal;if(s.phase===1){const b=state.breakers.find(q=>!q.active);return b?{x:b.x,y:b.y,label:'РУБИЛЬНИК'}:v104Points.generator}if(s.phase===2)return v104Points.survivor;if(s.phase===3)return v104Points.card;if(s.phase===4)return v104Points.sample;return v104Points.elevator}
function v104Hold(point,dt,need=1.2,radius=54){const s=v104StoryState(),near=dist(player.x,player.y,point.x,point.y)<radius;s.progress=near?Math.min(need,s.progress+dt):Math.max(0,s.progress-dt*.65);return s.progress>=need}

function v104NearestNode(x,y){let bi=0,bd=Infinity;for(let i=0;i<v104Path.length;i++){const d=dist(x,y,v104Path[i].x,v104Path[i].y);if(d<bd){bd=d;bi=i}}return bi}
function v104NavTarget(x,y,tx,ty){const ri=roomAt(x,y),ti=roomAt(tx,ty);if(ri>=0&&ri===ti)return{x:tx,y:ty};const a=v104NearestNode(x,y),b=v104NearestNode(tx,ty);if(a===b)return{x:tx,y:ty};return v104Path[a+(b>a?1:-1)]}
moveEnemy=function(e,tx,ty,dt,mult=1){if(state.story?.active){const n=v104NavTarget(e.x,e.y,tx,ty);return v104BaseMoveEnemy(e,n.x,n.y,dt,mult)}return v104BaseMoveEnemy(e,tx,ty,dt,mult)};

function v104MoveSurvivor(dt,now){
 const s=v104StoryState(),a=s?.survivor;if(!a?.rescued)return;
 const d=dist(a.x,a.y,player.x,player.y);if(d>72){const n=v104NavTarget(a.x,a.y,player.x,player.y),dx=n.x-a.x,dy=n.y-a.y,m=Math.hypot(dx,dy)||1,spd=d>220?150:112,nx=a.x+dx/m*spd*dt,ny=a.y+dy/m*spd*dt;if(canMove(nx,a.y,11))a.x=nx;if(canMove(a.x,ny,11))a.y=ny}
 for(const e of state.enemies){if(e.dead||dist(e.x,e.y,a.x,a.y)>e.r+20||now<(e.storyAttackAt||0))continue;e.storyAttackAt=now+850;a.hp-=Math.max(4,e.damage*.55);particles(a.x,a.y,5,'#ff7185');if(a.hp<=0){a.hp=0;finish(false,'Анна погибла. Эвакуация сорвана.');return}}
 const hp=$('survivorHp');if(hp)hp.textContent='АННА '+Math.max(0,Math.ceil(a.hp))+'/'+a.maxHp
}
const v104BaseUpdatePickups=updatePickups;
updateEnemies=function(dt,now){v104BaseUpdateEnemies(dt,now);v104MoveSurvivor(dt,now)};

function v104Ambient(now){
 const s=v104StoryState();if(!s||s.phase>=8||now<s.nextSpawn)return;const cap=s.phase>=5?13:9;if(state.enemies.length+state.telegraphs.length>=cap){s.nextSpawn=now+1000;return}
 const pr=roomAt(player.x,player.y),candidates=[0,1,2,3,4,5].filter(i=>i!==pr||rand()<.45),ri=candidates[Math.floor(rand()*candidates.length)];
 const roll=rand(),type=s.phase>=5&&roll<.15?'brute':roll<.24?'runner':roll<.39?'spitter':roll<.46?'elite':'walker';queueSpawn(type,ri,.65+rand()*.55);s.nextSpawn=now+2100+rand()*2200
}
function v104ShowChoice(){const s=v104StoryState();if(s.choiceOpen||s.choice)return;s.choiceOpen=true;state.paused=true;fireHeld=false;aim.active=false;$('storyChoice').classList.remove('hidden');v104Radio('АННА','Это источник заражения. Мы можем уничтожить его… или вынести доказательство наружу.')}
function v104ChooseSample(choice){const s=v104StoryState();s.choice=choice;s.choiceOpen=false;state.paused=false;$('storyChoice').classList.add('hidden');if(choice==='destroy'){state.score+=260;particles(v104Points.sample.x,v104Points.sample.y,42,'#9aabff');v104Phase(5,'АННА','Образец уничтожен. Теперь к лифту — вместе.',160)}else{state.score+=340;v104Phase(5,'АННА','Ты взял образец… Надеюсь, мы не совершаем ошибку. Идём к лифту.',190)}}
function v104StartBoss(){const s=v104StoryState();if(s.bossSpawned)return;s.bossSpawned=true;s.phase=6;state.roomsCleared=5;spawnEnemy('boss',390,760);queueSpawn('runner',5,.7);queueSpawn('walker',5,1.1);banner(5,'ОХОТНИК ПРОРВАЛСЯ');v104Radio('АННА','Он перекрыл лифт! Убей его, иначе мы не выйдем.')}
function updateObjective(dt,now){
 const s=v104StoryState();if(!s?.active)return;v104Ambient(now);
 if(s.phase===0&&v104Hold(v104Points.terminal,dt,1.25)){state.breakers=breakerTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,active:false,progress:0}));v104Phase(1,'СИСТЕМА','Терминал работает. Главная сеть обесточена — запусти три рубильника в генераторной.',130)}
 else if(s.phase===1){for(const b of state.breakers)if(!b.active){if(dist(player.x,player.y,b.x,b.y)<52)b.progress=Math.min(1.15,b.progress+dt);else b.progress=Math.max(0,b.progress-dt*.35);if(b.progress>=1.15){b.active=true;state.score+=75;particles(b.x,b.y,18,'#ffca68');tone(680,.16,'square',.15);v104Radio('СИСТЕМА','Рубильник '+state.breakers.filter(q=>q.active).length+' из 3 активирован.')}}if(state.breakers.length&&state.breakers.every(b=>b.active))v104Phase(2,'АННА','Питание вернулось. Двери медблока открыты. Пожалуйста, быстрее.',170)}
 else if(s.phase===2&&dist(player.x,player.y,s.survivor.x,s.survivor.y)<58){s.survivor.rescued=true;v104Phase(3,'АННА','Спасибо. Для лифта нужна карта начальника смены — она осталась в архиве.',220)}
 else if(s.phase===3&&v104Hold(v104Points.card,dt,1.1)){v104Phase(4,'АННА','Карта у нас. Но сначала решим, что делать с образцом в лаборатории.',150)}
 else if(s.phase===4&&dist(player.x,player.y,v104Points.sample.x,v104Points.sample.y)<64)v104ShowChoice();
 else if(s.phase===5&&dist(player.x,player.y,v104Points.elevator.x,v104Points.elevator.y)<72&&dist(s.survivor.x,s.survivor.y,v104Points.elevator.x,v104Points.elevator.y)<96)v104StartBoss();
 else if(s.phase===6&&s.bossSpawned&&!state.enemies.some(e=>e.type==='boss')){s.phase=7;s.extractProgress=0;state.roomsCleared=6;v104Radio('СИСТЕМА','Лифт перезапускается. Удерживайте площадку эвакуации пять секунд.')}
 else if(s.phase===7){const both=dist(player.x,player.y,v104Points.elevator.x,v104Points.elevator.y)<80&&dist(s.survivor.x,s.survivor.y,v104Points.elevator.x,v104Points.elevator.y)<105;s.extractProgress=both?Math.min(5,s.extractProgress+dt):Math.max(0,s.extractProgress-dt*.7);if(s.extractProgress>=5){s.phase=8;state.score+=s.choice==='destroy'?520:600;finish(true,s.choice==='destroy'?'Анна спасена, источник заражения уничтожен.':'Анна спасена. Образец вынесен наружу — последствия неизвестны.')}}
}
completeSector=function(){};

function v104SegmentCircleT(x1,y1,x2,y2,cx,cy,r){const dx=x2-x1,dy=y2-y1,fx=x1-cx,fy=y1-cy,a=dx*dx+dy*dy;if(a<.0001)return null;const b=2*(fx*dx+fy*dy),c=fx*fx+fy*fy-r*r,disc=b*b-4*a*c;if(disc<0)return null;const q=Math.sqrt(disc),t1=(-b-q)/(2*a),t2=(-b+q)/(2*a);if(t1>=0&&t1<=1)return t1;if(t2>=0&&t2<=1)return t2;return null}
function v104WallT(x1,y1,x2,y2){const len=Math.hypot(x2-x1,y2-y1),steps=Math.max(1,Math.ceil(len/5));for(let i=1;i<=steps;i++){const t=i/steps,x=x1+(x2-x1)*t,y=y1+(y2-y1)*t;if(!walkable(x,y)||blocked(x,y,-4))return t}return 1.01}
updateBullets=function(dt){
 for(const b of [...state.bullets]){const x1=b.x,y1=b.y,x2=x1+b.vx*dt,y2=y1+b.vy*dt;b.px=x1;b.py=y1;b.life-=dt;b.hitIds=b.hitIds||[];const wallT=v104WallT(x1,y1,x2,y2),hits=[];
  for(const pod of state.pods){if(pod.dead)continue;pod._v104id=pod._v104id||'p'+v104PodId++;if(b.hitIds.includes(pod._v104id))continue;const t=v104SegmentCircleT(x1,y1,x2,y2,pod.x,pod.y,39);if(t!==null&&t<wallT)hits.push({t,pod,id:pod._v104id})}
  for(const e of state.enemies){if(e.dead)continue;e._v104id=e._v104id||'e'+v104EnemyId++;if(b.hitIds.includes(e._v104id))continue;const t=v104SegmentCircleT(x1,y1,x2,y2,e.x,e.y,Math.max(18,e.r+10));if(t!==null&&t<wallT)hits.push({t,e,id:e._v104id})}
  hits.sort((a,c)=>a.t-c.t);let removed=false;for(const h of hits){b.hitIds.push(h.id);const hx=x1+(x2-x1)*h.t,hy=y1+(y2-y1)*h.t;if(h.pod)damagePod(h.pod,b.damage);else{const d=Math.hypot(b.vx,b.vy)||1;damageEnemy(h.e,b.damage,b.vx/d,b.vy/d)}particles(hx,hy,4,h.pod?'#aebcff':'#ff6a7d');b.pierce--;if(b.pierce<0){removed=true;break}}
  if(!removed&&wallT>1){b.x=x2;b.y=y2}else removed=true;if(removed||b.life<=0)state.bullets.splice(state.bullets.indexOf(b),1)
 }
 for(const b of [...state.enemyBullets]){b.x+=b.vx*dt;b.y+=b.vy*dt;b.life-=dt;if(dist(b.x,b.y,player.x,player.y)<player.r+6){damagePlayer(b.damage);b.life=0}if(b.life<=0||!walkable(b.x,b.y))state.enemyBullets.splice(state.enemyBullets.indexOf(b),1)}
 for(const g of [...state.grenadeObjs]){g.x+=g.vx*dt;g.y+=g.vy*dt;g.vx*=.968;g.vy*=.968;g.time-=dt;if(g.time<=0){explode(g);state.grenadeObjs.splice(state.grenadeObjs.indexOf(g),1)}}
 for(const q of [...state.shockwaves]){q.r+=q.speed*dt;q.life-=dt;if(!q.hit&&Math.abs(dist(q.x,q.y,player.x,player.y)-q.r)<18){q.hit=true;damagePlayer(q.damage)}if(q.life<=0)state.shockwaves.splice(state.shockwaves.indexOf(q),1)}
};

function v104DrawMarker(point,now,label){if(!point)return;const pulse=(Math.sin(now/170)+1)/2;ctx.save();ctx.strokeStyle=`rgba(255,210,105,${.55+pulse*.35})`;ctx.lineWidth=3;ctx.setLineDash([7,6]);ctx.beginPath();ctx.arc(point.x,point.y,30+pulse*7,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle='#ffe1a3';ctx.font='900 9px system-ui';ctx.textAlign='center';ctx.fillText(label||point.label,point.x,point.y-42);ctx.restore()}
function v104DrawSurvivor(now){const s=v104StoryState(),a=s?.survivor;if(!a)return;ctx.save();ctx.translate(a.x,a.y);ctx.shadowColor='#78d8ff';ctx.shadowBlur=12;ctx.fillStyle='#24657b';ctx.beginPath();ctx.roundRect(-10,-13,20,27,7);ctx.fill();ctx.fillStyle='#efb698';ctx.beginPath();ctx.arc(0,-15,7,0,Math.PI*2);ctx.fill();ctx.fillStyle='#a6ecff';ctx.font='900 8px system-ui';ctx.textAlign='center';ctx.fillText(a.rescued?'АННА':'SOS',0,-28);ctx.shadowBlur=0;if(a.rescued){ctx.fillStyle='#11262d';ctx.fillRect(-18,19,36,4);ctx.fillStyle='#65d8ff';ctx.fillRect(-18,19,36*Math.max(0,a.hp/a.maxHp),4)}ctx.restore()}
drawObjectives=function(now){v104BaseDrawObjectives(now);const t=v104Target();v104DrawMarker(t,now,t?.label);const s=v104StoryState();if(s?.phase===0&&s.progress>0)v104Progress(v104Points.terminal,s.progress/1.25);if(s?.phase===3&&s.progress>0)v104Progress(v104Points.card,s.progress/1.1);if(s?.phase===7)v104Progress(v104Points.elevator,s.extractProgress/5)};
function v104Progress(p,pct){ctx.strokeStyle='#75ffe8';ctx.lineWidth=5;ctx.beginPath();ctx.arc(p.x,p.y,39,-Math.PI/2,-Math.PI/2+Math.PI*2*clamp(pct,0,1));ctx.stroke()}
drawWorld=function(now){v104BaseDrawWorld(now);v104DrawSurvivor(now)};

function v104DrawMiniMap(now){const c=$('miniMap');if(!c||now-v104MapLast<100)return;v104MapLast=now;const m=c.getContext('2d'),w=c.width,h=c.height,sx=w/WORLD.w,sy=h/WORLD.h;m.clearRect(0,0,w,h);m.fillStyle='#020608e8';m.fillRect(0,0,w,h);for(let i=0;i<rooms.length;i++){const r=rooms[i];m.fillStyle=i===roomAt(player.x,player.y)?'#285b60':'#10272b';m.strokeStyle='#69e8d266';m.fillRect(r.x*sx,r.y*sy,r.w*sx,r.h*sy);m.strokeRect(r.x*sx,r.y*sy,r.w*sx,r.h*sy)}for(const c0 of corridors){m.fillStyle='#17363b';m.fillRect(c0.x*sx,c0.y*sy,c0.w*sx,c0.h*sy)}const target=v104Target();if(target){m.fillStyle='#ffd36d';m.beginPath();m.arc(target.x*sx,target.y*sy,3,0,Math.PI*2);m.fill()}const s=v104StoryState();if(s?.survivor.rescued){m.fillStyle='#6ddcff';m.beginPath();m.arc(s.survivor.x*sx,s.survivor.y*sy,2.5,0,Math.PI*2);m.fill()}m.fillStyle='#75ffe8';m.beginPath();m.arc(player.x*sx,player.y*sy,3.2,0,Math.PI*2);m.fill()}
updateHud=function(now){v104BaseHud(now);$('objective').textContent=v104Objective();const s=v104StoryState();if(s){const panel=$('radioHud');if(panel)panel.classList.toggle('faded',now-s.lastRadioAt>7000);v104DrawMiniMap(now)}if(state.activeRoom===99)$('roomName').textContent=(roomAt(player.x,player.y)>=0?rooms[roomAt(player.x,player.y)].name:'СЛУЖЕБНЫЙ КОРИДОР')};

$('destroySample')?.addEventListener('click',()=>v104ChooseSample('destroy'));
$('takeSample')?.addEventListener('click',()=>v104ChooseSample('take'));
