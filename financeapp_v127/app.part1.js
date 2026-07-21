(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#08060f');tg?.setBackgroundColor?.('#08060f');
  const qs=new URLSearchParams(location.search);
  const chatId=qs.get('chat_id')||'';
  const initData=tg?.initData||'';
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':initData};
  const $=id=>document.getElementById(id);
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const dateTime=value=>new Intl.DateTimeFormat('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(Number(value)*1000));
  let baseState=null,investState=null,requestState=null,historyState={items:[]},chartState={history:[]};
  let selectedPlan='safe7',selectedStock='EGO',selectedPeriod=86400,pendingAction=null,lastInvestmentLoad=0;

  function toast(text,type='success'){
    const node=$('toast');node.textContent=text;node.className=`toast show ${type}`;
    clearTimeout(node._timer);node._timer=setTimeout(()=>node.className='toast',3400);
  }
  async function api(url,{method='GET',body=null}={}){
    const target=new URL(url,location.origin);if(method==='GET')target.searchParams.set('chat_id',chatId);
    const options={method,headers};if(body)options.body=JSON.stringify({...body,chat_id:chatId});
    const response=await fetch(target.pathname+target.search,options);
    const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
    if(!response.ok||!data.ok)throw new Error(data.reason||'Операция не выполнена.');
    return data;
  }
  function openScreen(name){
    document.querySelectorAll('.screen').forEach(node=>node.classList.toggle('active',node.dataset.screen===name));
    document.querySelectorAll('[data-nav]').forEach(node=>node.classList.toggle('active',node.dataset.nav===name));
    if(name==='history')renderHistory();
    if(name==='market')loadChart(true);
    scrollTo({top:0,behavior:'smooth'});
  }
  function confirmAction(title,text,action){
    pendingAction=action;$('modalTitle').textContent=title;$('modalText').textContent=text;
    $('modal').classList.add('open');$('modal').setAttribute('aria-hidden','false');
  }
  async function runPending(){
    if(!pendingAction)return;const action=pendingAction;pendingAction=null;
    $('modal').classList.remove('open');$('modal').setAttribute('aria-hidden','true');
    try{
      const result=await action();toast(result.message||'Готово');tg?.HapticFeedback?.notificationOccurred?.('success');
      await loadAll(true);
    }catch(error){toast(error.message,'error');tg?.HapticFeedback?.notificationOccurred?.('error')}
  }
  function fillSelect(id){
    const select=$(id);const previous=select.value;select.innerHTML='';
    for(const person of baseState?.participants||[]){
      const option=document.createElement('option');option.value=person.user_id;
      option.textContent=person.name+(person.username?` · @${person.username}`:'');select.appendChild(option);
    }
    if(!select.options.length){const option=document.createElement('option');option.value='';option.textContent='Нет других участников';select.appendChild(option)}
    if([...select.options].some(o=>o.value===previous))select.value=previous;
    select.disabled=!baseState?.participants?.length;
  }
  function participantName(id){const select=$(id);return select.options[select.selectedIndex]?.textContent||'—'}

  function updateCredit(){
    const credit=baseState?.credit||{};const badge=$('creditBadge');badge.textContent=`${credit.label||'Надёжность'} · ${credit.reliability??100}%`;
    badge.className=(credit.reliability??100)<50?'danger':(credit.reliability??100)<80?'warn':'';
  }
  function updateHeader(){
    if(!baseState||!investState)return;
    $('playerName').textContent=baseState.player.name;$('balance').textContent=fmt(baseState.player.points);
    $('depositTotal').textContent=fmt(investState.totals.deposits);$('portfolioTotal').textContent=fmt(investState.totals.portfolio);
    const profit=Number(investState.totals.portfolio_profit)||0;const node=$('portfolioProfit');node.textContent=`${profit>=0?'+':''}${fmt(profit)}`;node.className=profit>0?'positive':profit<0?'negative':'';
    updateCredit();$('debtTotalLabel').textContent=fmt(baseState.totals.debt);$('owedTotalLabel').textContent=fmt(baseState.totals.owed);
  }
  function updatePreviews(){
