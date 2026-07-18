(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;

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
