(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const HEROES={
    1:{
      name:'Каблучий',title:'Узник обручального кольца',ability:'Разрешение получено',cooldown:'10 минут',
      lore:'Подчиняется жене и появляется у друзей только после получения разрешения. Раньше редко выходил на связь, а нормально играть и общаться ему разрешили лишь после свадьбы. В отношениях его нередко подкалывают, унижают и напоминают, что он «не типаж», но Каблучий стойко несёт своё семейное бремя.',
      abilityBuffs:['На 20 секунд получает −40% входящего урона','Весь отряд получает −15% входящего урона','Первый подходящий удар босса полностью блокируется'],
      itemKey:'permission_ring',itemName:'Обручальное кольцо дозволения',itemIcon:'💍',itemRarity:'ЭПИЧЕСКИЙ',
      itemBuffs:['Постоянно даёт +12% к защите','При HP ниже 25% один раз восстанавливает 20% здоровья','Одновременно создаёт аварийный щит от следующего удара']
    },
    2:{
      name:'Сливариус',title:'Призрак общей сходки',ability:'Я уже выхожу',cooldown:'8 минут',
      lore:'Представитель легендарного движения «Плюс Вайб». Всегда уверенно говорит, что придёт на встречу с друзьями, но в последний момент бесследно исчезает. Обычно его можно обнаружить курящим где-нибудь в стороне или занятым поисками загадочного крестика на карте.',
      abilityBuffs:['На 5 секунд исчезает и уклоняется от подходящего удара','После возвращения следующая атака наносит +80% урона','Усиление сохраняется до следующего успешного удара'],
      itemKey:'lost_cross',itemName:'Потерянный крестик на карте',itemIcon:'✚',itemRarity:'РЕДКИЙ',
      itemBuffs:['Даёт +8% к дополнительному критическому шансу','После неудачи шанс растёт ещё на +4%','Дополнительный бонус накапливается до +12% и сбрасывается после срабатывания']
    },
    3:{
      name:'Солёний',title:'Кузнец реальности',ability:'Переписать реальность',cooldown:'12 минут',
      lore:'Создатель игры, креативная личность и генератор безумных идей. Работает на заводе и способен превратить любую шутку в полноценную игровую механику. Получил имя Солёний за характерный аромат пота и тухлых носков, который иногда объявляет о его приближении раньше него самого.',
      abilityBuffs:['Сокращает текущие кулдауны всего отряда примерно на 30%','На 20 секунд даёт команде +15% к урону','Восстанавливает каждому живому участнику 10% максимального HP'],
      itemKey:'developer_sock',itemName:'Тухлый носок разработчика',itemIcon:'🧦',itemRarity:'ЛЕГЕНДАРНЫЙ',
      itemBuffs:['Владелец получает +5% к урону','Урон босса по всему отряду снижается на 7%','Командный эффект работает, пока предмет экипирован']
    },
    4:{
      name:'Сейфзоний',title:'Безопасная зона',ability:'Безопасная зона',cooldown:'10 минут',
      lore:'Тёмная лошадка: с первого взгляда кажется замкнутым, скрытным и странным, но со временем раскрывается с неожиданной стороны. Наблюдает за людьми, анализирует их и будто постоянно сканирует окружающих. Эрудирован, загадочен и спокоен. Девушки видят в нём безопасную зону, поэтому часто идут к Сейфзонию вместо Самозвания, из-за чего тот временами заметно бесится.',
      abilityBuffs:['Весь живой отряд получает защиту от следующей атаки','Каждому восстанавливается 10% максимального HP','На 15 секунд входящий урон отряда снижается ещё на 20%'],
      itemKey:'trust_scanner',itemName:'Сканер доверия',itemIcon:'📡',itemRarity:'ЭПИЧЕСКИЙ',
      itemBuffs:['Даёт +10% к уклонению','Даёт +8% к постоянной защите','После тяжёлого удара следующая атака босса наносит на 50% меньше урона']
    },
    5:{
      name:'Самозваний',title:'Ложный главный герой',ability:'Я здесь главный',cooldown:'9 минут',
      lore:'Умный, эрудированный, тактичный и крайне амбициозный. Постоянно ведёт себя так, будто именно он главный герой всей истории, хотя окружающие не всегда с этим согласны. Любит внимание девушек, часто спорит, действует импульсивно и особенно раздражается, когда они выбирают спокойного Сейфзония вместо него.',
      abilityBuffs:['На 15 секунд получает +30% к урону','Если в отряде есть Сейфзоний, ревность добавляет ещё +10%','Следующая одиночная атака босса перенаправляется на Самозвания'],
      itemKey:'false_crown',itemName:'Корона ложного протагониста',itemIcon:'👑',itemRarity:'ЛЕГЕНДАРНЫЙ',
      itemBuffs:['Постоянно даёт +10% к урону','Если владелец не первый по урону, каждые 20 секунд получает ещё +2%','Дополнительное усиление накапливается до +10%']
    },
    6:{
      name:'Скользий',title:'Малый дипломат',ability:'Дипломатический манёвр',cooldown:'8 минут',
      lore:'Второй представитель «Плюс Вайба» и постоянный спутник Сливариуса. Редко появляется на встречах один, часто курит и не отличается крупными размерами. Маленький и щуплый, зато быстрый, прыгучий и невероятно скользкий. Умеет договариваться, находить компромиссы и дипломатично выбираться из сложных ситуаций.',
      abilityBuffs:['Задерживает следующую атаку босса на 5 секунд','Сокращает текущие кулдауны всего отряда примерно на 15%','Получает 50% шанс уклониться от следующего удара'],
      itemKey:'diplomat_boots',itemName:'Скользкие ботинки переговорщика',itemIcon:'👢',itemRarity:'ЭПИЧЕСКИЙ',
      itemBuffs:['Даёт +12% к уклонению','Ускоряет восстановление обычной атаки','Ускоряет восстановление способности героя примерно на 8%']
    },
    7:{
      name:'Былогерий',title:'Наследник былой славы',ability:'Возвращение в сюжет',cooldown:'один раз за бой',
      lore:'Когда-то действительно был главным героем, но после переезда в другой город нашёл девушку и постепенно растворился в массовке. Несмотря на это, в нём всё ещё периодически пробиваются лучи прежнего величия. Стремительный, упорный и потенциально способен однажды вернуться и снова стать кем-то большим.',
      abilityBuffs:['Если выбит — возвращается в бой с 40% максимального HP','Если жив — восстанавливает 25% HP и получает +25% к урону на 20 секунд','Следующая успешная атака после активации наносит двойной урон'],
      itemKey:'faded_cloak',itemName:'Потускневший плащ героя',itemIcon:'🧥',itemRarity:'ЛЕГЕНДАРНЫЙ',
      itemBuffs:['Постоянно даёт +8% к урону','При HP ниже 40% добавляет ещё +15% к урону','Один раз за бой смертельный удар оставляет владельцу 1 HP']
    }
  };

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);

  let activeRequest=null;
  let overlay=null;

  function listMarkup(values){
    return `<ul>${(values||[]).map(value=>`<li>${escapeHtml(value)}</li>`).join('')}</ul>`;
  }

  function ensureModal(){
    if(overlay)return overlay;
    overlay=document.createElement('div');
    overlay.className='hero-preview-overlay';
    overlay.id='heroPreviewOverlay';
    overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML=`
      <section class="hero-preview-dialog" role="dialog" aria-modal="true" aria-labelledby="heroPreviewName">
        <button class="hero-preview-close" type="button" aria-label="Закрыть">×</button>
        <div class="hero-preview-scroll"></div>
      </section>`;
    document.body.appendChild(overlay);
    overlay.addEventListener('click',event=>{
      if(event.target===overlay||event.target.closest('.hero-preview-close'))closeModal();
    });
    return overlay;
  }

  function selectedHeroId(state){
    return Number(state?.self?.skin_id||state?.hero_skins?.selected||0);
  }

  function stateItem(state,heroId){
    return (state?.shop||[]).find(item=>Number(item.hero_id)===Number(heroId))||null;
  }

  function openModal(request){
    const heroId=Number(request?.heroId||0);
    const hero=HEROES[heroId];
    if(!hero)return;
    activeRequest=request;
    const modal=ensureModal();
    const selected=selectedHeroId(request.state)===heroId;
    const serverItem=stateItem(request.state,heroId);
    const itemName=serverItem?.name||hero.itemName;
    const itemDescription=serverItem?.description||'';
    const itemIcon=serverItem?.icon||hero.itemIcon;
    const rarity=serverItem?.rarity||hero.itemRarity;
    const image=`/boss-app/assets/hero_skin_${heroId}.svg?v=102`;
    const scroll=modal.querySelector('.hero-preview-scroll');
    scroll.innerHTML=`
      <header class="hero-preview-hero">
        <div class="hero-preview-image"><img src="${image}" alt="${escapeHtml(hero.name)}"></div>
        <div class="hero-preview-identity"><small>ГЕРОЙ ${heroId}/7</small><h2 id="heroPreviewName">${escapeHtml(hero.name)}</h2><strong>${escapeHtml(hero.title)}</strong></div>
      </header>
      <section class="hero-preview-section lore"><div class="hero-preview-heading"><span>◆</span><h3>ЛОР ПЕРСОНАЖА</h3></div><p>${escapeHtml(hero.lore)}</p></section>
      <section class="hero-preview-section ability"><div class="hero-preview-heading"><span>✦</span><h3>УНИКАЛЬНАЯ СПОСОБНОСТЬ</h3></div><div class="hero-preview-ability-title"><strong>${escapeHtml(hero.ability)}</strong><em>${escapeHtml(hero.cooldown)}</em></div>${listMarkup(hero.abilityBuffs)}</section>
      <section class="hero-preview-section item"><div class="hero-preview-heading"><span>⬡</span><h3>ОСОБЫЙ ПРЕДМЕТ</h3></div><div class="hero-preview-item-head"><div class="hero-preview-item-icon">${escapeHtml(itemIcon)}</div><div><em>${escapeHtml(rarity)}</em><strong>${escapeHtml(itemName)}</strong>${itemDescription?`<p>${escapeHtml(itemDescription)}</p>`:''}</div></div><div class="hero-preview-buffs"><small>БАФФЫ ПРЕДМЕТА</small>${listMarkup(hero.itemBuffs)}</div></section>
      <button class="hero-preview-select ${selected?'selected':''}" type="button" ${selected?'disabled':''}>${selected?'ГЕРОЙ УЖЕ ВЫБРАН':'ВЫБРАТЬ '+escapeHtml(hero.name.toUpperCase())}</button>`;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden','false');
    document.body.classList.add('hero-preview-open');
    scroll.scrollTop=0;
    tg?.HapticFeedback?.impactOccurred?.('light');
    const select=scroll.querySelector('.hero-preview-select');
    select?.addEventListener('click',async()=>{
      if(select.disabled||!activeRequest?.choose)return;
      select.disabled=true;
      select.classList.add('saving');
      select.textContent='СОХРАНЯЕМ ГЕРОЯ…';
      const ok=await activeRequest.choose();
      if(ok!==false){
        closeModal();
      }else{
        select.disabled=false;
        select.classList.remove('saving');
        select.textContent='ВЫБРАТЬ '+hero.name.toUpperCase();
      }
    });
  }

  function closeModal(){
    if(!overlay)return;
    overlay.classList.remove('open');
    overlay.setAttribute('aria-hidden','true');
    document.body.classList.remove('hero-preview-open');
    activeRequest=null;
  }

  window.addEventListener('hero-preview-request',event=>{
    event.preventDefault();
    openModal(event.detail||{});
  });

  document.addEventListener('keydown',event=>{
    if(event.key==='Escape'&&overlay?.classList.contains('open'))closeModal();
  });
})();
