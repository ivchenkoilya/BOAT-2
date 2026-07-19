(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#090713');tg?.setBackgroundColor?.('#090713');
  const initData=tg?.initData||'';
  const params=new URLSearchParams(location.search);
  let selectedChat=Number(params.get('chat_id')||localStorage.getItem('admin76Chat')||0);
  let selectedUser=Number(params.get('user_id')||localStorage.getItem('admin76User')||0);
  let state=null,activeTab='home',toastTimer=null,formConfirm=null,searchTimer=null,firstLoad=true;
  const $=id=>document.getElementById(id);
  const fmt=v=>new Intl.NumberFormat('ru-RU').format(Number(v)||0);
  const esc=v=>String(v??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const headers={'X-Telegram-Init-Data':initData,'Content-Type':'application/json'};
  const STATUS_NAMES={active:'идёт бой',resolving:'подсчёт наград',victory:'победа',cancelled:'отменён',defeat:'поражение',expired:'время истекло'};
  const RUN_STATUS={active:'активна',resolving:'сохраняется',finished:'завершена',expired:'истекла',voided:'аннулирована'};
  const GAME_NAMES={rooftop:'🌃 Бег по крышам',heist:'🏛 Ограбление хранилища'};
  const ACTION_NAMES={
    points_delta:'Изменение влияния',points_set:'Точное влияние',mute:'Мут участника',unmute:'Снятие мута',cooldown_user_chat:'Сброс личных КД',cooldown_user_global:'Сброс глобальных КД',stats_user_reset:'Сброс статистики участника',tree_delta:'Изменение очков древа',tree_set:'Точные очки древа',tree_refund:'Возврат очков древа',knowledge_week_reset:'Сброс недельного прогресса',knowledge_recalculate:'Пересчёт профиля',chat_cooldowns_reset:'Сброс КД беседы',chat_stats_reset:'Сброс статистики беседы',chat_profiles_recalculate:'Пересчёт профилей',database_check:'Проверка базы',boss_start:'Запуск рейда',boss_hp_delta:'Изменение HP босса',boss_hp_set:'Точное HP босса',boss_pressure_reset:'Сброс давления',boss_pressure_fill:'Заполнение давления',boss_cooldowns_reset:'Сброс КД рейда',boss_phase_set:'Смена фазы',boss_attack_set:'Выбор атаки',boss_attack_now:'Атака босса',boss_refresh_post:'Обновление поста',boss_recover:'Восстановление рейда',boss_victory:'Победа в рейде',boss_cancel:'Отмена рейда',game_attempts_reset:'Сброс игровых попыток',game_attempts_reset_chat:'Сброс попыток беседы',game_sessions_close:'Закрытие игровых сессий',game_clear_stuck_chat:'Закрытие зависших игр',game_run_void:'Аннулирование результата',undo:'Отмена изменения'
  };

  function toast(text,type=''){
    const node=$('toast');node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className='toast',3200);
  }
  function loading(show){$('loading').classList.toggle('hidden',!show)}
  async function request(url,options={}){
    const response=await fetch(url,{cache:'no-store',...options,headers:{...headers,...(options.headers||{})}});
    const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Действие не выполнено.');
    return data;
  }
  async function loadState(silent=false){
    if(firstLoad&&!silent)loading(true);
    $('connectionState').textContent='● Обновление…';$('connectionState').style.color='';
    const requestedUser=selectedUser;
    try{
      state=await request(`/admin-v76/api/state?chat_id=${selectedChat||0}&user_id=${requestedUser||0}`);
      selectedChat=Number(state.selected_chat?.chat_id)||0;
      if(state.target){
        selectedUser=Number(state.target.user_id)||0;
        localStorage.setItem('admin76User',String(selectedUser));
      }else if(requestedUser&&state.target_error){
        selectedUser=0;localStorage.removeItem('admin76User');
        toast(state.target_error,'error');
      }
      localStorage.setItem('admin76Chat',String(selectedChat));
      render();
      $('connectionState').textContent='● Подключено';$('connectionState').style.color='#68e2ab';
    }catch(e){
      $('connectionState').textContent='● Ошибка соединения';$('connectionState').style.color='#ff7187';toast(e.message,'error');
    }finally{
      firstLoad=false;loading(false);
    }
  }
  async function act(action,extra={},api='legacy'){
    if(!selectedUser&&requiresUser(action)){toast('Сначала выбери участника.','error');switchTab('participant');return}
    try{
      tg?.HapticFeedback?.impactOccurred?.('light');
      const endpoint=api==='games'?'/admin-v76/api/action':'/admin-app/api/action';
      const result=await request(endpoint,{method:'POST',body:JSON.stringify({action,chat_id:selectedChat,user_id:selectedUser,...extra})});
      toast(result.message||'Готово','success');tg?.HapticFeedback?.notificationOccurred?.('success');await loadState(true);
    }catch(e){toast(e.message,'error');tg?.HapticFeedback?.notificationOccurred?.('error')}
  }
  function requiresUser(action){
    return /^(points_|mute$|unmute$|cooldown_user|stats_user|tree_|knowledge_|game_attempts_reset$|game_sessions_close$|game_run_void$)/.test(action);
  }
  function metric(icon,label,value,note='',cls=''){
    return `<article class="metric ${cls}"><span>${icon}</span><small>${esc(label)}</small><b>${esc(value)}</b>${note?`<em>${esc(note)}</em>`:''}</article>`;
  }
  function render(){
    $('versionText').textContent=state.version||'Reality 76';
    $('chatSelect').innerHTML=(state.chats||[]).map(c=>`<option value="${c.chat_id}" ${Number(c.chat_id)===selectedChat?'selected':''}>${esc(c.title)} · ${c.users}</option>`).join('')||'<option value="0">Нет бесед</option>';
    const t=state.target;
    $('targetAvatar').textContent=t?.role?.emoji||'?';
    $('targetName').textContent=t?.full_name||'Не выбран';
    $('targetMeta').textContent=t?`${t.role.emoji} ${t.role.title} · ${fmt(t.points)} влияния`:'Нажми, чтобы выбрать участника';
    $('pointsSubtitle').textContent=`Текущий баланс: ${fmt(t?.points||0)}`;
    document.querySelectorAll('.requires-user').forEach(x=>x.classList.toggle('disabled',!t));
    renderHome();renderUsers(state.quick_users||[],'quickUsers');
    if(!$('userSearch').value.trim())renderUsers(state.quick_users||[],'searchResults');
    renderParticipant();renderGames();renderKnowledge();renderRaid();renderHistory();
  }
  function renderHome(){
    const boss=state.boss,health=state.health||{},games=state.games?.chat||{};
    const users=state.chats?.find(c=>Number(c.chat_id)===selectedChat)?.users||0;
    $('homeMetrics').innerHTML=[
      metric('🤖','Версия бота',state.bot_version||'—','админ-центр Reality 76'),
      metric('👥','Участников',fmt(users),'в выбранной беседе'),
      metric('🌌','Рейд',boss?(STATUS_NAMES[String(boss.status)]||boss.status):'не запускался',boss?`${fmt(boss.hp)} / ${fmt(boss.max_hp)} HP`:'можно запустить'),
      metric('🩺','База данных',health.status||'—',health.status==='ok'?'ошибок не найдено':'нужна проверка',health.status==='ok'?'good':'danger'),
      metric('🎮','Игры сегодня',fmt(games.finished_today||0),`${fmt(games.paid_today||0)} влияния выдано`,Number(games.stuck||0)>0?'danger':''),
      metric('⭐','Влияние сегодня',fmt(health.influence_today||0),'все положительные начисления')
    ].join('');
    const stuck=Number(games.stuck||0),resolving=Number(games.resolving||0);
    $('systemAlert').classList.toggle('hidden',!(stuck||resolving));
    $('systemAlertText').textContent=stuck?`Зависших игровых сессий: ${stuck}.`:`Сессий в сохранении: ${resolving}.`;
  }
  function userMarkup(u){
    const selected=Number(u.user_id)===selectedUser;
    return `<button class="user-item ${selected?'selected':''}" data-user-id="${u.user_id}"><span class="user-avatar">${u.role?.emoji||'👤'}</span><span><b>${esc(u.full_name)}</b><small>${u.username?'@'+esc(u.username):'ID '+u.user_id} · ${esc(u.role?.title||'')} · ${fmt(u.message_count)} сообщ.</small></span><strong>${fmt(u.points)}</strong></button>`;
  }
  function renderUsers(users,id){$(id).innerHTML=users.length?users.map(userMarkup).join(''):'<div class="empty">Участники не найдены.</div>'}
  async function searchUsers(){
    const q=$('userSearch').value.trim();
    try{const data=await request(`/admin-v76/api/users?chat_id=${selectedChat}&q=${encodeURIComponent(q)}`);renderUsers(data.users||[],'searchResults')}
    catch(e){toast(e.message,'error')}
  }
  async function selectUser(id){
    selectedUser=Number(id)||0;localStorage.setItem('admin76User',String(selectedUser));
    await loadState(true);switchTab('participant');
    if(Number(state?.target?.user_id)===selectedUser){toast(`Выбран: ${state.target.full_name}`,'success');setTimeout(()=>$('participantProfile')?.scrollIntoView({behavior:'smooth',block:'start'}),80)}
  }
  function renderParticipant(){
    const t=state.target,b=state.behavior||{},g=state.games?.games||{};
    const gamePaid=Object.values(g).reduce((sum,x)=>sum+Number(x.total_paid||0),0);
    $('participantMetrics').innerHTML=t?[
      metric(t.role.emoji,'Роль',t.role.title,`порог от ${fmt(t.role.floor)}`),
      metric('⭐','Влияние',fmt(t.points),t.username?'@'+t.username:`ID ${t.user_id}`),
      metric('💬','Сообщений',fmt(t.message_count),`активность: ${fmt(b.activity_score||b.score||0)}`),
      metric('🎮','Игровая добыча',fmt(gamePaid),'выдано сегодня')
    ].join(''):'<div class="empty" style="grid-column:1/-1">Выбери участника выше, чтобы открыть статистику и действия.</div>';
    const r=state.role_thresholds||{decoration:0,dust:1000,extras:3000,secondary:6000,hero:10000};
    const roles=[['decoration','🪑','Декорация'],['dust','🌫','Пыль'],['extras','👥','Массовка'],['secondary','🎭','Второстепенная'],['hero','👑','Главный герой']];
    $('roleGrid').innerHTML=roles.map(([key,emoji,title])=>`<button class="${key==='hero'?'role-hero ':''}${t?.role?.key===key?'active':''}" data-role-points="${r[key]||0}">${emoji}<span>${title}<small>от ${fmt(r[key]||0)}</small></span></button>`).join('');
  }
  function renderGames(){
    const gs=state.games||{},chat=gs.chat||{};
    $('gameSystemMetrics').innerHTML=gs.available?[
      metric('▶️','Активных',fmt(chat.active||0),`${fmt(chat.resolving||0)} сохраняются`,Number(chat.stuck||0)>0?'danger':''),
      metric('✅','Завершено сегодня',fmt(chat.finished_today||0),`${fmt(chat.runs_today||0)} запусков всего`),
      metric('⭐','Выдано сегодня',fmt(chat.paid_today||0),'влияния через игры'),
      metric('⚠️','Проблемные',fmt((chat.stuck||0)+(chat.expired_today||0)),`${fmt(chat.stuck||0)} зависших · ${fmt(chat.voided_today||0)} аннулировано`,Number(chat.stuck||0)>0?'danger':'')
    ].join(''):`<div class="empty" style="grid-column:1/-1">${esc(gs.reason||'Игровой центр недоступен.')}</div>`;
    const games=gs.games||{};
    $('gameCards').innerHTML=Object.values(games).map(g=>`<article class="game-card"><div class="game-head"><div><h3>${esc(g.emoji)} ${esc(g.title)}</h3><p>${Number(g.duration)||0} секунд · максимум ${fmt(g.max_reward)} влияния</p></div><div class="game-emoji">${esc(g.emoji)}</div></div><div class="game-stats"><div class="game-stat"><small>Попытки</small><b>${g.attempts_left}/${gs.attempts_per_day}</b></div><div class="game-stat"><small>Лучший счёт</small><b>${fmt(g.best_score)}</b></div><div class="game-stat"><small>Выдано</small><b>${fmt(g.total_paid)}</b></div></div><div class="game-actions"><button class="game-action" data-action="game_attempts_reset" data-api="games" data-game="${esc(g.key)}">🔄 Сбросить попытки</button><button class="game-action" data-action="game_sessions_close" data-api="games" data-game="${esc(g.key)}">⏹ Закрыть сессию</button></div></article>`).join('')||'<div class="empty">Выбери участника, чтобы увидеть его игры.</div>';
    const runs=gs.runs||[];
    $('gameRuns').innerHTML=runs.length?runs.map(run=>{
      const status=RUN_STATUS[run.status]||run.status;
      const canVoid=run.status==='finished'&&Number(run.actual_reward)>0;
      const meta=Object.entries(run.meta||{}).slice(0,4).map(([k,v])=>`<span>${esc(k)}: ${esc(v)}</span>`).join('');
      return `<article class="run-item"><header><h4>${esc(GAME_NAMES[run.game_key]||run.game_key)}</h4><time>${new Date(run.started_at*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</time></header><div class="run-meta"><span class="run-status ${esc(run.status)}">${esc(status)}</span><span>счёт ${fmt(run.score)}</span><span>награда ${fmt(run.actual_reward)}</span>${meta}</div>${canVoid?`<button class="run-action" data-confirm-action="game_run_void" data-api="games" data-session-id="${esc(run.session_id)}" data-confirm-title="Аннулировать этот результат?" data-confirm-text="Выданное за этот забег влияние (${fmt(run.actual_reward)}) будет списано с участника.">🚫 Аннулировать результат</button>`:''}</article>`;
    }).join(''):'<div class="empty">У выбранного участника ещё нет игровых забегов.</div>';
    $('openGamesButton').disabled=!gs.player_url;
  }
  function renderKnowledge(){
    const k=state.knowledge||{shards:0,weekly_tree_points:0,weekly_cap:12,profile:{total:0,spent:0,available:0},levels:[],buffs:{}};
    $('knowledgeMetrics').innerHTML=[
      metric('🌳','Всего очков',fmt(k.profile.total),`доступно ${fmt(k.profile.available)}`),
      metric('✨','Потрачено',fmt(k.profile.spent),`${k.levels.length} активных талантов`),
      metric('📅','За неделю',`${fmt(k.weekly_tree_points)} / ${fmt(k.weekly_cap)}`,'рейдовые очки'),
      metric('💠','Осколки знаний',fmt(k.shards),'наследие старой системы')
    ].join('');
    $('talentList').innerHTML=k.levels.length?k.levels.map(x=>`<div class="talent-item"><span><b>${esc(x.name)}</b><small>${branchName(x.branch)}</small></span><strong>${x.level}/${x.max}</strong></div>`).join(''):'<div class="empty">Участник ещё не прокачивал таланты.</div>';
    const labels={boss_damage:'Урон по боссу',boss_crit_chance:'Шанс крита',boss_crit_power:'Сила крита',first_hit_x3:'Первый удар ×3',influence:'Бонус влияния',activity:'Награды активности',tasks:'Награды заданий',daily_double:'Ежедневное удвоение',penalty_reduction:'Снижение штрафов',avoid_penalty:'Шанс избежать штрафа',sabotage_reduction:'Защита от саботажа',weekly_armor:'Недельная броня',game_reward:'Награды игр',rare_reward:'Редкая награда',second_chance:'Второй шанс',daily_reroll:'Ежедневный реролл'};
    const buffs=Object.entries(k.buffs||{}).filter(([,v])=>Number(v)>0);
    $('buffList').innerHTML=buffs.length?buffs.map(([key,val])=>`<div class="buff-item"><span>${esc(labels[key]||key)}</span><strong>${formatBuff(key,val)}</strong></div>`).join(''):'<div class="empty">Активных баффов пока нет.</div>';
  }
  function branchName(v){return ({damage:'⚔ Урон',influence:'⭐ Влияние',defense:'🛡 Защита',rewards:'🍀 Удача'}[v]||esc(v))}
  function formatBuff(key,val){const n=Number(val);if(['first_hit_x3','daily_double','weekly_armor','daily_reroll'].includes(key))return n>0?'активно':'—';return n<=1?`${Math.round(n*100)}%`:esc(val)}
  function renderRaid(){
    const b=state.boss;
    if(!b){$('raidContent').innerHTML=`<article class="boss-card"><div class="boss-sigil">🌌</div><h3>Центр Вселенной не вызван</h3><p>Запусти новый рейд для выбранной беседы.</p><button class="wide-button" data-action="boss_start">🌌 Запустить босса</button></article>`;return}
    const status=STATUS_NAMES[String(b.status)]||String(b.status),canStart=!['active','resolving'].includes(String(b.status));
    const hp=Math.max(0,Math.min(100,b.hp/Math.max(1,b.max_hp)*100)),pressure=Math.max(0,Math.min(100,b.pressure/Math.max(1,b.pressure_max)*100));
    $('raidContent').innerHTML=`<article class="boss-card"><div class="boss-sigil">👁</div><h3>ЦЕНТР ВСЕЛЕННОЙ</h3><p>${esc(status)} · фаза ${b.phase}/4 · ${b.fighters} участников</p><div class="hp-track"><i style="width:${hp}%"></i></div><div class="boss-numbers"><b>${fmt(b.hp)} HP</b><span>${fmt(b.max_hp)} HP</span></div><div class="pressure-track"><i style="width:${pressure}%"></i></div><div class="boss-numbers"><b>⚡ ${fmt(b.pressure)}/${fmt(b.pressure_max)}</b><span>${Math.round(pressure)}%</span></div><div class="boss-detail-grid"><div class="boss-detail"><small>Следующая атака</small><b>${esc(b.planned_action_icon)} ${esc(b.planned_action_name)}</b></div><div class="boss-detail"><small>В строю</small><b>${b.alive}/${b.fighters}</b></div></div>${b.player_url?`<button class="wide-button" data-open-url="${esc(b.player_url)}">🎮 Открыть как игрок</button>`:''}${canStart?'<button class="wide-button positive" data-action="boss_start">🌌 Запустить новый рейд</button>':''}</article>
    <article class="panel"><div class="panel-title"><span>❤️</span><div><b>Здоровье босса</b><small>Быстрые и точные изменения</small></div></div><div class="step-grid"><button data-action="boss_hp_delta" data-value="-5000">−5000</button><button data-action="boss_hp_delta" data-value="-1000">−1000</button><button data-action="boss_hp_delta" data-value="1000">+1000</button><button data-action="boss_hp_delta" data-value="5000">+5000</button></div><button class="wide-button" data-form="bossHp">✍️ Установить точное HP</button><div class="subheading">ПРИНУДИТЕЛЬНАЯ ФАЗА</div><div class="action-grid two"><button data-phase="1">I · Раскол</button><button data-phase="2">II · Тревога</button><button data-phase="3">III · Ярость</button><button data-phase="4">IV · Натиск</button></div></article>
    <article class="panel"><div class="panel-title"><span>⚡</span><div><b>Давление и кулдауны</b><small>Инструменты тестирования боя</small></div></div><div class="action-grid two"><button data-action="boss_pressure_reset">Сбросить давление</button><button data-action="boss_pressure_fill">Заполнить давление</button><button class="full" data-action="boss_cooldowns_reset">⏱ Сбросить КД участников</button></div></article>
    <article class="panel"><div class="panel-title"><span>🗯</span><div><b>Следующая атака</b><small>Назначь и запусти вручную</small></div></div><div class="attack-select"><select id="attackSelect"><option value="shield">🪞 Все мне завидуют</option><option value="silence">🗯 Тебя никто не слушает</option><option value="single">🌌 Сокрушить самооценку</option><option value="mass">👥 Вы всего лишь массовка</option></select><button class="raid-button" id="setAttackButton">Назначить</button></div><button class="wide-button" data-action="boss_attack_now">💥 Атаковать сейчас</button></article>
    <article class="panel"><div class="panel-title"><span>🛠</span><div><b>Обслуживание рейда</b><small>Сообщение, восстановление и завершение</small></div></div><div class="action-grid two"><button data-action="boss_refresh_post">🔄 Обновить пост</button><button data-action="boss_recover">🧯 Восстановить зависший</button><button class="danger-soft" data-confirm-action="boss_cancel" data-confirm-title="Отменить рейд?" data-confirm-text="Бой завершится без наград.">🛑 Отменить</button><button class="danger-soft" data-confirm-action="boss_victory" data-confirm-title="Завершить победой?" data-confirm-text="Босс получит 0 HP, участникам будут выданы реальные награды.">🏆 Победа и награды</button></div></article>
    <article class="panel"><div class="panel-title"><span>📜</span><div><b>Последние события</b><small>Журнал текущего боя</small></div></div><div class="log-list">${(b.logs||[]).map(x=>`<div class="log-entry">${esc(x)}</div>`).join('')||'<div class="empty">Событий пока нет.</div>'}</div></article>`;
  }
  function renderHistory(){
    const items=state.history||[];
    $('historyList').innerHTML=items.length?items.map(x=>`<article class="history-item ${x.undone?'undone':''}"><header><b>${esc(ACTION_NAMES[x.action]||x.action)}</b><time>${new Date(x.created_at*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})}</time></header><p>${esc(x.detail)}</p><footer><span>чат ${x.chat_id||'—'}</span><span>цель ${x.target_user_id||'—'}</span>${x.reversible&&!x.undone?'<span>можно отменить</span>':''}${x.undone?'<span>отменено</span>':''}</footer></article>`).join(''):'<div class="empty">История действий пока пуста.</div>';
  }
  function switchTab(tab){activeTab=tab;document.querySelectorAll('[data-screen]').forEach(x=>x.classList.toggle('active',x.dataset.screen===tab));document.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('active',x.dataset.tab===tab));window.scrollTo({top:0,behavior:'smooth'})}
  function closeModal(){$('modal').classList.remove('open');$('modal').setAttribute('aria-hidden','true');formConfirm=null}
  function openModal({icon='⚙',title,text='',field='',confirm='Подтвердить',onConfirm}){$('modalIcon').textContent=icon;$('modalTitle').textContent=title;$('modalText').textContent=text;$('modalField').innerHTML=field;$('modalConfirm').textContent=confirm;formConfirm=onConfirm;$('modal').classList.add('open');$('modal').setAttribute('aria-hidden','false');setTimeout(()=>$('modalField').querySelector('input,select')?.focus(),100)}
  function openNumberForm(kind){
    const map={points:['⭐','Установить влияние','Новое точное количество влияния',state.target?.points||0,'points_set'],tree:['🌳','Установить очки древа','Общее количество очков древа',state.knowledge?.profile?.total||0,'tree_set'],bossHp:['❤️','Установить HP босса','Значение от 0 до максимального HP',state.boss?.hp||0,'boss_hp_set']};
    const config=map[kind];if(!config)return;const [icon,title,text,current,action]=config;
    openModal({icon,title,text,field:`<input id="modalNumber" type="number" value="${current}">`,onConfirm:()=>{const value=Number($('modalNumber').value);closeModal();act(action,{value})}})
  }
  function datasetExtra(button){
    const extra={};if(button.dataset.value!==undefined)extra.value=Number(button.dataset.value||0);if(button.dataset.game)extra.game=button.dataset.game;if(button.dataset.sessionId)extra.session_id=button.dataset.sessionId;return extra;
  }
  function confirmAction(button){
    const api=button.dataset.api||'legacy',extra=datasetExtra(button);
    openModal({icon:'⚠️',title:button.dataset.confirmTitle||'Подтвердить действие',text:button.dataset.confirmText||'Это действие изменит данные.',confirm:'Да, выполнить',onConfirm:()=>{closeModal();act(button.dataset.confirmAction,extra,api)}})
  }
  function openUrl(url){if(!url)return;if(tg&&typeof tg.openLink==='function')tg.openLink(url,{try_instant_view:false});else window.open(url,'_blank')}

  document.addEventListener('click',e=>{
    const tab=e.target.closest('[data-tab],[data-tab-open]');if(tab){switchTab(tab.dataset.tab||tab.dataset.tabOpen);return}
    const user=e.target.closest('[data-user-id]');if(user){selectUser(user.dataset.userId);return}
    const role=e.target.closest('[data-role-points]');if(role){act('points_set',{value:Number(role.dataset.rolePoints)});return}
    const mute=e.target.closest('[data-mute]');if(mute){act('mute',{minutes:Number(mute.dataset.mute)});return}
    const phase=e.target.closest('[data-phase]');if(phase){act('boss_phase_set',{phase:Number(phase.dataset.phase)});return}
    const form=e.target.closest('[data-form]');if(form){openNumberForm(form.dataset.form);return}
    const confirm=e.target.closest('[data-confirm-action]');if(confirm){confirmAction(confirm);return}
    const action=e.target.closest('[data-action]');if(action){act(action.dataset.action,datasetExtra(action),action.dataset.api||'legacy');return}
    const open=e.target.closest('[data-open-url]');if(open){openUrl(open.dataset.openUrl);return}
    if(e.target.closest('[data-modal-close]'))closeModal();
    if(e.target.id==='setAttackButton'){act('boss_attack_set',{attack:$('attackSelect').value});return}
  });
  $('modalConfirm').addEventListener('click',()=>formConfirm?.());$('modal').addEventListener('click',e=>{if(e.target===$('modal'))closeModal()});
  $('selectSelfButton').addEventListener('click',()=>selectUser(Number(state?.admin?.user_id)||0));
  $('chatSelect').addEventListener('change',()=>{selectedChat=Number($('chatSelect').value);selectedUser=0;localStorage.removeItem('admin76User');loadState()});
  $('refreshButton').addEventListener('click',()=>loadState());$('searchButton').addEventListener('click',searchUsers);$('userSearch').addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(searchUsers,260)});
  $('openGamesButton').addEventListener('click',()=>openUrl(state?.games?.player_url));
  window.addEventListener('online',()=>loadState(true));window.addEventListener('offline',()=>toast('Нет соединения с интернетом.','error'));document.addEventListener('visibilitychange',()=>{if(!document.hidden)loadState(true)});
  tg?.BackButton?.onClick?.(()=>{if($('modal').classList.contains('open'))closeModal();else if(activeTab!=='home')switchTab('home');else tg.close()});
  loadState();
})();
