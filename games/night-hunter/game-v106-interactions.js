/* Reality 106: explicit interactions, character animation and subtle camera movement. */
const V106={version:'Reality 106 · Living Mission'};
let v106ActionHeld=false,v106ActionPointer=null,v106CurrentAction=null;

const v106ActionButton=$('action');
const v106ActionIcon=$('actionIcon'),v106ActionLabel=$('actionLabel'),v106ActionSub=$('actionSub');

function v106ReleaseAction(e){
 if(e&&v106ActionPointer!==null&&e.pointerId!==v106ActionPointer)return;
 v106ActionHeld=false;v106ActionPointer=null;
 v106ActionButton?.classList.remove('holding','pressed');
}
if(v106ActionButton){
 v106ActionButton.addEventListener('pointerdown',e=>{
  if(e.pointerType==='mouse'&&e.button!==0)return;
  e.preventDefault();e.stopPropagation();v106ActionPointer=e.pointerId;v106ActionHeld=true;
  v106ActionButton.classList.add('holding','pressed');v106ActionButton.setPointerCapture?.(e.pointerId);
 },{passive:false});
 v106ActionButton.addEventListener('pointerup',v106ReleaseAction,{passive:false});
 v106ActionButton.addEventListener('pointercancel',v106ReleaseAction,{passive:false});
 v106ActionButton.addEventListener('contextmenu',e=>e.preventDefault());
}
window.addEventListener('keydown',e=>{if(e.key.toLowerCase()==='e')v106ActionHeld=true});
window.addEventListener('keyup',e=>{if(e.key.toLowerCase()==='e')v106ReleaseAction()});

function v106NearestBreaker(){
 let best=null,bd=Infinity;
 for(const b of state.breakers||[]){if(b.active)continue;const d=dist(player.x,player.y,b.x,b.y);if(d<bd){best=b;bd=d}}
 return best?{point:best,distance:bd}:null;
}
function v106ActionContext(){
 const s=v104StoryState();if(!s?.active||state.finished)return null;
 let point=null,label='',sub='УДЕРЖИВАЙ',icon='✋',radius=86,need=1,progress=0;
 if(s.phase===0){point=v104Points.terminal;label='АКТИВИРОВАТЬ';sub='ТЕРМИНАЛ ОХРАНЫ';icon='◫';need=1;progress=s.progress/need}
 else if(s.phase===1){const q=v106NearestBreaker();if(!q)return null;point=q.point;label='ВКЛЮЧИТЬ';sub='РУБИЛЬНИК ПИТАНИЯ';icon='⚡';need=1.05;progress=(q.point.progress||0)/need}
 else if(s.phase===2&&!s.survivor.rescued){point=s.survivor;label='ПОМОЧЬ АННЕ';sub='ОСВОБОДИТЬ ВЫЖИВШУЮ';icon='✚';need=.35;progress=s.progress/need;radius=92}
 else if(s.phase===3){point=v104Points.card;label='ЗАБРАТЬ КАРТУ';sub='ДОСТУП К ЛИФТУ';icon='▰';need=.8;progress=s.progress/need}
 else if(s.phase===4){point=v104Points.sample;label='ОСМОТРЕТЬ';sub='ЗАРАЖЁННЫЙ ОБРАЗЕЦ';icon='◈';need=.28;progress=s.progress/need;radius=92}
 else if(s.phase===5){point=v104Points.elevator;label='ВЫЗВАТЬ ЛИФТ';sub='АННА ДОЛЖНА БЫТЬ РЯДОМ';icon='⇧';need=.4;progress=s.progress/need;radius=96}
 else if(s.phase===7){point=v104Points.elevator;label='УДЕРЖИВАТЬ';sub='ПЛОЩАДКА ЭВАКУАЦИИ';icon='⬆';need=5;progress=s.extractProgress/need;radius=92}
 else return null;
 const distance=dist(player.x,player.y,point.x,point.y);
 const companionReady=s.phase!==5&&s.phase!==7||dist(s.survivor.x,s.survivor.y,v104Points.elevator.x,v104Points.elevator.y)<112;
 return{phase:s.phase,point,label,sub,icon,radius,need,progress:clamp(progress,0,1),distance,near:distance<radius,companionReady};
}
function v106ConsumeAction(){v106ActionHeld=false;v106ActionButton?.classList.remove('holding','pressed')}

