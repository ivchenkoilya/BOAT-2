(async()=>{
'use strict';
const error=document.getElementById('startError');
const startButton=document.getElementById('start');
try{
  const response=await fetch('/games/night-hunter/game-v115.js?v=116',{cache:'no-store'});
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
    }else if(failed||Date.now()-started>20000){
      clearInterval(timer);
      window.dispatchEvent(new Event('night-hunter-ready'));
    }
  },100);
}catch(e){
  if(error){error.textContent='Reality 116 не загрузилась: '+e.message;error.style.display='block'}
  if(startButton){startButton.disabled=true;startButton.textContent='ОШИБКА ЗАГРУЗКИ'}
}
})();