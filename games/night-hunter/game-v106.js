(async()=>{
 const error=document.getElementById('startError'),start=document.getElementById('start');
 try{
  const names=['a','b','c','d','e','f','g','h'];
  const [parts,visual101,visual102,story104,fixes104,ui105,interactions106,fixes106]=await Promise.all([
   Promise.all(names.map(async n=>{const r=await fetch(`/games/night-hunter/game-v100-${n}.js?v=106`,{cache:'no-store'});if(!r.ok)throw new Error(`часть ${n.toUpperCase()}`);return r.text()})),
   fetch('/games/night-hunter/game-v101-art.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('визуальный слой 101');return r.text()}),
   fetch('/games/night-hunter/game-v102-art.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('визуальный слой 102');return r.text()}),
   fetch('/games/night-hunter/game-v104-story.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('сюжетный слой 104');return r.text()}),
   fetch('/games/night-hunter/game-v104-fixes.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('исправления 104');return r.text()}),
   fetch('/games/night-hunter/game-v105-ui.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('боевой интерфейс 105');return r.text()}),
   fetch('/games/night-hunter/game-v106-interactions.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('взаимодействия 106');return r.text()}),
   fetch('/games/night-hunter/game-v106-fixes.js?v=106',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('исправления 106');return r.text()})
  ]);
  const base=parts.join(''),marker='})();',index=base.lastIndexOf(marker);if(index<0)throw new Error('точка сборки');
  (0,eval)(base.slice(0,index)+'\n'+visual101+'\n'+visual102+'\n'+story104+'\n'+fixes104+'\n'+ui105+'\n'+interactions106+'\n'+fixes106+'\n'+base.slice(index));
 }catch(e){if(error){error.style.display='block';error.textContent='Не удалось загрузить Reality 106: '+e.message}if(start){start.disabled=true;start.textContent='ОШИБКА ЗАГРУЗКИ'}}
})();
