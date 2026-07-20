(()=>{
'use strict';
const tg=window.Telegram?.WebApp;
tg?.ready();tg?.expand();tg?.setHeaderColor?.('#020608');tg?.setBackgroundColor?.('#020608');
const $=id=>document.getElementById(id);
const params=new URLSearchParams(location.search),chatId=params.get('chat_id')||'';
const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
const canvas=$('game'),ctx=canvas.getContext('2d'),light=document.createElement('canvas'),lctx=light.getContext('2d');
let vw=1,vh=1,dpr=1,raf=0,audio=null;

const WORLD={w:1710,h:990};
const rooms=[
{id:'security',name:'ПОСТ ОХРАНЫ',x:45,y:45,w:470,h:350,color:'#12343a',accent:'#69f7e1',objective:'ЗАЧИСТКА'},
{id:'lab',name:'ЛАБОРАТОРИЯ',x:620,y:45,w:470,h:350,color:'#20284b',accent:'#93a9ff',objective:'УНИЧТОЖЬ КАПСУЛЫ'},
{id:'archive',name:'АРХИВ',x:1195,y:45,w:470,h:350,color:'#3a301c',accent:'#e2bd68',objective:'ПЕРЕЖИВИ РОЙ'},
{id:'med',name:'МЕДИЦИНСКИЙ БЛОК',x:1195,y:595,w:470,h:350,color:'#173d35',accent:'#a8ffdf',objective:'УДЕРЖИВАЙ ТОЧКУ'},
{id:'generator',name:'ГЕНЕРАТОРНАЯ',x:620,y:595,w:470,h:350,color:'#49331b',accent:'#ffb75d',objective:'ВКЛЮЧИ РУБИЛЬНИКИ'},
{id:'elevator',name:'ЛИФТОВОЙ ХОЛЛ',x:45,y:595,w:470,h:350,color:'#26383e',accent:'#aed7dc',objective:'УНИЧТОЖЬ БОССА'}
];
const corridors=[
{x:515,y:165,w:105,h:110,dir:'h',label:'A-01'},
{x:1090,y:165,w:105,h:110,dir:'h',label:'A-02'},
{x:1365,y:395,w:130,h:200,dir:'v',label:'B-03'},
{x:1090,y:715,w:105,h:110,dir:'h',label:'B-02'},
{x:515,y:715,w:105,h:110,dir:'h',label:'B-01'}
];
const doors=[
{x:558,y:165,w:18,h:110,o:'v',after:0},
{x:1133,y:165,w:18,h:110,o:'v',after:1},
{x:1365,y:485,w:130,h:18,o:'h',after:2},
{x:1133,y:715,w:18,h:110,o:'v',after:3},
{x:558,y:715,w:18,h:110,o:'v',after:4}
];
const solids=[
{x:85,y:96,w:350,h:38},{x:95,y:305,w:250,h:32},
{x:720,y:120,w:270,h:150},{x:675,y:310,w:115,h:28},{x:920,y:310,w:115,h:28},
{x:1240,y:100,w:55,h:230},{x:1345,y:100,w:55,h:230},{x:1450,y:100,w:55,h:230},{x:1555,y:100,w:55,h:230},
{x:1255,y:665,w:250,h:58},{x:1255,y:840,w:250,h:58},
{x:735,y:690,w:245,h:135},
{x:115,y:690,w:315,h:135}
];
const sectorCenters=rooms.map(r=>({x:r.x+r.w/2,y:r.y+r.h/2}));
const podTemplate=[{x:755,y:155},{x:855,y:155},{x:955,y:155}];
const breakerTemplate=[{x:720,y:690},{x:855,y:870},{x:990,y:690}];
const defensePoint={x:1430,y:770,r:112};

const weaponDefs={
pistol:{key:'pistol',name:'ПИСТОЛЕТ',icon:'🔫',damage:29,delay:235,mag:12,reserve:84,pellets:1,spread:.018,speed:760,color:'#fff1b0',recoil:2.8},
smg:{key:'smg',name:'ПИСТОЛЕТ-ПУЛЕМЁТ',icon:'▰',damage:13,delay:82,mag:30,reserve:180,pellets:1,spread:.075,speed:790,color:'#baffef',recoil:1.7},
shotgun:{key:'shotgun',name:'ДРОБОВИК',icon:'▱',damage:15,delay:610,mag:6,reserve:48,pellets:7,spread:.28,speed:680,color:'#ffd08a',recoil:5.6}
};
const enemyDefs={
walker:{hp:48,speed:48,r:15,damage:10,score:22,color:'#26383a'},
runner:{hp:29,speed:92,r:12,damage:8,score:30,color:'#3b2130'},
spitter:{hp:38,speed:39,r:14,damage:7,score:39,color:'#263b27'},
brute:{hp:135,speed:32,r:23,damage:19,score:68,color:'#39262a'},
elite:{hp:92,speed:58,r:17,damage:15,score:95,color:'#342b45'},
boss:{hp:920,speed:34,r:38,damage:25,score:650,color:'#21090f'}
};
const waveSets={
security:['walker','walker','walker','walker','runner','runner','walker','spitter'],
lab:['walker','runner','runner','spitter','walker','brute'],
archive:['runner','runner','walker','runner','spitter','runner','walker','elite'],
med:['walker','walker','runner','spitter','walker','brute','runner'],
generator:['walker','runner','spitter','brute','walker','elite','runner','spitter'],
boss:['boss','walker','runner','spitter','brute']
};

const player={
x:260,y:225,r:14,facingX:1,facingY:0,hp:100,maxHp:100,speed:155,weapon:'pistol',
mag:12,reserve:84,reloading:false,reloadEnd:0,lastShot:0,damageBonus:0,fireRateBonus:0,pierce:0,grenades:2,
vamp:0,invulnUntil:0,dashUntil:0,dashReadyAt:0,dashX:1,dashY:0,muzzle:0,recoil:0,walk:0
};
const state={
running:false,finished:false,paused:false,demo:false,sessionId:null,seed:1,time:240,last:0,score:0,kills:0,shots:0,hits:0,
roomsCleared:0,activeRoom:0,unlockedThrough:0,spawnQueue:[],telegraphs:[],enemies:[],bullets:[],enemyBullets:[],grenadeObjs:[],
pickups:[],particles:[],casings:[],smoke:[],corpses:[],floaters:[],messageUntil:0,shake:0,flash:0,combo:0,comboUntil:0,
sectorTime:0,sectorStartedAt:0,pods:[],breakers:[],defenseProgress:0,defenseHp:100,nextAmbientSpawn:0,bossPhase:1,
chargeTelegraph:null,shockwaves:[],turret:null,shieldUntil:0
};
const joy={id:null,x:0,y:0},aim={id:null,x:1,y:0,active:false},keys=new Set(),camera={x:0,y:0};
let fireHeld=false;

function rand(){state.seed=(state.seed*1664525+1013904223)>>>0;return state.seed/4294967296}
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const dist=(a,b,c,d)=>Math.hypot(c-a,d-b);
function fmtTime(v){v=Math.max(0,Math.ceil(v));return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0')}
async function api(path,body={}){const r=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});const d=await r.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));if(!r.ok||!d.ok)throw new Error(d.reason||'Ошибка игрового сервера.');return d}
function goGames(){location.href='/games/?'+new URLSearchParams({...Object.fromEntries(params),chat_id:chatId}).toString()}
function vibrate(t='light'){try{tg?.HapticFeedback?.impactOccurred?.(t)}catch(_){}}
function initAudio(){if(audio)return;try{const ac=new(window.AudioContext||window.webkitAudioContext)(),master=ac.createGain();master.gain.value=.12;master.connect(ac.destination);audio={ac,master}}catch(_){}}
function tone(f=120,d=.08,type='square',vol=.12){if(!audio)return;const o=audio.ac.createOscillator(),g=audio.ac.createGain();o.type=type;o.frequency.value=f;g.gain.setValueAtTime(vol,audio.ac.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.ac.currentTime+d);o.connect(g).connect(audio.master);o.start();o.stop(audio.ac.currentTime+d)}

function resize(){const r=canvas.getBoundingClientRect();vw=Math.max(1,r.width);vh=Math.max(1,r.height);dpr=Math.min(2,devicePixelRatio||1);canvas.width=Math.round(vw*dpr);canvas.height=Math.round(vh*dpr);light.width=canvas.width;light.height=canvas.height;ctx.setTransform(dpr,0,0,dpr,0,0);lctx.setTransform(dpr,0,0,dpr,0,0)}
function inside(r,x,y,p=0){return x>=r.x-p&&x<=r.x+r.w+p&&y>=r.y-p&&y<=r.y+r.h+p}
function walkable(x,y){return rooms.some(r=>inside(r,x,y))||corridors.some(r=>inside(r,x,y))}
function doorClosed(d){return state.roomsCleared<=d.after}
function blocked(x,y,p=0){return solids.some(s=>inside(s,x,y,p))||doors.some(d=>doorClosed(d)&&inside(d,x,y,p))}
