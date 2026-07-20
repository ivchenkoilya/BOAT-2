(async()=>{
 const error=document.getElementById('startError'),start=document.getElementById('start');
 try{
  const names=['a','b','c','d','e','f','g','h'];
  const [parts,visual101,visual102,story104]=await Promise.all([
   Promise.all(names.map(async n=>{const r=await fetch(`/games/night-hunter/game-v100-${n}.js?v=104`,{cache:'no-store'});if(!r.ok)throw new Error(`часть ${n.toUpperCase()}`);return r.text()})),
   fetch('/games/night-hunter/game-v101-art.js?v=104',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('визуальный слой 101');return r.text()}),
   fetch('/games/night-hunter/game-v102-art.js?v=104',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('визуальный слой 102');return r.text()}),
   fetch('/games/night-hunter/game-v104-story.js?v=104',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('сюжетный слой 104');return r.text()})
  ]);
  const base=parts.join(''),marker='})();',index=base.lastIndexOf(marker);if(index<0)throw new Error('точка сборки');
  (0,eval)(base.slice(0,index)+'\n'+visual101+'\n'+visual102+'\n'+story104+'\n'+base.slice(index));
 }catch(e){if(error){error.style.display='block';error.textContent='Не удалось загрузить Reality 104: '+e.message}if(start){start.disabled=true;start.textContent='ОШИБКА ЗАГРУЗКИ'}}
})();
