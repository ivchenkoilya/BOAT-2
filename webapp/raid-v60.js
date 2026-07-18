(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const initData=tg?.initData||'';
  const bossId=tg?.initDataUnsafe?.start_param||params.get('boss')||params.get('tgWebAppStartParam')||'';
  const API=`/boss-app/api/boss/state?boss_id=${encodeURIComponent(bossId)}`;

  let latest=null;
  let receivedAt=performance.now();
  let lastPhase=null;
  let lastComboAt=0;
  let failures=0;
  let recovering=false;
  let victoryHelpPatched=false;
  let pollBusy=false;

  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Math.max(0,Number(value)||0));
  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);

  const PHASES={
    2:{title:'ФАЗА II — ТРЕВОГА',icon:'◈',quote:'«Почему вы всё ещё смотрите не только на меня?»'},
    3:{title:'ФАЗА III — ЯРОСТЬ',icon:'✦',quote:'«Вы правда решили, что можете затмить меня?»'},
    4:{title:'ФАЗА IV — ПОСЛЕДНИЙ НАТИСК',icon:'♛',quote:'«Я останусь центром этой реальности любой ценой.»'}
  };

  const ABILITY_DETAILS={
    'НЕОЖИДАННО ОЖИТЬ':'600–800 урона · +25 HP · блок восстановления босса',
    'ПЫЛЬ В ГЛАЗА':'500–700 урона · разрушает Щит ЧСВ · отменяет следующую атаку',
    'ДАВЛЕНИЕ ТОЛПЫ':'750–950 урона · восстанавливает каждому герою 20 HP',
    'УКРАСТЬ СЦЕНУ':'850–1100 урона · даёт защиту от следующего ответа',
    'МИНУТА СЛАВЫ':'950–1250 урона · мгновенно сбрасывает обычную атаку',
    'УДАР ИЗ-ЗА КУЛИС':'1300–1800 урона · разбивает щит · возможен ответный урон',
    'КУЛЬМИНАЦИЯ':'Гарантированный сокрушительный критический удар',
    'ПРОБУЖДЕНИЕ ГЕРОЯ':'Усиленная способность текущей роли'
  };

  function ensureHud(){
    let pressure=document.getElementById('raidPressureV60');
    if(!pressure){
      pressure=document.createElement('section');
      pressure.id='raidPressureV60';
      pressure.className='raid-v60-pressure';
      pressure.innerHTML=`<div class="raid-v60-pressure-head"><span>⚡ ДАВЛЕНИЕ ОТРЯДА</span><strong id="raidPressureTextV60">0%</strong></div><div class="raid-v60-pressure-track"><i class="raid-v60-pressure-fill" id="raidPressureFillV60"></i></div><small>Атаки наполняют шкалу. При 100% отряд наносит совместный удар.</small>`;
      document.getElementById('bossStage')?.insertAdjacentElement('afterend',pressure);
    }

    const stage=document.getElementById('bossStage');
    if(stage&&!document.getElementById('raidWarningV60')){
      const warning=document.createElement('div');
      warning.id='raidWarningV60';
      warning.className='raid-v60-warning';
      warning.innerHTML='<span class="raid-v60-warning-icon" id="raidWarningIconV60">⚠</span><span class="raid-v60-warning-copy"><b id="raidWarningNameV60">БОСС ГОТОВИТ АТАКУ</b><small id="raidWarningHintV60">Приготовь защиту</small></span><strong class="raid-v60-warning-time" id="raidWarningTimeV60">7</strong>';
      stage.appendChild(warning);
    }

    if(!document.getElementById('raidConnectionV60')){
      const connection=document.createElement('div');
      connection.id='raidConnectionV60';
      connection.className='raid-v60-connection';
      connection.textContent='Переподключение к рейду…';
      document.body.appendChild(connection);
    }
  }

  function ensureEffects(){
    if(!document.getElementById('raidPhaseV60')){
      const phase=document.createElement('section');
      phase.id='raidPhaseV60';
      phase.className='raid-v60-phase-overlay';
      phase.innerHTML='<div class="raid-v60-phase-card"><div class="raid-v60-phase-sigil" id="raidPhaseIconV60">✦</div><small>ЦЕНТР ВСЕЛЕННОЙ МЕНЯЕТСЯ</small><h2 id="raidPhaseTitleV60">НОВАЯ ФАЗА</h2><p id="raidPhaseQuoteV60"></p></div>';
      document.body.appendChild(phase);
    }
    if(!document.getElementById('raidComboV60')){
      const combo=document.createElement('section');
      combo.id='raidComboV60';
      combo.className='raid-v60-combo-overlay';
      combo.innerHTML='<div class="raid-v60-combo-card"><div class="raid-v60-combo-sigil">⚡</div><small>ДАВЛЕНИЕ ДОСТИГЛО МАКСИМУМА</small><h2>КОЛЛЕКТИВНОЕ УНИЖЕНИЕ</h2><p id="raidComboDamageV60">Отряд наносит совместный удар</p></div>';
      document.body.appendChild(combo);
    }
  }

  function serverNow(){
    if(!latest)return Date.now()/1000;
    return Number(latest.now||Date.now()/1000)+(performance.now()-receivedAt)/1000;
  }

  function setConnection(mode,text){
    const node=document.getElementById('raidConnectionV60');
    if(!node)return;
    node.className=`raid-v60-connection ${mode||''} ${mode?'show':''}`;
    node.textContent=text||'';
  }

  function updatePressure(battle){
    const value=Math.max(0,Math.min(Number(battle?.pressure_max)||100,Number(battle?.pressure)||0));
    const max=Math.max(1,Number(battle?.pressure_max)||100);
    const percent=Math.round(value/max*100);
    const panel=document.getElementById('raidPressureV60');
    const fill=document.getElementById('raidPressureFillV60');
    const text=document.getElementById('raidPressureTextV60');
    if(fill)fill.style.width=`${percent}%`;
    if(text)text.textContent=`${percent}%`;
    panel?.classList.toggle('ready',percent>=80);
  }

  function warningTick(){
    const battle=latest?.battle;
    const warning=document.getElementById('raidWarningV60');
    if(!battle||!warning)return;
    const active=battle.status==='active'&&Number(battle.hp)>0;
    const seconds=Math.max(0,Math.ceil(Number(battle.next_action_at||0)-serverNow()));
    const visible=active&&seconds<=7;
    warning.classList.toggle('show',visible);
    warning.classList.toggle('urgent',visible&&seconds<=3);
    if(!visible)return;
    const name=battle.next_action_name||'Ответная атака';
    const target=battle.next_action_target||'отряд';
    const hint=battle.next_action_hint||`Цель: ${target}`;
    const icon=battle.next_action_icon||'⚠';
    const iconNode=document.getElementById('raidWarningIconV60');
    const nameNode=document.getElementById('raidWarningNameV60');
    const hintNode=document.getElementById('raidWarningHintV60');
    const timeNode=document.getElementById('raidWarningTimeV60');
    if(iconNode)iconNode.textContent=icon;
    if(nameNode)nameNode.textContent=name.toUpperCase();
    if(hintNode)hintNode.textContent=`${hint} · Цель: ${target}`;
    if(timeNode)timeNode.textContent=String(seconds);
  }

  function showPhase(phase){
    const info=PHASES[phase];
    const overlay=document.getElementById('raidPhaseV60');
    if(!info||!overlay)return;
    document.getElementById('raidPhaseIconV60').textContent=info.icon;
    document.getElementById('raidPhaseTitleV60').textContent=info.title;
    document.getElementById('raidPhaseQuoteV60').textContent=info.quote;
    overlay.classList.add('show');
    tg?.HapticFeedback?.notificationOccurred?.('warning');
    setTimeout(()=>overlay.classList.remove('show'),2200);
  }

  function showCombo(damage){
    const overlay=document.getElementById('raidComboV60');
    if(!overlay)return;
    document.getElementById('raidComboDamageV60').innerHTML=`Совместный удар нанёс <b>−${fmt(damage)} HP</b>`;
    overlay.classList.add('show');
    tg?.HapticFeedback?.notificationOccurred?.('success');
    setTimeout(()=>overlay.classList.remove('show'),1900);
  }

  function updateTransitions(battle){
    const phase=Number(battle?.hp)<=0?5:Math.max(1,Math.min(4,Number(battle?.phase)||1));
    if(lastPhase!==null&&phase>lastPhase&&phase<=4)showPhase(phase);
    lastPhase=phase;

    const comboAt=Number(battle?.last_combo_at)||0;
    if(comboAt>lastComboAt){
      if(serverNow()-comboAt<12)showCombo(Number(battle?.last_combo_damage)||0);
      lastComboAt=comboAt;
    }
  }

  function patchAbilityDetails(){
    const name=document.getElementById('abilityName');
    const hint=document.getElementById('abilityHint');
    if(!name||!hint)return;
    const detail=ABILITY_DETAILS[name.textContent.trim().toUpperCase()];
    if(detail&&hint.textContent!==detail)hint.textContent=detail;
  }

  function helpCard(icon,title,text,kind=''){
    return `<article class="page-help-card ${kind}"><span class="help-icon">${icon}</span><div><b>${title}</b><small>${text}</small></div></article>`;
  }

  function helpMarkup(){
    const controls=[
      ['⚔','Задеть эго','Обычный удар: 200–500. Критический удар: 800–1200. Перезарядка — 5 секунд.'],
      ['🛡','Защита','Полностью отражает следующую подходящую атаку босса. Перед атакой появляется предупреждение.'],
      ['✚','Лечение','Восстанавливает личное HP. Кнопка недоступна при полном здоровье.'],
      ['✦','Способность роли','Уникальный эффект роли. Точный эффект и диапазон отображаются прямо на карточке.'],
      ['⚡','Давление отряда','Удары наполняют общую шкалу. При 100% запускается коллективное унижение на 1200–1800 урона.'],
      ['📡','Переподключение','При потере сети приложение само продолжает попытки соединения и возвращает актуальное состояние.']
    ];
    const roles=[
      ['🪑','Декорация — Неожиданно ожить','600–800 урона, лечение себя и временный запрет восстановления босса.'],
      ['🌫','Пыль — Пыль в глаза','500–700 урона, уничтожение Щита ЧСВ и отмена следующей атаки.'],
      ['👥','Массовка — Давление толпы','750–950 урона и восстановление всему отряду по 20 HP.'],
      ['🎭','Второстепенная роль — Украсть сцену','850–1100 урона и защита от следующего ответа босса.'],
      ['🌟','Временный Главный герой — Минута славы','950–1250 урона и мгновенный сброс обычной атаки.'],
      ['💣','Саботажный Главный герой — Удар из-за кулис','1300–1800 урона, разрушение щита и риск ответного урона.'],
      ['👑','Честный Главный герой — Кульминация','Гарантированный сокрушительный критический удар.']
    ];
    const boss=[
      ['🪞','Все мне завидуют','Добавляет заряды Щита ЧСВ, которые ослабляют последующие удары.'],
      ['🗯','Тебя никто не слушает','Временно запрещает одному герою атаковать.'],
      ['🌌','Сокрушить самооценку','Сильная атака по одному случайному участнику.'],
      ['👥','Вы всего лишь массовка','Атака по всему отряду. Активная защита полностью отражает удар.'],
      ['♻','Возвращение внимания','Каждые пять минут восстанавливает боссу 25 HP, если эффект не заблокирован.']
    ];
    const phases=[
      ['1','Фаза I — Раскол эго','100–76% HP. Базовые атаки и первые заряды Щита ЧСВ.'],
      ['2','Фаза II — Тревога','75–51% HP. Босс начинает атаковать весь отряд.'],
      ['3','Фаза III — Ярость','50–26% HP. Появляется обесценивание, временно запрещающее атаки.'],
      ['4','Фаза IV — Последний натиск','25–1% HP. Максимальное давление и самые опасные комбинации.'],
      ['🏆','Победа — Эго разрушено','Открывается итоговое меню со статистикой, местом и начисленной наградой.']
    ];
    return `<div class="raid-v60-help-banner"><b>ТАКТИЧЕСКИЙ РЕЙД REALITY 60</b><br>Следи за предупреждением атаки, используй защиту вовремя и вместе с отрядом заполняй шкалу давления.</div>
      <h3 class="page-section-title">УПРАВЛЕНИЕ И МЕХАНИКИ</h3><div class="page-help-grid">${controls.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="page-section-title">СПОСОБНОСТИ РОЛЕЙ</h3><div class="page-help-grid">${roles.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="page-section-title">АТАКИ БОССА</h3><div class="page-help-grid">${boss.map(item=>helpCard(...item,'phase')).join('')}</div>
      <h3 class="page-section-title">ФАЗЫ БОССА</h3><div class="page-help-grid">${phases.map(item=>helpCard(...item,'phase')).join('')}</div>
      <h3 class="page-section-title">НАГРАДЫ ЗА ПОБЕДУ</h3><div class="reward-board"><div class="reward-row"><span>🥇</span><div><b>1-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+250</strong></div><div class="reward-row"><span>🥈</span><div><b>2-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+150</strong></div><div class="reward-row"><span>🥉</span><div><b>3-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+100</strong></div></div>
      <div class="raid-v60-help-tip">Если соединение пропало, не закрывай приложение: сверху появится статус переподключения, а бой автоматически продолжится после восстановления сети.</div>`;
  }

  function clearBlockingState(){
    const modal=document.getElementById('modal');
    modal?.classList.remove('open');
    modal?.setAttribute('aria-hidden','true');
    const victory=document.getElementById('raidVictoryV59');
    victory?.classList.remove('open');
    victory?.setAttribute('aria-hidden','true');
    const error=document.getElementById('errorScreen');
    if(error)error.hidden=true;
    document.body.classList.remove('combat-overlay-open','raid-victory-open');
    document.body.style.removeProperty('overflow');
  }

  function ensureRaidPage(){
    let page=document.getElementById('raidPage');
    if(page)return page;
    page=document.createElement('section');
    page.className='raid-page';
    page.id='raidPage';
    page.setAttribute('aria-hidden','true');
    page.innerHTML='<header class="raid-page-head"><button class="raid-page-back" type="button" aria-label="Назад">‹</button><div class="raid-page-title">СПРАВКА ПО РЕЙДУ</div><div class="raid-page-mark">✦</div></header><div class="raid-page-scroll"></div>';
    document.body.appendChild(page);
    page.querySelector('.raid-page-back')?.addEventListener('click',()=>{
      page.classList.remove('open');
      page.setAttribute('aria-hidden','true');
      document.body.classList.remove('raid-subpage-open','raid-help-v60-open');
      document.body.style.removeProperty('overflow');
      tg?.BackButton?.hide?.();
    });
    return page;
  }

  function openHelp(){
    clearBlockingState();
    const page=ensureRaidPage();
    const title=page.querySelector('.raid-page-title');
    const scroll=page.querySelector('.raid-page-scroll');
    page.dataset.page='help';
    if(title)title.textContent='СПРАВКА ПО РЕЙДУ';
    if(scroll){scroll.innerHTML=helpMarkup();scroll.scrollTop=0;}
    page.classList.add('open');
    page.setAttribute('aria-hidden','false');
    document.body.classList.add('raid-subpage-open','raid-help-v60-open');
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
    requestAnimationFrame(()=>{if(scroll)scroll.scrollTop=0;});
  }

  function installHelpButton(){
    const old=document.querySelector('.resource-info-top');
    if(!old||old.dataset.v60Help==='1')return;
    const button=old.cloneNode(true);
    button.removeAttribute('data-open-raid-page');
    button.dataset.v60Help='1';
    old.replaceWith(button);
    button.addEventListener('click',event=>{
      event.preventDefault();
      event.stopPropagation();
      openHelp();
    });
  }

  function patchVictoryHelp(){
    const button=document.querySelector('#raidVictoryV59 [data-victory-help]');
    if(!button||button.dataset.v60Patched==='1')return;
    button.dataset.v60Patched='1';
    button.addEventListener('click',()=>setTimeout(openHelp,0));
    victoryHelpPatched=true;
  }

  function enhanceVictory(victory){
    if(!victory?.visible)return;
    patchVictoryHelp();
    const overlay=document.getElementById('raidVictoryV59');
    const card=overlay?.querySelector('.raid-victory-card');
    if(!card)return;
    let stats=card.querySelector('.raid-v60-victory-stats');
    if(!stats){
      stats=document.createElement('div');
      stats.className='raid-v60-victory-stats';
      card.querySelector('.raid-victory-actions')?.before(stats);
    }
    const self=victory.self_stats||{};
    stats.innerHTML=`<div class="raid-v60-stat"><small>ТВОЙ УРОН</small><b>${fmt(self.damage)}</b></div><div class="raid-v60-stat"><small>АТАКИ</small><b>${fmt(self.attacks)}</b></div><div class="raid-v60-stat"><small>КРИТИЧЕСКИЕ УДАРЫ</small><b>${fmt(self.critical_hits)}</b></div><div class="raid-v60-stat"><small>ВОССТАНОВЛЕНО HP</small><b>${fmt(self.healing_done)}</b></div><div class="raid-v60-best"><b>ЛУЧШИЙ МОМЕНТ:</b> ${escapeHtml(self.best_moment||'Участие в победе')}<br>Общий урон отряда: <b>${fmt(victory.team_damage)}</b></div>`;

    const ranking=overlay.querySelector('#raidVictoryRanking');
    if(ranking&&Array.isArray(victory.rankings)){
      const medals=['🥇','🥈','🥉'];
      ranking.innerHTML=victory.rankings.slice(0,4).map((item,index)=>`<div class="raid-victory-row ${item.is_self?'self':''}"><span>${medals[index]||index+1}</span><div><b>${escapeHtml(item.name)}</b><small>${fmt(item.damage)} урона</small><small class="raid-v60-row-stats">${fmt(item.attacks)} атак · ${fmt(item.critical_hits)} критов · ${fmt(item.healing_done)} лечения</small></div><strong>${Number(item.reward)>0?`+${fmt(item.reward)}`:'—'}</strong></div>`).join('');
    }
  }

  function applyState(data){
    latest=data;
    receivedAt=performance.now();
    updatePressure(data.battle||{});
    updateTransitions(data.battle||{});
    enhanceVictory(data.victory);
    patchAbilityDetails();
    warningTick();
  }

  async function poll(){
    if(pollBusy||!bossId||!initData||document.hidden)return;
    pollBusy=true;
    try{
      const response=await fetch(API,{headers:{'X-Telegram-Init-Data':initData},cache:'no-store'});
      const data=await response.json();
      if(!response.ok||!data?.ok)throw new Error(data?.reason||'Сервер рейда недоступен');
      const hadFailures=failures>0;
      failures=0;
      applyState(data);
      if(hadFailures){
        setConnection('ok','Соединение восстановлено');
        setTimeout(()=>setConnection('',''),1500);
      }else{
        setConnection('','');
      }
      const error=document.getElementById('errorScreen');
      if(error&&!error.hidden&&!recovering){
        recovering=true;
        error.hidden=true;
        document.getElementById('retryButton')?.click();
        setTimeout(()=>{recovering=false;},2500);
      }
    }catch(_error){
      failures++;
      setConnection(failures>=3?'error':'','Переподключение к рейду…');
    }finally{
      pollBusy=false;
    }
  }

  ensureHud();
  ensureEffects();
  installHelpButton();
  patchAbilityDetails();

  const abilityName=document.getElementById('abilityName');
  if(abilityName)new MutationObserver(patchAbilityDetails).observe(abilityName,{childList:true,subtree:true,characterData:true});

  const page=ensureRaidPage();
  new MutationObserver(()=>{
    if(!page.classList.contains('open')){
      document.body.classList.remove('raid-help-v60-open');
      if(!document.body.classList.contains('raid-subpage-open'))document.body.style.removeProperty('overflow');
    }
  }).observe(page,{attributes:true,attributeFilter:['class','aria-hidden']});

  new MutationObserver(()=>{
    installHelpButton();
    patchVictoryHelp();
    if(latest?.victory)enhanceVictory(latest.victory);
  }).observe(document.body,{childList:true,subtree:true});

  window.addEventListener('online',()=>{setConnection('','Переподключение к рейду…');poll();});
  window.addEventListener('offline',()=>setConnection('error','Нет соединения. Бой продолжится после восстановления сети.'));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});

  setInterval(warningTick,250);
  setInterval(poll,2500);
  poll();
})();
