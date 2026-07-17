(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  const qs = new URLSearchParams(location.search);
  const bossId = (tg?.initDataUnsafe?.start_param || qs.get('boss') || qs.get('boss_id') || '').trim();
  const initData = tg?.initData || '';
  const demoRequested = qs.get('demo') === '1' || !initData;
  const apiBase = location.pathname.startsWith('/boss-app') ? './api/boss' : '/boss-app/api/boss';
  const phaseInfo = {
    1: { name: 'ФАЗА I · САМОУВЕРЕННОСТЬ', text: 'Он уверен, что всё внимание уже принадлежит ему.' },
    2: { name: 'ФАЗА II · РАЗДРАЖЕНИЕ', text: 'Его улыбка исчезает: чужая воля начинает мешать абсолютному эго.' },
    3: { name: 'ФАЗА III · ЯРОСТЬ', text: 'Реальность трещит, а Центр Вселенной отвечает всё опаснее.' },
    4: { name: 'ФАЗА IV · РАЗРУШЕНИЕ ЭГО', text: 'Трон рушится. Осталось выдержать последний всплеск его ярости.' },
  };

  const state = {
    data: null,
    serverOffset: 0,
    polling: null,
    busy: false,
    sound: true,
    audio: null,
    lastPhase: 1,
    lastHp: null,
    localDemo: demoRequested,
    demo: null,
  };

  const el = id => document.getElementById(id);
  const ui = {
    loading: el('loading'), loadingText: el('loadingText'), timer: el('timer'), bossImage: el('bossImage'),
    bossHpText: el('bossHpText'), bossHpBar: el('bossHpBar'), bossPercent: el('bossPercent'), phaseBadge: el('phaseBadge'),
    phaseText: el('phaseText'), selfAvatar: el('selfAvatar'), selfName: el('selfName'), selfRole: el('selfRole'),
    selfHpBar: el('selfHpBar'), selfHpText: el('selfHpText'), selfDamage: el('selfDamage'), statusLine: el('statusLine'),
    attackBtn: el('attackBtn'), abilityBtn: el('abilityBtn'), healBtn: el('healBtn'), defendBtn: el('defendBtn'),
    attackHint: el('attackHint'), abilityName: el('abilityName'), abilityHint: el('abilityHint'),
    attackCooldown: el('attackCooldown'), abilityCooldown: el('abilityCooldown'), healCooldown: el('healCooldown'),
    defendCooldown: el('defendCooldown'), fighterCount: el('fighterCount'), fighters: el('fighters'), logs: el('logs'),
    damageLayer: el('damageLayer'), toast: el('toast'), soundBtn: el('soundBtn'), resultOverlay: el('resultOverlay'),
    resultTitle: el('resultTitle'), resultSubtitle: el('resultSubtitle'), podium: el('podium'), allParticipants: el('allParticipants'),
    closeResultBtn: el('closeResultBtn'), imageWrap: document.querySelector('.image-wrap'),
  };

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  }
  function initials(name) {
    const parts = String(name || '?').trim().split(/\s+/).filter(Boolean);
    return (parts.slice(0,2).map(p => p[0]).join('') || '?').toUpperCase();
  }
  function fmtTime(seconds) {
    seconds = Math.max(0, Math.ceil(seconds || 0));
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  }
  function fmtCd(seconds) {
    seconds = Math.max(0, Math.ceil(seconds || 0));
    if (seconds <= 0) return 'ГОТОВО';
    if (seconds < 60) return `${seconds} С`;
    return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')}`;
  }
  function haptic(type='light') {
    try { tg?.HapticFeedback?.impactOccurred(type); } catch (_) {}
  }
  function notify(type='success') {
    try { tg?.HapticFeedback?.notificationOccurred(type); } catch (_) {}
  }
  function toast(text, ms=2200) {
    ui.toast.textContent = text;
    ui.toast.classList.add('visible');
    clearTimeout(toast._t);
    toast._t = setTimeout(() => ui.toast.classList.remove('visible'), ms);
  }
  function showDamage(value, kind='normal') {
    const node = document.createElement('div');
    node.className = `damage-number ${kind === 'critical' ? 'critical' : kind === 'heal' ? 'heal' : ''}`;
    node.textContent = kind === 'heal' ? `+${value} HP` : `${kind === 'critical' ? 'КРИТ ' : ''}−${value}`;
    node.style.left = `${42 + Math.random()*18}%`;
    node.style.top = `${39 + Math.random()*16}%`;
    ui.damageLayer.appendChild(node);
    setTimeout(() => node.remove(), 1100);
  }
  function screenImpact(critical=false) {
    document.body.classList.remove('shake','hit-flash');
    void document.body.offsetWidth;
    document.body.classList.add('shake','hit-flash');
    setTimeout(() => document.body.classList.remove('shake','hit-flash'), 500);
    haptic(critical ? 'heavy' : 'medium');
  }

  class SoundEngine {
    constructor() { this.ctx = null; this.master = null; this.started = false; this.padTimer = null; }
    ensure() {
      if (!state.sound) return;
      if (!this.ctx) {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        this.ctx = new Ctx();
        this.master = this.ctx.createGain();
        this.master.gain.value = .12;
        this.master.connect(this.ctx.destination);
      }
      if (this.ctx.state === 'suspended') this.ctx.resume();
      if (!this.started) this.startAmbient();
    }
    tone(freq, duration=.18, type='sine', gain=.18, detune=0) {
      if (!state.sound) return;
      this.ensure();
      if (!this.ctx) return;
      const now = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const g = this.ctx.createGain();
      osc.type = type; osc.frequency.value = freq; osc.detune.value = detune;
      g.gain.setValueAtTime(0.0001, now);
      g.gain.exponentialRampToValueAtTime(gain, now + .012);
      g.gain.exponentialRampToValueAtTime(.0001, now + duration);
      osc.connect(g); g.connect(this.master); osc.start(now); osc.stop(now + duration + .03);
    }
    hit(critical=false) {
      this.tone(critical ? 95 : 130, critical ? .42 : .23, 'sawtooth', critical ? .36 : .22);
      setTimeout(() => this.tone(critical ? 390 : 260, .16, 'triangle', .14), 30);
    }
    heal() { this.tone(330,.3,'sine',.12); setTimeout(()=>this.tone(440,.34,'sine',.11),110); setTimeout(()=>this.tone(660,.38,'sine',.08),220); }
    boss() { this.tone(62,.7,'sawtooth',.28); this.tone(87,.65,'square',.08,-15); }
    startAmbient() {
      if (!this.ctx || this.started) return;
      this.started = true;
      const playPad = () => {
        if (!state.sound) return;
        const roots = [55,65.41,73.42,49];
        const root = roots[Math.floor(Math.random()*roots.length)];
        this.tone(root, 5.8, 'sine', .025);
        this.tone(root*1.5, 5.2, 'sine', .015, 6);
        this.tone(root*2, 4.7, 'triangle', .012, -7);
      };
      playPad();
      this.padTimer = setInterval(playPad, 4700);
    }
    toggle() {
      state.sound = !state.sound;
      ui.soundBtn.textContent = state.sound ? '🔊' : '🔇';
      if (state.sound) this.ensure();
      if (this.master && this.ctx) this.master.gain.setTargetAtTime(state.sound ? .12 : .0001, this.ctx.currentTime, .05);
      return state.sound;
    }
  }
  state.audio = new SoundEngine();

  function startStars() {
    const canvas = el('stars');
    const ctx = canvas.getContext('2d');
    let stars = [];
    function resize() {
      const dpr = Math.min(2, devicePixelRatio || 1);
      canvas.width = innerWidth*dpr; canvas.height = innerHeight*dpr;
      canvas.style.width = `${innerWidth}px`; canvas.style.height = `${innerHeight}px`;
      ctx.setTransform(dpr,0,0,dpr,0,0);
      stars = Array.from({length:Math.min(115,Math.floor(innerWidth*innerHeight/5000))},()=>({x:Math.random()*innerWidth,y:Math.random()*innerHeight,r:.3+Math.random()*1.1,s:.08+Math.random()*.28,a:.22+Math.random()*.7}));
    }
    function frame() {
      ctx.clearRect(0,0,innerWidth,innerHeight);
      for (const st of stars) {
        st.y += st.s; if (st.y > innerHeight+2) { st.y=-2; st.x=Math.random()*innerWidth; }
        ctx.globalAlpha = st.a; ctx.fillStyle = Math.random()>.84 ? '#e9c873' : '#cdb9ff';
        ctx.beginPath(); ctx.arc(st.x,st.y,st.r,0,Math.PI*2); ctx.fill();
      }
      requestAnimationFrame(frame);
    }
    addEventListener('resize',resize,{passive:true}); resize(); frame();
  }

  async function api(path='', options={}) {
    const headers = {'Content-Type':'application/json', ...(options.headers || {})};
    if (initData) headers['X-Telegram-Init-Data'] = initData;
    const response = await fetch(`${apiBase}${path}`, {...options, headers});
    const data = await response.json().catch(()=>({ok:false,reason:'Сервер вернул неправильный ответ.'}));
    if (!response.ok || data.ok === false) throw new Error(data.reason || data.error || 'Действие не выполнено.');
    return data;
  }

  function makeDemoState() {
    const now = Math.floor(Date.now()/1000);
    return {
      ok:true, now,
      battle:{boss_id:'demo',status:'active',hp:50000,max_hp:50000,phase:1,ends_at:now+10800},
      self:{user_id:802628215,name:'Илья',role_key:'honest_hero',role_title:'Честный Главный герой',role_emoji:'👑',hp:140,max_hp:140,damage:0,attacks:0,critical_hits:0,protected:false,knocked_out_until:0,cooldowns:{attack:0,ability:0,heal:0,defend:0},ability_name:'Кульминация',ability_hint:'Гарантированный сокрушительный крит'},
      fighters:[
        {user_id:802628215,name:'Илья',role_title:'Честный Главный герой',role_emoji:'👑',hp:140,max_hp:140,damage:0,attacks:0,critical_hits:0,is_self:true},
        {user_id:201,name:'Солёный',role_title:'Второстепенная роль',role_emoji:'🎭',hp:125,max_hp:125,damage:820,attacks:6,critical_hits:1},
        {user_id:202,name:'Максовка',role_title:'Массовка',role_emoji:'👥',hp:115,max_hp:115,damage:590,attacks:5,critical_hits:0},
      ],
      logs:['🌌 Центр Вселенной потребовал всё внимание беседы.','🎭 Солёный перетянул внимание: −174 HP.','👥 Максовка задела его эго: −121 HP.'],
      rewards:[250,150,100]
    };
  }

  function demoAction(action) {
    const d = state.demo;
    const now = Math.floor(Date.now()/1000);
    const self = d.self;
    if (d.battle.status !== 'active') throw new Error('Бой уже завершён.');
    const cd = self.cooldowns[action === 'hit' ? 'attack' : action];
    if (cd > 0) throw new Error('Действие ещё восстанавливается.');
    let result = {ok:true,action};
    if (action === 'hit') {
      const critical = Math.random()<.3;
      const damage = Math.round((175+Math.random()*75)*(critical?2.4:1));
      d.battle.hp=Math.max(0,d.battle.hp-damage); self.damage+=damage; self.attacks++; if(critical)self.critical_hits++;
      self.cooldowns.attack=5; result={...result,damage,critical};
      d.logs.push(`${critical?'💥':'💢'} Илья ${critical?'нанёс критический удар':'задел его эго'}: −${damage} HP.`);
    } else if (action === 'ability') {
      const damage=Math.round(1050+Math.random()*300); d.battle.hp=Math.max(0,d.battle.hp-damage); self.damage+=damage; self.attacks++;
      self.cooldowns.ability=600; result={...result,damage,critical:true,ability:self.ability_name}; d.logs.push(`✨ Илья: «Кульминация» — −${damage} HP.`);
    } else if (action === 'heal') {
      const healed=Math.min(self.max_hp-self.hp,55); if(healed<=0)throw new Error('Здоровье уже полное.'); self.hp+=healed; self.cooldowns.heal=90; result={...result,healed}; d.logs.push(`❤️‍🩹 Илья восстановил ${healed} HP.`);
    } else if (action === 'defend') {
      self.protected=true; self.cooldowns.defend=180; d.logs.push('🛡 Илья приготовился отразить следующую атаку.');
    }
    d.fighters[0]={...d.fighters[0],hp:self.hp,damage:self.damage,attacks:self.attacks,critical_hits:self.critical_hits};
    d.battle.phase = d.battle.hp/d.battle.max_hp>.75?1:d.battle.hp/d.battle.max_hp>.5?2:d.battle.hp/d.battle.max_hp>.25?3:4;
    if (d.battle.hp<=0) d.battle.status='victory';
    return result;
  }

  async function joinBattle() {
    if (state.localDemo) {
      state.demo = makeDemoState();
      state.data = state.demo;
      render(state.data,true);
      hideLoading();
      toast('Открыт демонстрационный режим.');
      return;
    }
    if (!bossId) throw new Error('Не найден идентификатор боя. Открой приложение из карточки босса.');
    const data = await api('/session',{method:'POST',body:JSON.stringify({boss_id:bossId})});
    state.data=data; state.serverOffset=(data.now||Date.now()/1000)-Date.now()/1000;
    render(data,true); hideLoading(); startPolling();
  }

  async function poll() {
    if (state.localDemo || state.busy || !bossId) return;
    try {
      const data=await api(`/state?boss_id=${encodeURIComponent(bossId)}`,{method:'GET'});
      state.data=data; state.serverOffset=(data.now||Date.now()/1000)-Date.now()/1000; render(data,false);
    } catch (err) { ui.statusLine.textContent=err.message; ui.statusLine.classList.add('danger'); }
  }
  function startPolling() { clearInterval(state.polling); state.polling=setInterval(poll,1400); }

  async function action(name) {
    if (state.busy) return;
    state.audio.ensure(); state.busy=true; setButtonsBusy(true);
    try {
      let result;
      if (state.localDemo) result=demoAction(name);
      else result=await api('/action',{method:'POST',body:JSON.stringify({boss_id:bossId,action:name})});
      if (result.damage) { showDamage(result.damage,result.critical?'critical':'normal'); screenImpact(!!result.critical); state.audio.hit(!!result.critical); toast(result.critical?`Критический удар: −${result.damage} HP`:`Урон: −${result.damage} HP`); }
      else if (result.healed) { showDamage(result.healed,'heal'); state.audio.heal(); notify('success'); toast(`Восстановлено ${result.healed} HP`); }
      else if (name==='defend') { haptic('medium'); toast('Следующая атака босса будет отражена.'); }
      if (state.localDemo) render(state.demo,false); else await poll();
    } catch (err) { notify('error'); toast(err.message,3000); }
    finally { state.busy=false; setButtonsBusy(false); }
  }

  function setButtonsBusy(value) {
    if (!state.data?.self) return;
    for (const btn of [ui.attackBtn,ui.abilityBtn,ui.healBtn,ui.defendBtn]) btn.dataset.busy=value?'1':'0';
    updateCooldownUI();
  }

  function render(data, first=false) {
    if (!data?.battle) return;
    const b=data.battle; const self=data.self; const phase=Math.max(1,Math.min(4,Number(b.phase)||1));
    const ratio=Math.max(0,Math.min(1,b.hp/b.max_hp));
    ui.bossHpText.textContent=`${Number(b.hp).toLocaleString('ru-RU')} / ${Number(b.max_hp).toLocaleString('ru-RU')} HP`;
    ui.bossHpBar.style.width=`${ratio*100}%`; ui.bossPercent.textContent=`${Math.ceil(ratio*100)}%`;
    ui.phaseBadge.textContent=phaseInfo[phase].name; ui.phaseText.textContent=phaseInfo[phase].text;
    if (state.lastPhase!==phase || first) {
      ui.imageWrap.classList.remove('phase-change'); void ui.imageWrap.offsetWidth; ui.imageWrap.classList.add('phase-change');
      ui.bossImage.src=`./assets/boss_phase_${phase}.webp`; state.lastPhase=phase;
    }
    if (self) {
      ui.selfAvatar.textContent=initials(self.name); ui.selfName.textContent=self.name; ui.selfRole.textContent=`${self.role_emoji||''} ${self.role_title||''}`.trim();
      const pr=Math.max(0,Math.min(1,self.hp/self.max_hp)); ui.selfHpBar.style.width=`${pr*100}%`;
      ui.selfHpText.textContent=`${self.hp} / ${self.max_hp} HP`; ui.selfDamage.textContent=`Урон: ${Number(self.damage||0).toLocaleString('ru-RU')}`;
      ui.abilityName.textContent=self.ability_name||'Способность роли'; ui.abilityHint.textContent=self.ability_hint||'Особый эффект роли';
      const now=Date.now()/1000+state.serverOffset;
      const down=Math.max(0,(self.knocked_out_until||0)-now);
      ui.statusLine.classList.toggle('danger',down>0||self.hp<=Math.max(1,self.max_hp*.25));
      ui.statusLine.textContent=down>0?`Ты выбит из боя ещё на ${Math.ceil(down)} сек. Лечение может вернуть тебя раньше.`:self.protected?'Щит активен: следующая атака босса будет отражена.':'Ты в бою. Следи за здоровьем и действиями босса.';
    }
    renderFighters(data.fighters||[],self?.user_id); renderLogs(data.logs||[]);
    ui.fighterCount.textContent=`${(data.fighters||[]).length}/4`;
    if (b.status==='victory') showResult(data,true);
    else if (b.status!=='active' && b.status!=='resolving') showResult(data,false);
    state.data=data; updateCooldownUI();
    if (state.lastHp!==null && b.hp>state.lastHp) showDamage(b.hp-state.lastHp,'heal');
    state.lastHp=b.hp;
  }

  function renderFighters(fighters,selfId) {
    const slots=[...fighters]; while(slots.length<4)slots.push(null);
    ui.fighters.innerHTML=slots.slice(0,4).map((f,i)=>{
      if(!f)return `<div class="fighter-card"><div class="avatar">${i+1}</div><div class="fighter-info"><div class="fighter-name">Свободное место</div><div class="fighter-sub">Ожидает участника</div><div class="mini-hp"><div style="width:0"></div></div></div></div>`;
      const pct=Math.max(0,Math.min(100,(f.hp/f.max_hp)*100));
      return `<div class="fighter-card ${Number(f.user_id)===Number(selfId)?'me':''}"><div class="avatar">${escapeHtml(initials(f.name))}</div><div class="fighter-info"><div class="fighter-name">${escapeHtml(f.name)} ${Number(f.user_id)===Number(selfId)?'<span>· ты</span>':''}</div><div class="fighter-sub">${escapeHtml((f.role_emoji||'')+' '+(f.role_title||''))} · ${Number(f.damage||0).toLocaleString('ru-RU')} урона</div><div class="mini-hp"><div style="width:${pct}%"></div></div></div></div>`;
    }).join('');
  }
  function renderLogs(logs) {
    ui.logs.innerHTML=(logs.length?logs.slice(-6):['Бой только начался.']).reverse().map(v=>`<div class="log-item">${escapeHtml(v)}</div>`).join('');
  }

  function currentNow() { return Date.now()/1000+state.serverOffset; }
  function updateCooldownUI() {
    const d=state.data; if(!d?.self)return;
    const c=d.self.cooldowns||{}; const now=currentNow();
    const down=Math.max(0,(d.self.knocked_out_until||0)-now); const active=d.battle?.status==='active';
    const vals={attack:Math.max(0,c.attack||0),ability:Math.max(0,c.ability||0),heal:Math.max(0,c.heal||0),defend:Math.max(0,c.defend||0)};
    if(state.localDemo){ for(const k of Object.keys(vals)){ if(vals[k]>0){ vals[k]=Math.max(0,vals[k]-.25); d.self.cooldowns[k]=vals[k]; } } }
    ui.attackCooldown.textContent=fmtCd(vals.attack); ui.abilityCooldown.textContent=fmtCd(vals.ability); ui.healCooldown.textContent=fmtCd(vals.heal); ui.defendCooldown.textContent=fmtCd(vals.defend);
    ui.attackBtn.disabled=!active||state.busy||vals.attack>0||down>0; ui.abilityBtn.disabled=!active||state.busy||vals.ability>0||down>0;
    ui.healBtn.disabled=!active||state.busy||vals.heal>0||d.self.hp>=d.self.max_hp; ui.defendBtn.disabled=!active||state.busy||vals.defend>0||down>0;
    const remaining=Math.max(0,(d.battle.ends_at||0)-currentNow()); ui.timer.textContent=fmtTime(remaining);
  }

  function showResult(data,victory) {
    if(ui.resultOverlay.classList.contains('visible'))return;
    const fighters=[...(data.fighters||[])].sort((a,b)=>b.damage-a.damage||b.attacks-a.attacks);
    const rewards=data.rewards||[250,150,100]; const top=fighters.filter(f=>f.attacks>0).slice(0,3);
    ui.resultTitle.textContent=victory?'Центр Вселенной свергнут':'Центр Вселенной устоял';
    ui.resultSubtitle.textContent=victory?'Его эго рассыпалось, а последнее изображение показывает окончательное поражение. Тройка лучших получает награды.':'Время закончилось. Участники и их вклад сохранены, но награды за победу не выдаются.';
    const ordered=top.length===3?[top[1],top[0],top[2]]:top;
    ui.podium.innerHTML=ordered.map((f,idx)=>{
      const rank=top.indexOf(f); const medals=['🥇','🥈','🥉'];
      return `<div class="podium-card ${rank===0?'first':''}"><span class="medal">${medals[rank]}</span><span class="podium-name">${escapeHtml(f.name)}</span><span class="podium-damage">${Number(f.damage).toLocaleString('ru-RU')} урона</span><span class="podium-reward">${victory?`+${rewards[rank]} очков`:'без награды'}</span></div>`;
    }).join('');
    ui.allParticipants.innerHTML=fighters.map((f,i)=>`<div class="all-row"><span>${i+1}. ${escapeHtml(f.name)} ${i<3&&victory?['🥇','🥈','🥉'][i]:''}</span><span>${Number(f.damage).toLocaleString('ru-RU')} урона</span></div>`).join('')||'<div class="all-row"><span>Участников нет</span><span>0 урона</span></div>';
    ui.resultOverlay.classList.add('visible'); ui.resultOverlay.setAttribute('aria-hidden','false'); notify(victory?'success':'error');
  }

  function hideLoading(){ui.loading.classList.remove('visible');}
  function fatal(message){ui.loadingText.textContent=message; ui.loading.querySelector('h2').textContent='Не удалось войти в бой';}

  ui.attackBtn.addEventListener('click',()=>action('hit'));
  ui.abilityBtn.addEventListener('click',()=>action('ability'));
  ui.healBtn.addEventListener('click',()=>action('heal'));
  ui.defendBtn.addEventListener('click',()=>action('defend'));
  ui.soundBtn.addEventListener('click',()=>{const on=state.audio.toggle();toast(on?'Звук включён':'Звук выключен');});
  ui.closeResultBtn.addEventListener('click',()=>{try{tg?.close();}catch(_){history.back();}});
  document.addEventListener('pointerdown',()=>state.audio.ensure(),{once:true});
  setInterval(updateCooldownUI,250);
  setInterval(()=>{
    if(!state.localDemo||!state.demo||state.demo.battle.status!=='active')return;
    if(Math.random()<.08){
      const self=state.demo.self; const dmg=Math.round(15+Math.random()*24*state.demo.battle.phase);
      if(self.protected){self.protected=false;state.demo.logs.push('🛡 Илья отразил ответную атаку босса.');toast('Щит отразил атаку босса.');}
      else{self.hp=Math.max(0,self.hp-dmg);state.demo.fighters[0].hp=self.hp;state.demo.logs.push(`🌌 Центр Вселенной нанёс Илье ${dmg} урона.`);state.audio.boss();screenImpact(true);toast(`Босс атаковал: −${dmg} HP`);if(self.hp<=0){self.knocked_out_until=Math.floor(Date.now()/1000)+45;state.demo.logs.push('💀 Илья временно выбит из боя.');}}
      render(state.demo,false);
    }
  },4000);

  try {
    tg?.ready(); tg?.expand(); tg?.setHeaderColor?.('#080611'); tg?.setBackgroundColor?.('#07050d');
    setTimeout(()=>{try{tg?.requestFullscreen?.();}catch(_){}},450);
  } catch (_) {}
  startStars();
  joinBattle().catch(err=>fatal(err.message));
})();
