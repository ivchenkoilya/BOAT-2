(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
const emitFailure=message=>{
  window.__NIGHT_HUNTER_LOAD_ERROR__=message;
  window.dispatchEvent(new CustomEvent('night-hunter-error',{detail:message}));
};
try{
  const response=await fetch('/games/night-hunter/game-v115.js?v=117',{cache:'no-store'});
  if(!response.ok)throw new Error('не загружен визуальный слой Reality 115');
  let source=await response.text();

  const start=source.indexOf('  const outsideTail=');
  const end=source.indexOf('\n\n  const reality115Setup=',start);
  if(start<0||end<0)throw new Error('не найден устаревший блок подключения окружения');

  const robustPatch=`  const injectLayer=(loaderSource,startMarker,endMarker,call,layer)=>{
    const a=loaderSource.indexOf(startMarker),b=loaderSource.indexOf(endMarker,a);
    if(a<0||b<0)throw new Error('не найден визуальный блок '+startMarker);
    const block=loaderSource.slice(a,b),p=block.lastIndexOf(call);
    if(p<0)throw new Error('не найдена точка отрисовки '+startMarker);
    return loaderSource.slice(0,a)+block.slice(0,p)+layer+'\\n  '+block.slice(p)+loaderSource.slice(b);
   };
   source=injectLayer(source,"swap('function drawOutside(now){'","swap('function machine('","drawPlayer(now)","v115StreetLayer(now);");
   source=injectLayer(source,"swap('function drawFactory(now){'","swap('function drawFlashlight(){'","drawPlayer(now)","v115FactoryLayer(now);");`;

  source=source.slice(0,start)+robustPatch+source.slice(end);
  source=source.replaceAll('Reality 115 не загрузилась','Reality 116 не загрузилась');

  const setupNeedle=`  const setupAnchor=" document.body.classList.add('reality110');";`;
  if(!source.includes(setupNeedle))throw new Error('не найдена точка безопасной вставки записок');
  const escapePatch=String.raw`  const safeReality115Setup=reality115Setup.split('\\n').join('\\\\n');
`;
  source=source.replace(setupNeedle,escapePatch+setupNeedle);
  if(!source.includes('+reality115Setup);'))throw new Error('не найдено подключение сюжетного слоя');
  source=source.replace('+reality115Setup);','+safeReality115Setup);');
  source=source.replace("document.body.classList.add('reality115');","document.body.classList.add('reality115','reality116');");

  new Function(source);
  await (0,eval)(source);

  const started=Date.now();
  const timer=setInterval(()=>{
    const failed=error&&error.style.display==='block'&&Boolean(error.textContent);
    if(typeof startButton?.onclick==='function'){
      clearInterval(timer);
      startButton.disabled=false;
      startButton.classList.remove('loading');
      window.__NIGHT_HUNTER_READY__=true;
      window.dispatchEvent(new Event('night-hunter-ready'));
      return;
    }
    if(failed){
      clearInterval(timer);
      emitFailure(error.textContent);
      return;
    }
    if(Date.now()-started>22000){
      clearInterval(timer);
      const message='Reality 116 не успела подготовить игровой движок.';
      if(error){error.textContent=message;error.style.display='block'}
      emitFailure(message);
    }
  },100);
}catch(e){
  const message='Reality 116 не загрузилась: '+e.message;
  if(error){error.textContent=message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
  emitFailure(message);
}
})();
