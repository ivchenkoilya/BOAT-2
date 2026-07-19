(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  const originalFetch=window.fetch.bind(window);
  const runtime={state:null,renderTimer:null,busy:false};
  window.AdminV89=runtime;

  function sourceUrl(input){
    if(typeof input==='string'||input instanceof URL)return String(input);
    if(input instanceof Request)return input.url;
    return '';
  }
  function replaceInput(input,url){
    if(typeof input==='string'||input instanceof URL)return url;
    if(input instanceof Request)return new Request(url,input);
    return input;
  }
  function bodyAction(init){
    try{return JSON.parse(String(init?.body||'{}')).action||''}catch{return ''}
  }
  function scheduleRender(){
    clearTimeout(runtime.renderTimer);
    runtime.renderTimer=setTimeout(renderUpgrade,90);
  }

  window.fetch=async(input,init={})=>{
    let url=sourceUrl(input);
    let changed=url;
    if(url.includes('/admin-v76/api/state')){
      changed=url.replace('/admin-v76/api/state','/admin-v89/api/state');
    }else if(url.includes('/admin-v76/api/action')&&bodyAction(init)==='game_attempts_set'){
      changed=url.replace('/admin-v76/api/action','/admin-v89/api/action');
    }
    const response=await originalFetch(replaceInput(input,changed),init);
    if(changed.includes('/admin-v89/api/state')){
      response.clone().json().then(data=>{
        if(data?.ok){runtime.state=data;scheduleRender()}
      }).catch(()=>{});
    }
    return response;
  };

  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'
  }[char]));

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node.__v89Timer);
    node.__v89Timer=setTimeout(()=>node.className='toast',3600);
  }

  function selectedIds(){
    const state=runtime.state||{};
    return {
      chat_id:Number(state.selected_chat?.chat_id||localStorage.getItem('admin76Chat')||0),
      user_id:Number(state.target?.user_id||localStorage.getItem('admin76User')||0)
    };
  }

  async function setAttempts(value,game='all'){
    const ids=selectedIds();
    if(!ids.chat_id||!ids.user_id){toast('Сначала выбери беседу и участника.','error');return}
    const amount=Number(value);
    if(!Number.isInteger(amount)||amount<0||amount>2000000000){
      toast('Введи целое число от 0 до 2 000 000 000.','error');return;
    }
    if(runtime.busy)return;
    runtime.busy=true;
    const button=document.getElementById('v89ApplyAttempts');
    if(button){button.disabled=true;button.textContent='СОХРАНЯЕМ…'}
    try{
      const response=await originalFetch('/admin-v89/api/action',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},
        body:JSON.stringify({action:'game_attempts_set',...ids,game,value:amount})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось выдать попытки.');
      toast(data.message||`Выдано ${fmt(amount)} попыток.`,'success');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('refreshButton')?.click();
    }catch(error){
      toast(error.message||'Не удалось выдать попытки.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      runtime.busy=false;
      if(button){button.disabled=false;button.textContent='🎟 ВЫДАТЬ ПАКЕТ'}
    }
  }

  function ensureAttemptPanel(){
    const screen=document.querySelector('[data-screen="games"]');
    const cards=document.getElementById('gameCards');
    if(!screen||!cards||document.getElementById('v89AttemptPanel'))return;
    const panel=document.createElement('article');
    panel.className='panel requires-user';
    panel.id='v89AttemptPanel';
    panel.innerHTML=`
      <div class="panel-title"><span>🎟</span><div><b>Персональные попытки</b><small>Любое число для выбранного игрока — хоть 10, хоть 1000 или больше</small></div></div>
      <label class="field-label" for="v89AttemptGame">Куда выдать</label>
      <div class="v89-attempt-row">
        <select id="v89AttemptGame">
          <option value="all">Обе игры</option>
          <option value="rooftop">🌃 Бег по крышам</option>
          <option value="heist">🏛 Ограбление хранилища</option>
        </select>
        <input id="v89AttemptValue" type="number" min="0" max="2000000000" step="1" value="1000" inputmode="numeric">
      </div>
      <div class="v89-preset-grid">
        <button type="button" data-v89-preset="3">3</button>
        <button type="button" data-v89-preset="10">10</button>
        <button type="button" data-v89-preset="100">100</button>
        <button type="button" data-v89-preset="1000">1000</button>
      </div>
      <button class="wide-button positive" id="v89ApplyAttempts" type="button">🎟 ВЫДАТЬ ПАКЕТ</button>
      <p class="v89-note">После выдачи будет показано, например, <b>1000/1000</b>. Использованные попытки обнулятся, но рекорды, результаты и уже выданное влияние сохранятся.</p>`;
    cards.parentNode.insertBefore(panel,cards);
  }

  function ensureEconomyPanel(){
    const screen=document.querySelector('[data-screen="knowledge"]');
    const metrics=document.getElementById('knowledgeMetrics');
    if(!screen||!metrics||document.getElementById('v89EconomyPanel'))return;
    const panel=document.createElement('article');
    panel.className='panel requires-user';
    panel.id='v89EconomyPanel';
    panel.innerHTML='<div class="panel-title"><span>📈</span><div><b>Источники прогресса</b><small>Откуда игрок получает очки Древа и карьерное влияние</small></div></div><div id="v89EconomyGrid" class="v89-source-grid"></div>';
    metrics.insertAdjacentElement('afterend',panel);
  }

  function renderGameLimits(){
    const games=runtime.state?.games?.games||{};
    const cards=[...document.querySelectorAll('#gameCards .game-card')];
    Object.values(games).forEach((game,index)=>{
      const card=cards[index];
      if(!card)return;
      const value=card.querySelector('.game-stat b');
      if(value)value.textContent=`${fmt(game.attempts_left)}/${fmt(game.attempt_limit||3)}`;
      let badge=card.querySelector('.v89-limit-badge');
      if(game.custom_attempts){
        if(!badge){
          badge=document.createElement('span');badge.className='v89-limit-badge';
          card.querySelector('.game-head>div')?.appendChild(badge);
        }
        badge.textContent=`АДМИН-ПАКЕТ ${fmt(game.attempt_limit)}`;
      }else badge?.remove();
    });
  }

  function renderSources(){
    const source=runtime.state?.knowledge?.sources_v89||runtime.state?.economy_v89||{};
    const grid=document.getElementById('v89EconomyGrid');
    if(!grid)return;
    const items=[
      ['🏆','Карьерное влияние',fmt(source.career||0),'1 очко за каждые 500'],
      ['🌳','Очки от влияния',fmt(source.entitled||0),'включая стартовые'],
      ['🎮','Игры за неделю',`${fmt(source.game_career_week||0)}/2 000`,'до 4 очков Древа'],
      ['🎯','Задания за неделю',`${fmt(source.task_points_week||0)}/4`,'прямые очки'],
      ['📅','Активные дни',`${fmt(source.activity_points_week||0)}/3`,'за 2, 4 и 6 дней'],
      ['🎖','Достижения',fmt(source.achievement_points||0),'разовые очки'],
      ['🌌','Побед над боссом',fmt(source.boss_wins||0),'всего'],
      ['🕹','Победных игр',fmt(source.game_wins||0),'всего']
    ];
    grid.innerHTML=items.map(([icon,label,value,note])=>`<div class="v89-source"><span>${icon}</span><small>${esc(label)}</small><b>${esc(value)}</b><em>${esc(note)}</em></div>`).join('');
  }

  function renderUpgrade(){
    ensureAttemptPanel();
    ensureEconomyPanel();
    renderGameLimits();
    renderSources();
    const version=document.getElementById('versionText');
    if(version)version.textContent=runtime.state?.version||'Reality 89';
  }

  document.addEventListener('click',event=>{
    const preset=event.target.closest('[data-v89-preset]');
    if(preset){
      const input=document.getElementById('v89AttemptValue');
      if(input)input.value=preset.dataset.v89Preset;
      setAttempts(Number(preset.dataset.v89Preset),document.getElementById('v89AttemptGame')?.value||'all');
      return;
    }
    if(event.target.closest('#v89ApplyAttempts')){
      setAttempts(Number(document.getElementById('v89AttemptValue')?.value),document.getElementById('v89AttemptGame')?.value||'all');
    }
  },true);

  const observer=new MutationObserver(()=>scheduleRender());
  document.addEventListener('DOMContentLoaded',()=>{
    observer.observe(document.body,{childList:true,subtree:true});
    scheduleRender();
  });
})();
