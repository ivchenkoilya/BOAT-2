(()=>{
  'use strict';
  if(window.__presidentDirectDeputyV173)return;
  window.__presidentDirectDeputyV173=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  let state=null;
  let sending=false;

  function isPresident(){
    const access=state?.oversight_deputy_v167||{};
    return Boolean(access.is_admin||(access.offices||[]).includes('president'));
  }

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__v173Toast);
    node.__v173Toast=setTimeout(()=>node.className='toast',3800);
  }

  async function loadState(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_v173=${Date.now()}`,{
        cache:'no-store',
        headers:{'X-Telegram-Init-Data':tg?.initData||''},
      });
      const data=await response.json();
      if(response.ok&&data?.ok){state=data;patchTexts()}
    }catch(_error){}
  }

  function patchTexts(){
    const president=isPresident();
    const compact=document.querySelector('[data-od172-action="appointment"]');
    if(compact){
      const hint=compact.querySelector('small');
      if(hint)hint.textContent=president?'Назначение сразу, без Госдумы':'Кандидатура проходит через Госдуму';
    }

    const structure=document.getElementById('oversightDeputyInstitutionV169');
    if(structure&&!state?.offices?.some(item=>item.office_key==='oversight_deputy')){
      const small=structure.querySelector('small');
      if(small)small.textContent='Свободно · Президент назначает напрямую; глава Надзора предлагает через Госдуму';
    }

    const form=document.getElementById('powerForm');
    const officeSelect=form?.querySelector('select[name="office_key"]');
    const custom=form?.dataset?.od172Action==='appointment';
    const standard=form?.dataset?.action==='appointment'&&officeSelect?.value==='oversight_deputy';
    if(president&&(custom||standard)){
      const subtitle=document.getElementById('powerModalOffice');
      const submit=form.querySelector('button[type="submit"]');
      if(subtitle)subtitle.textContent='ПРЯМОЕ РЕШЕНИЕ ПРЕЗИДЕНТА · БЕЗ ГОЛОСОВАНИЯ';
      if(submit)submit.textContent='🦅 НАЗНАЧИТЬ НЕМЕДЛЕННО';
    }
  }

  function closeModal(){
    const modal=document.getElementById('powerModal');
    const form=document.getElementById('powerForm');
    modal?.classList.remove('open');
    if(form){delete form.dataset.od172Action;delete form.dataset.action}
    document.body.style.overflow='';
  }

  async function appointDirect(targetId,reason){
    if(sending)return;
    if(!confirm('Назначить заместителя главы Надзора указом Президента без голосования Госдумы?'))return;
    sending=true;
    try{
      const response=await fetch('/government-v173/api/direct-appointment',{
        method:'POST',
        cache:'no-store',
        headers,
        body:JSON.stringify({chat_id:chatId,target_user_id:Number(targetId)||0,reason:String(reason||'')}),
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Назначение не выполнено.');
      closeModal();
      toast(data.message||'Заместитель назначен напрямую.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      await loadState();
      document.getElementById('refreshButton')?.click();
    }catch(error){
      toast(error.message||'Назначение не выполнено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      sending=false;
    }
  }

  window.addEventListener('submit',event=>{
    const form=event.target;
    if(!isPresident()||form?.id!=='powerForm')return;

    const custom=form.dataset.od172Action==='appointment';
    const officeSelect=form.querySelector('select[name="office_key"]');
    const standard=form.dataset.action==='appointment'&&officeSelect?.value==='oversight_deputy';
    if(!(custom||standard))return;

    event.preventDefault();
    event.stopImmediatePropagation();
    const data=Object.fromEntries(new FormData(form).entries());
    appointDirect(data.target_user_id,data.reason);
  },true);

  window.addEventListener('click',event=>{
    if(event.target.closest?.('[data-od172-action="appointment"],[data-power-action="appointment"]')){
      setTimeout(patchTexts,40);
      setTimeout(patchTexts,180);
    }
    if(event.target.closest?.('#refreshButton'))setTimeout(loadState,220);
  },true);

  window.addEventListener('change',event=>{
    if(event.target?.matches?.('#powerForm select[name="office_key"]'))patchTexts();
  },true);

  loadState();
  const observer=new MutationObserver(patchTexts);
  observer.observe(document.documentElement,{childList:true,subtree:true});
})();
