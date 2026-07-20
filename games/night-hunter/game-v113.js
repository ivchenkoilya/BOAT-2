(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
try{
  const response=await fetch('/games/night-hunter/game-v110.js?v=113',{cache:'no-store'});
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
  source=source.replace("document.body.classList.add('reality110');","document.body.classList.add('reality110','reality113');");
  (0,eval)(source);
}catch(e){
  if(error){error.textContent='Reality 113 не загрузилась: '+e.message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
}
})();
