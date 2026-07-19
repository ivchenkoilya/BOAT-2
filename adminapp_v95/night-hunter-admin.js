(()=>{
  'use strict';

  const GAME_KEY='night-hunter';
  const VERSION='Reality 95 · 3 игры';
  let scheduled=false;

  function schedule(){
    if(scheduled)return;
    scheduled=true;
    setTimeout(()=>{scheduled=false;patch();},60);
  }

  function installStyles(){
    if(document.getElementById('v95NightHunterStyles'))return;
    const style=document.createElement('style');
    style.id='v95NightHunterStyles';
    style.textContent=`
      .v95-game-choices{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin:10px 0 2px}
      .v95-game-choice{min-height:46px;border:1px solid #4e3566;border-radius:13px;background:#120d1b;color:#bcaec8;font-weight:900;font-size:11px}
      .v95-game-choice.active{border-color:#a477c8;color:#fff;background:linear-gradient(180deg,#503071,#29163d);box-shadow:0 0 18px #9252bf35}
      .v95-game-choice[data-v95-game="night-hunter"]{border-color:#245b5a;color:#9bf8e9;background:linear-gradient(180deg,#113534,#081a1b)}
      .v95-game-choice[data-v95-game="night-hunter"].active{border-color:#70e8d6;color:#eafffb;background:linear-gradient(180deg,#17635e,#0b312f);box-shadow:0 0 22px #42d7c943}
      #gameCards .game-card.v95-night-hunter{position:relative;overflow:hidden;border-color:#2f7470;background:radial-gradient(circle at 100% 0,#39d9c72d,transparent 42%),linear-gradient(155deg,#102727,#070f12);box-shadow:0 18px 48px #0008,0 0 28px #39cdbb1d}
      #gameCards .game-card.v95-night-hunter:before{content:"";position:absolute;inset:0;pointer-events:none;background:repeating-linear-gradient(0deg,transparent 0 5px,#8affef08 6px);opacity:.45}
      #gameCards .game-card.v95-night-hunter>*{position:relative}
      .v95-hunter-tag{display:inline-flex;margin-top:7px;padding:5px 8px;border:1px solid #397d78;border-radius:999px;color:#aafff1;background:#0a2b2a;font-size:8px;font-weight:900;letter-spacing:.09em}
      .v95-night-hunter .v89-attempt-hero{border-color:#285b58;background:#071616}
      .v95-night-hunter .v89-attempt-hero b{color:#a9fff2}
      .v95-night-hunter .v89-meter{border-color:#285b58}.v95-night-hunter .v89-meter i{background:linear-gradient(90deg,#167a70,#72f3df)}
      .v95-night-hunter .v89-card-give{border-color:#377c76;background:linear-gradient(180deg,#18534f,#0b2b29);color:#d8fff9;box-shadow:0 9px 22px #1aa99825}
      .v95-hunter-note{margin:9px 0 0;padding:9px 10px;border:1px solid #254b49;border-radius:11px;background:#071313;color:#78cfc4;font-size:9px;line-height:1.4}
      @media(min-width:480px){.v95-game-choices{grid-template-columns:repeat(4,1fr)}}
    `;
    document.head.appendChild(style);
  }

  function ensureSelector(){
    const select=document.getElementById('v89AttemptGame');
    if(!select)return false;
    const all=select.querySelector('option[value="all"]');
    if(all&&all.textContent!=='Все три игры одновременно')all.textContent='Все три игры одновременно';
    if(!select.querySelector(`option[value="${GAME_KEY}"]`)){
      const option=document.createElement('option');
      option.value=GAME_KEY;
      option.textContent='🔦 Только Ночной охотник';
      select.appendChild(option);
    }
    if(!document.getElementById('v95GameChoices')){
      const choices=document.createElement('div');
      choices.id='v95GameChoices';
      choices.className='v95-game-choices';
      choices.innerHTML=`
        <button type="button" class="v95-game-choice active" data-v95-game="all">🎮 Все 3</button>
        <button type="button" class="v95-game-choice" data-v95-game="rooftop">🌃 Крыши</button>
        <button type="button" class="v95-game-choice" data-v95-game="heist">🏛 Ограбление</button>
        <button type="button" class="v95-game-choice" data-v95-game="${GAME_KEY}">🔦 Ночной охотник</button>`;
      document.querySelector('#v89AttemptPanel .v89-attempt-row')?.insertAdjacentElement('afterend',choices);
    }
    return true;
  }

  function hunterCard(){
    return [...document.querySelectorAll('#gameCards .game-card')].find(card=>{
      const key=card.dataset.gameKey||card.querySelector('[data-v89-game]')?.dataset.v89Game||'';
      const title=card.querySelector('h3')?.textContent||'';
      return key===GAME_KEY||title.includes('Ночной охотник');
    })||null;
  }

  function enhanceHunterCard(){
    const card=hunterCard();
    if(!card)return false;
    card.dataset.gameKey=GAME_KEY;
    card.classList.add('v95-night-hunter');
    const headCopy=card.querySelector('.game-head>div');
    if(headCopy&&!headCopy.querySelector('.v95-hunter-tag')){
      const tag=document.createElement('span');
      tag.className='v95-hunter-tag';
      tag.textContent='SURVIVAL HORROR · 2:30';
      headCopy.appendChild(tag);
    }
    const give=card.querySelector('.v89-card-give');
    if(give){
      give.dataset.v89Game=GAME_KEY;
      if(give.textContent!=='🔦 ВЫДАТЬ ПОПЫТКИ НОЧНОМУ ОХОТНИКУ'){
        give.textContent='🔦 ВЫДАТЬ ПОПЫТКИ НОЧНОМУ ОХОТНИКУ';
      }
    }
    if(!card.querySelector('.v95-hunter-note')){
      const note=document.createElement('div');
      note.className='v95-hunter-note';
      note.textContent='Отдельный лимит попыток, рекорд, выплаты и активные сессии Ночного охотника.';
      (give||card.lastElementChild)?.insertAdjacentElement(give?'beforebegin':'afterend',note);
    }
    return true;
  }

  function patchHistory(){
    document.querySelectorAll('#gameRuns .run-item h4').forEach(title=>{
      if(title.textContent.trim()===GAME_KEY)title.textContent='🔦 Ночной охотник';
    });
  }

  function patchVersion(){
    const version=document.getElementById('versionText');
    if(version&&version.textContent!==VERSION)version.textContent=VERSION;
    if(document.title!=='Админ-центр Reality 95')document.title='Админ-центр Reality 95';
  }

  function syncChoice(){
    const select=document.getElementById('v89AttemptGame');
    if(!select)return;
    document.querySelectorAll('[data-v95-game]').forEach(button=>{
      button.classList.toggle('active',button.dataset.v95Game===select.value);
    });
  }

  function patch(){
    installStyles();
    ensureSelector();
    enhanceHunterCard();
    patchHistory();
    patchVersion();
    syncChoice();
  }

  document.addEventListener('click',event=>{
    const choice=event.target.closest('[data-v95-game]');
    if(choice){
      const select=document.getElementById('v89AttemptGame');
      if(select)select.value=choice.dataset.v95Game||'all';
      syncChoice();
      window.Telegram?.WebApp?.HapticFeedback?.selectionChanged?.();
      return;
    }
    if(event.target.closest('[data-v89-game]'))setTimeout(()=>{syncChoice();patchVersion();},0);
  },true);

  document.addEventListener('change',event=>{
    if(event.target?.id==='v89AttemptGame')syncChoice();
  });

  document.addEventListener('DOMContentLoaded',()=>{
    patch();
    new MutationObserver(schedule).observe(document.body,{childList:true,subtree:true});
    setTimeout(patch,250);
  });
})();
