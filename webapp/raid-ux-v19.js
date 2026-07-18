(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const stage=document.getElementById('bossStage');

  function effectLayer(type){
    document.querySelector('.v19-effect-layer')?.remove();
    const layer=document.createElement('div');
    layer.className=`v19-effect-layer ${type}`;
    if(type==='shield'){
      layer.innerHTML='<div class="v19-screen"></div><div class="v19-shield-ring"></div><div class="v19-effect-title">🛡 ЗАЩИТА АКТИВНА</div>';
      document.querySelector('.fighter.self')?.classList.add('v19-defended');
      setTimeout(()=>document.querySelector('.fighter.self')?.classList.remove('v19-defended'),1050);
    }else{
      const particles=Array.from({length:12},(_,i)=>{
        const angle=(Math.PI*2*i)/12;
        const radius=85+(i%3)*18;
        const x=Math.round(Math.cos(angle)*radius);
        const y=Math.round(Math.sin(angle)*radius-35);
        return `<i class="v19-heal-particle" style="--x:${x}px;--y:${y}px;animation-delay:${(i%4)*.04}s"></i>`;
      }).join('');
      layer.innerHTML=`<div class="v19-screen"></div>${particles}<div class="v19-effect-title">✚ ВОССТАНОВЛЕНИЕ HP</div>`;
      document.querySelector('.fighter.self')?.classList.add('v19-healed');
      setTimeout(()=>document.querySelector('.fighter.self')?.classList.remove('v19-healed'),1050);
    }
    document.body.appendChild(layer);
    setTimeout(()=>layer.remove(),1250);
  }

  /* Telegram Android иногда не передаёт нативную прокрутку, когда жест начинается
     прямо на большой сцене босса. Перехватываем жест в capture-фазе и прокручиваем
     настоящий scrollingElement. Так работает и по лицу босса, и по пустой области. */
  if(stage){
    let gesture=null;
    const interactive='button,a,input,textarea,select,[role="button"]';
    const scrollRoot=()=>document.scrollingElement||document.documentElement||document.body;

    document.addEventListener('touchstart',event=>{
      if(event.touches.length!==1)return;
      const target=event.target instanceof Element?event.target:null;
      if(!target||!target.closest('#bossStage')||target.closest(interactive)){
        gesture=null;
        return;
      }
      const touch=event.touches[0];
      gesture={x:touch.clientX,y:touch.clientY,locked:false};
    },{capture:true,passive:true});

    document.addEventListener('touchmove',event=>{
      if(!gesture||event.touches.length!==1)return;
      const touch=event.touches[0];
      const dx=gesture.x-touch.clientX;
      const dy=gesture.y-touch.clientY;
      if(!gesture.locked){
        if(Math.abs(dx)<3&&Math.abs(dy)<3)return;
        if(Math.abs(dx)>Math.abs(dy)*1.15){gesture=null;return;}
        gesture.locked=true;
      }
      const root=scrollRoot();
      root.scrollTop+=dy;
      gesture.x=touch.clientX;
      gesture.y=touch.clientY;
      event.preventDefault();
      event.stopPropagation();
    },{capture:true,passive:false});

    const clearGesture=()=>{gesture=null;};
    document.addEventListener('touchend',clearGesture,{capture:true,passive:true});
    document.addEventListener('touchcancel',clearGesture,{capture:true,passive:true});
  }

  document.addEventListener('click',event=>{
    const action=event.target.closest('[data-action]');
    if(!action||action.disabled)return;
    if(action.dataset.action==='heal')effectLayer('heal');
    if(action.dataset.action==='defend')effectLayer('shield');
    if(action.dataset.action==='heal'||action.dataset.action==='defend'){
      tg?.HapticFeedback?.impactOccurred?.('medium');
    }
  },true);
})();
