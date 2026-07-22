(() => {
  'use strict';

  const tg = window.Telegram?.WebApp;
  tg?.ready();
  tg?.expand();
  tg?.setHeaderColor?.('#050407');
  tg?.setBackgroundColor?.('#050407');

  const $ = id => document.getElementById(id);
  const params = new URLSearchParams(location.search);
  const initData = tg?.initData || '';
  let bossId = tg?.initDataUnsafe?.start_param || params.get('boss') || '';
  let state = null;
  let stateReceivedAt = performance.now();
  let busy = false;
  let demoMode = false;
  let refreshTimer = null;
  let toastTimer = null;
  // Фоновая музыка битвы
const bossMusic = new Audio('/boss-app/assets/boss_music.mp3');

bossMusic.loop = true;
bossMusic.volume = 0.35;
bossMusic.preload = 'auto';

// Браузер разрешает запуск музыки только после нажатия пользователя
function startBossMusic() {
  bossMusic.play().catch(() => {});
}

document.addEventListener('pointerdown', startBossMusic, {
  once: true
});

  const API_ROOT = '/boss-app/api/boss/';
  const ICONS = '/boss-app/assets/icons.svg';
  const PHASE_NAMES = ['','Раскол эго','Тревога','Ярость','Последний натиск'];
  const COOLDOWN_TOTALS = {attack:5, ability:600, heal:90, defend:180};
  const ROLE_COLORS = {
    decoration:'#a47b4c', dust:'#8f8396', extras:'#9c59bb', secondary:'#4e91c2',
    temporary_hero:'#c86fdf', sabotage_hero:'#c65555', honest_hero:'#e0ae4e', hero:'#e0ae4e'
  };
  const headers = {'Content-Type':'application/json','X-Telegram-Init-Data':initData};
  const fmt = value => new Intl.NumberFormat('ru-RU').format(Math.max(0, Number(value) || 0));

  function duration(value) {
    let seconds = Math.max(0, Math.ceil(Number(value) || 0));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const rest = seconds % 60;
    return hours
      ? `${hours}:${String(minutes).padStart(2,'0')}:${String(rest).padStart(2,'0')}`
      : `${String(minutes).padStart(2,'0')}:${String(rest).padStart(2,'0')}`;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    })[char]);
  }

  function decodeServerText(value) {
    const area = document.createElement('textarea');
    area.innerHTML = String(value ?? '');
    return area.value;
  }

  function icon(name) {
    return `<svg><use href="${ICONS}#${name}"/></svg>`;
  }

  function serverNow() {
    if (!state) return Date.now() / 1000;
    return Number(state.now || Date.now() / 1000) + (performance.now() - stateReceivedAt) / 1000;
  }

  function cooldownLeft(value) {
    return Math.max(0, (Number(value) || 0) - (performance.now() - stateReceivedAt) / 1000);
  }

  function assignState(next) {
    state = next;
    stateReceivedAt = performance.now();
    render();
  }

  function notify(message, type='info') {
    const toast = $('toast');
    toast.textContent = message;
    toast.className = `toast show ${type}`;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.className = 'toast'; }, 2600);
  }

  async function api(path, options={}) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    try {
      const response = await fetch(`${API_ROOT}${path}`, {
        ...options,
        signal:controller.signal,
        headers:{...headers,...(options.headers || {})}
      });
      const data = await response.json().catch(() => ({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if (!response.ok || !data.ok) throw new Error(data.reason || 'Действие не выполнено.');
      return data;
    } catch (error) {
      if (error.name === 'AbortError') throw new Error('Сервер долго не отвечает. Попробуй ещё раз.');
      throw error;
    } finally {
      clearTimeout(timeout);
    }
  }

  async function start() {
    preloadPhases();
    if (!bossId && !initData) {
      startDemo();
      return;
    }
    showError(false);
    try {
      const next = await api('session', {method:'POST',body:JSON.stringify({boss_id:bossId})});
      bossId = next.battle.boss_id;
      assignState(next);
      clearInterval(refreshTimer);
      refreshTimer = setInterval(refresh, 4000);
    } catch (error) {
      showError(true, error.message);
    }
  }

  async function refresh() {
    if (busy || demoMode || !bossId || document.hidden) return;
    try {
      assignState(await api(`state?boss_id=${encodeURIComponent(bossId)}`));
    } catch (error) {
      if (!state) showError(true, error.message);
    }
  }

  function preloadPhases() {
    for (let phase=1; phase<=5; phase++) {
      const image = new Image();
      image.src = `/boss-app/assets/boss_phase_${phase}.webp`;
    }
  }

  function render() {
    if (!state?.battle) return;
    const battle = state.battle;
    const me = state.self || {};
    const hpRatio = battle.max_hp > 0 ? Math.max(0, Math.min(1, battle.hp / battle.max_hp)) : 0;
    const visiblePhase = battle.hp <= 0 || battle.status === 'victory' ? 5 : Math.max(1, Math.min(4, battle.phase || 1));

    $('partyCount').textContent = `${(state.fighters || []).length}/${state.max_fighters || 4}`;
    $('score').textContent = fmt(me.damage || 0);
    $('bossHpFill').style.width = `${hpRatio * 100}%`;
    $('bossHpText').textContent = `${fmt(battle.hp)} / ${fmt(battle.max_hp)} HP`;
    $('bossPercent').textContent = `${Math.round(hpRatio * 100)}%`;
    $('phaseText').textContent = visiblePhase === 5 ? 'ПОБЕДА' : `${visiblePhase}/4`;
    $('phaseName').textContent = visiblePhase === 5 ? 'Эго разрушено' : PHASE_NAMES[visiblePhase];
    $('abilityName').textContent = String(me.ability_name || 'Способность роли').toUpperCase();
    $('abilityHint').textContent = me.ability_hint || 'Особая атака вашей роли';

    const targetImage = `/boss-app/assets/boss_phase_${visiblePhase}.webp`;
    switchBossImage(targetImage);
    renderBossEffects();
    renderFighters();
    renderLogs();
    tick();
    if ($('modal').classList.contains('open')) refreshOpenModal();
  }

  function switchBossImage(src) {
    const image = $('bossImage');
    if (image.getAttribute('src') === src) return;
    image.classList.add('switching');
    const ready = new Image();
    ready.onload = () => {
      image.src = src;
      requestAnimationFrame(() => image.classList.remove('switching'));
    };
    ready.onerror = () => image.classList.remove('switching');
    ready.src = src;
  }

  function renderBossEffects() {
    const battle = state.battle;
    const now = serverNow();
    $('shieldText').textContent = battle.shield_hits > 0 ? `${battle.shield_hits} заряда` : 'разбит';
    if (Number(battle.heal_block_until) > now) {
      $('effectText').textContent = `антихил ${duration(battle.heal_block_until - now)}`;
    } else if (Number(battle.skip_next_action) > 0) {
      $('effectText').textContent = 'атака сорвана';
    } else {
      $('effectText').textContent = 'нет';
    }
  }

  function roleColor(key) {
    return ROLE_COLORS[key] || '#9b7135';
  }

  function renderFighters() {
    const now = serverNow();
    const fighters = [...(state.fighters || [])].sort((a,b) => Number(b.is_self)-Number(a.is_self) || b.damage-a.damage);
    while (fighters.length < (state.max_fighters || 4)) fighters.push(null);
    $('fighters').innerHTML = fighters.slice(0, state.max_fighters || 4).map(fighter => {
      if (!fighter) {
        return `<article class="fighter empty-fighter"><div class="fighter-avatar">${icon('helmet')}</div><strong>СВОБОДНО</strong><small>ЖДЁМ ГЕРОЯ</small><em>—</em><div class="player-hp"><i style="width:0"></i></div><div class="fighter-damage">место в отряде</div></article>`;
      }
      const hp = Math.max(0, Number(fighter.hp) || 0);
      const maxHp = Math.max(1, Number(fighter.max_hp) || 1);
      const knocked = hp <= 0 || Number(fighter.knocked_out_until) > now;
      const classNames = ['fighter', fighter.is_self?'self':'', knocked?'knocked':'', fighter.protected?'protected':''].filter(Boolean).join(' ');
      const initial = Array.from(String(fighter.name || '?').trim())[0] || '?';
      return `<article class="${classNames}" style="--role:${roleColor(fighter.role_key)}">
        <div class="fighter-avatar">${icon('helmet')}<i>${escapeHtml(fighter.role_emoji || initial)}</i></div>
        <strong>${escapeHtml(fighter.name)}</strong><small>${escapeHtml(fighter.role_title)}</small>
        <em>${fmt(hp)}/${fmt(maxHp)}</em><div class="player-hp"><i style="width:${Math.max(0,hp/maxHp*100)}%"></i></div>
        <div class="fighter-damage">⚔ ${fmt(fighter.damage)} урона</div>
      </article>`;
    }).join('');
  }

  function renderLogs() {
    const logs = state.logs?.length ? state.logs : ['Бой только начался.'];
    $('logs').innerHTML = logs.map((entry,index) => {
      const text = escapeHtml(decodeServerText(entry));
      return `<div class="log-entry">${index === 0 ? '<strong>Сейчас · </strong>' : ''}${text}</div>`;
    }).join('');
  }

  function tick() {
    if (!state?.battle) return;
    const battle = state.battle;
    const me = state.self || {};
    const now = serverNow();
    const active = battle.status === 'active' && battle.hp > 0 && battle.ends_at > now;

    $('battleTimer').textContent = duration(Math.max(0, battle.ends_at - now));
    $('nextAction').textContent = active ? duration(Math.max(0, battle.next_action_at - now)) : 'бой завершён';
    renderBossEffects();

    const cooldowns = me.cooldowns || {};
    const attackLeft = cooldownLeft(cooldowns.attack);
    const abilityLeft = cooldownLeft(cooldowns.ability);
    const healLeft = cooldownLeft(cooldowns.heal);
    const defendLeft = cooldownLeft(cooldowns.defend);
    const knockedLeft = Math.max(0, Number(me.knocked_out_until || 0) - now);
    const unavailable = !active || !state.self || Number(me.hp) <= 0 || knockedLeft > 0;

    const attackButton = document.querySelector('[data-action="hit"]');
    attackButton.disabled = busy || unavailable || attackLeft > 0;
    $('attackHint').textContent = !active ? 'БОСС ПОВЕРЖЕН' : knockedLeft > 0 ? `ВСТАТЬ ЧЕРЕЗ ${duration(knockedLeft)}` : attackLeft > 0 ? `СНОВА ЧЕРЕЗ ${duration(attackLeft)}` : 'НАНЕСТИ УДАР';
    $('attackCooldown').style.width = `${Math.min(100, attackLeft / COOLDOWN_TOTALS.attack * 100)}%`;

    const defendButton = document.querySelector('[data-action="defend"]');
    defendButton.disabled = busy || unavailable || defendLeft > 0 || Boolean(me.protected);
    $('defendCooldown').textContent = me.protected ? 'АКТИВНА' : defendLeft > 0 ? duration(defendLeft) : 'ГОТОВО';

    const fullHp = Number(me.hp) >= Number(me.max_hp);
    const healButton = document.querySelector('[data-action="heal"]');
    healButton.disabled = busy || !active || !state.self || healLeft > 0 || fullHp;
    $('healCooldown').textContent = fullHp ? 'HP ПОЛНОЕ' : healLeft > 0 ? duration(healLeft) : 'ГОТОВО';

    const abilityButton = document.querySelector('[data-action="ability"]');
    abilityButton.disabled = busy || unavailable || abilityLeft > 0;
    $('abilityCooldown').textContent = abilityLeft > 0 ? duration(abilityLeft) : 'ГОТОВО';
  }

  async function performAction(type, button) {
    if (busy || button.disabled || !state) return;
    busy = true;
    button.classList.add('firing');
    tick();
    tg?.HapticFeedback?.impactOccurred?.(type === 'hit' ? 'heavy' : 'medium');
    try {
      if (demoMode) {
        await demoAction(type);
        return;
      }
      const result = await api('action', {method:'POST',body:JSON.stringify({boss_id:bossId,action:type})});
      actionFeedback(type, result);
      assignState(await api(`state?boss_id=${encodeURIComponent(bossId)}`));
      tg?.HapticFeedback?.notificationOccurred?.('success');
    } catch (error) {
      notify(error.message, 'error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    } finally {
      busy = false;
      button.classList.remove('firing');
      tick();
    }
  }

  function actionFeedback(type, result) {
    if (type === 'hit' || type === 'ability') {
      if (result.miss) {
        showDamage('ПРОМАХ', 'miss');
        notify('Ты промахнулся по чужому самолюбию.');
      } else {
        showDamage(`${result.critical ? 'КРИТ ' : ''}−${fmt(result.damage)}`, result.critical ? 'critical' : '');
        notify(type === 'ability' ? `${result.ability || 'Способность'}: −${fmt(result.damage)} HP` : `Эго задето: −${fmt(result.damage)} HP`, 'success');
      }
    } else if (type === 'heal') {
      notify(`Восстановлено ${fmt(result.healed)} HP`, 'success');
    } else if (type === 'defend') {
      notify('Защита активна до следующей атаки босса.', 'success');
    }
  }

  function showDamage(text, className='') {
    const popup = $('damagePop');
    const flash = $('hitFlash');
    popup.textContent = text;
    popup.className = `damage-pop ${className}`;
    flash.className = 'hit-flash';
    void popup.offsetWidth;
    popup.classList.add('show');
    flash.classList.add('show');
  }

  function normalizeDemoCooldowns() {
    const elapsed = (performance.now() - stateReceivedAt) / 1000;
    for (const key of Object.keys(state.self.cooldowns)) {
      state.self.cooldowns[key] = Math.max(0, state.self.cooldowns[key] - elapsed);
    }
    state.now = Math.floor(Date.now() / 1000);
  }

  async function demoAction(type) {
    await new Promise(resolve => setTimeout(resolve, 260));
    normalizeDemoCooldowns();
    const me = state.self;
    let result = {ok:true,action:type};
    if (type === 'hit' || type === 'ability') {
      const critical = type === 'ability' || Math.random() < .28;
      let damage = type === 'ability' ? 1800 : Math.floor(175 + Math.random() * 75);
      if (critical && type === 'hit') damage = Math.round(damage * 2.4);
      state.battle.hp = Math.max(0, state.battle.hp - damage);
      state.battle.phase = phaseForHp(state.battle.hp,state.battle.max_hp);
      me.damage += damage;
      me.attacks += 1;
      me.cooldowns[type === 'hit' ? 'attack' : 'ability'] = COOLDOWN_TOTALS[type === 'hit' ? 'attack' : 'ability'];
      result = {...result,damage,critical,ability:me.ability_name};
      state.logs.unshift(`${type === 'ability' ? '✨' : '💢'} ${me.name} нанёс боссу ${damage} урона.`);
      if (state.battle.hp <= 0) state.battle.status = 'victory';
    } else if (type === 'heal') {
      const healed = Math.min(me.max_hp-me.hp,53);
      me.hp += healed;
      me.cooldowns.heal = COOLDOWN_TOTALS.heal;
      result = {...result,healed};
      state.logs.unshift(`❤️‍🩹 ${me.name} восстановил ${healed} HP.`);
    } else if (type === 'defend') {
      me.protected = true;
      me.cooldowns.defend = COOLDOWN_TOTALS.defend;
      state.logs.unshift(`🛡 ${me.name} приготовился отразить атаку.`);
    }
    const selfFighter = state.fighters.find(item => item.is_self);
    if (selfFighter) Object.assign(selfFighter,{hp:me.hp,damage:me.damage,protected:me.protected,attacks:me.attacks});
    state.logs = state.logs.slice(0,8);
    actionFeedback(type,result);
    assignState(state);
    tg?.HapticFeedback?.notificationOccurred?.('success');
  }

  function phaseForHp(hp,maxHp) {
    const ratio = maxHp > 0 ? hp/maxHp : 0;
    return ratio > .75 ? 1 : ratio > .5 ? 2 : ratio > .25 ? 3 : 4;
  }

  function startDemo() {
    demoMode = true;
    const now = Math.floor(Date.now()/1000);
    assignState({
      ok:true,now,max_fighters:4,rewards:[250,150,100],
      battle:{boss_id:'demo',status:'active',hp:32480,max_hp:50000,phase:2,ends_at:now+7620,next_action_at:now+27,shield_hits:2,heal_block_until:0,skip_next_action:0},
      self:{user_id:1,name:'Илья',role_key:'honest_hero',role_title:'Честный Главный герой',role_emoji:'👑',hp:98,max_hp:140,damage:12450,attacks:24,critical_hits:5,healing_done:90,damage_taken:42,protected:false,knocked_out_until:0,is_self:true,ability_name:'Кульминация',ability_hint:'Гарантированный сокрушительный критический удар',cooldowns:{attack:0,ability:0,heal:0,defend:0}},
      fighters:[
        {user_id:1,name:'Илья',role_key:'honest_hero',role_title:'Главный герой',role_emoji:'👑',hp:98,max_hp:140,damage:12450,attacks:24,critical_hits:5,healing_done:90,damage_taken:42,protected:false,knocked_out_until:0,is_self:true},
        {user_id:2,name:'Маша',role_key:'extras',role_title:'Массовка',role_emoji:'👥',hp:101,max_hp:115,damage:8200,attacks:18,critical_hits:3,healing_done:120,damage_taken:55,protected:false,knocked_out_until:0,is_self:false},
        {user_id:3,name:'Саня',role_key:'secondary',role_title:'Второстепенная роль',role_emoji:'🎭',hp:125,max_hp:125,damage:7700,attacks:17,critical_hits:2,healing_done:35,damage_taken:60,protected:false,knocked_out_until:0,is_self:false},
        {user_id:4,name:'Влад',role_key:'dust',role_title:'Пыль',role_emoji:'🌫',hp:86,max_hp:110,damage:6100,attacks:15,critical_hits:1,healing_done:40,damage_taken:72,protected:true,knocked_out_until:0,is_self:false}
      ],
      logs:['💢 Илья задел его эго: −540 HP.','❤️‍🩹 Маша восстановила 44 HP.','🛡 Влад приготовился отразить следующую атаку.']
    });
    notify('Демонстрационный режим: все кнопки можно нажимать.');
  }

  function modalShop() {
    return `<div class="modal-hero"><span class="modal-main-icon">${icon('shop')}</span><small class="modal-kicker">ЦЕНТР ВСЕЛЕННОЙ</small><h2 class="modal-title">МАГАЗИН</h2><p class="modal-subtitle">В РАЗРАБОТКЕ</p><div class="modal-rule"><i></i><b>СКОРО</b><i></i></div></div>`;
  }

  function modalInventory() {
    return `<div class="modal-hero"><span class="modal-main-icon">${icon('bag')}</span><small class="modal-kicker">СНАРЯЖЕНИЕ ГЕРОЯ</small><h2 class="modal-title">ИНВЕНТАРЬ</h2><p class="modal-subtitle">В РАЗРАБОТКЕ</p><div class="modal-rule"><i></i><b>СКОРО</b><i></i></div></div>`;
  }

  function modalHeroes() {
    const fighters = state?.fighters || [];
    const rows = fighters.length ? fighters.map(f => `<div class="modal-row"><span class="modal-rank">${escapeHtml(f.role_emoji || '◆')}</span><span class="modal-row-copy"><b>${escapeHtml(f.name)}${f.is_self?' · ВЫ':''}</b><small>${escapeHtml(f.role_title)} · HP ${fmt(f.hp)}/${fmt(f.max_hp)}</small></span><strong>${fmt(f.damage)}</strong></div>`).join('') : '<div class="modal-empty">В отряде пока никого нет.</div>';
    return `<h2 class="modal-list-title">ГЕРОИ ОТРЯДА</h2><div class="modal-list">${rows}</div>`;
  }

  function modalRating() {
    const sorted = [...(state?.fighters || [])].sort((a,b)=>b.damage-a.damage);
    const rewards = state?.rewards || [250,150,100];
    const medals = ['🥇','🥈','🥉'];
    const rows = sorted.length ? sorted.map((f,index) => `<div class="modal-row"><span class="modal-rank">${medals[index] || index+1}</span><span class="modal-row-copy"><b>${escapeHtml(f.name)}${f.is_self?' · ВЫ':''}</b><small>${escapeHtml(f.role_title)} · ${fmt(f.attacks)} атак</small></span><strong>${fmt(f.damage)}${index<3?`<small> +${fmt(rewards[index])}</small>`:''}</strong></div>`).join('') : '<div class="modal-empty">Рейтинг появится после первого удара.</div>';
    return `<h2 class="modal-list-title">РЕЙТИНГ УРОНА</h2><div class="modal-list">${rows}</div>`;
  }

  function openModal(type) {
    const content = $('modalContent');
    content.dataset.type = type;
    content.innerHTML = type === 'heroes' ? modalHeroes() : type === 'rating' ? modalRating() : type === 'inventory' ? modalInventory() : modalShop();
    $('modal').classList.add('open');
    $('modal').setAttribute('aria-hidden','false');
    document.body.style.overflow = 'hidden';
    tg?.BackButton?.show?.();
    tg?.HapticFeedback?.impactOccurred?.('light');
  }

  function refreshOpenModal() {
    const type = $('modalContent').dataset.type;
    if (type === 'heroes') $('modalContent').innerHTML = modalHeroes();
    if (type === 'rating') $('modalContent').innerHTML = modalRating();
  }

  function closeModal() {
    $('modal').classList.remove('open');
    $('modal').setAttribute('aria-hidden','true');
    document.body.style.overflow = '';
    tg?.BackButton?.hide?.();
  }

  function showError(show, message='') {
    $('errorScreen').hidden = !show;
    if (show) $('errorText').textContent = message;
  }

  document.querySelectorAll('[data-action]').forEach(button => {
    button.addEventListener('click', () => performAction(button.dataset.action, button));
  });
  document.querySelectorAll('[data-modal]').forEach(button => {
    button.addEventListener('click', () => openModal(button.dataset.modal));
  });
  document.querySelectorAll('[data-scroll]').forEach(button => {
    button.addEventListener('click', () => {
      document.querySelectorAll('.bottom-nav button').forEach(item=>item.classList.remove('active'));
      button.classList.add('active');
      $(button.dataset.scroll)?.scrollIntoView({behavior:'smooth',block:'start'});
    });
  });
  $('closeModal').addEventListener('click', closeModal);
  $('modal').addEventListener('click', event => { if (event.target === $('modal')) closeModal(); });
  $('retryButton').addEventListener('click', start);
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  document.addEventListener('keydown', event => { if (event.key === 'Escape') closeModal(); });
  tg?.BackButton?.onClick?.(closeModal);
  setInterval(tick, 200);
  start();
})();
