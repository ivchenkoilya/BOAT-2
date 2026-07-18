(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const stage=document.getElementById('bossStage');
  const fighters=document.getElementById('fighters');
  const modal=document.getElementById('modal');
  const modalContent=document.getElementById('modalContent');
  const toast=document.getElementById('toast');
  const navButtons=[...document.querySelectorAll('.bottom-nav button')];
  const chooseHero=document.querySelector('.squad-section .section-head>button');
  const skinsButton=navButtons.at(-1);

  function setActiveNav(button){
    if(!button)return;
    navButtons.forEach(item=>item.classList.toggle('active',item===button));
  }

  function showToast(text){
    if(!toast)return;
    toast.textContent=text;
    toast.className='toast show';
    clearTimeout(showToast.timer);
    showToast.timer=setTimeout(()=>{toast.className='toast'},2400);
  }

  function openCustomModal(type){
    if(!modal||!modalContent)return;
    modalContent.dataset.type=type;
    modalContent.innerHTML=type==='skins'?skinsMarkup():helpMarkup();
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function skinsMarkup(){
    const slots=Array.from({length:8},(_,index)=>`
      <button class="future-skin-slot" type="button" data-future-skin="${index+1}">
        <span class="future-skin-number">${index+1}/8</span>
        <span class="future-skin-lock">◇</span>
        <b>ПУСТОЙ СЛОТ</b>
        <small>Образ появится позже</small>
      </button>`).join('');
    return `<h2 class="future-skin-title">ОБРАЗЫ ГЕРОЯ</h2>
      <p class="future-skin-sub">Здесь появятся восемь разных скинов. Сейчас ячейки оставлены пустыми, чтобы позже добавить отдельные изображения и эффекты каждого образа.</p>
      <div class="future-skin-grid">${slots}</div>`;
  }

  function helpCard(icon,title,text,kind=''){
    return `<article class="v19-help-card ${kind}"><span class="v19-help-icon">${icon}</span><div><b>${title}</b><small>${text}</small></div></article>`;
  }

  function helpMarkup(){
    const controls=[
      ['⚔','Задеть эго','Основная атака по боссу. После удара запускается короткая перезарядка на 5 секунд.'],
      ['🛡','Защита','Полностью отражает следующую подходящую атаку босса. Повторное использование доступно после кулдауна.'],
      ['✚','Лечение','Восстанавливает личное здоровье героя. Кнопка недоступна при полном запасе HP.'],
      ['✦','Способность роли','Уникальное действие текущей роли. Оно сильнее обычной атаки, но восстанавливается 10 минут.'],
      ['👥','Герои','Показывает всех участников отряда, их роли, здоровье и нанесённый урон.'],
      ['🎭','Образы','Отдельный раздел будущих скинов. Кнопка «Выбрать героя» открывает именно его.'],
      ['🎒','Инвентарь','Будущий раздел предметов и снаряжения героя.'],
      ['🏪','Магазин','Будущий раздел покупки образов, предметов и улучшений.']
    ];
    const roles=[
      ['🪑','Декорация — Неожиданно ожить','Наносит урон, лечит себя и временно блокирует восстановление босса.'],
      ['🌫','Пыль — Пыль в глаза','Срывает следующую атаку Центра Вселенной и разбивает его Щит ЧСВ.'],
      ['👥','Массовка — Давление толпы','Наносит сильный удар и восстанавливает здоровье всему отряду.'],
      ['🎭','Второстепенная роль — Украсть сцену','Наносит большой урон и защищает героя от следующего ответа босса.'],
      ['🌟','Временный Главный герой — Минута славы','Мощно атакует и мгновенно сбрасывает кулдаун обычного удара.'],
      ['💣','Саботажный Главный герой — Удар из-за кулис','Наносит огромный урон, но иногда часть атаки возвращается самому герою.'],
      ['👑','Честный Главный герой — Кульминация','Гарантированно наносит сокрушительный критический удар.']
    ];
    const boss=[
      ['🪞','Щит ЧСВ','Ослабляет несколько следующих ударов отряда, пока все заряды не будут разбиты.'],
      ['🗯','Тебя никто не слушает','Временно лишает выбранного героя возможности атаковать.'],
      ['🌌','Сокрушить самооценку','Наносит усиленный урон одному случайному участнику.'],
      ['👥','Вы всего лишь массовка','Атакует сразу весь отряд. Защищённые герои отражают удар.'],
      ['🌀','Все мне завидуют','Добавляет боссу заряды защиты и ослабляет следующие атаки.'],
      ['♻','Возвращение внимания','Раз в 5 минут Центр Вселенной пассивно восстанавливает 25 HP.']
    ];
    return `<h2 class="v19-help-title">СПРАВКА ПО РЕЙДУ</h2>
      <p class="v19-help-intro">Все важные действия закреплены внизу экрана. Состояние боя общее для участников беседы и обновляется с сервера.</p>
      <h3 class="v19-help-heading">КНОПКИ И РАЗДЕЛЫ</h3><div class="v19-help-grid">${controls.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="v19-help-heading">СПОСОБНОСТИ РОЛЕЙ</h3><div class="v19-help-grid">${roles.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="v19-help-heading">СПОСОБНОСТИ БОССА</h3><div class="v19-help-grid">${boss.map(item=>helpCard(...item,'boss')).join('')}</div>`;
  }

  function decorateFighters(){
    document.querySelectorAll('.fighter').forEach(card=>{
      if(!card.querySelector('.fighter-aura-frame')){
        const frame=document.createElement('span');
        frame.className='fighter-aura-frame';
        frame.setAttribute('aria-hidden','true');
        card.prepend(frame);
      }
    });
  }

  function effectLayer(type){
    const old=document.querySelector('.v19-effect-layer');
    old?.remove();
    const layer=document.createElement('div');
    layer.className=`v19-effect-layer ${type}`;
    if(type==='shield'){
      layer.innerHTML='<div class="v19-screen"></div><div class="v19-shield-ring"></div><div class="v19-effect-title">🛡 ЗАЩИТА АКТИВНА</div>';
      document.querySelector('.fighter.self')?.classList.add('v19-defended');
      setTimeout(()=>document.querySelector('.fighter.self')?.classList.remove('v19-defended'),1050);
    }else{
      const particles=Array.from({length:12},(_,i)=>{
        const angle=(Math.PI*2*i)/12;
        const radius=85+(i%3)*18;
        const x=Math.round(Math.cos(angle)*radius);
        const y=Math.round(Math.sin(angle)*radius-35);
        return `<i class="v19-heal-particle" style="--x:${x}px;--y:${y}px;animation-delay:${(i%4)*.04}s"></i>`;
      }).join('');
      layer.innerHTML=`<div class="v19-screen"></div>${particles}<div class="v19-effect-title">✚ ВОССТАНОВЛЕНИЕ HP</div>`;
      document.querySelector('.fighter.self')?.classList.add('v19-healed');
      setTimeout(()=>document.querySelector('.fighter.self')?.classList.remove('v19-healed'),1050);
    }
    document.body.appendChild(layer);
    setTimeout(()=>layer.remove(),1250);
  }

  /* Telegram Android sometimes treats the large boss artwork as a drag target.
     Proxy vertical gestures from the stage directly to page scrolling. */
  if(stage){
    let lastY=null;
    let blocked=false;
    stage.addEventListener('touchstart',event=>{
      blocked=Boolean(event.target.closest('button,a,input,textarea,select'));
      lastY=!blocked&&event.touches.length===1?event.touches[0].clientY:null;
    },{passive:true});
    stage.addEventListener('touchmove',event=>{
      if(blocked||lastY===null||event.touches.length!==1)return;
      const nextY=event.touches[0].clientY;
      const delta=lastY-nextY;
      lastY=nextY;
      if(Math.abs(delta)>1){
        window.scrollBy(0,delta);
        event.preventDefault();
      }
    },{passive:false});
    stage.addEventListener('touchend',()=>{lastY=null;blocked=false},{passive:true});
  }

  if(skinsButton){
    skinsButton.dataset.modal='skins';
    skinsButton.setAttribute('aria-label','Образы героя');
  }
  if(chooseHero)chooseHero.dataset.modal='skins';

  if(stage&&!stage.querySelector('.raid-help-button')){
    const help=document.createElement('button');
    help.type='button';
    help.className='raid-help-button';
    help.dataset.openRaidHelp='1';
    help.setAttribute('aria-label','Справка по рейду');
    help.textContent='?';
    stage.appendChild(help);
  }

  document.addEventListener('click',event=>{
    const nav=event.target.closest('.bottom-nav button');
    if(nav)setActiveNav(nav);

    const custom=event.target.closest('[data-modal="skins"],[data-open-raid-help]');
    if(custom){
      event.preventDefault();
      event.stopImmediatePropagation();
      const type=custom.matches('[data-modal="skins"]')?'skins':'help';
      if(type==='skins')setActiveNav(skinsButton);
      openCustomModal(type);
      return;
    }

    const slot=event.target.closest('[data-future-skin]');
    if(slot){
      event.preventDefault();
      showToast(`Слот ${slot.dataset.futureSkin}: образ пока не добавлен.`);
      tg?.HapticFeedback?.notificationOccurred?.('warning');
      return;
    }

    const action=event.target.closest('[data-action]');
    if(!action||action.disabled)return;
    if(action.dataset.action==='heal')effectLayer('heal');
    if(action.dataset.action==='defend')effectLayer('shield');
  },true);

  navButtons.forEach(button=>button.addEventListener('click',()=>setActiveNav(button)));

  if(fighters){
    new MutationObserver(decorateFighters).observe(fighters,{childList:true,subtree:true});
  }
  decorateFighters();
})();
