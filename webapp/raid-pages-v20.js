(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const resources=document.querySelector('.resources');
  const fighters=document.getElementById('fighters');
  const toast=document.getElementById('toast');
  const modal=document.getElementById('modal');
  const navButtons=[...document.querySelectorAll('.bottom-nav button')];
  const chooseHero=document.querySelector('.squad-section .section-head>button');

  const labelOf=button=>(button?.querySelector('small')?.textContent||'').trim().toLowerCase();
  const navByLabel=label=>navButtons.find(button=>labelOf(button)===label);

  document.querySelector('.raid-help-button')?.remove();

  if(resources&&!resources.querySelector('.resource-info-top')){
    const info=document.createElement('button');
    info.type='button';
    info.className='resource resource-info-top';
    info.dataset.openRaidPage='help';
    info.setAttribute('aria-label','Справка по рейду');
    info.innerHTML='<span class="info-orb">?</span><small>СПРАВКА</small>';
    resources.insertBefore(info,resources.children[1]||null);
  }

  const page=document.createElement('section');
  page.className='raid-page';
  page.id='raidPage';
  page.setAttribute('aria-hidden','true');
  page.innerHTML='<header class="raid-page-head"><button class="raid-page-back" type="button" aria-label="Назад">‹</button><div class="raid-page-title">РАЗДЕЛ</div><div class="raid-page-mark">✦</div></header><div class="raid-page-scroll"></div>';
  document.body.appendChild(page);

  const pageTitle=page.querySelector('.raid-page-title');
  const pageScroll=page.querySelector('.raid-page-scroll');
  const backButton=page.querySelector('.raid-page-back');

  const pageNames={heroes:'ГЕРОИ ОТРЯДА',inventory:'ИНВЕНТАРЬ',shop:'МАГАЗИН',skins:'ОБРАЗЫ ГЕРОЯ',help:'СПРАВКА ПО РЕЙДУ'};

  function setActiveNav(button){
    navButtons.forEach(item=>item.classList.toggle('active',item===button));
  }

  function helpCard(icon,title,text,kind=''){
    return `<article class="page-help-card ${kind}"><span class="help-icon">${icon}</span><div><b>${title}</b><small>${text}</small></div></article>`;
  }

  function heroesMarkup(){
    const cards=[...(fighters?.querySelectorAll('.fighter')||[])].map(card=>card.outerHTML).join('');
    return `<p class="page-intro">Полный состав рейда. Цвет внешнего свечения зависит от роли героя.</p><div class="page-heroes-grid">${cards||'<div class="page-placeholder"><span class="page-placeholder-icon">👥</span><h2>ОТРЯД ПУСТ</h2><p>Участники появятся после входа в рейд.</p></div>'}</div>`;
  }

  function skinsMarkup(){
    const slots=Array.from({length:8},(_,index)=>`<button class="page-skin-slot" type="button" data-empty-skin="${index+1}"><em>${index+1}/8</em><span class="slot-orb">◇</span><b>ПУСТОЙ СЛОТ</b><small>Скин появится позже</small></button>`).join('');
    return `<p class="page-intro">Отдельная коллекция образов героя. Позже в эти восемь ячеек будут добавлены изображения, названия и уникальные эффекты скинов.</p><div class="page-skin-grid">${slots}</div>`;
  }

  function placeholderMarkup(type){
    const inventory=type==='inventory';
    return `<div class="page-placeholder"><span class="page-placeholder-icon">${inventory?'🎒':'🏪'}</span><h2>${inventory?'ИНВЕНТАРЬ':'МАГАЗИН'}</h2><p>Раздел уже вынесен на отдельную страницу.<br><b>Содержимое находится в разработке.</b></p></div>`;
  }

  function helpMarkup(){
    const controls=[
      ['⚔','Задеть эго','Основная атака. Наносит урон боссу и перезаряжается 5 секунд.'],
      ['🛡','Защита','Полностью отражает следующую подходящую атаку босса.'],
      ['✚','Лечение','Восстанавливает личное HP героя. При полном здоровье кнопка недоступна.'],
      ['✦','Способность роли','Уникальное действие роли с перезарядкой 10 минут.'],
      ['👥','Герои','Отдельная страница со всем отрядом, здоровьем, ролями и уроном.'],
      ['🎭','Образы','Отдельная страница восьми будущих скинов героя.'],
      ['🎒','Инвентарь','Будущие предметы и экипировка героя.'],
      ['🏪','Магазин','Будущая покупка предметов, образов и улучшений.']
    ];
    const roles=[
      ['🪑','Декорация — Неожиданно ожить','Наносит урон, лечит себя и временно блокирует восстановление босса.'],
      ['🌫','Пыль — Пыль в глаза','Срывает следующую атаку босса и разбивает Щит ЧСВ.'],
      ['👥','Массовка — Давление толпы','Сильно бьёт и восстанавливает здоровье всему отряду.'],
      ['🎭','Второстепенная роль — Украсть сцену','Наносит большой урон и получает защиту от следующего ответа.'],
      ['🌟','Временный Главный герой — Минута славы','Мощно атакует и мгновенно сбрасывает кулдаун обычного удара.'],
      ['💣','Саботажный Главный герой — Удар из-за кулис','Наносит огромный урон, но часть атаки иногда возвращается герою.'],
      ['👑','Честный Главный герой — Кульминация','Гарантированно наносит сокрушительный критический удар.']
    ];
    const boss=[
      ['🪞','Щит ЧСВ','Ослабляет несколько следующих ударов, пока отряд не разобьёт все заряды.'],
      ['🗯','Тебя никто не слушает','Временно запрещает выбранному герою атаковать.'],
      ['🌌','Сокрушить самооценку','Наносит усиленный урон одному случайному участнику.'],
      ['👥','Вы всего лишь массовка','Атакует сразу весь отряд. Защищённые участники отражают удар.'],
      ['🌀','Все мне завидуют','Добавляет боссу новые заряды Щита ЧСВ.'],
      ['♻','Возвращение внимания','Каждые 5 минут пассивно восстанавливает боссу 25 HP.']
    ];
    const phases=[
      ['1','Фаза 1 — Раскол эго','От 100% до 76% HP. Босс только входит в бой и использует базовые атаки.'],
      ['2','Фаза 2 — Тревога','От 75% до 51% HP. Урон и давление босса постепенно возрастают.'],
      ['3','Фаза 3 — Ярость','От 50% до 26% HP. Атаки становятся значительно опаснее.'],
      ['4','Фаза 4 — Последний натиск','От 25% до 1% HP. Самая опасная стадия перед разрушением эго.'],
      ['🏆','Победа — Эго разрушено','При 0 HP бой завершается, фиксируется рейтинг и выдаются награды.']
    ];
    return `<p class="page-intro">Состояние рейда общее для всей беседы. Все важные боевые кнопки закреплены внизу только на странице рейда.</p>
      <h3 class="page-section-title">КНОПКИ И РАЗДЕЛЫ</h3><div class="page-help-grid">${controls.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="page-section-title">СПОСОБНОСТИ РОЛЕЙ</h3><div class="page-help-grid">${roles.map(item=>helpCard(...item)).join('')}</div>
      <h3 class="page-section-title">АТАКИ БОССА</h3><div class="page-help-grid">${boss.map(item=>helpCard(...item,'phase')).join('')}</div>
      <h3 class="page-section-title">ФАЗЫ БОССА</h3><div class="page-help-grid">${phases.map(item=>helpCard(...item,'phase')).join('')}</div>
      <h3 class="page-section-title">НАГРАДЫ ЗА ПОБЕДУ</h3><div class="reward-board">
        <div class="reward-row"><span>🥇</span><div><b>1-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+250</strong></div>
        <div class="reward-row"><span>🥈</span><div><b>2-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+150</strong></div>
        <div class="reward-row"><span>🥉</span><div><b>3-е место по урону</b><small>Нужно нанести хотя бы один удар</small></div><strong>+100</strong></div>
        <div class="reward-note">Награды начисляются очками влияния после окончательной победы над Центром Вселенной. Остальные участники попадают в итоговый список боя, но отдельная награда для них пока не настроена.</div>
      </div>`;
  }

  function markupFor(type){
    if(type==='heroes')return heroesMarkup();
    if(type==='skins')return skinsMarkup();
    if(type==='help')return helpMarkup();
    return placeholderMarkup(type);
  }

  function closeLegacyModal(){
    if(!modal)return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden','true');
  }

  function openPage(type){
    closeLegacyModal();
    page.dataset.page=type;
    pageTitle.textContent=pageNames[type]||'РАЗДЕЛ';
    pageScroll.innerHTML=markupFor(type);
    pageScroll.scrollTop=0;
    page.classList.add('open');
    page.setAttribute('aria-hidden','false');
    document.body.classList.add('raid-subpage-open');
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function closePage(){
    page.classList.remove('open');
    page.setAttribute('aria-hidden','true');
    document.body.classList.remove('raid-subpage-open');
    setActiveNav(navByLabel('рейд'));
    tg?.BackButton?.hide?.();
  }

  function openNavPage(label){
    if(label==='рейд'){
      closePage();
      window.scrollTo({top:0,behavior:'smooth'});
      return;
    }
    const type={герои:'heroes',инвентарь:'inventory',магазин:'shop',образы:'skins'}[label];
    if(type)openPage(type);
  }

  document.addEventListener('click',event=>{
    const back=event.target.closest('.raid-page-back');
    if(back){event.preventDefault();event.stopImmediatePropagation();closePage();return;}

    const info=event.target.closest('[data-open-raid-page="help"]');
    if(info){event.preventDefault();event.stopImmediatePropagation();openPage('help');return;}

    const choose=event.target.closest('.squad-section .section-head>button');
    if(choose){event.preventDefault();event.stopImmediatePropagation();setActiveNav(navByLabel('образы'));openPage('skins');return;}

    const nav=event.target.closest('.bottom-nav button');
    if(nav){
      event.preventDefault();
      event.stopImmediatePropagation();
      setActiveNav(nav);
      openNavPage(labelOf(nav));
      return;
    }

    const empty=event.target.closest('[data-empty-skin]');
    if(empty){event.preventDefault();tg?.HapticFeedback?.notificationOccurred?.('warning');}
  },true);

  backButton.addEventListener('click',closePage);
  tg?.BackButton?.onClick?.(()=>{if(page.classList.contains('open'))closePage();});

  if(fighters){
    new MutationObserver(()=>{
      if(page.classList.contains('open')&&page.dataset.page==='heroes')pageScroll.innerHTML=heroesMarkup();
    }).observe(fighters,{childList:true,subtree:true});
  }

  /* Боевые анимации уже показывают успешное действие. Убираем только дублирующие
     нижние success-тосты, сохраняя сообщения об ошибках и предупреждения. */
  if(toast){
    new MutationObserver(()=>{
      if(toast.classList.contains('show')&&toast.classList.contains('success')){
        toast.className='toast';
        toast.textContent='';
      }
    }).observe(toast,{attributes:true,childList:true,characterData:true,subtree:true});
  }
})();