/* Story interactions no longer complete merely because the player walks over a marker. */
updateObjective=function(dt,now){
 const s=v104StoryState();if(!s?.active)return;v104Ambient(now);
 const context=v106ActionContext();v106CurrentAction=context;
 if(s.phase===0){
  const active=context?.near&&v106ActionHeld;s.progress=active?Math.min(1,s.progress+dt):Math.max(0,s.progress-dt*.7);
  if(s.progress>=1){state.breakers=breakerTemplate.map((q,k)=>({id:k,x:q.x,y:q.y,active:false,progress:0}));v106ConsumeAction();v104Phase(1,'СИСТЕМА','Терминал работает. Главная сеть обесточена — запусти три рубильника в генераторной.',130)}
 }else if(s.phase===1){
  for(const b of state.breakers)if(!b.active){const near=dist(player.x,player.y,b.x,b.y)<86&&context?.point===b&&v106ActionHeld;b.progress=near?Math.min(1.05,b.progress+dt):Math.max(0,b.progress-dt*.5);if(b.progress>=1.05){b.active=true;v106ConsumeAction();state.score+=75;particles(b.x,b.y,18,'#ffca68');tone(680,.16,'square',.15);v104Radio('СИСТЕМА','Рубильник '+state.breakers.filter(q=>q.active).length+' из 3 активирован.')}}
  if(state.breakers.length&&state.breakers.every(b=>b.active))v104Phase(2,'АННА','Питание вернулось. Двери медблока открыты. Пожалуйста, быстрее.',170)
 }else if(s.phase===2){
  const active=context?.near&&v106ActionHeld;s.progress=active?Math.min(.35,s.progress+dt):Math.max(0,s.progress-dt*.8);
  if(s.progress>=.35){s.survivor.rescued=true;v106ConsumeAction();v104Phase(3,'АННА','Спасибо. Для лифта нужна карта начальника смены — она осталась в архиве.',220)}
 }else if(s.phase===3){
  const active=context?.near&&v106ActionHeld;s.progress=active?Math.min(.8,s.progress+dt):Math.max(0,s.progress-dt*.7);
  if(s.progress>=.8){v106ConsumeAction();v104Phase(4,'АННА','Карта у нас. Но сначала решим, что делать с образцом в лаборатории.',150)}
 }else if(s.phase===4){
  const active=context?.near&&v106ActionHeld;s.progress=active?Math.min(.28,s.progress+dt):Math.max(0,s.progress-dt*1.1);
  if(s.progress>=.28){v106ConsumeAction();v104ShowChoice()}
 }else if(s.phase===5){
  const ready=context?.near&&context.companionReady&&v106ActionHeld;s.progress=ready?Math.min(.4,s.progress+dt):Math.max(0,s.progress-dt*.8);
  if(s.progress>=.4){v106ConsumeAction();v104StartBoss()}
 }else if(s.phase===6&&s.bossSpawned&&!state.enemies.some(e=>e.type==='boss')){
  s.phase=7;s.extractProgress=0;state.roomsCleared=6;v104Radio('СИСТЕМА','Лифт перезапускается. Встаньте с Анной на площадку и удерживайте кнопку эвакуации.')
 }else if(s.phase===7){
  const both=context?.near&&context.companionReady,active=both&&v106ActionHeld;
  s.extractProgress=active?Math.min(5,s.extractProgress+dt):Math.max(0,s.extractProgress-dt*.75);
  if(s.extractProgress>=5){v106ConsumeAction();s.phase=8;state.score+=s.choice==='destroy'?520:600;finish(true,s.choice==='destroy'?'Анна спасена, источник заражения уничтожен.':'Анна спасена. Образец вынесен наружу — последствия неизвестны.')}
 }
};

function v106UpdateActionButton(){
 if(!v106ActionButton)return;const c=v106ActionContext();v106CurrentAction=c;
 const show=!!c&&c.distance<c.radius+24&&c.phase!==6;
 v106ActionButton.classList.toggle('hidden',!show);
 if(!show){v106ReleaseAction();return}
 if(v106ActionIcon)v106ActionIcon.textContent=c.icon;
 if(v106ActionLabel)v106ActionLabel.textContent=c.label;
 if(v106ActionSub)v106ActionSub.textContent=!c.companionReady?'ДОЖДИСЬ АННУ':c.sub;
 v106ActionButton.disabled=!c.near||!c.companionReady;
 v106ActionButton.classList.toggle('ready',c.near&&c.companionReady);
 v106ActionButton.style.setProperty('--action-angle',c.progress.toFixed(3)+'turn');
}

const v106HudBase=updateHud;
updateHud=function(now){
 v106HudBase(now);v106UpdateActionButton();
 const target=v104Target(),el=$('direction');
 if(target&&el){const dx=target.x-player.x,dy=target.y-player.y,d=Math.hypot(dx,dy);if(d>125){el.classList.remove('hidden');el.style.setProperty('--angle',Math.atan2(dy,dx)+'rad');const b=el.querySelector('b');if(b)b.textContent=target.label||'ЦЕЛЬ';const sm=$('directionDistance');if(sm)sm.textContent=Math.max(1,Math.round(d/10))+' м'}else el.classList.add('hidden')}
};

