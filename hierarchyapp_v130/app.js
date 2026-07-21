(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#09070d');tg?.setBackgroundColor?.('#09070d');
  const $=id=>document.getElementById(id);
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('hierarchy_')?start.slice(10):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  let state=null,currentMetric='power_score',toastTimer=null;

  function toast(text){const node=$('toast');node.textContent=text;node.className='toast show';clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.className='toast',3200)}
  function initials(name){return String(name||'?').trim().split(/\s+/).slice(0,2).map(x=>x[0]||'').join('').toUpperCase()||'?'}
  function rankDelta(value){const n=Number(value)||0;if(!n)return '<small>без изменений</small>';return `<small class="${n>0?'up':'down'}">${n>0?'▲':'▼'} ${Math.abs(n)} за неделю</small>`}
  function officeText(person){return person.offices?.length?person.offices.map(x=>`${x.emoji} ${x.title}`).join(' · '):'Государственной должности нет'}
  function metricValue(person,key){return Number(person?.[key])||0}
  function metricLabel(key){return ({power_score:'могущества',career_points:'карьеры',points:'влияния',talent_spent:'очков талантов',government_score:'власти',activity_score:'активности',game_profit:'игровой прибыли'})[key]||key}

  async function load(){
    try{
      const response=await fetch(`/hierarchy-v130/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить иерархию.');
      state=data;render();$('loading').classList.add('hidden');
    }catch(error){$('loading').classList.add('hidden');toast(error.message||'Не удалось загрузить иерархию.')}
  }

  function renderSummary(){
    $('chatTitle').textContent=state.chat?.title||String(state.chat?.chat_id||'');
    const s=state.summary||{};
    $('summary').innerHTML=`<div class="metric"><small>УЧАСТНИКОВ</small><b>${fmt(s.total)}</b></div><div class="metric"><small>АКТИВНЫХ</small><b>${fmt(s.active)}</b></div><div class="metric"><small>ОБЩЕЕ ВЛИЯНИЕ</small><b>${fmt(s.total_points)}</b></div><div class="metric"><small>ДЕПУТАТОВ</small><b>${fmt(s.deputy_seats)}</b></div>`;
    $('activeBadge').textContent=`${fmt(s.active)} активных из ${fmt(s.total)}`;
  }

  function podiumCard(person,index){
    if(!person)return '<div></div>';
    const classes=['first','second','third'];const medals=['🥇','🥈','🥉'];
    return `<button type="button" class="podium-card ${classes[index]}" data-profile="${person.user_id}"><span class="medal">${medals[index]}</span><span class="avatar">${esc(initials(person.name))}</span><b>${esc(person.name)}</b><small>${person.role_emoji} ${esc(person.role_title)}</small><small>${esc(person.type_title||'Типаж не определён')}</small><div class="power">${fmt(person.power_score)}</div></button>`;
  }

  function rankRow(person,index,key='power_score'){
    const value=metricValue(person,key);
    return `<button type="button" class="rank-row" data-profile="${person.user_id}"><span class="rank-number">${index+1}</span><span class="avatar">${esc(initials(person.name))}</span><span class="rank-main"><b>${esc(person.name)}</b><small>${person.role_emoji} ${esc(person.role_title)} · ${esc(officeText(person))}</small></span><span class="rank-value"><b>${fmt(value)}</b>${key==='power_score'?rankDelta(person.rank_change):`<small>${esc(metricLabel(key))}</small>`}</span></button>`;
  }

  function renderTop(){
    const people=state.participants||[];
    $('podium').innerHTML=podiumCard(people[1],1)+podiumCard(people[0],0)+podiumCard(people[2],2);
    $('topList').innerHTML=people.length?people.map((p,i)=>rankRow(p,i)).join(''):'<div class="empty">Участников пока нет.</div>';
  }

  function personCard(person){
    return `<button type="button" class="person-card ${person.active?'':'inactive'}" data-profile="${person.user_id}"><span class="avatar">${esc(initials(person.name))}</span><span class="person-main"><b>${esc(person.name)}</b><small>${person.role_emoji} ${esc(person.role_title)} · ${esc(person.type_title||'без типажа')}</small><span class="person-meta"><span class="chip ${person.active?'active':''}">${person.active?'● активен':'○ неактивен'}</span><span class="chip">№${person.rank}</span><span class="chip">🌳 ${fmt(person.talent_spent)}</span>${person.offices?.length?'<span class="chip">🏛 власть</span>':''}</span></span></button>`;
  }

  function renderPeople(){
    const query=String($('peopleSearch').value||'').trim().toLocaleLowerCase('ru');
    const people=(state.participants||[]).filter(person=>!query||[person.name,person.username,person.role_title,person.type_title,officeText(person)].join(' ').toLocaleLowerCase('ru').includes(query));
    $('peopleGrid').innerHTML=people.length?people.map(personCard).join(''):'<div class="empty">Никого не найдено.</div>';
  }

  function renderRatings(){
    const people=[...(state.participants||[])].sort((a,b)=>metricValue(b,currentMetric)-metricValue(a,currentMetric)||a.rank-b.rank);
    $('ratingList').innerHTML=people.map((p,i)=>rankRow(p,i,currentMetric)).join('');
  }

  function renderGovernment(){
    const s=state.summary||{};
    $('governmentNote').innerHTML=`Для <b>${fmt(s.active)} активных участников</b> система рекомендует <b>${fmt(s.deputy_seats)} депутатов</b>. Председатель остаётся одним из депутатов, а один человек может совмещать выборную и назначаемую должность.`;
    const rows=state.government||[];
    $('governmentList').innerHTML=rows.length?rows.map(item=>`<button type="button" class="office-row" data-profile="${item.user_id}"><span class="office-icon">${item.emoji}</span><span><b>${esc(item.title)}</b><small>${esc(item.name)} · доверие ${fmt(item.trust)}% · ${esc(item.remaining)}</small></span></button>`).join(''):'<div class="empty">Правительство ещё не сформировано.</div>';
  }

  function talentBars(person){
    const branches=person.talent_branches||{};const max=Math.max(1,...Object.values(branches).map(Number));
    const labels={damage:'⚔️ Урон',influence:'👑 Влияние',defense:'🛡 Защита',rewards:'🎁 Награды'};
    return Object.entries(labels).map(([key,label])=>`<div class="talent-line"><span>${label}</span><span class="track"><i style="width:${Math.min(100,(Number(branches[key])||0)/max*100)}%"></i></span><b>${fmt(branches[key])}</b></div>`).join('');
  }

  function profileMarkup(person){
    if(!person)return '<div class="empty">Профиль не найден.</div>';
    return `<article class="profile-card"><div class="profile-head"><span class="avatar">${esc(initials(person.name))}</span><div><h3>${esc(person.name)}</h3><p>№${person.rank} в беседе · ${person.active?'активный участник':'сейчас неактивен'}</p><p>${person.role_emoji} ${esc(person.role_title)} · ${esc(person.type_emoji||'🎭')} ${esc(person.type_title||'Типаж не определён')}</p></div></div><div class="profile-grid"><div class="profile-stat"><small>МОГУЩЕСТВО</small><b>${fmt(person.power_score)}</b></div><div class="profile-stat"><small>ОБЫЧНОЕ ВЛИЯНИЕ</small><b>${fmt(person.points)}</b></div><div class="profile-stat"><small>КАРЬЕРА</small><b>${fmt(person.career_points)}</b></div><div class="profile-stat"><small>ТАЛАНТЫ</small><b>${fmt(person.talent_spent)} / ${fmt(person.talent_total)}</b></div><div class="profile-stat"><small>АУРА</small><b>${fmt(person.aura)}</b></div><div class="profile-stat"><small>ЧСВ</small><b>${fmt(person.chsv)}</b></div></div><div class="profile-section"><h4>🏛 ГОСУДАРСТВО</h4><div class="detail-list"><div class="detail-row"><span>Текущие должности</span><b>${esc(officeText(person))}</b></div><div class="detail-row"><span>Государственные действия</span><b>${fmt(person.government_actions)}</b></div><div class="detail-row"><span>Законопроекты и голоса</span><b>${fmt(person.bills_authored)} / ${fmt(person.bill_votes)}</b></div></div></div><div class="profile-section"><h4>🌳 ДРЕВО ТАЛАНТОВ</h4><div class="talent-bars">${talentBars(person)}</div></div><div class="profile-section"><h4>📊 АКТИВНОСТЬ И ИГРЫ</h4><div class="detail-list"><div class="detail-row"><span>Сообщения</span><b>${fmt(person.messages)}</b></div><div class="detail-row"><span>Получено реакций</span><b>${fmt(person.reactions_received)}</b></div><div class="detail-row"><span>Ответы участникам</span><b>${fmt(person.replies_sent)}</b></div><div class="detail-row"><span>Игровая прибыль</span><b>${person.game_profit>=0?'+':''}${fmt(person.game_profit)}</b></div><div class="detail-row"><span>Победы / поражения</span><b>${fmt(person.game_wins)} / ${fmt(person.game_losses)}</b></div></div></div></article>`;
  }

  function openProfile(userId){
    const person=(state.participants||[]).find(x=>Number(x.user_id)===Number(userId));
    $('profileContent').innerHTML=profileMarkup(person);$('profileModal').classList.add('show');$('profileModal').setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
  }
  function closeProfile(){$('profileModal').classList.remove('show');$('profileModal').setAttribute('aria-hidden','true');document.body.style.overflow=''}

  function render(){
    renderSummary();renderTop();renderPeople();renderRatings();renderGovernment();
    const me=(state.participants||[]).find(x=>Number(x.user_id)===Number(state.user_id));
    $('myProfile').innerHTML=profileMarkup(me);
  }

  document.addEventListener('click',event=>{
    const tab=event.target.closest('[data-tab]');
    if(tab){document.querySelectorAll('.bottom-nav button').forEach(x=>x.classList.toggle('active',x===tab));document.querySelectorAll('.screen').forEach(x=>x.classList.toggle('active',x.dataset.screen===tab.dataset.tab));window.scrollTo({top:0,behavior:'smooth'});return}
    const profile=event.target.closest('[data-profile]');if(profile){openProfile(profile.dataset.profile);return}
    const metric=event.target.closest('[data-metric]');if(metric){currentMetric=metric.dataset.metric;document.querySelectorAll('[data-metric]').forEach(x=>x.classList.toggle('active',x===metric));renderRatings();return}
    if(event.target.closest('#refresh')){load();return}
    if(event.target.closest('#profileClose')||event.target===$('profileModal')){closeProfile();return}
  });
  $('peopleSearch').addEventListener('input',renderPeople);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)load()});
  load();
})();