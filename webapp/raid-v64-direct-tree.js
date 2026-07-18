(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const initData=tg?.initData||'';
  const bossId=tg?.initDataUnsafe?.start_param||params.get('boss')||params.get('tgWebAppStartParam')||'';
  const API=`/boss-app/api/boss/state?boss_id=${encodeURIComponent(bossId)}`;
  let latestVictory=null;
  let busy=false;
  let rewardObserver=null;

  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Math.max(0,Number(value)||0));

  function directHelpMarkup(){
    return `
      <div class="raid-v61-help-intro">
        <b>ТАКТИЧЕСКИЙ РЕЙД · REALITY 64</b>
        <span>У босса 75 000 HP. Следи за предупреждением атаки, защищайся вовремя и поддерживай общий темп отряда.</span>
      </div>

      <h3>БОЙ И ДАВЛЕНИЕ ОТРЯДА</h3>
      <article><i>⚔</i><div><b>Задеть эго</b><small>Обычный удар: 200–500. Критический удар: 800–1200. Перезарядка — 5 секунд.</small></div></article>
      <article><i>⚡</i><div><b>Давление отряда</b><small>Обычный удар добавляет 2 единицы, крит — ещё 1, способность роли — 5. Максимум шкалы — 120. Без новых атак давление постепенно уменьшается.</small></div></article>
      <article><i>💥</i><div><b>Коллективное унижение</b><small>При полном заполнении шкалы отряд автоматически наносит дополнительные 1200–1800 урона.</small></div></article>
      <article><i>🛡</i><div><b>Защита</b><small>Полностью отражает следующую подходящую атаку. За 7 секунд до удара показывается его название и цель.</small></div></article>
      <article><i>✚</i><div><b>Лечение</b><small>Восстанавливает личное HP героя. При полном здоровье кнопка недоступна.</small></div></article>

      <h3>НАГРАДЫ ЗА ПОБЕДУ</h3>
      <div class="raid-v61-reward-row"><span>🥇</span><div><b>1-е место</b><small>600 влияния и 4 очка древа</small></div></div>
      <div class="raid-v61-reward-row"><span>🥈</span><div><b>2-е место</b><small>400 влияния и 3 очка древа</small></div></div>
      <div class="raid-v61-reward-row"><span>🥉</span><div><b>3-е место</b><small>250 влияния и 2 очка древа</small></div></div>
      <div class="raid-v61-reward-row"><span>⚔️</span><div><b>Активное участие</b><small>75 влияния и 1 очко древа каждому участнику ниже топ-3, если он нанёс хотя бы один удар.</small></div></div>
      <div class="raid-v61-reward-row"><span>💀</span><div><b>Последний удар</b><small>Дополнительно 100 влияния. Дополнительное очко древа за добивание не выдаётся.</small></div></div>

      <h3>ОЧКИ ДРЕВА</h3>
      <article><i>🌳</i><div><b>Прямая награда</b><small>Очки сразу появляются в древе развития. Никаких промежуточных валют и преобразования не требуется.</small></div></article>
      <article><i>📅</i><div><b>Недельный лимит</b><small>За победы над боссом один участник может получить не больше 12 очков древа за неделю.</small></div></article>

      <h3>СТАБИЛЬНОСТЬ</h3>
      <article><i>📡</i><div><b>Автопереподключение</b><small>При временной потере сети Mini App самостоятельно загрузит актуальное состояние боя после восстановления соединения.</small></div></article>`;
  }

  function patchHelp(){
    const scroll=document.querySelector('#raidHelpV61 .raid-v61-help-scroll');
    if(!scroll)return;
    if(scroll.textContent.includes('ОСКОЛК')||!scroll.textContent.includes('12 очков древа')){
      scroll.innerHTML=directHelpMarkup();
      scroll.dataset.rewardVersion='64';
    }
  }

  function renderVictory(){
    const victory=latestVictory;
    if(!victory?.visible)return;
    const rewards=document.querySelector('#raidVictoryV59 .raid-v61-victory-rewards');
    if(!rewards)return;

    const influence=Number(victory.self_reward)||0;
    const tree=Number(victory.self_tree_points)||0;
    const requested=Number(victory.self_tree_points_requested)||tree;
    const finisher=Boolean(victory.is_finisher);
    const self=victory.self_stats||{};
    const limited=tree<requested;
    const signature=[influence,tree,requested,finisher,Number(self.damage)||0,Number(self.attacks)||0,Number(self.critical_hits)||0,Number(self.healing_done)||0].join(':');
    if(rewards.dataset.v64Signature===signature&&!rewards.textContent.includes('ОСКОЛК'))return;

    rewards.dataset.v64Signature=signature;
    rewards.innerHTML=`
      <div><small>ОЧКИ ВЛИЯНИЯ</small><b>+${fmt(influence)}</b></div>
      <div><small>ОЧКИ ДРЕВА</small><b>+${fmt(tree)}</b></div>
      ${limited?'<p>📅 Часть награды не выдана: достигнут недельный лимит 12 очков древа.</p>':''}
      ${finisher?'<p>💀 Бонус +100 влияния за последний удар уже включён.</p>':''}
      <section><span>Урон: <b>${fmt(self.damage)}</b></span><span>Атак: <b>${fmt(self.attacks)}</b></span><span>Критов: <b>${fmt(self.critical_hits)}</b></span><span>Лечение: <b>${fmt(self.healing_done)}</b></span></section>`;
  }

  function watchVictory(){
    const rewards=document.querySelector('#raidVictoryV59 .raid-v61-victory-rewards');
    if(!rewards||rewards.dataset.v64Observed==='1')return;
    rewards.dataset.v64Observed='1';
    rewardObserver?.disconnect();
    rewardObserver=new MutationObserver(()=>{
      if(rewards.textContent.includes('ОСКОЛК')||rewards.dataset.v64Signature==='')renderVictory();
    });
    rewardObserver.observe(rewards,{childList:true,subtree:true,characterData:true});
  }

  async function refresh(){
    if(busy||!bossId||!initData||document.hidden)return;
    busy=true;
    try{
      const response=await fetch(API,{headers:{'X-Telegram-Init-Data':initData},cache:'no-store'});
      const data=await response.json();
      if(response.ok&&data?.ok){
        latestVictory=data.victory||null;
        patchHelp();
        watchVictory();
        renderVictory();
      }
    }catch(_error){
      // Основной интерфейс сам показывает состояние сети.
    }finally{
      busy=false;
    }
  }

  document.addEventListener('click',event=>{
    if(event.target.closest('[data-v61-help],#raidVictoryV59 [data-victory-help]')){
      setTimeout(patchHelp,0);
    }
  },true);

  setInterval(()=>{
    patchHelp();
    watchVictory();
    renderVictory();
  },400);
  setInterval(refresh,2500);
  refresh();
})();