/* Clear in-world interaction feedback. */
const v106ObjectivesBase=drawObjectives;
drawObjectives=function(now){
 v106ObjectivesBase(now);const c=v106ActionContext();if(!c)return;
 const pulse=(Math.sin(now/145)+1)/2;ctx.save();ctx.translate(c.point.x,c.point.y);
 if(c.distance<c.radius+40){ctx.strokeStyle=c.near?'#8ffff0':'#ffd36d88';ctx.lineWidth=2.5;ctx.setLineDash([5,5]);ctx.beginPath();ctx.arc(0,0,34+pulse*4,0,Math.PI*2);ctx.stroke();ctx.setLineDash([])}
 if(c.near){ctx.fillStyle='rgba(3,16,19,.94)';ctx.strokeStyle='#8ffff0aa';ctx.lineWidth=1;ctx.beginPath();ctx.roundRect(-43,36,86,19,9);ctx.fill();ctx.stroke();ctx.fillStyle='#cafff7';ctx.font='900 7px system-ui';ctx.textAlign='center';ctx.fillText('✋ НАЖМИ ДЕЙСТВИЕ',0,49)}ctx.restore()
};

/* More readable, animated operative: legs follow movement while torso and weapon follow aim. */
function v106DrawOperative(now,alpha=1,offset=0){
 const moveMag=Math.min(1,Math.hypot(joy.x,joy.y)),moving=moveMag>.08,walk=Math.sin(player.walk),step=walk*4.2*moveMag,breath=Math.sin(now/430)*.75;
 const aimA=aimAngle(),moveA=moving?Math.atan2(joy.y,joy.x):aimA,hitFlash=now<player.invulnUntil&&Math.floor(now/65)%2===0;
 ctx.save();ctx.globalAlpha=alpha;ctx.translate(player.x-player.dashX*offset,player.y-player.dashY*offset);
 ctx.fillStyle='#0009';ctx.beginPath();ctx.ellipse(2,10,21,13,aimA,0,Math.PI*2);ctx.fill();
 ctx.save();ctx.rotate(moveA);ctx.strokeStyle=hitFlash?'#ffb7c1':'#172328';ctx.lineWidth=8;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-5,8);ctx.lineTo(-8-step,25);ctx.moveTo(6,8);ctx.lineTo(9+step,25);ctx.stroke();ctx.fillStyle='#080d0f';ctx.beginPath();ctx.ellipse(-8-step,26,7,4,0,0,Math.PI*2);ctx.ellipse(9+step,26,7,4,0,0,Math.PI*2);ctx.fill();ctx.restore();
 ctx.save();ctx.rotate(aimA);const reloadTilt=player.reloading?.42:0,kick=Math.min(5,Math.abs(player.recoil)*.09);ctx.rotate(reloadTilt);
 ctx.shadowColor=hitFlash?'#ff3758':'#54ffe4';ctx.shadowBlur=hitFlash?18:10;ctx.fillStyle=hitFlash?'#ff9aab':'#16383c';ctx.beginPath();ctx.roundRect(-17,-17+breath,34,36,10);ctx.fill();ctx.shadowBlur=0;
 ctx.fillStyle='#091316';ctx.beginPath();ctx.roundRect(-20,-12+breath,10,27,5);ctx.fill();ctx.strokeStyle='#45666b';ctx.lineWidth=2;ctx.stroke();
 ctx.fillStyle='#2f8f81';ctx.beginPath();ctx.roundRect(-12,-14+breath,24,27,7);ctx.fill();ctx.fillStyle='#8bfff02b';ctx.fillRect(-8,-9+breath,16,4);
 ctx.strokeStyle=hitFlash?'#ffd3d9':'#e9aa86';ctx.lineWidth=7;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(4,-7+breath);ctx.lineTo(20-kick,-3+breath);ctx.moveTo(3,5+breath);ctx.lineTo(20-kick,4+breath);ctx.stroke();
 ctx.fillStyle='#dce8e6';const weaponLen=player.weapon==='shotgun'?49:player.weapon==='smg'?42:34;ctx.beginPath();ctx.roundRect(17-kick,-6+breath,weaponLen,10,3);ctx.fill();ctx.fillStyle=player.weapon==='shotgun'?'#63584c':'#65767a';ctx.fillRect(37-kick,-4+breath,weaponLen-19,7);if(player.weapon==='smg'){ctx.fillStyle='#1c292c';ctx.fillRect(31-kick,5+breath,8,13)}
 ctx.fillStyle='#eeb08d';ctx.beginPath();ctx.arc(1,-21+breath,10,0,Math.PI*2);ctx.fill();ctx.fillStyle='#16272b';ctx.beginPath();ctx.arc(1,-23+breath,10,Math.PI,Math.PI*2);ctx.fill();ctx.fillStyle='#76fff0';ctx.fillRect(5,-24+breath,7,3);
 if(player.reloading){const rp=clamp(1-(player.reloadEnd-now)/(player.weapon==='shotgun'?1450:1100),0,1);ctx.fillStyle='#ffd06e';ctx.globalAlpha*=.75;ctx.fillRect(30,9+rp*9,6,11)}
 if(player.muzzle>0){ctx.shadowColor='#ffbd4b';ctx.shadowBlur=30;ctx.fillStyle='#fff3b0';ctx.beginPath();ctx.moveTo(18+weaponLen-kick,0);ctx.lineTo(34+weaponLen-kick,-10);ctx.lineTo(30+weaponLen-kick,0);ctx.lineTo(34+weaponLen-kick,10);ctx.closePath();ctx.fill()}
 ctx.restore();ctx.restore();
}
drawPlayer=function(now){if(now<player.dashUntil)for(let i=4;i>=1;i--)v106DrawOperative(now-i*22,.055*i,i*7);v106DrawOperative(now,1,0)};

