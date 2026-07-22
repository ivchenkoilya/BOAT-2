(()=>{
  'use strict';
  if(window.__governmentMandateRevocationV152)return;
  window.__governmentMandateRevocationV152=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
  let snapshot=null;
  let activeMandateId='';
  let frame=0;

  function sourceTitle(item){
    return item?.revocation_source_title||({law_violation:'Нарушение закона',system:'Система',impeachment:'Импичмент',creator:'Решение создателя системы'})[item?.revocation_source]||'Система';
  }

  function lawLine(item){
    const number=Number(item?.revocation_law_number)||0;
    if(!number)return '';
    return `<div><small>ПРАВОВОЕ ОСНОВАНИЕ</small><b>Закон Реальности №${number} «${esc(item.revocation_law_title||'') }»</b></div>`;
  }

  function revocationMarkup(item,compact=false){
    if(!item||item.status!=='annulled')return '';
    const reference=item.revocation_reference?`<div><small>ЗАПИСЬ РЕЕСТРА</small><code>${esc(item.revocation_reference)}</code></div>`:'';
    const revoked=Number(item.revoked_at)>0?`<div><small>ДАТА АННУЛИРОВАНИЯ</small><b>${date(item.revoked_at)}</b></div>`:'';
    if(compact){
      return `<div class="mandate-annulment-summary-v152"><small>🚫 ${esc(sourceTitle(item))}</small><b>${esc(item.revocation_reason||'Полномочия досрочно прекращены системой.')}</b>${Number(item.revocation_law_number)>0?`<span>Закон №${Number(item.revocation_law_number)} «${esc(item.revocation_law_title||'')}»</span>`:''}</div>`;
    }
    return `<section class="mandate-annulment-v152">
      <div class="mandate-annulment-title-v152"><span>🚫</span><div><small>ГОСУДАРСТВЕННЫЙ РЕЕСТР</small><h3>Причина аннулирования</h3></div></div>
      <div class="mandate-annulment-grid-v152">
        <div><small>ИСТОЧНИК РЕШЕНИЯ</small><b>${esc(sourceTitle(item))}</b></div>
        ${revoked}
        <div class="mandate-annulment-reason-v152"><small>УСТАНОВЛЕННАЯ ПРИЧИНА</small><b>${esc(item.revocation_reason||'Полномочия досрочно прекращены системой.')}</b></div>
        ${lawLine(item)}
        ${reference}
      </div>
      <p>С момента аннулирования перечисленные в документе полномочия юридической силы не имеют.</p>
    </section>`;
  }

  function itemById(id){
    return (snapshot?.mandates||[]).find(item=>String(item.mandate_id||'')===String(id||''));
  }

  function itemFromDocument(documentNode){
    if(activeMandateId){
      const direct=itemById(activeMandateId);
      if(direct)return direct;
    }
    const numberText=String(documentNode.querySelector('.mandate-number-v143')?.textContent||'');
    const match=numberText.match(/(\d{1,8})/);
    if(!match)return null;
    const number=Number(match[1]);
    return (snapshot?.mandates||[]).find(item=>Number(item.mandate_no)===number)||null;
  }

  function decorateCards(){
    document.querySelectorAll('.mandate-card-v143.annulled').forEach(card=>{
      const button=card.querySelector('[data-open-mandate]');
      const item=itemById(button?.dataset.openMandate||'');
      if(!item)return;
      let block=card.querySelector('.mandate-annulment-summary-v152');
      const markup=revocationMarkup(item,true);
      if(!block){
        card.insertAdjacentHTML('beforeend',markup);
        block=card.querySelector('.mandate-annulment-summary-v152');
        if(block&&button)card.insertBefore(block,button);
      }else{
        const holder=document.createElement('div');
        holder.innerHTML=markup;
        const fresh=holder.firstElementChild;
        if(fresh&&block.innerHTML!==fresh.innerHTML)block.replaceWith(fresh);
      }
    });
  }

  function decorateDocument(){
    document.querySelectorAll('.mandate-document-v143').forEach(documentNode=>{
      const item=itemFromDocument(documentNode);
      const old=documentNode.querySelector('.mandate-annulment-v152');
      if(!item||item.status!=='annulled'){
        old?.remove();
        return;
      }
      const markup=revocationMarkup(item,false);
      if(!old){
        const fields=documentNode.querySelector('.mandate-fields-v143');
        if(fields)fields.insertAdjacentHTML('afterend',markup);
        else documentNode.insertAdjacentHTML('beforeend',markup);
      }else{
        const holder=document.createElement('div');
        holder.innerHTML=markup;
        const fresh=holder.firstElementChild;
        if(fresh&&old.innerHTML!==fresh.innerHTML)old.replaceWith(fresh);
      }
      documentNode.classList.add('mandate-annulled-document-v152');
    });
  }

  function apply(){
    decorateCards();
    decorateDocument();
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(apply);
  }

  async function load(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});
      const data=await response.json();
      if(!response.ok||!data?.ok)return;
      snapshot=data;
      schedule();
    }catch(_error){}
  }

  document.addEventListener('click',event=>{
    const open=event.target.closest?.('[data-open-mandate]');
    if(open){
      activeMandateId=String(open.dataset.openMandate||'');
      setTimeout(schedule,0);
      setTimeout(schedule,80);
    }
    if(event.target.closest?.('[data-tab="mandates"],#refreshButton'))setTimeout(load,180);
  },true);

  const observer=new MutationObserver(schedule);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});
  window.addEventListener('focus',load);
  load();
  schedule();
})();
