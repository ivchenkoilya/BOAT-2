(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  const originalFetch=window.fetch.bind(window);
  const runtime={state:null,renderTimer:null,busy:false,renderRetries:0};
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
  function scheduleRender(delay=90){
    clearTimeout(runtime.renderTimer);
    runtime.renderTimer=setTimeout(renderUpgrade,delay);
  }

  window.fetch=async(input,init={})=>{
    const url=sourceUrl(input);
    let changed=url;
    if(url.includes('/admin-v76/api/state')){
      changed=url.replace('/admin-v76/api/state','/admin-v89/api/state');
    }else if(url.includes('/admin-v76/api/action')&&bodyAction(init)==='game_attempts_set'){
      changed=url.replace('/admin-v76/api/action','/admin-v89/api/action');
    }
    const response=await originalFetch(replaceInput(input,changed),init);
    if(changed.includes('/admin-v89/api/state')){
      response.clone().json().then(data=>{
        if(data?.ok){
          runtime.state=data;
          runtime.renderRetries=0;
          scheduleRender();
        }
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

  function installVisualStyles(){
    if(document.getElementById('v90VisualStyles'))return;
    const style=document.createElement('style');
    style.id='v90VisualStyles';
    style.textContent=`
      [data-screen="games"] .section-head{align-items:center}
      [data-screen="games"] .section-head h2{font-size:25px}
      #v89AttemptPanel{position:relative;overflow:hidden;border-color:#865ac0;background:radial-gradient(circle at 100% 0,#5b278055,transparent 42%),linear-gradient(155deg,#251535,#100b19);box-shadow:0 18px 48px #0008,0 0 30px #934ad329}
      #v89AttemptPanel:before{content:"";position:absolute;width:150px;height:150px;right:-70px;top:-72px;border-radius:50%;background:#c568ff26;filter:blur(14px)}
      #v89AttemptPanel .panel-title{position:relative;margin-bottom:15px}
      #v89AttemptPanel .panel-title>span{background:linear-gradient(145deg,#6e31a5,#32154c);border-color:#a66bd2;box-shadow:0 0 22px #a65ce855}
      #v89AttemptPanel .panel-title b{font-size:17px}
      .v89-attempt-row{display:grid;grid-template-columns:1.15fr .85fr;gap:8px;position:relative}
      .v89-attempt-row select,.v89-attempt-row input{width:100%;min-height:52px;border:1px solid #5a3a76;background:#0b0812;color:var(--text);border-radius:14px;padding:0 12px;outline:none;font-weight:800}
      .v89-attempt-row input{font-size:20px;text-align:center;color:#ffe293}
      .v89-preset-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:7px;margin-top:9px;position:relative}
      .v89-preset-grid button{min-height:43px;border:1px solid #4e3566;border-radius:12px;background:#171020;color:#cfc3d8;font-weight:900}
      .v89-preset-grid button.active{border-color:#d2a6ff;color:#fff;background:linear-gradient(180deg,#623393,#331a4e);box-shadow:0 0 18px #9d54dc44}
      #v89ApplyAttempts{min-height:56px;font-size:13px;letter-spacing:.05em;background:linear-gradient(135deg,#c885ff,#7e3bc7)!important;border-color:#c99cf0!important;color:#fff!important;box-shadow:0 12px 30px #7f32b94a}
      .v89-note{margin:10px 2px 0;color:var(--muted);font-size:10px;line-height:1.5;position:relative}.v89-note b{color:var(--gold)}
      .v89-game-summary{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center;padding:13px 14px;margin:10px 0;border:1px solid #51346a;border-radius:17px;background:linear-gradient(135deg,#1f142e,#0e0a16)}
      .v89-game-summary small,.v89-game-summary b{display:block}.v89-game-summary small{font-size:9px;color:var(--gold);letter-spacing:.12em;font-weight:900}.v89-game-summary b{font-size:15px;margin-top:4px}.v89-summary-number{text-align:right}.v89-summary-number strong{display:block;font-size:22px;color:#f2d68a}.v89-summary-number span{font-size:9px;color:var(--muted)}
      #gameCards .game-card{border-color:#4b3261;background:radial-gradient(circle at 100% 0,#63318b30,transparent 38%),linear-gradient(155deg,#1d132a,#0d0914)}
      #gameCards .game-card.v89-custom{border-color:#8d5fb1;box-shadow:0 16px 42px #0007,0 0 26px #9a50cf22}
      .v89-limit-badge{display:inline-flex;margin-top:7px;padding:5px 8px;border:1px solid #9b68c7;border-radius:999px;color:#ecd7ff;background:#321948;font-size:8px;font-weight:900;letter-spacing:.08em}
      .v89-attempt-hero{display:flex;justify-content:space-between;align-items:end;margin-top:13px;padding:13px;border:1px solid #49315e;border-radius:15px;background:#0c0812}
      .v89-attempt-hero small,.v89-attempt-hero b{display:block}.v89-attempt-hero small{font-size:9px;color:var(--muted);letter-spacing:.08em}.v89-attempt-hero b{font-size:28px;margin-top:3px;line-height:1;color:#f8e7b2}.v89-attempt-hero span{font-size:10px;color:#b5a7c0;text-align:right}
      .v89-meter{height:8px;margin-top:9px;border:1px solid #3e2a4e;border-radius:999px;background:#09060e;overflow:hidden}.v89-meter i{display:block;height:100%;width:0;background:linear-gradient(90deg,#7d3dc2,#d18cff);transition:width .3s ease}
      .v89-card-give{width:100%;min-height:46px;margin-top:9px;border:1px solid #765096;border-radius:13px;background:linear-gradient(180deg,#3c2057,#20122f);color:#f0dcff;font-weight:900}
      .v89-source-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.v89-source{border:1px solid #382944;border-radius:13px;padding:10px;background:#0f0b17;min-width:0}.v89-source span{font-size:18px}.v89-source small,.v89-source b,.v89-source em{display:block}.v89-source small{color:var(--muted);font-size:9px;margin-top:5px}.v89-source b{font-size:15px;margin-top:2px}.v89-source em{font-style:normal;color:var(--gold);font-size:8px;margin-top:3px}
      @media(max-width:390px){.v89-attempt-row{grid-template-columns:1fr}.v89-preset-grid{grid-template-columns:1fr 1fr}}
    `;
    document.head.appendChild(style);
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
    if(button){button.disabled=true;button.textContent='СОХРАНЯЕМ ПАКЕТ…'}
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
      if(button){button.disabled=false;button.textContent='🎟 ВЫДАТЬ ПЕРСОНАЛЬНЫЕ ПОПЫТКИ'}
    }
  }

  function ensureGameSummary(){
    const metrics=document.getElementById('gameSystemMetrics');
    if(!metrics||document.getElementById('v89GameSummary'))return Boolean(metrics);
    const summary=document.createElement('div');
    summary.id='v89GameSummary';
    summary.className='v89-game-summary';
    summary.innerHTML='<div><small>ВЫБРАННЫЙ ИГРОК</small><b>Загрузка участника…</b></div><div class="v89-summary-number"><strong>—</strong><span>ПОПЫТОК ДОСТУПНО</span></div>';
    metrics.insertAdjacentElement('beforebegin',summary);
    return true;
  }

  function ensureAttemptPanel(){
    const cards=document.getElementById('gameCards');
    if(!cards||document.getElementById('v89AttemptPanel'))return Boolean(cards);
    const panel=document.createElement('article');
    panel.className='panel requires-user';
    panel.id='v89AttemptPanel';
    panel.innerHTML=`
      <div class="panel-title"><span>🎟</span><div><b>Выдать персональные попытки</b><small>Установи отдельный пакет выбранному игроку — хоть 10, хоть 1000</small></div></div>
      <label class="field-label" for="v89AttemptGame">Игра</label>
      <div class="v89-attempt-row">
        <select id="v89AttemptGame">
          <option value="all">Обе игры одновременно</option>
          <option value="rooftop">🌃 Только бег по крышам</option>
          <option value="heist">🏛 Только ограбление</option>
        </select>
        <input id="v89AttemptValue" type="number" min="0" max="2000000000" step="1" value="1000" inputmode="numeric" aria-label="Количество попыток">
      </div>
      <div class="v89-preset-grid">
        <button type="button" data-v89-preset="3">3</button>
        <button type="button" data-v89-preset="10">10</button>
        <button type="button" data-v89-preset="100">100</button>
        <button type="button" data-v89-preset="1000" class="active">1000</button>
      </div>
      <button class="wide-button positive" id="v89ApplyAttempts" type="button">🎟 ВЫДАТЬ ПЕРСОНАЛЬНЫЕ ПОПЫТКИ</button>
      <p class="v89-note">После выдачи игрок увидит, например, <b>1000/1000</b>. Новый пакет сбрасывает только использованные попытки; рекорды и полученное влияние сохраняются.</p>`;
    cards.parentNode.insertBefore(panel,cards);
    return true;
  }

  function ensureEconomyPanel(){
    const metrics=document.getElementById('knowledgeMetrics');
    if(!metrics||document.getElementById('v89EconomyPanel'))return Boolean(metrics);
    const panel=document.createElement('article');
    panel.className='panel requires-user';
    panel.id='v89EconomyPanel';
    panel.innerHTML='<div class="panel-title"><span>📈</span><div><b>Источники прогресса</b><small>Откуда игрок получает очки Древа и карьерное влияние</small></div></div><div id="v89EconomyGrid" class="v89-source-grid"></div>';
    metrics.insertAdjacentElement('afterend',panel);
    return true;
  }

  function renderGameSummary(){
    const summary=document.getElementById('v89GameSummary');
    if(!summary)return;
    const target=runtime.state?.target;
    const games=Object.values(runtime.state?.games?.games||{});
    const total=games.reduce((sum,game)=>sum+Number(game.attempts_left||0),0);
    summary.querySelector('b').textContent=target?.full_name||target?.name||'Участник не выбран';
    summary.querySelector('strong').textContent=fmt(total);
  }

  function renderGameLimits(){
    const entries=Object.entries(runtime.state?.games?.games||{});
    const cards=[...document.querySelectorAll('#gameCards .game-card')];
    entries.forEach(([key,game],index)=>{
      const card=cards[index];
      if(!card)return;
      const limit=Math.max(0,Number(game.attempt_limit||3));
      const left=Math.max(0,Number(game.attempts_left||0));
      const percent=limit>0?Math.max(0,Math.min(100,left/limit*100)):0;
      card.classList.toggle('v89-custom',Boolean(game.custom_attempts));
      const oldAttemptStat=card.querySelector('.game-stat');
      if(oldAttemptStat)oldAttemptStat.style.display='none';
      let hero=card.querySelector('.v89-attempt-hero');
      if(!hero){
        hero=document.createElement('div');
        hero.className='v89-attempt-hero';
        hero.innerHTML='<div><small>ОСТАЛОСЬ ПОПЫТОК</small><b>—</b></div><span>из —<br>доступных</span>';
        const stats=card.querySelector('.game-stats');
        stats?.insertAdjacentElement('beforebegin',hero);
      }
      hero.querySelector('b').textContent=fmt(left);
      hero.querySelector('span').innerHTML=`из ${fmt(limit)}<br>доступных`;
      let meter=card.querySelector('.v89-meter');
      if(!meter){meter=document.createElement('div');meter.className='v89-meter';meter.innerHTML='<i></i>';hero.insertAdjacentElement('afterend',meter)}
      meter.querySelector('i').style.width=`${percent}%`;
      let badge=card.querySelector('.v89-limit-badge');
      if(game.custom_attempts){
        if(!badge){badge=document.createElement('span');badge.className='v89-limit-badge';card.querySelector('.game-head>div')?.appendChild(badge)}
        badge.textContent=`ПЕРСОНАЛЬНЫЙ ПАКЕТ · ${fmt(limit)}`;
      }else badge?.remove();
      let give=card.querySelector('.v89-card-give');
      if(!give){
        give=document.createElement('button');
        give.type='button';
        give.className='v89-card-give';
        give.dataset.v89Game=key;
        give.textContent='🎟 ВЫДАТЬ ПОПЫТКИ ЭТОЙ ИГРЕ';
        card.appendChild(give);
      }
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
    const markup=items.map(([icon,label,value,note])=>`<div class="v89-source"><span>${icon}</span><small>${esc(label)}</small><b>${esc(value)}</b><em>${esc(note)}</em></div>`).join('');
    if(grid.innerHTML!==markup)grid.innerHTML=markup;
  }

  function renderHistoryNames(){
    document.querySelectorAll('#historyList .history-item header b').forEach(node=>{
      if(node.textContent.trim()==='game_attempts_set')node.textContent='Выдача игровых попыток';
    });
  }

  function renderUpgrade(){
    installVisualStyles();
    const summaryReady=ensureGameSummary();
    const attemptsReady=ensureAttemptPanel();
    const economyReady=ensureEconomyPanel();
    renderGameSummary();
    renderGameLimits();
    renderSources();
    renderHistoryNames();
    const version=document.getElementById('versionText');
    if(version&&version.textContent!=='Reality 89 · Pro')version.textContent='Reality 89 · Pro';
    if((!summaryReady||!attemptsReady||!economyReady)&&runtime.renderRetries<15){
      runtime.renderRetries+=1;
      scheduleRender(140);
    }
  }

  document.addEventListener('click',event=>{
    const preset=event.target.closest('[data-v89-preset]');
    if(preset){
      document.querySelectorAll('[data-v89-preset]').forEach(node=>node.classList.remove('active'));
      preset.classList.add('active');
      const input=document.getElementById('v89AttemptValue');
      if(input)input.value=preset.dataset.v89Preset;
      tg?.HapticFeedback?.selectionChanged?.();
      return;
    }
    const gameButton=event.target.closest('[data-v89-game]');
    if(gameButton){
      const select=document.getElementById('v89AttemptGame');
      if(select)select.value=gameButton.dataset.v89Game;
      document.getElementById('v89AttemptPanel')?.scrollIntoView({behavior:'smooth',block:'center'});
      document.getElementById('v89AttemptValue')?.focus();
      return;
    }
    if(event.target.closest('#v89ApplyAttempts')){
      setAttempts(Number(document.getElementById('v89AttemptValue')?.value),document.getElementById('v89AttemptGame')?.value||'all');
    }
  },true);

  document.addEventListener('DOMContentLoaded',()=>{
    installVisualStyles();
    scheduleRender();
  });
})();
