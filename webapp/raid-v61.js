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
  let failures=0;
  let pollBusy=false;
  const previousDamage=new Map();

  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Math.max(0,Number(value)||0));
  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);

  const PHASES={
    2:{title:'ФАЗА II — ТРЕВОГА',quote:'«Почему вы всё ещё смотрите не только на меня?»'},
    3:{title:'ФАЗА III — ЯРОСТЬ',quote:'«Вы правда решили, что можете затмить меня?»'},
    4:{title:'ФАЗА IV — ПОСЛЕДНИЙ НАТИСК',quote:'«Я останусь центром этой реальности любой ценой.»'}
  };

  const ABILITY_DETAILS={
    'НЕОЖИДАННО ОЖИТЬ':'600–800 урона · лечение · блок восстановления босса',
    'ПЫЛЬ В ГЛАЗА':'500–700 урона · разрушает щит · отменяет следующую атаку',
    'ДАВЛЕНИЕ ТОЛПЫ':'750–950 урона · восстанавливает HP всему отряду',
    'УКРАСТЬ СЦЕНУ':'850–1100 урона · даёт защиту от следующего ответа',
    'МИНУТА СЛАВЫ':'950–1250 урона · мгновенно сбрасывает обычную атаку',
    'УДАР ИЗ-ЗА КУЛИС':'1300–1800 урона · разрушает щит · возможен ответный урон',
    'КУЛЬМИНАЦИЯ':'Гарантированный сокрушительный критический удар',
    'ПРОБУЖДЕНИЕ ГЕРОЯ':'Усиленная способность текущей роли'
  };

  function serverNow(){
    if(!latest)return Date.now()/1000;
    return Number(latest.now||Date.now()/1000)+(performance.now()-receivedAt)/1000;
  }

  function ensureInterface(){
    const bossImage=document.getElementById('bossImage');
    bossImage?.classList.add('raid-v61-alive');

    if(!document.getElementById('raidPressureV61')){
      const panel=document.createElement('section');
      panel.id='raidPressureV61';
      panel.className='raid-v61-pressure';
      panel.innerHTML=`
        <div class="raid-v61-pressure-title"><span>⚡ ДАВЛЕНИЕ ОТРЯДА</span><strong id="raidPressureTextV61">0%</strong></div>
        <div class="raid-v61-pressure-track"><i id="raidPressureFillV61"></i></div>
        <small>Шкала заполняется медленно и ослабевает без постоянных атак.</small>`;
      document.getElementById('bossStage')?.insertAdjacentElement('afterend',panel);
    }

    if(!document.getElementById('raidWarningV61')){
      const warning=document.createElement('div');
      warning.id='raidWarningV61';
      warning.className='raid-v61-warning';
      warning.innerHTML=`<span id="raidWarningIconV61">⚠</span><div><b id="raidWarningNameV61">БОСС ГОТОВИТ АТАКУ</b><small id="raidWarningHintV61">Приготовь защиту</small></div><strong id="raidWarningTimeV61">7</strong>`;
      document.getElementById('bossStage')?.appendChild(warning);
    }

    if(!document.getElementById('raidImpactV61')){
      const impact=document.createElement('div');
      impact.id='raidImpactV61';
      impact.className='raid-v61-impact';
      impact.innerHTML='<div class="raid-v61-impact-ring"></div><b id="raidImpactTextV61">УДАР БОССА</b>';
      document.body.appendChild(impact);
    }

    if(!document.getElementById('raidPhaseV61')){
      const phase=document.createElement('section');
      phase.id='raidPhaseV61';
      phase.className='raid-v61-phase';
      phase.innerHTML='<div><small>ЦЕНТР ВСЕЛЕННОЙ МЕНЯЕТСЯ</small><h2 id="raidPhaseTitleV61">НОВАЯ ФАЗА</h2><p id="raidPhaseQuoteV61"></p></div>';
      document.body.appendChild(phase);
    }

    if(!document.getElementById('raidConnectionV61')){
      const connection=document.createElement('div');
      connection.id='raidConnectionV61';
      connection.className='raid-v61-connection';
      document.body.appendChild(connection);
    }

    ensureHelpOverlay();
    installHelpButton();
  }

  function helpMarkup(){
    return `
      <div class="raid-v61-help-intro">
        <b>ТАКТИЧЕСКИЙ РЕЙД · REALITY 61</b>
        <span>У босса 75 000 HP. Следи за предупреждением атаки, защищайся вовремя и поддерживай общий темп отряда.</span>
      </div>

      <h3>БОЙ И ДАВЛЕНИЕ ОТРЯДА</h3>
      <article><i>⚔</i><div><b>Задеть эго</b><small>Обычный удар: 200–500. Критический удар: 800–1200. Перезарядка — 5 секунд.</small></div></article>
      <article><i>⚡</i><div><b>Давление отряда</b><small>Обычный удар добавляет 2 единицы, крит — ещё 1, способность роли — 5. Максимум шкалы — 120. Без новых атак давление постепенно уменьшается.</small></div></article>
      <article><i>💥</i><div><b>Коллективное унижение</b><small>При полном заполнении шкалы отряд автоматически наносит дополнительные 1200–1800 урона.</small></div></article>
      <article><i>🛡</i><div><b>Защита</b><small>Полностью отражает следующую подходящую атаку. За 7 секунд до удара показывается его название и цель.</small></div></article>
      <article><i>✚</i><div><b>Лечение</b><small>Восстанавливает личное HP героя. При полном здоровье кнопка недоступна.</small></div></article>

      <h3>НАГРАДЫ ЗА ПОБЕДУ</h3>
      <div class="raid-v61-reward-row"><span>🥇</span><div><b>1-е место</b><small>600 влияния и 4 осколка знаний</small></div></div>
      <div class="raid-v61-reward-row"><span>🥈</span><div><b>2-е место</b><small>400 влияния и 3 осколка знаний</small></div></div>
      <div class="raid-v61-reward-row"><span>🥉</span><div><b>3-е место</b><small>250 влияния и 2 осколка знаний</small></div></div>
      <div class="raid-v61-reward-row"><span>⚔️</span><div><b>Активное участие</b><small>75 влияния и 1 осколок знаний каждому участнику ниже топ-3, если он нанёс хотя бы один удар.</small></div></div>
      <div class="raid-v61-reward-row"><span>💀</span><div><b>Последний удар</b><small>Дополнительно 100 влияния и 1 осколок знаний.</small></div></div>

      <h3>ОСКОЛКИ ЗНАНИЙ</h3>
      <article><i>🌳</i><div><b>Преобразование</b><small>Каждые 5 осколков автоматически превращаются в 1 очко древа.</small></div></article>
      <article><i>📅</i><div><b>Недельное ограничение</b><small>За рейдовые осколки можно получить не больше 3 очков древа за неделю. Лишние осколки сохраняются.</small></div></article>

      <h3>СТАБИЛЬНОСТЬ</h3>
      <article><i>📡</i><div><b>Автопереподключение</b><small>При временной потере сети Mini App самостоятельно загрузит актуальное состояние боя после восстановления соединения.</small></div></article>`;
  }

  function ensureHelpOverlay(){
    if(document.getElementById('raidHelpV61'))return;
    const overlay=document.createElement('section');
    overlay.id='raidHelpV61';
    overlay.className='raid-v61-help';
    overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML=`
      <header><button type="button" data-v61-help-close aria-label="Назад">‹</button><b>СПРАВКА ПО РЕЙДУ</b><span>✦</span></header>
      <div class="raid-v61-help-scroll">${helpMarkup()}</div>`;
    document.body.appendChild(overlay);
  }

  function clearBlockingLayers(){
    const oldPage=document.getElementById('raidPage');
    oldPage?.classList.remove('open');
    oldPage?.setAttribute('aria-hidden','true');
    const modal=document.getElementById('modal');
    modal?.classList.remove('open');
    modal?.setAttribute('aria-hidden','true');
    const victory=document.getElementById('raidVictoryV59');
    victory?.classList.remove('open');
    victory?.setAttribute('aria-hidden','true');
    const error=document.getElementById('errorScreen');
    if(error)error.hidden=true;
    document.body.classList.remove('raid-subpage-open','combat-overlay-open','raid-victory-open');
    document.body.style.removeProperty('overflow');
  }

  function openHelp(){
    ensureHelpOverlay();
    clearBlockingLayers();
    const overlay=document.getElementById('raidHelpV61');
    const scroll=overlay?.querySelector('.raid-v61-help-scroll');
    if(scroll){
      scroll.innerHTML=helpMarkup();
      scroll.scrollTop=0;
    }
    overlay?.classList.add('open');
    overlay?.setAttribute('aria-hidden','false');
    document.body.classList.add('raid-v61-help-open');
    document.body.style.overflow='hidden';
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function closeHelp(){
    const overlay=document.getElementById('raidHelpV61');
    overlay?.classList.remove('open');
    overlay?.setAttribute('aria-hidden','true');
    document.body.classList.remove('raid-v61-help-open');
    document.body.style.removeProperty('overflow');
    tg?.BackButton?.hide?.();
  }

  function installHelpButton(){
    const old=document.querySelector('.resource-info-top');
    if(old?.dataset.v61Help==='1')return;
    const button=document.createElement('button');
    button.type='button';
    button.className='resource resource-info-top';
    button.dataset.v61Help='1';
    button.setAttribute('aria-label','Открыть справку по рейду');
    button.innerHTML='<span class="info-orb">?</span><small>СПРАВКА</small>';
    if(old)old.replaceWith(button);
    else document.querySelector('.resources')?.insertBefore(button,document.querySelector('.resources')?.children[1]||null);
  }

  function updatePressure(battle){
    const value=Math.max(0,Number(battle?.pressure)||0);
    const max=Math.max(1,Number(battle?.pressure_max)||120);
    const percent=Math.max(0,Math.min(100,Math.round(value/max*100)));
    const fill=document.getElementById('raidPressureFillV61');
    const text=document.getElementById('raidPressureTextV61');
    if(fill)fill.style.width=`${percent}%`;
    if(text)text.textContent=`${percent}%`;
    document.getElementById('raidPressureV61')?.classList.toggle('charged',percent>=80);
  }

  function warningTick(){
    const battle=latest?.battle;
    const warning=document.getElementById('raidWarningV61');
    if(!battle||!warning)return;
    const active=battle.status==='active'&&Number(battle.hp)>0;
    const seconds=Math.max(0,Math.ceil(Number(battle.next_action_at||0)-serverNow()));
    const visible=active&&seconds<=7;
    warning.classList.toggle('show',visible);
    warning.classList.toggle('urgent',visible&&seconds<=3);
    if(!visible)return;
    const name=battle.next_action_name||'Ответная атака';
    const target=battle.next_action_target||'отряд';
    const hint=battle.next_action_hint||'Приготовь защиту';
    const icon=battle.next_action_icon||'⚠';
    const iconNode=document.getElementById('raidWarningIconV61');
    const nameNode=document.getElementById('raidWarningNameV61');
    const hintNode=document.getElementById('raidWarningHintV61');
    const timeNode=document.getElementById('raidWarningTimeV61');
    if(iconNode)iconNode.textContent=icon;
    if(nameNode)nameNode.textContent=name.toUpperCase();
    if(hintNode)hintNode.textContent=`${hint} · Цель: ${target}`;
    if(timeNode)timeNode.textContent=String(seconds);
  }

  function showPhase(phase){
    const info=PHASES[phase];
    const overlay=document.getElementById('raidPhaseV61');
    if(!info||!overlay)return;
    const title=document.getElementById('raidPhaseTitleV61');
    const quote=document.getElementById('raidPhaseQuoteV61');
    if(title)title.textContent=info.title;
    if(quote)quote.textContent=info.quote;
    overlay.classList.add('show');
    tg?.HapticFeedback?.notificationOccurred?.('warning');
    setTimeout(()=>overlay.classList.remove('show'),2200);
  }

  function findFighterCard(name){
    return [...document.querySelectorAll('#fighters .fighter')].find(card=>{
      const text=card.querySelector('strong')?.textContent?.trim()||'';
      return text===String(name||'').trim();
    });
  }

  function triggerBossImpact(changes){
    if(!changes.length)return;
    const boss=document.getElementById('bossImage');
    const stage=document.getElementById('bossStage');
    const impact=document.getElementById('raidImpactV61');
    const impactText=document.getElementById('raidImpactTextV61');
    const selfHit=changes.find(item=>item.is_self);
    const total=changes.reduce((sum,item)=>sum+item.damage,0);

    boss?.classList.remove('raid-v61-strike');
    stage?.classList.remove('raid-v61-stage-hit');
    void boss?.offsetWidth;
    boss?.classList.add('raid-v61-strike');
    stage?.classList.add('raid-v61-stage-hit');
    document.body.classList.add('raid-v61-screen-hit');

    changes.forEach(item=>{
      const card=findFighterCard(item.name);
      card?.classList.add('raid-v61-fighter-hit');
      setTimeout(()=>card?.classList.remove('raid-v61-fighter-hit'),900);
    });

    if(impactText){
      impactText.textContent=selfHit?`−${fmt(selfHit.damage)} HP`:`УДАР ПО ОТРЯДУ · −${fmt(total)} HP`;
    }
    impact?.classList.add('show');
    if(selfHit)tg?.HapticFeedback?.notificationOccurred?.('error');
    else tg?.HapticFeedback?.impactOccurred?.('heavy');

    setTimeout(()=>{
      boss?.classList.remove('raid-v61-strike');
      stage?.classList.remove('raid-v61-stage-hit');
      document.body.classList.remove('raid-v61-screen-hit');
      impact?.classList.remove('show');
    },900);
  }

  function detectBossDamage(fighters){
    const changes=[];
    for(const fighter of fighters||[]){
      const userId=Number(fighter.user_id)||0;
      const current=Number(fighter.damage_taken)||0;
      if(previousDamage.has(userId)){
        const previous=previousDamage.get(userId)||0;
        if(current>previous){
          changes.push({
            user_id:userId,
            name:fighter.name,
            damage:current-previous,
            is_self:Boolean(fighter.is_self)
          });
        }
      }
      previousDamage.set(userId,current);
    }
    triggerBossImpact(changes);
  }

  function patchAbilityDetails(){
    const name=document.getElementById('abilityName');
    const hint=document.getElementById('abilityHint');
    if(!name||!hint)return;
    const detail=ABILITY_DETAILS[name.textContent.trim().toUpperCase()];
    if(detail&&hint.textContent!==detail)hint.textContent=detail;
  }

  function enhanceVictory(victory){
    if(!victory?.visible)return;
    const card=document.querySelector('#raidVictoryV59 .raid-victory-card');
    if(!card)return;
    let rewards=card.querySelector('.raid-v61-victory-rewards');
    if(!rewards){
      rewards=document.createElement('div');
      rewards.className='raid-v61-victory-rewards';
      card.querySelector('.raid-victory-ranking')?.before(rewards);
    }
    const influence=Number(victory.self_reward)||0;
    const shards=Number(victory.self_shards)||0;
    const tree=Number(victory.self_tree_points)||0;
    const finisher=Boolean(victory.is_finisher);
    const self=victory.self_stats||{};
    rewards.innerHTML=`
      <div><small>ОЧКИ ВЛИЯНИЯ</small><b>+${fmt(influence)}</b></div>
      <div><small>ОСКОЛКИ ЗНАНИЙ</small><b>+${fmt(shards)}</b></div>
      ${tree>0?`<div><small>ОЧКИ ДРЕВА</small><b>+${fmt(tree)}</b></div>`:''}
      ${finisher?'<p>💀 Бонус за последний удар уже включён в награду.</p>':''}
      <section><span>Урон: <b>${fmt(self.damage)}</b></span><span>Атак: <b>${fmt(self.attacks)}</b></span><span>Критов: <b>${fmt(self.critical_hits)}</b></span><span>Лечение: <b>${fmt(self.healing_done)}</b></span></section>`;
  }

  function setConnection(mode,text){
    const node=document.getElementById('raidConnectionV61');
    if(!node)return;
    node.textContent=text||'';
    node.className=`raid-v61-connection ${mode||''} ${text?'show':''}`;
  }

  function applyState(data){
    latest=data;
    receivedAt=performance.now();
    const phase=Number(data?.battle?.hp)<=0?5:Math.max(1,Math.min(4,Number(data?.battle?.phase)||1));
    if(lastPhase!==null&&phase>lastPhase&&phase<=4)showPhase(phase);
    lastPhase=phase;
    updatePressure(data.battle||{});
    detectBossDamage(data.fighters||[]);
    patchAbilityDetails();
    enhanceVictory(data.victory);
    warningTick();
  }

  async function poll(){
    if(pollBusy||!bossId||!initData||document.hidden)return;
    pollBusy=true;
    try{
      const response=await fetch(API,{headers:{'X-Telegram-Init-Data':initData},cache:'no-store'});
      const data=await response.json();
      if(!response.ok||!data?.ok)throw new Error(data?.reason||'Сервер рейда недоступен');
      const restored=failures>0;
      failures=0;
      applyState(data);
      if(restored){
        setConnection('ok','Соединение восстановлено');
        setTimeout(()=>setConnection('',''),1500);
      }else setConnection('','');
    }catch(_error){
      failures++;
      setConnection(failures>=3?'error':'','Переподключение к рейду…');
    }finally{
      pollBusy=false;
    }
  }

  // Перехватываем справку раньше старых обработчиков кнопки победы.
  document.addEventListener('click',event=>{
    const help=event.target.closest('[data-v61-help],#raidVictoryV59 [data-victory-help]');
    if(help){
      event.preventDefault();
      event.stopImmediatePropagation();
      openHelp();
      return;
    }
    const close=event.target.closest('[data-v61-help-close]');
    if(close){
      event.preventDefault();
      event.stopImmediatePropagation();
      closeHelp();
    }
  },true);

  tg?.BackButton?.onClick?.(()=>{
    if(document.getElementById('raidHelpV61')?.classList.contains('open'))closeHelp();
  });
  window.addEventListener('online',()=>{setConnection('','Переподключение к рейду…');poll();});
  window.addEventListener('offline',()=>setConnection('error','Нет соединения. Бой продолжится после восстановления сети.'));
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)poll();});

  ensureInterface();
  patchAbilityDetails();
  setInterval(()=>{ensureInterface();warningTick();},500);
  setInterval(poll,2500);
  poll();
})();