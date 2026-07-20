(()=>{'use strict';
const tg=window.Telegram?.WebApp;tg?.ready();tg?.expand();tg?.setHeaderColor?.('#020608');tg?.setBackgroundColor?.('#020608');
const $=id=>document.getElementById(id),params=new URLSearchParams(location.search),chatId=params.get('chat_id')||'',headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
const canvas=$('game'),ctx=canvas.getContext('2d'),light=document.createElement('canvas'),lctx=light.getContext('2d');let vw=1,vh=1,dpr=1,raf=0,audio=null;
const WORLD={w:1670,h:900};
const rooms=[
{id:'security',name:'ПОСТ ОХРАНЫ',x:50,y:50,w:450,h:340,color:'#12343a',accent:'#69f7e1'},
{id:'lab',name:'ЛАБОРАТОРИЯ',x:610,y:50,w:450,h:340,color:'#20284b',accent:'#93a9ff'},
{id:'archive',name:'АРХИВ',x:1170,y:50,w:450,h:340,color:'#3a301c',accent:'#e2bd68'},
{id:'med',name:'МЕДИЦИНСКИЙ БЛОК',x:1170,y:510,w:450,h:340,color:'#173d35',accent:'#a8ffdf'},
{id:'generator',name:'ГЕНЕРАТОРНАЯ',x:610,y:510,w:450,h:340,color:'#49331b',accent:'#ffb75d'},
{id:'elevator',name:'ЛИФТОВОЙ ХОЛЛ',x:50,y:510,w:450,h:340,color:'#26383e',accent:'#aed7dc'}];
const corridors=[{x:500,y:170,w:110,h:100},{x:1060,y:170,w:110,h:100},{x:1345,y:390,w:100,h:120},{x:1060,y:630,w:110,h:100},{x:500,y:630,w:110,h:100}];
const doors=[{x:547,y:170,w:16,h:100,o:'v'},{x:1107,y:170,w:16,h:100,o:'v'},{x:1345,y:442,w:100,h:16,o:'h'},{x:1107,y:630,w:16,h:100,o:'v'},{x:547,y:630,w:16,h:100,o:'v'}];
const waveTypes=[['walker','walker','walker','walker','walker','runner','runner'],['walker','walker','runner','runner','runner','spitter','spitter','walker','walker'],['walker','walker','walker','runner','runner','spitter','spitter','brute','walker','runner','walker'],['runner','runner','runner','walker','walker','spitter','spitter','spitter','brute','walker','runner','walker','walker'],['walker','walker','runner','runner','runner','spitter','spitter','brute','brute','walker','walker','runner','spitter','walker','runner','walker'],['boss','walker','walker','runner','runner','spitter','spitter','brute','walker','runner']];
const enemyDefs={walker:{hp:42,speed:50,r:14,damage:10,score:20,color:'#28393b'},runner:{hp:25,speed:88,r:11,damage:8,score:28,color:'#3a2430'},spitter:{hp:34,speed:42,r:13,damage:7,score:36,color:'#283827'},brute:{hp:115,speed:34,r:21,damage:18,score:62,color:'#34272a'},boss:{hp:620,speed:38,r:32,damage:24,score:500,color:'#240d13'}};
const player={x:260,y:230,r:14,facingX:1,facingY:0,hp:100,maxHp:100,speed:150,damage:24,fireDelay:255,lastShot:0,mag:12,magSize:12,reserve:72,reloading:false,reloadEnd:0,pierce:0,grenades:2,vamp:0,invuln:0};
const state={running:false,finished:false,paused:false,demo:false,sessionId:null,seed:1,time:180,last:0,score:0,kills:0,shots:0,hits:0,activeRoom:0,roomsCleared:0,unlockedThrough:0,spawnQueue:[],nextSpawn:0,enemies:[],bullets:[],enemyBullets:[],pickups:[],grenadeObjs:[],particles:[],messageUntil:0,shake:0,flash:0};
const joy={id:null,x:0,y:0},keys=new Set(),camera={x:0,y:0};let fireHeld=false;
function rand(){state.seed=(state.seed*1664525+1013904223)>>>0;return state.seed/4294967296}const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),dist=(a,b,c,d)=>Math.hypot(c-a,d-b);
function fmtTime(v){v=Math.max(0,Math.ceil(v));return String(Math.floor(v/60)).padStart(2,'0')+':'+String(v%60).padStart(2,'0')}
async function api(path,body={}){const r=await fetch('/games/api/'+path,{method:'POST',headers,body:JSON.stringify({...body,chat_id:chatId})});const d=await r.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));if(!r.ok||!d.ok)throw new Error(d.reason||'Ошибка игрового сервера.');return d}
function goGames(){location.href='/games/?'+new URLSearchParams({...Object.fromEntries(params),chat_id:chatId}).toString()}
function vibrate(t='light'){try{tg?.HapticFeedback?.impactOccurred?.(t)}catch(_){}}
function initAudio(){if(audio)return;tr