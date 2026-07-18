(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const initData=tg?.initData||'';
  const bossId=tg?.initDataUnsafe?.start_param||params.get('boss')||params.get('tgWebAppStartParam')||'';
  let dismissed=false;
  let latestVictory=null;
  let polling=false;

  const escapeHtml=value=>String(value??'').replace(/[&<>"']/g,char=>({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  })[char]);
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Math.max(0,Number(value)||0));

  function unlockScreen(){
    document.body.style.removeProperty('overflow');
    document.body.classList.remove('raid-victory-open','combat-overlay-open');
    const legacy=document.getElementById('modal');
    if(legacy){
      legacy.classList.remove('open');
      legacy.setAttribute('aria-hidden','true');
    }
  }

  function ensureOverlay(){
    let overlay=document.getElementById('raidVictoryV59');
    if(overlay)return overlay;
    overlay=document.createElement('section');
    overlay.id='raidVictoryV59';
    overlay.className='raid-victory-v59';
    overlay.setAttribute('aria-hidden','true');
    overlay.innerHTML=`
      <div class="raid-victory-card" role="dialog" aria-modal="true" aria-labelledby="raidVictoryTitle">
        <div class="raid-victory-crown">♛</div>
        <small class="raid-victory-kicker">РЕЙД ЗАВЕРШЁН</small>
        <h2 id="raidVictoryTitle">ЦЕНТР ВСЕЛЕННОЙ СВЕРГНУТ</h2>
        <p class="raid-victory-reward" id="raidVictoryReward">Подводим итоги боя…</p>
        <div class="raid-victory-ranking" id="raidVictoryRanking"></div>
        <div class="raid-victory-actions">
          <button type="button" data-victory-help>СПРАВКА</button>
          <button type="button" data-victory-close>ПРОДОЛЖИТЬ</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    overlay.querySelector('[data-victory-close]')?.addEventListener('click',()=>closeVictory(true));
    overlay.querySelector('[data-victory-help]')?.addEventListener('click',()=>{
      closeVictory(true);
      const help=document.querySelector('[data-open-raid-page="help"]');
      if(help){
        help.click();
        requestAnimationFrame(unlockScreen);
      }
    });
    return overlay;
  }

  function closeVictory(markDismissed){
    if(markDismissed)dismissed=true;
    const overlay=document.getElementById('raidVictoryV59');
    if(overlay){
      overlay.classList.remove('open');
      overlay.setAttribute('aria-hidden','true');
    }
    unlockScreen();
    tg?.BackButton?.hide?.();
  }

  function renderVictory(victory){
    latestVictory=victory||latestVictory||{};
    const overlay=ensureOverlay();
    const reward=overlay.querySelector('#raidVictoryReward');
    const ranking=overlay.querySelector('#raidVictoryRanking');
    const rows=Array.isArray(latestVictory.rankings)?latestVictory.rankings:[];
    const selfReward=Number(latestVictory.self_reward)||0;

    if(reward){
      reward.innerHTML=latestVictory.resolved
        ? selfReward>0
          ? `Твоя награда: <b>+${fmt(selfReward)} очков влияния</b>`
          : 'Победа засчитана. Ты не вошёл в наградной топ-3.'
        : 'Босс повержен. Начисляем очки влияния…';
    }
    if(ranking){
      const medals=['🥇','🥈','🥉'];
      ranking.innerHTML=rows.length
        ? rows.slice(0,4).map((item,index)=>`<div class="raid-victory-row ${item.is_self?'self':''}">
            <span>${medals[index]||index+1}</span>
            <div><b>${escapeHtml(item.name)}</b><small>${fmt(item.damage)} урона</small></div>
            <strong>${Number(item.reward)>0?`+${fmt(item.reward)}`:'—'}</strong>
          </div>`).join('')
        : '<div class="raid-victory-wait">Итоговый рейтинг загружается…</div>';
    }

    if(!dismissed){
      overlay.classList.add('open');
      overlay.setAttribute('aria-hidden','false');
      document.body.classList.add('raid-victory-open');
      document.body.style.overflow='hidden';
      tg?.BackButton?.show?.();
      tg?.HapticFeedback?.notificationOccurred?.('success');
    }
  }

  async function fetchVictory(){
    if(polling||!bossId||!initData)return;
    polling=true;
    try{
      const response=await fetch(`/boss-app/api/boss/state?boss_id=${encodeURIComponent(bossId)}`,{
        headers:{'X-Telegram-Init-Data':initData},
        cache:'no-store'
      });
      const data=await response.json();
      if(response.ok&&data?.ok&&data.victory?.visible)renderVictory(data.victory);
    }catch(_error){
      /* Основной app.js продолжает обновлять состояние; здесь достаточно повторить позже. */
    }finally{
      polling=false;
    }
  }

  function inspectVictoryDom(){
    const phase=document.getElementById('phaseText')?.textContent?.trim().toUpperCase();
    const hp=document.getElementById('bossHpText')?.textContent||'';
    if(phase==='ПОБЕДА'||/^\s*0\s*\//.test(hp)){
      if(!dismissed)renderVictory(latestVictory||{resolved:false,rankings:[]});
      fetchVictory();
    }
  }

  const phaseNode=document.getElementById('phaseText');
  const hpNode=document.getElementById('bossHpText');
  const observer=new MutationObserver(inspectVictoryDom);
  if(phaseNode)observer.observe(phaseNode,{childList:true,subtree:true,characterData:true});
  if(hpNode)observer.observe(hpNode,{childList:true,subtree:true,characterData:true});

  const raidPage=document.getElementById('raidPage');
  if(raidPage){
    new MutationObserver(()=>{
      if(raidPage.classList.contains('open')){
        const overlay=document.getElementById('raidVictoryV59');
        if(overlay){
          overlay.classList.remove('open');
          overlay.setAttribute('aria-hidden','true');
        }
        unlockScreen();
      }
    }).observe(raidPage,{attributes:true,attributeFilter:['class','aria-hidden']});
  }

  tg?.BackButton?.onClick?.(()=>{
    if(document.getElementById('raidVictoryV59')?.classList.contains('open'))closeVictory(true);
  });

  inspectVictoryDom();
  if(bossId&&initData){
    fetchVictory();
    setInterval(fetchVictory,3000);
  }
})();
