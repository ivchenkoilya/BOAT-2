(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const TRACK_URL='/boss-app/assets/main-hero-theme.ogg?v=151';

  let latest=null;
  let lastLog='';
  let receivedAt=performance.now();
  let track=null;
  let musicRequested=false;

  function ensureUi(){
    const stage=document.getElementById('bossStage');
    if(!stage)return;
    document.body.classList.add('raid-v149-ready');

    // Старый генератор фазовой музыки и все связанные с ним кнопки удалены.
    document.getElementById('raidMusicV149')?.remove();
    document.querySelectorAll('.raid-v149-music').forEach(node=>node.remove());

    if(!document.getElementById('raidNoticesV149')){
      const lane=document.createElement('div');
      lane.id='raidNoticesV149';
      lane.className='raid-v149-notices';
      lane.setAttribute('aria-live','polite');
      stage.appendChild(lane);
    }
  }

  function notice(text,kind=''){
    ensureUi();
    const lane=document.getElementById('raidNoticesV149');
    if(!lane||!text)return;
    const node=document.createElement('div');
    node.className=`raid-v149-notice ${kind}`.trim();
    node.textContent=String(text).replace(/^Сейчас\s*·\s*/i,'').trim();
    lane.appendChild(node);
    while(lane.children.length>3)lane.firstElementChild?.remove();
    setTimeout(()=>node.remove(),3100);
  }

  function kindFor(text){
    const value=String(text||'').toLowerCase();
    if(value.includes('ульта')||value.includes('ты здесь никто'))return 'ultimate';
    if(value.includes('дебаф')||value.includes('подавлен')||value.includes('уверенност'))return 'debuff';
    if(value.includes('восстановил')&&value.includes('центр вселенной'))return 'heal';
    return '';
  }

  function patchWarning(battle){
    const warning=document.getElementById('raidWarningV61');
    if(!warning)return;
    const armed=Boolean(battle?.ultimate_armed);
    warning.classList.toggle('ultimate-v149',armed);
    if(!armed)return;
    const serverNow=Number(latest?.now||Date.now()/1000)+(performance.now()-receivedAt)/1000;
    const seconds=Math.max(0,Math.ceil(Number(battle.ultimate_at||battle.next_action_at||0)-serverNow));
    warning.classList.add('show');
    warning.classList.toggle('urgent',seconds<=3);
    const icon=document.getElementById('raidWarningIconV61');
    const name=document.getElementById('raidWarningNameV61');
    const hint=document.getElementById('raidWarningHintV61');
    const time=document.getElementById('raidWarningTimeV61');
    if(icon)icon.textContent='☄️';
    if(name)name.textContent='ТЫ ЗДЕСЬ НИКТО';
    if(hint)hint.textContent='УЛЬТА: 200–300 урона каждому · защита не спасёт';
    if(time)time.textContent=String(seconds);
  }

  function patchFighters(data){
    requestAnimationFrame(()=>{
      const fighters=data?.fighters||[];
      const cards=[...document.querySelectorAll('#fighters .fighter:not(.empty-fighter)')];
      cards.forEach(card=>card.querySelector('.raid-v149-debuffs')?.remove());
      fighters.forEach((fighter,index)=>{
        const values=fighter?.debuffs||{};
        const weaken=Number(values.weaken_hits)||0;
        const crit=Number(values.crit_block_hits)||0;
        if(!weaken&&!crit)return;
        const card=cards[index];
        if(!card)return;
        const row=document.createElement('div');
        row.className='raid-v149-debuffs';
        if(weaken)row.insertAdjacentHTML('beforeend',`<span title="Урон снижен на 15%">−15% ×${weaken}</span>`);
        if(crit)row.insertAdjacentHTML('beforeend',`<span title="Критический урон ослаблен на 25%">КРИТ−25% ×${crit}</span>`);
        card.appendChild(row);
      });
    });
  }

  function patchHelp(){
    const scroll=document.querySelector('#raidHelpV61 .raid-v61-help-scroll');
    if(!scroll)return;
    const intro=scroll.querySelector('.raid-v61-help-intro');
    if(intro){
      const text=intro.querySelector('span');
      if(text)text.textContent='У босса 100 000 HP. Обычные ответы стали мягче, а кнопки игрока перезаряжаются быстрее.';
    }
    let card=scroll.querySelector('.raid-v149-help-card');
    if(!card){
      card=document.createElement('div');
      card.className='raid-v149-help-card';
      intro?.insertAdjacentElement('afterend',card);
    }
    card.innerHTML=`
      <b>АКТУАЛЬНЫЙ БАЛАНС ЦЕНТРА ВСЕЛЕННОЙ</b>
      <span>Обычная атака босса наносит 50–100 базового урона. Защита, уклонение и предметы могут уменьшить итоговый урон.</span>
      <span>Дебаф срабатывает реже и действует только на один удар: −15% урона или ослабление критического урона на 25%.</span>
      <span>«Задеть эго» перезаряжается 3 секунды. Способности всех героев — не дольше 5 минут.</span>
      <span>У босса одновременно может быть максимум 3 заряда Щита ЧСВ.</span>
      <span>Былогерий может применять «Возвращение в сюжет» сколько угодно раз с перезарядкой 5 минут.</span>`;
  }

  function isBattleActive(){
    const battle=latest?.battle||{};
    return battle.status==='active'&&Number(battle.hp)>0;
  }

  function ensureTrack(){
    if(track)return track;
    track=new Audio(TRACK_URL);
    track.loop=true;
    track.preload='auto';
    track.volume=.32;
    track.setAttribute('playsinline','');
    return track;
  }

  async function playTrack(){
    if(!musicRequested||!isBattleActive()||document.hidden)return;
    const player=ensureTrack();
    try{await player.play();}catch(_error){}
  }

  function stopTrack(){
    if(track&&!track.paused)track.pause();
  }

  function applyState(data){
    if(!data?.ok)return;
    latest=data;
    receivedAt=performance.now();
    const battle=data.battle||{};
    patchWarning(battle);
    patchFighters(data);
    patchHelp();

    if(!isBattleActive())stopTrack();
    else playTrack();

    const current=String((data.logs||[])[0]||'').trim();
    if(lastLog&&current&&current!==lastLog)notice(current,kindFor(current));
    if(current)lastLog=current;
  }

  function installToastMirror(){
    const toast=document.getElementById('toast');
    if(!toast)return;
    let seen='';
    const mirror=()=>{
      if(!toast.classList.contains('show'))return;
      const text=toast.textContent?.trim()||'';
      if(text&&text!==seen){
        seen=text;
        notice(text,kindFor(text));
        setTimeout(()=>{if(seen===text)seen='';},2800);
      }
    };
    new MutationObserver(mirror).observe(toast,{attributes:true,childList:true,subtree:true});
  }

  // Telegram разрешает звук после действия игрока. Отдельной музыкальной
  // кнопки нет: присланный трек запускается после первого касания экрана.
  const requestMusic=()=>{
    musicRequested=true;
    playTrack();
  };
  document.addEventListener('pointerdown',requestMusic,{capture:true});
  document.addEventListener('click',requestMusic,{capture:true});
  document.addEventListener('visibilitychange',()=>{
    if(document.hidden)stopTrack();
    else playTrack();
  });
  window.addEventListener('beforeunload',stopTrack);

  window.addEventListener('raid-state-updated',event=>applyState(event.detail));
  document.addEventListener('click',()=>setTimeout(patchHelp,0),true);

  ensureUi();
  installToastMirror();
  ensureTrack();
  if(window.__raidBossState)applyState(window.__raidBossState);
  setInterval(()=>{
    ensureUi();
    patchHelp();
    if(latest)patchWarning(latest.battle||{});
  },250);
})();
