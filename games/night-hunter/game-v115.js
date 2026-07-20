(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
try{
  const machineSources={
    cncBlue:'/games/night-hunter/assets/machine-cnc-blue-v114.svg?v=115',
    cncGreen:'/games/night-hunter/assets/machine-cnc-green-v114.svg?v=115',
    cncRed:'/games/night-hunter/assets/machine-cnc-red-v114.svg?v=115',
    laser:'/games/night-hunter/assets/machine-laser-v114.svg?v=115',
    press:'/games/night-hunter/assets/machine-press-v114.svg?v=115',
    zero:'/games/night-hunter/assets/machine-zero-v114.svg?v=115'
  };
  const machineEntries=await Promise.all(Object.entries(machineSources).map(([key,url])=>new Promise(resolve=>{
    const image=new Image();
    image.decoding='async';
    image.onload=()=>resolve([key,image]);
    image.onerror=()=>resolve([key,null]);
    image.src=url;
  })));
  window.__NH_MACHINE_SPRITES=Object.fromEntries(machineEntries.filter(([,image])=>image));

  const response=await fetch('/games/night-hunter/game-v110.js?v=115',{cache:'no-store'});
  if(!response.ok)throw new Error('не загружена стабильная версия игры');
  let source=await response.text();

  const directReplacements=[
    ['АО «ОРФЕЙ-МЕХАНИКА»','АО «ALIVSPORT»'],
    ['ОРФЕЙ-МЕХАНИКА','ALIVSPORT'],
    ['ОРФЕЙ','ALIVSPORT'],
    ['И. ИВЧЕНКОВ','ИВЧ'],
    ['И. Ивченков','Ивч'],
    ['ИВЧЕНКОВ','ИВЧ'],
    ['Ивченков','Ивч']
  ];
  for(const [from,to] of directReplacements)source=source.split(from).join(to);

  const enginePatch=`let source=engine;
  const v115Branding=[
    ['АО «ОРФЕЙ-МЕХАНИКА»','АО «ALIVSPORT»'],
    ['ОРФЕЙ-МЕХАНИКА','ALIVSPORT'],
    ['ОРФЕЙ','ALIVSPORT'],
    ['И. ИВЧЕНКОВ','ИВЧ'],
    ['И. Ивченков','Ивч'],
    ['ИВЧЕНКОВ','ИВЧ'],
    ['Ивченков','Ивч']
  ];
  for(const [from,to] of v115Branding)source=source.split(from).join(to);
  source=source.replace("const FACTORY={w:1800,h:1000};","const FACTORY={w:2100,h:1200};");
  source=source.replace("if(x<35||x>1765||y<35||y>965)return false;","if(x<35||x>2065||y<35||y>1165)return false;");`;
  if(!source.includes('let source=engine;'))throw new Error('не найдена точка подготовки движка');
  source=source.replace('let source=engine;',enginePatch);

  const machineAnchor="function v110Machine(x,y,w,h,label,active,now,accent='#5f7b7c'){";
  const machineHelper="function v114MachineSprite(key,x,y,w,h,label,active,now,accent){\n const image=window.__NH_MACHINE_SPRITES&&window.__NH_MACHINE_SPRITES[key];\n if(!image||!image.complete||!image.naturalWidth){v110Machine(x,y,w,h,label,active,now,accent);return}\n ctx.save();\n ctx.shadowColor='rgba(0,0,0,.58)';ctx.shadowBlur=20;ctx.shadowOffsetY=11;\n ctx.drawImage(image,x,y,w,h);ctx.shadowBlur=0;ctx.shadowOffsetY=0;\n if(active){\n  const pulse=(Math.sin(now/145)+1)/2;\n  ctx.fillStyle='rgba(255,186,73,'+(.07+pulse*.13)+')';ctx.beginPath();ctx.roundRect(x-5,y-5,w+10,h+10,16);ctx.fill();\n  ctx.strokeStyle='rgba(255,202,93,'+(.52+pulse*.43)+')';ctx.lineWidth=3;ctx.beginPath();ctx.roundRect(x-4,y-4,w+8,h+8,16);ctx.stroke();\n  ctx.shadowColor='#ffc45d';ctx.shadowBlur=18;ctx.fillStyle='#ffd36f';ctx.beginPath();ctx.arc(x+w-24,y+25,6+pulse*2,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;\n }\n ctx.fillStyle='#e4eee9';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,.9)';ctx.shadowBlur=5;ctx.fillText(label,x+w/2,y+h-12);ctx.restore()\n}\n";
  if(!source.includes(machineAnchor))throw new Error('не найдена функция отрисовки станков');
  source=source.replace(machineAnchor,machineHelper+machineAnchor);

  const machineReplacements=[
    ["v110Machine(480,105,260,250,'СТАНОК №3',false,now)","v114MachineSprite('cncBlue',480,105,260,250,'СТАНОК №3',false,now)"],
    ["v110Machine(800,105,260,250,'СТАНОК №4',state.phase===2,now)","v114MachineSprite('cncGreen',800,105,260,250,'СТАНОК №4',state.phase===2,now)"],
    ["v110Machine(1120,105,260,250,'СТАНОК №5',state.phase>=7&&Math.floor(now/550)%2===0,now)","v114MachineSprite('cncRed',1120,105,260,250,'СТАНОК №5',state.phase>=7&&Math.floor(now/550)%2===0,now)"],
    ["v110Machine(465,520,340,200,'ЛАЗЕРНЫЙ УЧАСТОК',state.phase>=4,now,'#3b4749')","v114MachineSprite('laser',465,520,340,200,'ЛАЗЕРНЫЙ УЧАСТОК',state.phase>=4,now,'#3b4749')"],
    ["v110Machine(855,515,275,205,'ГИБОЧНЫЙ ПРЕСС',state.phase>=5&&Math.floor(now/420)%2===0,now,'#47463d')","v114MachineSprite('press',855,515,275,205,'ГИБОЧНЫЙ ПРЕСС',state.phase>=5&&Math.floor(now/420)%2===0,now,'#47463d')"],
    ["v110Machine(1540,95,200,290,'СТАНОК №0',state.phase>=9,now,'#201317')","v114MachineSprite('zero',1540,95,200,290,'СТАНОК №0',state.phase>=9,now,'#201317')"]
  ];
  for(const [from,to] of machineReplacements){
    if(!source.includes(from))throw new Error('не найдена позиция станка: '+from);
    source=source.replace(from,to);
  }

  const outsideTail="  drawPlayer(now)\n }`);\n  swap('function machine('";
  if(!source.includes(outsideTail))throw new Error('не найдена точка детализации улицы');
  source=source.replace(outsideTail,"  v115StreetLayer(now);\n  drawPlayer(now)\n }`);\n  swap('function machine('");

  const factoryTail="  drawPlayer(now)\n }`);\n  swap('function drawFlashlight(){'";
  if(!source.includes(factoryTail))throw new Error('не найдена точка детализации цеха');
  source=source.replace(factoryTail,"  v115FactoryLayer(now);\n  drawPlayer(now)\n }`);\n  swap('function drawFlashlight(){'");

  const reality115Setup=String.raw`
 const v115Lore={
  rules:{title:'Правила, которых нет в официальной инструкции',kind:'ЛИСТ ИЗ ПАПКИ 047',body:'1. После 23:00 не называй своё имя в пустом цехе.\n2. Если станок работает без оператора — сначала посмотри в выключенный монитор.\n3. Не отвечай на внутренний номер 047 после третьего звонка.\n4. Услышишь три удара пресса — погаси фонарь и не двигайся.\n5. Если утренняя смена выглядит как ты, журнал не подписывай.'},
  operator:{title:'Я оставляю это себе в следующую ночь',kind:'ЗАПИСКА В ШКАФЧИКЕ МАСТЕРА',body:'Камеры не показывают прошлое. Они показывают ту версию смены, которая случится, если ты снова всё починишь.\n\nФигура у поста не входит через проходную. Она появляется после второй подписи.\n\nНе заканчивай ремонт станка №0. Он ремонтирует не себя.'},
  maintenance:{title:'Наряд №047: исполнитель прибыл раньше себя',kind:'ТЕХНИЧЕСКИЙ ДОКУМЕНТ',body:'Дата: сегодня.\nВремя завершения: 05:55.\nИсполнитель: ИВЧ.\n\nРаботы выполнены на станке №0. Подпись совпадает с твоей, но чернила высохли много лет назад.\n\nВнизу дописано: «Не буди того, кто ждёт окончания смены».'},
  photo:{title:'Ночная бригада, которой не существовало',kind:'АРХИВНАЯ ФОТОГРАФИЯ',body:'На обороте: «Смена №12. Все сотрудники покинули цех».\n\nНа снимке шесть человек. В журнале указано пять. Шестой стоит рядом со станком №0 и смотрит прямо в объектив.\n\nУ него твоё лицо, но на форме написано другое имя.'}
 };
 for(const id of Object.keys(v115Lore)){if(noteDefs[id])Object.assign(noteDefs[id],v115Lore[id])}
 if(!noteDefs.radioLog){
  const radioLog={id:'radioLog',x:1880,y:365,title:'Расшифровка вызова 047',kind:'ЗАПИСЬ СЛУЖЕБНОЙ РАЦИИ',body:'02:17: «Пост, ответьте. Я всё ещё внутри».\n02:18: «Не включайте свет в старом коридоре».\n02:19: голос оператора повторяет твою фразу за четыре секунды до того, как ты её произносишь.\n02:20: слышно, как кто-то ставит подпись.'};
  optionalNotes.push(radioLog);noteDefs.radioLog=radioLog;
 }
 if(!noteDefs.shiftMap){
  const shiftMap={id:'shiftMap',x:1760,y:1080,title:'План цеха с лишним помещением',kind:'СХЕМА ЭВАКУАЦИИ',body:'На официальном плане нет сектора 0. На этом листе он нарисован поверх комнаты отдыха.\n\nКрасная линия ведёт от станка №0 к посту дежурного, затем к проходной. Рядом написано: «Маршрут передачи оператора».\n\nПоследняя стрелка уходит за край бумаги.'};
  optionalNotes.push(shiftMap);noteDefs.shiftMap=shiftMap;
 }
 solids.push({x:1840,y:115,w:170,h:255},{x:1815,y:690,w:210,h:145},{x:1510,y:1010,w:150,h:115});
 shadowSpots.push({x:1940,y:500},{x:1840,y:1060},{x:1260,y:1035});
 function v115Round(x,y,w,h,r,fill,stroke){ctx.beginPath();ctx.roundRect(x,y,w,h,r);if(fill){ctx.fillStyle=fill;ctx.fill()}if(stroke){ctx.strokeStyle=stroke;ctx.stroke()}}
 function v115DetailedWorker(x,y,phase,scale,vest,bag){
  const step=Math.sin(phase)*4*scale,bob=Math.abs(Math.sin(phase))*.8*scale;
  ctx.save();ctx.translate(x,y-bob);ctx.fillStyle='rgba(1,7,8,.26)';ctx.beginPath();ctx.ellipse(0,20*scale,16*scale,7*scale,0,0,Math.PI*2);ctx.fill();
  ctx.strokeStyle='#172124';ctx.lineWidth=5*scale;ctx.lineCap='round';ctx.beginPath();ctx.moveTo(-4*scale,8*scale);ctx.lineTo(-7*scale-step,25*scale);ctx.moveTo(4*scale,8*scale);ctx.lineTo(7*scale+step,25*scale);ctx.stroke();
  ctx.fillStyle=vest?'#b77936':'#36565a';ctx.beginPath();ctx.roundRect(-11*scale,-13*scale,22*scale,30*scale,7*scale);ctx.fill();
  if(vest){ctx.fillStyle='#e2d38e';ctx.fillRect(-10*scale,-3*scale,20*scale,3*scale);ctx.fillRect(-10*scale,7*scale,20*scale,3*scale)}
  ctx.fillStyle='#d2a080';ctx.beginPath();ctx.arc(0,-17*scale,7*scale,0,Math.PI*2);ctx.fill();ctx.fillStyle='#263234';ctx.beginPath();ctx.arc(0,-20*scale,7*scale,Math.PI,Math.PI*2);ctx.fill();
  if(bag){ctx.fillStyle='#51432f';ctx.beginPath();ctx.roundRect(10*scale,-1*scale,10*scale,15*scale,3*scale);ctx.fill()}
  ctx.restore();
 }
 function v115Tree(x,y,scale,now){
  const sway=Math.sin(now/1000+x*.01)*3*scale;ctx.save();ctx.translate(x,y);ctx.fillStyle='#4b3424';ctx.fillRect(-6*scale,0,12*scale,46*scale);
  ctx.strokeStyle='#5b402a';ctx.lineWidth=4*scale;ctx.beginPath();ctx.moveTo(0,9*scale);ctx.lineTo(-17*scale,-8*scale);ctx.moveTo(1*scale,5*scale);ctx.lineTo(19*scale,-13*scale);ctx.stroke();
  for(const p of [[0,-23,25,'#315d45'],[-20,-10,19,'#284d39'],[20,-11,21,'#386a4d'],[-5,-40,18,'#407553'],[13,-31,17,'#2f6145']]){ctx.fillStyle=p[3];ctx.beginPath();ctx.arc(p[0]*scale+sway,p[1]*scale,p[2]*scale,0,Math.PI*2);ctx.fill()}
  ctx.fillStyle='rgba(237,196,104,.22)';ctx.beginPath();ctx.arc(-8*scale+sway,-39*scale,6*scale,0,Math.PI*2);ctx.fill();ctx.restore();
 }
 function v115Car(x,y,w,h,color,lights){
  ctx.save();ctx.translate(x,y);ctx.fillStyle='rgba(0,0,0,.25)';ctx.beginPath();ctx.ellipse(w/2,h+4,w*.48,7,0,0,Math.PI*2);ctx.fill();
  ctx.fillStyle=color;ctx.beginPath();ctx.roundRect(0,0,w,h,11);ctx.fill();ctx.fillStyle='rgba(208,235,241,.36)';ctx.beginPath();ctx.roundRect(w*.18,6,w*.52,13,5);ctx.fill();ctx.fillStyle='#0a0e0f';ctx.beginPath();ctx.arc(20,h,8,0,Math.PI*2);ctx.arc(w-20,h,8,0,Math.PI*2);ctx.fill();
  if(lights){ctx.shadowColor='#ffe5a0';ctx.shadowBlur=15;ctx.fillStyle='#ffe6a4';ctx.fillRect(-2,12,7,6);ctx.fillRect(w-5,12,7,6);ctx.shadowBlur=0}ctx.restore();
 }
 function v115StreetLayer(now){
  const t=now/360;
  ctx.save();
  ctx.fillStyle='rgba(245,232,190,.23)';for(let i=0;i<7;i++)ctx.fillRect(55+i*72,252,42,9);
  ctx.strokeStyle='rgba(47,55,56,.28)';ctx.lineWidth=2;for(let i=0;i<18;i++){const x=(i*83+35)%720,y=300+(i*47)%330;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+10+(i%3)*5,y+4);ctx.stroke()}
  v115Tree(105,425,1.05,now);v115Tree(340,596,.88,now);v115Tree(585,392,.82,now);v115Tree(55,620,.7,now);v115Tree(680,555,.68,now);
  v115Car(((now*.062)%1500)-180,146,122,40,'#794b43',true);v115Car((((now*.045)+530)%1500)-210,54,112,39,'#365c6c',false);v115Car(182,318,110,35,'#596462',false);v115Car(320,322,98,33,'#725044',false);
  for(let i=0;i<6;i++)v115DetailedWorker(610+i*39,425+(i%2)*18,t+i*.7,.78,i%3===0,i%2===0);
  for(let i=0;i<8;i++)v115DetailedWorker(748+i*25,535+(i%3)*10,t*1.25+i*.45,.54,i%4===0,false);
  v115DetailedWorker(845,492,t*1.4,1.02,true,true);v115DetailedWorker(883,510,t*1.2,1.06,false,false);
  ctx.fillStyle='rgba(235,219,171,.58)';ctx.font='800 10px system-ui';ctx.textAlign='center';ctx.fillText('ДНЕВНАЯ СМЕНА',690,487);ctx.fillText('ОЖИДАНИЕ У ПРОХОДНОЙ',855,592);
  for(let i=0;i<9;i++){const leafX=(now*.018+i*127)%760,leafY=310+(Math.sin(now/600+i)*55+i*31)%330;ctx.fillStyle=i%2?'#755f37':'#4c7043';ctx.save();ctx.translate(leafX,leafY);ctx.rotate(now/900+i);ctx.fillRect(-3,-1,7,3);ctx.restore()}
  ctx.restore();
 }
 function v115HazardStrip(x,y,w,h){ctx.fillStyle='#d4a43e';ctx.fillRect(x,y,w,h);ctx.save();ctx.beginPath();ctx.rect(x,y,w,h);ctx.clip();ctx.strokeStyle='#1b1b18';ctx.lineWidth=8;for(let i=-h;i<w+h;i+=18){ctx.beginPath();ctx.moveTo(x+i,y+h);ctx.lineTo(x+i+h,y);ctx.stroke()}ctx.restore()}
 function v115FactoryLayer(now){
  const pulse=(Math.sin(now/170)+1)/2,night=state.phase>=3;
  ctx.save();
  ctx.globalAlpha=night?.42:.25;ctx.strokeStyle='#d7eee9';ctx.lineWidth=1;for(let i=0;i<32;i++){const x=(i*193)%2080,y=(i*127)%1170;ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+18+(i%4)*8,y+(i%2?3:-2));ctx.stroke()}ctx.globalAlpha=1;
  for(let i=0;i<14;i++){const x=(i*157+90)%2050,y=(i*91+180)%1160,r=16+(i%5)*8;ctx.fillStyle='rgba(5,9,10,'+(.10+(i%3)*.035)+')';ctx.beginPath();ctx.ellipse(x,y,r,r*.35,(i%4)*.45,0,Math.PI*2);ctx.fill()}
  ctx.strokeStyle='rgba(222,190,101,.48)';ctx.lineWidth=3;ctx.setLineDash([18,14]);ctx.beginPath();ctx.moveTo(1780,35);ctx.lineTo(1780,1165);ctx.moveTo(35,990);ctx.lineTo(2065,990);ctx.stroke();ctx.setLineDash([]);
  v115Round(1815,75,235,420,16,'#111b1d','#607476');ctx.fillStyle='#263438';for(let row=0;row<4;row++){ctx.fillRect(1842,112+row*88,180,58);for(let c=0;c<4;c++)v110Crate(1852+c*42,120+row*88,34,29)}ctx.fillStyle='#dbc77e';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.fillText('АРХИВНЫЙ СКЛАД',1932,98);
  v115Round(1795,650,270,210,15,'#172426','#677c7d');for(let i=0;i<5;i++){ctx.fillStyle='#3f5558';ctx.beginPath();ctx.arc(1845+i*45,733,20,0,Math.PI*2);ctx.fill();ctx.strokeStyle='#b28148';ctx.lineWidth=5;ctx.stroke()}ctx.fillStyle='#d7c480';ctx.fillText('РЕСИВЕРЫ · РЕЗЕРВ',1930,835);v110Steam(1825,700,now,.75);
  v115Round(1490,1005,530,135,12,'#0e181a','#4c6265');ctx.fillStyle='#26383a';for(let i=0;i<7;i++)ctx.fillRect(1522+i*67,1032,48,72);ctx.fillStyle='#d5c27f';ctx.fillText('СЕРВИСНЫЙ КОРИДОР · ТОЛЬКО ПЕРСОНАЛ',1755,1127);v115HazardStrip(1490,995,530,10);
  ctx.strokeStyle='#64777a';ctx.lineWidth=8;ctx.beginPath();ctx.moveTo(1800,565);ctx.lineTo(2040,565);ctx.lineTo(2040,930);ctx.stroke();ctx.strokeStyle='#b4844b';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(1795,582);ctx.lineTo(2022,582);ctx.lineTo(2022,925);ctx.stroke();
  ctx.save();ctx.translate(1320,645);ctx.rotate(now/950);ctx.strokeStyle='rgba(211,171,88,.62)';ctx.lineWidth=5;for(let i=0;i<6;i++){ctx.rotate(Math.PI/3);ctx.beginPath();ctx.moveTo(15,0);ctx.lineTo(52,0);ctx.stroke()}ctx.restore();
  ctx.fillStyle='rgba(101,225,210,'+(.08+pulse*.08)+')';ctx.fillRect(88,82,296,100);for(let i=0;i<4;i++){ctx.fillStyle=i===2&&state.phase>=3?'rgba(255,70,98,'+(.18+pulse*.3)+')':'rgba(102,226,210,.12)';ctx.fillRect(103+i*67,98,54,50)}
  ctx.strokeStyle='rgba(255,76,105,'+(.34+pulse*.38)+')';ctx.lineWidth=3;ctx.strokeRect(1518,73,244,360);ctx.fillStyle='rgba(255,76,105,.9)';ctx.font='900 10px system-ui';ctx.fillText('ДОСТУП ЗАПРЕЩЁН',1640,446);
  if(!state.oldShopOpen){for(let i=0;i<7;i++)v115HazardStrip(1530+i*32,402,25,8)}
  if(state.phase>=3){ctx.save();ctx.globalAlpha=.13+.12*pulse;ctx.translate(1658,334);ctx.fillStyle='#000';ctx.beginPath();ctx.ellipse(0,18,15,34,0,0,Math.PI*2);ctx.fill();ctx.beginPath();ctx.arc(0,-12,11,0,Math.PI*2);ctx.fill();ctx.restore()}
  if(state.phase===4){ctx.shadowColor='#ff405f';ctx.shadowBlur=18;ctx.fillStyle='rgba(255,64,95,'+(.25+pulse*.5)+')';for(let i=0;i<6;i++)ctx.fillRect(1465+i*39,705,24,8);ctx.shadowBlur=0}
  const target=getMainTarget();if(target){const r=35+pulse*7;ctx.strokeStyle='rgba(255,220,133,'+(.42+pulse*.45)+')';ctx.lineWidth=3;ctx.beginPath();ctx.arc(target.x,target.y,r,0,Math.PI*2);ctx.stroke();ctx.fillStyle='rgba(16,23,24,.88)';ctx.beginPath();ctx.roundRect(target.x-54,target.y-62,108,20,7);ctx.fill();ctx.fillStyle='#f2d98d';ctx.font='900 8px system-ui';ctx.fillText('ТОЧКА ВЗАИМОДЕЙСТВИЯ',target.x,target.y-49)}
  if(!state.notes.has('radioLog')){ctx.shadowColor='#f3d37d';ctx.shadowBlur=15;ctx.fillStyle='#ead8a8';ctx.save();ctx.translate(1880,365);ctx.rotate(-.09);ctx.fillRect(-15,-20,30,40);ctx.restore();ctx.shadowBlur=0}
  if(!state.notes.has('shiftMap')){ctx.shadowColor='#f3d37d';ctx.shadowBlur=15;ctx.fillStyle='#ead8a8';ctx.save();ctx.translate(1760,1080);ctx.rotate(.07);ctx.fillRect(-18,-14,36,28);ctx.restore();ctx.shadowBlur=0}
  ctx.restore();
 }
 function v115CameraPerson(g,x,y,scale,arriving){
  g.save();g.translate(x,y);g.fillStyle='rgba(0,0,0,.25)';g.beginPath();g.ellipse(0,34*scale,28*scale,9*scale,0,0,Math.PI*2);g.fill();
  g.fillStyle='#06090a';g.beginPath();g.roundRect(-22*scale,-58*scale,44*scale,82*scale,13*scale);g.fill();g.fillStyle='#26383b';g.fillRect(-17*scale,-22*scale,34*scale,5*scale);g.fillStyle='#b78642';g.fillRect(-17*scale,-9*scale,34*scale,4*scale);
  g.fillStyle='#b88a6e';g.beginPath();g.arc(0,-67*scale,17*scale,0,Math.PI*2);g.fill();g.fillStyle='#12191b';g.beginPath();g.arc(0,-72*scale,17*scale,Math.PI,Math.PI*2);g.fill();
  g.fillStyle='#dce8e4';g.font='900 '+(8*scale)+'px monospace';g.fillText('ИВЧ',-11*scale,-30*scale);
  if(!arriving){g.shadowColor='#ff3f60';g.shadowBlur=14;g.fillStyle='#ff4b69';g.beginPath();g.arc(-6*scale,-69*scale,2.5*scale,0,Math.PI*2);g.arc(6*scale,-69*scale,2.5*scale,0,Math.PI*2);g.fill();g.shadowBlur=0}g.restore();
 }
 function v115CameraLayer(id){
  const c=$('cameraFeed'),g=c.getContext('2d'),w=c.width,h=c.height,pulse=(Math.sin(performance.now()/220)+1)/2;
  g.save();for(let y=0;y<h;y+=6){g.fillStyle='rgba(255,255,255,.018)';g.fillRect(0,y,w,1)}const scan=(performance.now()/10)%h;g.fillStyle='rgba(111,255,230,.055)';g.fillRect(14,scan,w-28,9);g.strokeStyle='rgba(113,242,222,.18)';g.strokeRect(12,12,w-24,h-24);
  g.fillStyle='rgba(164,244,231,.76)';g.font='900 13px monospace';g.fillText('ALIVSPORT / NIGHT WATCH / SHIFT '+shiftNumber,23,h-18);
  if(id===1&&state.cameraMode==='zero'){v115CameraPerson(g,455,397,.78,true);g.strokeStyle='rgba(255,76,105,'+(.52+pulse*.42)+')';g.lineWidth=2;g.strokeRect(405,275,102,175);g.fillStyle='#ff637b';g.fillText('ЛИЧНОСТЬ НЕ ОПРЕДЕЛЕНА',365,472)}
  if(id===6&&state.cameraMode==='zero'){v115CameraPerson(g,520,425,.72,false);g.strokeStyle='rgba(255,76,105,'+(.5+pulse*.45)+')';g.strokeRect(474,300,94,166);g.fillStyle='#ff637b';g.fillText('ОБЪЕКТ ДВИЖЕТСЯ К ПОСТУ',345,495)}
  if(id===7){v115CameraPerson(g,505,398,.86,false);g.strokeStyle='rgba(255,76,105,'+(.5+pulse*.45)+')';g.lineWidth=3;g.strokeRect(448,250,118,210);g.fillStyle='#ff637b';g.fillText('СОВПАДЕНИЕ ЛИЦА: 99.8%',370,492)}
  if(id===0){g.fillStyle='rgba(255,65,94,'+(.25+pulse*.35)+')';g.fillRect(296,91,368,8);g.font='900 15px monospace';g.fillText('ОПЕРАТОР ВНУТРИ СТАНКА',350,510)}
  if(id===3||id===5){g.fillStyle='rgba(255,216,127,.9)';g.font='900 14px monospace';g.fillText('АНОМАЛИЯ СИГНАЛА '+(81+Math.floor(pulse*17))+'%',690,33)}
  g.restore();
 }
 const v115BaseDrawCamera=drawCamera;
 drawCamera=function(id){v115BaseDrawCamera(id);v115CameraLayer(id)};
 document.body.classList.add('reality115');
 const detail=$('objectiveDetail');if(detail)detail.textContent='Дневная смена выходит с территории. У проходной слишком много людей, но один из них не двигается.';
 `;
  const setupAnchor=" document.body.classList.add('reality110');";
  if(!source.includes(setupAnchor))throw new Error('не найдена точка запуска визуального слоя');
  source=source.replace(setupAnchor," document.body.classList.add('reality110','reality113','reality114');\n"+reality115Setup);

  (0,eval)(source);
}catch(e){
  if(error){error.textContent='Reality 115 не загрузилась: '+e.message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
}
})();
