(()=>{
  'use strict';
  if(window.__governmentElectionButtonVisibilityV158)return;
  window.__governmentElectionButtonVisibilityV158=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);

  let state=null;
  let loading=false;
  let activeElection='';
  let frame=0;
  let timer=0;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__v158Timer);
    node.__v158Timer=setTimeout(()=>node.className='toast',3900);
  }

  function currentUserId(){return Number(state?.user?.user_id)||0}

  function campaignFor(electionId){
    return (state?.election_shadow_v153?.campaigns||[]).find(item=>String(item.election_id)===String(electionId));
  }

  function isCandidate(election){
    const userId=currentUserId();
    return userId>0&&(election?.candidates||[]).some(candidate=>Number(candidate.user_id)===userId);
  }

  function electionsScreenOpen(){
    return document.querySelector('[data-screen="elections"]')?.classList.contains('active');
  }

  function ensureCandidateButtons(){
    if(!state)return;
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 158';

    const elections=state.elections||[];
    const cards=[...document.querySelectorAll('#electionList>.election-card')];

    cards.forEach((card,index)=>{
      const election=elections[index];
      if(!election)return;
      const allowed=String(election.phase)==='voting'&&isCandidate(election);
      let box=card.querySelector('.v153-campaign-box');

      if(!allowed){
        if(box)box.remove();
        return;
      }

      const campaign=campaignFor(election.election_id);
      const status=campaign
        ?`Принято ${fmt(campaign.accepted)} · потрачено ${fmt(campaign.spent)}`
        :'Предложений пока нет';

      if(!box){
        card.insertAdjacentHTML('beforeend',`<div class="v153-campaign-box" data-v158-campaign="${esc(election.election_id)}"><div><small>ТЕНЕВАЯ КАМПАНИЯ КАНДИДАТА</small><b>${status}</b></div><button class="v153-buy-vote" type="button" data-v158-bribe="${esc(election.election_id)}">😈 ПОДКУПИТЬ ГОЛОСА</button></div>`);
        box=card.querySelector('.v153-campaign-box');
      }

      box.dataset.v158Campaign=String(election.election_id);
      const small=box.querySelector('small');
      if(small)small.textContent='ТЕНЕВАЯ КАМПАНИЯ КАНДИДАТА';
      const bold=box.querySelector('b');
      if(bold)bold.textContent=status;
      let button=box.querySelector('button');
      if(!button){
        button=document.createElement('button');
        box.appendChild(button);
      }
      button.type='button';
      button.className='v153-buy-vote';
      button.dataset.v158Bribe=String(election.election_id);
      button.removeAttribute('data-buy-vote');
      button.textContent='😈 ПОДКУПИТЬ ГОЛОСА';
    });
  }

  function scheduleEnsure(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(ensureCandidateButtons);
  }

  async function loadState(){
    if(!chatId||loading)return;
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});
      const data=await response.json();
      if(response.ok&&data?.ok){
        state=data;
        scheduleEnsure();
        setTimeout(scheduleEnsure,80);
        setTimeout(scheduleEnsure,260);
      }
    }catch(_error){}
    finally{loading=false}
  }

  function userOptions(){
    const me=currentUserId();
    return (state?.eligible_users||[])
      .filter(person=>Number(person.user_id)!==me)
      .map(person=>`<option value="${Number(person.user_id)}">${esc(person.name)} · 💰 ${fmt(person.points)} · ⭐ ${fmt(person.career_points)}</option>`)
      .join('');
  }

  function ensureModal(){
    let modal=document.getElementById('shadowModalV158');
    if(modal)return modal;
    document.body.insertAdjacentHTML('beforeend','<div class="v153-modal" id="shadowModalV158" hidden><section class="v153-sheet"><button class="v153-close" type="button" data-v158-close>×</button><div id="shadowModalContentV158"></div></section></div>');
    return document.getElementById('shadowModalV158');
  }

  function openModal(electionId){
    const election=(state?.elections||[]).find(item=>String(item.election_id)===String(electionId));
    if(!election||String(election.phase)!=='voting'||!isCandidate(election)){
      toast('Подкуп доступен только зарегистрированному кандидату во время голосования.','error');
      loadState();
      return;
    }
    activeElection=String(electionId);
    const modal=ensureModal();
    const host=document.getElementById('shadowModalContentV158');
    host.innerHTML=`<div class="v153-modal-icon">😈</div><small>ТЕНЕВАЯ ИЗБИРАТЕЛЬНАЯ КАМПАНИЯ</small><h2>Подкупить голоса</h2><p>Получатель увидит сумму, название выборов и скрытое сообщение. Имя кандидата останется неизвестным.</p><form id="buyVoteFormV158"><div class="field"><label>ПОЛУЧАТЕЛЬ ПРЕДЛОЖЕНИЯ</label><select name="target_user_id" required>${userOptions()}</select></div><div class="field"><label>СУММА · 1 000–500 000</label><input name="amount" type="number" min="1000" max="500000" step="1000" value="10000" required></div><div class="field v156-message-field"><label>СКРЫТОЕ СООБЩЕНИЕ · ДО 300 СИМВОЛОВ</label><textarea name="secret_message" maxlength="300" placeholder="Например: Поддержи меня — о нашей сделке никто не узнает"></textarea><small class="hint">Сообщение увидит только получатель. Имя кандидата останется скрытым.</small></div><button class="v153-buy-confirm wide" type="submit">😈 ОТПРАВИТЬ ТАЙНОЕ ПРЕДЛОЖЕНИЕ</button></form><div class="v153-warning">Предложение действует до завершения выборов. При принятии голос будет автоматически отдан тебе и заблокирован.</div>`;
    modal.hidden=false;
    document.body.classList.add('v153-modal-open');
  }

  function closeModal(){
    const modal=document.getElementById('shadowModalV158');
    if(modal)modal.hidden=true;
    document.body.classList.remove('v153-modal-open');
    activeElection='';
  }

  async function submitOffer(form){
    const values=Object.fromEntries(new FormData(form).entries());
    const submit=form.querySelector('button[type="submit"]');
    if(submit)submit.disabled=true;
    try{
      const response=await fetch('/government-v156/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({
          action:'bribe_create_message',chat_id:chatId,election_id:activeElection,
          target_user_id:Number(values.target_user_id),amount:Number(values.amount),
          secret_message:String(values.secret_message||'')
        })
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Предложение не отправлено.');
      toast(result.message||'Тайное предложение отправлено.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      closeModal();
      await loadState();
    }catch(error){
      toast(error?.message||'Предложение не отправлено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      if(submit)submit.disabled=false;
    }
  }

  window.addEventListener('click',event=>{
    const button=event.target.closest?.('[data-v158-bribe]');
    if(button){
      event.preventDefault();
      event.stopImmediatePropagation();
      openModal(button.dataset.v158Bribe);
      return;
    }
    if(event.target.closest?.('[data-v158-close]')||event.target.id==='shadowModalV158'){
      event.preventDefault();
      event.stopImmediatePropagation();
      closeModal();
      return;
    }
    if(event.target.closest?.('[data-tab="elections"]')){
      loadState();
      setTimeout(scheduleEnsure,0);
      setTimeout(scheduleEnsure,100);
      setTimeout(scheduleEnsure,350);
      setTimeout(scheduleEnsure,800);
    }
  },true);

  window.addEventListener('submit',event=>{
    if(event.target.id!=='buyVoteFormV158')return;
    event.preventDefault();
    event.stopImmediatePropagation();
    submitOffer(event.target);
  },true);

  const observer=new MutationObserver(()=>{
    if(electionsScreenOpen())scheduleEnsure();
  });
  observer.observe(document.documentElement,{subtree:true,childList:true});

  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden){loadState();scheduleEnsure()}
  });
  window.addEventListener('focus',()=>{loadState();scheduleEnsure()});

  loadState();
  clearInterval(timer);
  timer=setInterval(()=>{
    if(!document.hidden){
      if(electionsScreenOpen())ensureCandidateButtons();
      loadState();
    }
  },1500);
})();