/* Existing silhouettes gain gait, impact and type-specific motion without replacing their hitboxes. */
const v106EnemyBase=drawEnemy;
drawEnemy=function(e,now){
 const freq=e.type==='runner'?.02:e.type==='brute'?.006:e.type==='boss'?.004:.011,phase=now*freq+e.x*.013+e.y*.007;
 const squash=e.hit>0?-.12:Math.sin(phase)*((e.type==='runner')?.07:.035),tilt=Math.sin(phase*.65)*(e.type==='runner'?.11:.045);
 ctx.save();ctx.translate(e.x,e.y);ctx.rotate(tilt);ctx.scale(1+squash,1-squash*.7);ctx.translate(-e.x,-e.y);v106EnemyBase(e,now);ctx.restore();
 ctx.save();ctx.translate(e.x,e.y);
 if(e.type==='spitter'){const p=(Math.sin(now/105)+1)/2;ctx.strokeStyle=`rgba(124,255,103,${.22+p*.35})`;ctx.lineWidth=3;ctx.beginPath();ctx.arc(0,-10,10+p*4,0,Math.PI*2);ctx.stroke()}
 if(e.type==='brute'||e.type==='boss'){const stomp=(Math.sin(phase)+1)/2;if(stomp>.93){ctx.strokeStyle='rgba(255,92,112,.24)';ctx.lineWidth=4;ctx.beginPath();ctx.arc(0,15,24+stomp*12,0,Math.PI*2);ctx.stroke()}}
 if(e.type==='runner'){ctx.strokeStyle='rgba(255,76,111,.18)';ctx.lineWidth=3;for(let i=1;i<4;i++){ctx.beginPath();ctx.moveTo(-i*10,5+i*2);ctx.lineTo(-i*19,5+i*2);ctx.stroke()}}
 ctx.restore();
};

const v106CorpseBase=drawCorpse;
drawCorpse=function(c){ctx.save();ctx.globalAlpha=clamp(c.life/2,0,.42);ctx.fillStyle='#33081277';ctx.beginPath();ctx.ellipse(c.x,c.y+5,c.r*1.6,c.r*.75,c.angle||0,0,Math.PI*2);ctx.fill();ctx.restore();v106CorpseBase(c)};

/* Very light camera bob: noticeable as motion, small enough not to disturb aiming. */
render=function(now){
 const maxX=Math.max(0,WORLD.w-vw),maxY=Math.max(0,WORLD.h-vh),moveMag=Math.min(1,Math.hypot(joy.x,joy.y));
 const look=fireHeld?7:11,tx=clamp(player.x-vw/2+player.facingX*look,0,maxX),ty=clamp(player.y-vh/2+player.facingY*look,0,maxY);camera.x+=(tx-camera.x)*.13;camera.y+=(ty-camera.y)*.13;
 const walking=moveMag>.08&&now>=player.dashUntil,bobDamp=fireHeld?.35:1,bx=walking?Math.sin(now*.012)*1.25*moveMag*bobDamp:0,by=walking?Math.cos(now*.024)*1.1*moveMag*bobDamp:0;
 const sx=(rand()-.5)*state.shake+bx,sy=(rand()-.5)*state.shake+by;state.shake*=.83;state.flash=Math.max(0,state.flash-.022);player.muzzle=Math.max(0,player.muzzle-.035);player.recoil*=.72;
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,vw,vh);ctx.save();ctx.translate(-camera.x+sx,-camera.y+sy);drawWorld(now);ctx.restore();drawLight(now);
 if(state.flash>0){ctx.fillStyle=`rgba(255,235,180,${state.flash})`;ctx.fillRect(0,0,vw,vh)}
};

document.addEventListener('visibilitychange',()=>{if(document.hidden)v106ReleaseAction()});
