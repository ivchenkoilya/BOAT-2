(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  let winRate=0;
  let busy=false;

  function showToast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node._v129Timer);
    node._v129Timer=setTimeout(()=>node.className='toast',3600);
  }

  async function loadRate(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{
        cache:'no-store',headers:{'X-Telegram-Init-Data':tg?.initData||''}
      });
      const data=await response.json();
      if(response.ok&&data.ok){
        winRate=Number(data.tax?.win_rate)||0;
        enhance();
      }
    }catch(_error){}
  }

  function winTaxFields(){
    return `<div class="field"><label>НАЛОГ С ПОЛОЖИТЕЛЬНОГО ВЫИГРЫША, %</label><input name="win_rate" type="number" min="0" max="100" value="${winRate}"></div><p class="hint">Допустимо от 0% до 100%. Закон вступит в силу только после голосования депутатов и подписи президента.</p>`;
  }

  function enhanceBillComposer(){
    const select=document.getElementById('billType');
    if(!select)return;
    select.querySelector('option[value="appointment"]')?.remove();
    if(!select.querySelector('option[value="win_tax"]')){
      const option=document.createElement('option');
      option.value='win_tax';
      option.textContent='🎰 Налог на выигрыш';
      const budget=select.querySelector('option[value="budget"]');
      select.insertBefore(option,budget||null);
    }
    if(select.value==='appointment')select.value='general';
    if(select.value==='win_tax'){
      const extra=document.getElementById('billExtra');
      if(extra&&!extra.querySelector('[name="win_rate"]'))extra.innerHTML=winTaxFields();
    }
  }

  function enhanceTreasury(){
    const panel=document.querySelector('#taxPolicy .panel');
    if(!panel)return;
    let card=panel.querySelector('.win-tax-v129');
    if(!card){
      card=document.createElement('div');
      card.className='win-tax-v129';
      card.style.cssText='margin-top:10px;padding:12px;border:1px solid #6b4b36;border-radius:13px;background:linear-gradient(145deg,#20140d,#100b09)';
      panel.appendChild(card);
    }
    card.innerHTML=`<div style="display:flex;align-items:center;justify-content:space-between;gap:10px"><span><b style="display:block;font-size:11px">🎰 Налог на игровой выигрыш</b><small style="display:block;margin-top:4px;color:#a99cb2;font-size:8px">Удерживается автоматически и поступает в казну</small></span><strong style="font-size:19px;color:#efcc76">${winRate}%</strong></div>`;
  }

  function enhanceOfficeLabels(){
    document.querySelectorAll('.office-card.vacant small').forEach(node=>{
      if(node.textContent.trim()==='Порог: 0 карьеры')node.textContent='Назначается Президентом';
    });
  }

  function enhance(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 129';
    enhanceBillComposer();
    enhanceTreasury();
    enhanceOfficeLabels();
  }

  document.addEventListener('change',event=>{
    if(event.target.id==='billType'){
      setTimeout(()=>{
        if(event.target.value==='win_tax'){
          const extra=document.getElementById('billExtra');
          if(extra)extra.innerHTML=winTaxFields();
        }
      },0);
    }
  });

  document.addEventListener('submit',async event=>{
    if(event.target.id!=='billForm')return;
    const form=event.target;
    const data=Object.fromEntries(new FormData(form).entries());
    if(data.bill_type!=='win_tax')return;
    event.preventDefault();
    event.stopImmediatePropagation();
    if(busy)return;
    const rate=Number(data.win_rate);
    if(!Number.isFinite(rate)||rate<0||rate>100){
      showToast('Ставка должна быть от 0 до 100%.','error');
      return;
    }
    if(!confirm(`Передать депутатам закон о налоге ${rate}% с выигрыша?`))return;
    busy=true;
    try{
      const response=await fetch('/government-v127/api/action',{
        method:'POST',headers,
        body:JSON.stringify({
          action:'create_bill',chat_id:chatId,bill_type:'win_tax',
          title:data.title||'О налоге на игровой выигрыш',
          description:data.description||`Установить налог на положительный игровой выигрыш в размере ${rate}%.`,
          payload:{rate}
        })
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Законопроект не создан.');
      showToast('Законопроект передан депутатам.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      setTimeout(()=>document.getElementById('refreshButton')?.click(),300);
    }catch(error){
      showToast(error.message||'Законопроект не создан.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{busy=false}
  },true);

  document.addEventListener('click',event=>{
    if(event.target.closest('#refreshButton'))setTimeout(loadRate,350);
  });

  const observer=new MutationObserver(enhance);
  observer.observe(document.body,{subtree:true,childList:true});
  setInterval(enhance,900);
  loadRate();
})();
