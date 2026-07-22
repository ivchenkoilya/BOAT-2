(()=>{
  'use strict';
  if(window.__governmentMandateLiveRefreshV159)return;
  window.__governmentMandateLiveRefreshV159=true;

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
  let loading=false;
  let reloadQueued=false;
  let burstTimers=[];

  function mandatesOpen(){
    return document.querySelector('[data-screen="mandates"]')?.classList.contains('active');
  }

  function sourceTitle(item){
    return item?.revocation_source_title||({law_violation:'Нарушение закона',system:'Система',impeachment:'Импичмент',creator:'Решение создателя системы'})[item?.revocation_source]||'Система';
  }

  function itemById(id){
    return (snapshot?.mandates||[]).find(item=>String(item.mandate_id||'')===String(id||''));
  }

  function summaryMarkup(item){
    if(!item||item.status!=='annulled')return '';
    const reason=String(item.revocation_reason||'Полномочия досрочно прекращены государственной системой.');
    const law=Number(item.revocation_law_number)>0
      ?`<span>Закон №${Number(item.revocation_law_number)} «${esc(item.revocation_law_title||'')}»</span>`
      :'';
    return `<div class="mandate-annulment-summary-v152" data-v159-summary="${esc(item.mandate_id)}"><small>🚫 ${esc(sourceTitle(item))}</small><b>${esc(reason)}</b>${law}</div>`;
  }

  function fullMarkup(item){
    if(!item||item.status!=='annulled')return '';
    const revoked=Number(item.revoked_at)>0?`<div><small>ДАТА АННУЛИРОВАНИЯ</small><b>${date(item.revoked_at)}</b></div>`:'';
    const law=Number(item.revocation_law_number)>0?`<div><small>ПРАВОВОЕ ОСНОВАНИЕ</small><b>Закон Реальности №${Number(item.revocation_law_number)} «${esc(item.revocation_law_title||'')}»</b></div>`:'';
    const reference=item.revocation_reference?`<div><small>ЗАПИСЬ РЕЕСТРА</small><code>${esc(item.revocation_reference)}</code></div>`:'';
    return `<section class="mandate-annulment-v152" data-v159-document="${esc(item.mandate_id)}"><div class="mandate-annulment-title-v152"><span>🚫</span><div><small>ГОСУДАРСТВЕННЫЙ РЕЕСТР</small><h3>Причина аннулирования</h3></div></div><div class="mandate-annulment-grid-v152"><div><small>ИСТОЧНИК РЕШЕНИЯ</small><b>${esc(sourceTitle(item))}</b></div>${revoked}<div class="mandate-annulment-reason-v152"><small>УСТАНОВЛЕННАЯ ПРИЧИНА</small><b>${esc(item.revocation_reason||'Полномочия досрочно прекращены государственной системой.')}</b></div>${law}${reference}</div><p>С момента аннулирования перечисленные в документе полномочия юридической силы не имеют.</p></section>`;
  }

  function replaceOrInsert(card,item){
    const markup=summaryMarkup(item);
    if(!markup)return;
    const old=card.querySelector('.mandate-annulment-summary-v152');
    const holder=document.createElement('div');
    holder.innerHTML=markup;
    const fresh=holder.firstElementChild;
    if(!fresh)return;
    if(old){
      if(old.outerHTML!==fresh.outerHTML)old.replaceWith(fresh);
      return;
    }
    const button=card.querySelector('[data-open-mandate]');
    if(button)card.insertBefore(fresh,button);
    else card.appendChild(fresh);
  }

  function decorateCards(){
    if(!snapshot)return;
    document.querySelectorAll('.mandate-card-v143.annulled').forEach(card=>{
      const id=String(card.querySelector('[data-open-mandate]')?.dataset.openMandate||'');
      const item=itemById(id);
      if(item)replaceOrInsert(card,item);
    });
  }

  function documentItem(node){
    if(activeMandateId){
      const direct=itemById(activeMandateId);
      if(direct)return direct;
    }
    const text=String(node.querySelector('.mandate-number-v143')?.textContent||'');
    const match=text.match(/(\d{1,8})/);
    if(!match)return null;
    return (snapshot?.mandates||[]).find(item=>Number(item.mandate_no)===Number(match[1]))||null;
  }

  function decorateDocuments(){
    if(!snapshot)return;
    document.querySelectorAll('.mandate-document-v143').forEach(node=>{
      const item=documentItem(node);
      if(!item||item.status!=='annulled')return;
      const markup=fullMarkup(item);
      const holder=document.createElement('div');
      holder.innerHTML=markup;
      const fresh=holder.firstElementChild;
      if(!fresh)return;
      const old=node.querySelector('.mandate-annulment-v152');
      if(old){
        if(old.outerHTML!==fresh.outerHTML)old.replaceWith(fresh);
      }else{
        const fields=node.querySelector('.mandate-fields-v143');
        if(fields)fields.insertAdjacentElement('afterend',fresh);
        else node.appendChild(fresh);
      }
      node.classList.add('mandate-annulled-document-v152');
    });
  }

  function apply(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 159';
    decorateCards();
    decorateDocuments();
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(apply);
  }

  function burst(){
    burstTimers.forEach(clearTimeout);
    burstTimers=[0,60,180,420,850,1500,2600].map(delay=>setTimeout(schedule,delay));
  }

  async function load(){
    if(!chatId)return;
    if(loading){reloadQueued=true;return;}
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_mandate_v159=${Date.now()}`,{
        cache:'no-store',headers
      });
      const data=await response.json();
      if(response.ok&&data?.ok){
        snapshot=data;
        schedule();
        burst();
      }
    }catch(_error){}
    finally{
      loading=false;
      if(reloadQueued){reloadQueued=false;setTimeout(load,80);}
    }
  }

  document.addEventListener('click',event=>{
    const open=event.target.closest?.('[data-open-mandate]');
    if(open){
      activeMandateId=String(open.dataset.openMandate||'');
      load();
      burst();
    }
    if(event.target.closest?.('[data-tab="mandates"]')){
      load();
      burst();
      setTimeout(load,350);
      setTimeout(load,1200);
    }
    if(event.target.closest?.('#refreshButton')){
      load();
      burst();
    }
  },true);

  const observer=new MutationObserver(()=>{
    if(mandatesOpen()||document.querySelector('.mandate-document-v143'))schedule();
  });
  observer.observe(document.documentElement,{subtree:true,childList:true});

  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden){load();burst();}
  });
  window.addEventListener('focus',()=>{load();burst();});

  load();
  burst();
  setInterval(()=>{
    if(!document.hidden&&mandatesOpen()){
      apply();
      load();
    }
  },2000);
})();