(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  let latest=null;
  let lastLog='';
  let phase=1;
  let audio=null;
  let receivedAt=performance.now();

  function ensureUi(){
    const stage=document.getElementById('bossStage');
    if(!stage)return;
    document.body.classList.add('raid-v149-ready');

    if(!document.getElementById('raidNoticesV149')){
      const lane=document.createElement('div');
      lane.id='raidNoticesV149';
      lane.className='raid-v149-notices';
      lane.setAttribute('aria-live','polite');
      stage.appendChild(lane);
    }

    if(!document.getElementById('raidMusicV149')){
      const button=document.createElement('button');
      button.id='raidMusicV149';
      button.type='button';
      button.className='raid-v149-music';
      button.setAttribute('aria-label','Включить или выключить музыку боя');
      button.innerHTML='<strong>♫</strong><span>МУЗЫКА</span>';
      stage.appendChild(button);
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
        if(weaken)row.insertAdjacentHTML('beforeend',`<span title="Урон снижен">−30% ×${weaken}</span>`);
        if(crit)row.insertAdjacentHTML('beforeend',`<span title="Критический урон отключён">КРИТ×${crit}</span>`);
        card.appendChild(row);
      });
    });
  }

  function patchHelp(){
    const scroll=document.querySelector('#raidHelpV61 .raid-v61-help-scroll');
    if(!scroll||scroll.querySelector('.raid-v149-help-card'))return;
    const intro=scroll.querySelector('.raid-v61-help-intro');
    if(intro){
      const text=intro.querySelector('span');
      if(text)text.textContent='У босса 100 000 HP. Следи за нижним предупреждением, защищайся вовремя и не пропускай ульту.';
    }
    const card=document.createElement('div');
    card.className='raid-v149-help-card';
    card.innerHTML=`
      <b>УСИЛЕННЫЙ ЦЕНТР ВСЕЛЕННОЙ</b>
      <span>Обычные удары наносят 100–200 базового урона каждой выбранной цели. Защита, уклонение и предметы продолжают его снижать.</span>
      <span>После 50% HP босс один раз готовит ульту «Ты здесь никто»: предупреждение длится 10 секунд, затем весь живой отряд получает 200–300 урона с игнорированием защиты.</span>
      <span>Атаки могут на 2 обычных удара снизить урон игрока на 30% или полностью отключить критический урон.</span>
      <span>Каждые 5 минут босс восстанавливает случайно 100–150 HP, если восстановление не заблокировано.</span>`;
    intro?.insertAdjacentElement('afterend',card);
  }

  function applyState(data){
    if(!data?.ok)return;
    latest=data;
    receivedAt=performance.now();
    const battle=data.battle||{};
    phase=Number(battle.hp)<=0?4:Math.max(1,Math.min(4,Number(battle.phase)||1));
    patchWarning(battle);
    patchFighters(data);
    patchHelp();
    audio?.setPhase(phase);

    const current=String((data.logs||[])[0]||'').trim();
    if(lastLog&&current&&current!==lastLog){
      notice(current,kindFor(current));
    }
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

  function createAudioEngine(){
    const AudioContext=window.AudioContext||window.webkitAudioContext;
    if(!AudioContext)return null;
    let context=null;
    let master=null;
    let timer=null;
    let currentPhase=1;
    let playing=false;
    let step=0;
    const button=()=>document.getElementById('raidMusicV149');
    const patterns={
      1:{bpm:68,notes:[43,null,38,null],wave:'triangle',gain:.055},
      2:{bpm:88,notes:[43,50,38,50],wave:'sawtooth',gain:.05},
      3:{bpm:112,notes:[36,43,48,46,36,50,43,53],wave:'sawtooth',gain:.047},
      4:{bpm:142,notes:[31,38,43,31,46,38,50,41],wave:'square',gain:.038}
    };
    const names=['','ПРОБУЖДЕНИЕ','ТРЕВОГА','ЯРОСТЬ','ФИНАЛ'];

    function frequency(midi){return 440*Math.pow(2,(midi-69)/12)}
    function pulse(note,config,when){
      if(note==null||!context||!master)return;
      const osc=context.createOscillator();
      const gain=context.createGain();
      const filter=context.createBiquadFilter();
      osc.type=config.wave;
      osc.frequency.setValueAtTime(frequency(note),when);
      if(currentPhase>=3)osc.frequency.exponentialRampToValueAtTime(frequency(note+7),when+.09);
      filter.type='lowpass';
      filter.frequency.setValueAtTime(currentPhase===4?950:650,when);
      gain.gain.setValueAtTime(.0001,when);
      gain.gain.exponentialRampToValueAtTime(config.gain,when+.018);
      gain.gain.exponentialRampToValueAtTime(.0001,when+.22);
      osc.connect(filter);filter.connect(gain);gain.connect(master);
      osc.start(when);osc.stop(when+.25);

      if(currentPhase===4&&step%2===0){
        const kick=context.createOscillator();
        const kg=context.createGain();
        kick.type='sine';
        kick.frequency.setValueAtTime(85,when);
        kick.frequency.exponentialRampToValueAtTime(35,when+.12);
        kg.gain.setValueAtTime(.08,when);
        kg.gain.exponentialRampToValueAtTime(.0001,when+.16);
        kick.connect(kg);kg.connect(master);kick.start(when);kick.stop(when+.18);
      }
    }
    function schedule(){
      if(!playing||!context)return;
      const config=patterns[currentPhase];
      pulse(config.notes[step%config.notes.length],config,context.currentTime+.02);
      step++;
      const delay=Math.max(95,60000/config.bpm/2);
      timer=setTimeout(schedule,delay);
    }
    async function start(){
      if(!context){
        context=new AudioContext();
        master=context.createGain();
        master.gain.value=.75;
        master.connect(context.destination);
      }
      await context.resume();
      if(playing)return;
      playing=true;step=0;schedule();render();
    }
    function stop(){
      playing=false;
      clearTimeout(timer);timer=null;
      render();
    }
    function render(){
      const node=button();
      if(!node)return;
      node.classList.toggle('playing',playing);
      const label=node.querySelector('span');
      if(label)label.textContent=playing?names[currentPhase]:'МУЗЫКА';
    }
    function setPhase(value){
      currentPhase=Math.max(1,Math.min(4,Number(value)||1));
      step=0;render();
    }
    function toggle(){playing?stop():start().catch(()=>{});}
    return {toggle,setPhase,start,stop,get playing(){return playing;}};
  }

  let autoMusicStarted=false;
  document.addEventListener('pointerdown',event=>{
    if(autoMusicStarted||event.target.closest('#raidMusicV149'))return;
    autoMusicStarted=true;
    audio?.start().catch(()=>{});
  },{capture:true,once:true});

  document.addEventListener('click',event=>{
    if(event.target.closest('#raidMusicV149')){
      event.preventDefault();
      audio?.toggle();
      tg?.HapticFeedback?.impactOccurred?.('light');
    }
  },true);

  window.addEventListener('raid-state-updated',event=>applyState(event.detail));
  document.addEventListener('click',()=>setTimeout(patchHelp,0),true);

  ensureUi();
  installToastMirror();
  audio=createAudioEngine();
  if(window.__raidBossState)applyState(window.__raidBossState);
  setInterval(()=>{
    ensureUi();
    patchHelp();
    if(latest)patchWarning(latest.battle||{});
  },250);
})();
