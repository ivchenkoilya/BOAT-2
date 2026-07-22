(()=>{
  'use strict';
  if(window.__governmentElectionMessageV156)return;
  window.__governmentElectionMessageV156=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  let frame=0;
  let loading=false;
  let incoming=[];

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__v156Timer);
    node.__v156Timer=setTimeout(()=>node.className='toast',3900);
  }

  function closeModal(){
    const modal=document.getElementById('shadowModalV153');
    if(modal)modal.hidden=true;
    document.body.classList.remove('v153-modal-open');
  }

  function patchModal(){
    const modal=document.getElementById('shadowModalV153');
    if(!modal||modal.hidden)return;

    const icon=modal.querySelector('.v153-modal-icon');
    if(icon)icon.textContent='😈';
    const title=modal.querySelector('#shadowModalContentV153 h2');
    if(title)title.textContent='Подкупить голоса';

    const warning=modal.querySelector('.v153-warning');
    if(warning){
      warning.textContent='Предложение действует до завершения выборов. При принятии голос автоматически будет отдан тебе и заблокирован.';
    }

    const form=modal.querySelector('#buyVoteFormV153,#buyVoteFormV156');
    if(!form)return;
    form.id='buyVoteFormV156';

    if(!form.querySelector('[data-v156-secret-message]')){
      const submit=form.querySelector('button[type="submit"]');
      const field=document.createElement('div');
      field.className='field v156-message-field';
      field.dataset.v156SecretMessage='1';
      field.innerHTML='<label>СКРЫТОЕ СООБЩЕНИЕ · ДО 300 СИМВОЛОВ</label><textarea name="secret_message" maxlength="300" placeholder="Например: Поддержи меня — о нашей сделке никто не узнает"></textarea><small class="hint">Сообщение увидит только получатель предложения. Имя кандидата останется скрытым.</small>';
      if(submit)form.insertBefore(field,submit);
      else form.appendChild(field);
    }

    const submit=form.querySelector('button[type="submit"]');
    if(submit)submit.textContent='😈 ОТПРАВИТЬ ТАЙНОЕ ПРЕДЛОЖЕНИЕ';
  }

  function patchButtons(){
    document.querySelectorAll('[data-buy-vote]').forEach(button=>{
      button.textContent='😈 ПОДКУПИТЬ ГОЛОСА';
    });
  }

  function decorateIncoming(){
    const cards=[...document.querySelectorAll('#shadowOffersV153 .v153-offer')];
    const visible=incoming.filter(item=>['pending','accepted','reported'].includes(String(item.status||'')));
    cards.forEach((card,index)=>{
      card.querySelector('.v156-secret-message')?.remove();
      const item=visible[index];
      const message=String(item?.secret_message||'').trim();
      if(!message)return;
      const block=document.createElement('div');
      block.className='v156-secret-message';
      block.innerHTML=`<small>😈 СКРЫТОЕ СООБЩЕНИЕ КАНДИДАТА</small><p>${esc(message)}</p>`;
      const meta=card.querySelector('.v153-offer-meta');
      if(meta)card.insertBefore(block,meta);
      else card.appendChild(block);
    });
  }

  function apply(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 156';
    patchButtons();
    patchModal();
    decorateIncoming();
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(apply);
  }

  async function loadState(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{
        cache:'no-store',headers
      });
      const data=await response.json();
      if(response.ok&&data?.ok){
        incoming=data.election_shadow_v153?.incoming_offers||[];
        schedule();
      }
    }catch(_error){}
    finally{loading=false}
  }

  async function submitBribe(form){
    const data=Object.fromEntries(new FormData(form).entries());
    const electionId=String(window.__v156ElectionId||form.closest('#shadowModalV153')?.dataset.electionId||'');
    const fallbackButton=document.querySelector('[data-buy-vote].v156-active-election');
    const resolvedElectionId=electionId||String(fallbackButton?.dataset.buyVote||'');
    if(!resolvedElectionId){
      toast('Не удалось определить выборы. Закрой окно и открой его снова.','error');
      return;
    }
    const submit=form.querySelector('button[type="submit"]');
    if(submit)submit.disabled=true;
    try{
      const response=await fetch('/government-v156/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({
          action:'bribe_create_message',
          chat_id:chatId,
          election_id:resolvedElectionId,
          target_user_id:Number(data.target_user_id),
          amount:Number(data.amount),
          secret_message:String(data.secret_message||'')
        })
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Предложение не отправлено.');
      toast(result.message||'Тайное предложение отправлено.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      closeModal();
      setTimeout(()=>location.reload(),350);
    }catch(error){
      toast(error?.message||'Предложение не отправлено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      if(submit)submit.disabled=false;
    }
  }

  document.addEventListener('click',event=>{
    const buy=event.target.closest?.('[data-buy-vote]');
    if(buy){
      document.querySelectorAll('[data-buy-vote]').forEach(button=>button.classList.remove('v156-active-election'));
      buy.classList.add('v156-active-election');
      window.__v156ElectionId=String(buy.dataset.buyVote||'');
      setTimeout(schedule,0);
      setTimeout(schedule,80);
    }
  },true);

  document.addEventListener('submit',event=>{
    if(event.target.id!=='buyVoteFormV156')return;
    event.preventDefault();
    event.stopImmediatePropagation();
    submitBribe(event.target);
  },true);

  const observer=new MutationObserver(schedule);
  observer.observe(document.documentElement,{subtree:true,childList:true});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadState()});
  window.addEventListener('focus',loadState);

  schedule();
  loadState();
  setInterval(()=>{if(!document.hidden)loadState()},12000);
})();