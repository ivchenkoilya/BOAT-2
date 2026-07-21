(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
try{
  const machineSources={"cncBlue":"/games/night-hunter/assets/machine-cnc-blue-v114.svg?v=114","cncGreen":"/games/night-hunter/assets/machine-cnc-green-v114.svg?v=114","cncRed":"/games/night-hunter/assets/machine-cnc-red-v114.svg?v=114","laser":"/games/night-hunter/assets/machine-laser-v114.svg?v=114","press":"/games/night-hunter/assets/machine-press-v114.svg?v=114","zero":"/games/night-hunter/assets/machine-zero-v114.svg?v=114"};
  const machineEntries=await Promise.all(Object.entries(machineSources).map(([key,url])=>new Promise(resolve=>{
    const image=new Image();image.decoding='async';
    image.onload=()=>resolve([key,image]);
    image.onerror=()=>resolve([key,null]);
    image.src=url;
  })));
  window.__NH_MACHINE_SPRITES=Object.fromEntries(machineEntries.filter(([,image])=>image));

  const response=await fetch('/games/night-hunter/game-v110.js?v=114',{cache:'no-store'});
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

  const machineAnchor="function v110Machine(x,y,w,h,label,active,now,accent='#5f7b7c'){";
  const machineHelper="function v114MachineSprite(key,x,y,w,h,label,active,now,accent){\n const image=window.__NH_MACHINE_SPRITES&&window.__NH_MACHINE_SPRITES[key];\n if(!image||!image.complete||!image.naturalWidth){v110Machine(x,y,w,h,label,active,now,accent);return}\n ctx.save();\n ctx.shadowColor='rgba(0,0,0,.55)';ctx.shadowBlur=18;ctx.shadowOffsetY=10;\n ctx.drawImage(image,x,y,w,h);ctx.shadowBlur=0;ctx.shadowOffsetY=0;\n if(active){\n  const pulse=(Math.sin(now/150)+1)/2;\n  ctx.fillStyle='rgba(255,186,73,'+(.08+pulse*.12)+')';ctx.beginPath();ctx.roundRect(x-5,y-5,w+10,h+10,16);ctx.fill();\n  ctx.strokeStyle='rgba(255,202,93,'+(.55+pulse*.4)+')';ctx.lineWidth=3;ctx.beginPath();ctx.roundRect(x-4,y-4,w+8,h+8,16);ctx.stroke();\n  ctx.shadowColor='#ffc45d';ctx.shadowBlur=18;ctx.fillStyle='#ffd36f';ctx.beginPath();ctx.arc(x+w-24,y+25,6+pulse*2,0,Math.PI*2);ctx.fill();ctx.shadowBlur=0;\n }\n ctx.fillStyle='#e4eee9';ctx.font='900 12px system-ui';ctx.textAlign='center';ctx.shadowColor='rgba(0,0,0,.9)';ctx.shadowBlur=5;ctx.fillText(label,x+w/2,y+h-12);ctx.restore()\n}\n";
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

  const enginePatch=`let source=engine;
  const v113Branding=[
    ['АО «ОРФЕЙ-МЕХАНИКА»','АО «ALIVSPORT»'],
    ['ОРФЕЙ-МЕХАНИКА','ALIVSPORT'],
    ['ОРФЕЙ','ALIVSPORT'],
    ['И. ИВЧЕНКОВ','ИВЧ'],
    ['И. Ивченков','Ивч'],
    ['ИВЧЕНКОВ','ИВЧ'],
    ['Ивченков','Ивч']
  ];
  for(const [from,to] of v113Branding)source=source.split(from).join(to);`;

  if(!source.includes('let source=engine;'))throw new Error('не найдена точка применения брендинга');
  source=source.replace('let source=engine;',enginePatch);
  source=source.replace("document.body.classList.add('reality110');","document.body.classList.add('reality110','reality113','reality114');");
  (0,eval)(source);

  const readyStarted=Date.now();
  const readyTimer=setInterval(()=>{
    const demo=document.getElementById('demo');
    const hasStartHandler=typeof startButton?.onclick==='function';
    const demoReady=demo&&!demo.classList.contains('hidden');
    const failed=error&&error.style.display==='block'&&Boolean(error.textContent);
    if(hasStartHandler){
      clearInterval(readyTimer);
      startButton.disabled=false;
      startButton.classList.remove('loading');
      window.__NIGHT_HUNTER_READY__=true;
      window.dispatchEvent(new Event('night-hunter-ready'));
      return;
    }
    if(demoReady||failed||Date.now()-readyStarted>15000){
      clearInterval(readyTimer);
      if(demoReady)demo.disabled=false;
      window.dispatchEvent(new Event('night-hunter-ready'));
    }
  },100);
}catch(e){
  if(error){error.textContent='Reality 114 не загрузилась: '+e.message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
}
})();
