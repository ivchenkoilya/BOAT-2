(()=>{
  'use strict';
  if(window.__governmentSoldVoteHistoryV160)return;
  window.__governmentSoldVoteHistoryV160=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—';

  let snapshot=null;
  let loading=false;
  let queued=false;
  let frame=0;

  function electionsOpen(){
    return document.querySelector('[data-screen="elections"]')?.classList.contains('active');
  }

  function ensureHost(){
    const screen=document.querySelector('[data-screen="elections"]');
    const list=document.getElementById('electionList');
    if(!screen||!list)return null;
    let host=document.getElementById('soldVoteHistoryV160');
    if(!host){
      host=document.createElement('section');
      host.id='soldVoteHistoryV160';
      host.className='sold-vote-history-v160';
      list.insertAdjacentElement('afterend',host);
    }else if(host.previousElementSibling!==list){
      list.insertAdjacentElement('afterend',host);
    }
    return host;
  }

  function candidateLine(item){
    const username=String(item.candidate_username||'').trim();
    return username
      ?`${esc(item.candidate_name)} <span>@${esc(username)}</span>`
      :esc(item.candidate_name||`Telegram ID ${Number(item.candidate_id)||0}`);
  }

  function card(item){
    const convicted=String(item.status)==='convicted';
    return `<article class="sold-vote-card-v160 ${convicted?'convicted':''}">
      <div class="sold-vote-card-head-v160">
        <div><small>${esc(item.office_emoji||'🗳')} ${esc(item.office_title||'Выборы')}</small><h3>${candidateLine(item)}</h3></div>
        <span class="sold-vote-status-v160 ${convicted?'danger':''}">${esc(item.status_title||'Голос продан')}</span>
      </div>
      <div class="sold-vote-grid-v160">
        <div><small>КОМУ ОТДАН ГОЛОС</small><b>${candidateLine(item)}</b></div>
        <div><small>СУММА СДЕЛКИ</small><b>💰 ${fmt(item.amount)} влияния</b></div>
        <div><small>КОГДА ПРИНЯТО</small><b>${date(item.accepted_at)}</b></div>
        <div><small>ВЫБОРЫ</small><b>${esc(item.office_emoji||'🗳')} ${esc(item.office_title||'—')}</b></div>
      </div>
      ${convicted?'<p class="sold-vote-warning-v160">🚨 Подкуп был раскрыт расследованием. Запись сохранена в твоей личной истории.</p>':''}
    </article>`;
  }

  function render(){
    const host=ensureHost();
    if(!host)return;
    const history=Array.isArray(snapshot?.election_shadow_v153?.my_sold_vote_history)
      ?snapshot.election_shadow_v153.my_sold_vote_history
      :[];
    host.innerHTML=`
      <div class="sold-vote-title-v160">
        <div><small>ЛИЧНЫЙ ТЕНЕВОЙ АРХИВ</small><h2>😈 Мои проданные голоса</h2></div>
        <span>🔒 ВИДНО ТОЛЬКО ТЕБЕ</span>
      </div>
      <p class="sold-vote-description-v160">Здесь хранится, какому кандидату, за какую сумму и когда ты передал свой голос.</p>
      <div class="sold-vote-list-v160">${history.length?history.map(card).join(''):'<div class="sold-vote-empty-v160"><span>🕶</span><b>Проданных голосов пока нет</b><p>После принятия тайного предложения сделка появится здесь автоматически.</p></div>'}</div>`;
  }

  function schedule(){
    cancelAnimationFrame(frame);
    frame=requestAnimationFrame(render);
  }

  async function load(){
    if(!chatId)return;
    if(loading){queued=true;return;}
    loading=true;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}&_sold_vote_v160=${Date.now()}`,{cache:'no-store',headers});
      const data=await response.json();
      if(response.ok&&data?.ok){
        snapshot=data;
        schedule();
      }
    }catch(_error){}
    finally{
      loading=false;
      if(queued){queued=false;setTimeout(load,80);}
    }
  }

  document.addEventListener('click',event=>{
    if(event.target.closest?.('[data-tab="elections"]')){
      load();
      setTimeout(schedule,0);
      setTimeout(load,350);
    }
    if(event.target.closest?.('#refreshButton'))load();
  },true);

  const observer=new MutationObserver(()=>{
    if(electionsOpen())schedule();
  });
  observer.observe(document.documentElement,{subtree:true,childList:true});

  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden){load();schedule();}
  });
  window.addEventListener('focus',()=>{load();schedule();});

  load();
  setInterval(()=>{
    if(!document.hidden&&electionsOpen())load();
  },4000);
})();
