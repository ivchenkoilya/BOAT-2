(async()=>{
  const error=document.getElementById('startError');
  const start=document.getElementById('start');
  try{
    const names=['a','b','c','d','e','f','g','h'];
    const [parts,visual]=await Promise.all([
      Promise.all(names.map(async n=>{
        const r=await fetch(`/games/night-hunter/game-v100-${n}.js?v=101`,{cache:'no-store'});
        if(!r.ok)throw new Error(`часть ${n.toUpperCase()}`);
        return r.text();
      })),
      fetch('/games/night-hunter/game-v101-art.js?v=101',{cache:'no-store'}).then(r=>{
        if(!r.ok)throw new Error('визуальный слой');
        return r.text();
      })
    ]);
    const base=parts.join('');
    const marker='})();';
    const index=base.lastIndexOf(marker);
    if(index<0)throw new Error('точка сборки');
    const code=base.slice(0,index)+'\n'+visual+'\n'+base.slice(index);
    (0,eval)(code);
  }catch(e){
    if(error){
      error.style.display='block';
      error.textContent='Не удалось загрузить Reality 101: '+e.message;
    }
    if(start){
      start.disabled=true;
      start.textContent='ОШИБКА ЗАГРУЗКИ';
    }
  }
})();
