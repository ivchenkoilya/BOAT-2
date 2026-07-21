(()=>{
  'use strict';
  const tg=window.Telegram?.WebApp;
  tg?.ready();tg?.expand();tg?.setHeaderColor?.('#08060f');tg?.setBackgroundColor?.('#08060f');
  const qs=new URLSearchParams(location.search);
  const chatId=qs.get('chat_id')||'';
  const initData=tg?.initData||'';
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':initData};
  const $=id=>document.getElementById(id);
  const fmt=value=>new Intl.NumberFormat('ru-RU',{maximumFractionDigits:2}).format(Number(value)||0);
  const esc=value=>String(value??'').replace(/[&<>'"]/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
  const dateTime=value=>new Intl.DateTimeFormat('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}).format(new Date(Number(value)*1000));
  const clockTime=value=>new Intl.DateTimeFormat('ru-RU',{hour:'2-digit',minute:'2-digit'}).format(new Date(Number(value)*1000));
  const COMPANY_PROFILES={
    EGO:{news_id:'company:EGO',symbol:'EGO',source_type:'company_profile',category:'О КОМПАНИИ',title:'EGO Corp — рынок статуса и влияния',summary:'Премиальная экосистема репутации, рекламы и услуг для самых влиятельных участников.',outlook:'умеренно позитивная · низкий риск',body:'ВО ЧТО ТЫ ВКЛАДЫВАЕШЬСЯ\nEGO Corp зарабатывает на премиальных статусах, рекламных интеграциях, репутационных сервисах и продуктах для участников с высоким влиянием. Компания ориентируется на обеспеченную аудиторию и получает устойчивую маржу.\n\nБУДУЩЕЕ КОМПАНИИ\nРост возможен за счёт расширения элитных программ, государственных наград и повышения интереса к статусным продуктам. Лучше всего EGO чувствует себя при стабильной власти и растущей экономике.\n\nГЛАВНЫЕ РИСКИ\nНалоги на крупные корпорации, антимонопольные ограничения, репутационные скандалы и падение интереса к премиальному сегменту.'},
    HERO:{news_id:'company:HERO',symbol:'HERO',source_type:'company_profile',category:'О КОМПАНИИ',title:'Hero Energy — энергия и инфраструктура',summary:'Компания снабжает Реальность энергией и развивает крупные инфраструктурные проекты.',outlook:'позитивная · средний риск',body:'ВО ЧТО ТЫ ВКЛАДЫВАЕШЬСЯ\nHero Energy строит энергетическую инфраструктуру, обслуживает крупные объекты и получает доход от долгосрочных контрактов. Спрос на её услуги существует почти при любом состоянии экономики.\n\nБУДУЩЕЕ КОМПАНИИ\nГлавные точки роста — государственные заказы, модернизация сети и новые районы Реальности. При режиме экономического роста акции обычно получают дополнительную поддержку.\n\nГЛАВНЫЕ РИСКИ\nВысокая стоимость строительства, дефицит ресурсов, заморозка проектов и сокращение государственного бюджета.'},
    NPC:{news_id:'company:NPC',symbol:'NPC',source_type:'company_profile',category:'О КОМПАНИИ',title:'NPC Industries — массовый рынок',summary:'Доступные товары и сервисы для самой широкой аудитории участников.',outlook:'нейтральная · высокий риск',body:'ВО ЧТО ТЫ ВКЛАДЫВАЕШЬСЯ\nNPC Industries работает в массовом сегменте: доступные товары, базовые услуги и продукты повседневного спроса. Компания зарабатывает не высокой наценкой, а огромным количеством покупателей.\n\nБУДУЩЕЕ КОМПАНИИ\nРост возможен при социальных выплатах, повышении активности массовки и расширении доступного рынка. Компания может быстро набирать обороты, когда люди начинают больше тратить.\n\nГЛАВНЫЕ РИСКИ\nНизкая маржа, падение покупательской способности, рост налогов и сильная зависимость от настроения большинства участников.'},
    CORV:{news_id:'company:CORV',symbol:'CORV',source_type:'company_profile',category:'О КОМПАНИИ',title:'CORVUS — производитель снюса',summary:'Высокорисковый производитель снюса с сильным брендом и зависимостью от регулирования.',outlook:'спекулятивно позитивная · высокий риск',body:'ВО ЧТО ТЫ ВКЛАДЫВАЕШЬСЯ\nCORVUS производит снюс, развивает новые линейки и получает доход от продаж через внутреннюю сеть распространения. Сильный бренд способен давать быстрый рост при удачном запуске продукции.\n\nБУДУЩЕЕ КОМПАНИИ\nПотенциал связан с расширением производства, новыми вкусами, ростом спроса и борьбой государства с нелегальными конкурентами. При успешных отчётах акция может расти быстрее рынка.\n\nГЛАВНЫЕ РИСКИ\nАкцизы, ограничения рекламы и продаж, проверки качества, дефицит сырья и любые новые законы против никотиновой продукции. Поэтому акция остаётся высоковолатильной.'},
    CENTER:{news_id:'company:CENTER',symbol:'CENTER',source_type:'company_profile',category:'О КОМПАНИИ',title:'Центр Вселенной — актив внимания',summary:'Медиа, события и спекулятивный капитал, стоимость которого держится на внимании аудитории.',outlook:'непредсказуемая · экстремальный риск',body:'ВО ЧТО ТЫ ВКЛАДЫВАЕШЬСЯ\nЦентр Вселенной объединяет шоу, события, рекламные интеграции и лицензии вокруг самого громкого бренда Реальности. Его цена зависит от внимания, конфликтов и общественного ажиотажа.\n\nБУДУЩЕЕ КОМПАНИИ\nВо время крупных событий и политической неопределённости актив способен резко дорожать. Удачная кампания может принести самую высокую доходность среди всех компаний.\n\nГЛАВНЫЕ РИСКИ\nЦена часто опережает реальные результаты. После всплеска интереса возможен резкий обвал, поэтому актив подходит только для тех, кто принимает экстремальную волатильность.'}
  };
  let baseState=null,investState=null,requestState=null,historyState={items:[]},chartState={history:[],events:[]};
  let selectedPlan='safe7',selectedStock='EGO',selectedPeriod=86400,pendingAction=null,lastInvestmentLoad=0;
  let chartModel={points:[],coords:[],events:[],eventCoords:[],width:640,height:300,padX:16,padTop:20,padBottom:42};
  let chartInteracting=false,lastChartIndex=-1,pointerStartX=0,pointerMoved=false;

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
  function allNews(){
    const map=new Map();
    for(const item of [...Object.values(COMPANY_PROFILES),...(investState?.news||[]),...(chartState?.events||[])])if(item?.news_id)map.set(String(item.news_id),item);
    return [...map.values()];
  }
  function findNews(newsId){return allNews().find(item=>String(item.news_id)===String(newsId))}
  function openNews(newsId){
    const item=findNews(newsId);if(!item)return;
    const profile=item.source_type==='company_profile';
    $('newsCategory').textContent=item.category||'НОВОСТЬ';$('newsDate').textContent=profile?'ИНВЕСТИЦИОННЫЙ ПРОФИЛЬ':dateTime(item.source_at||item.event_at);
    $('newsTitle').textContent=item.title||'Новость рынка';$('newsSummary').textContent=item.summary||'';$('newsBody').textContent=item.body||item.summary||'';
    const effectNode=$('newsEffect');
    if(profile){effectNode.textContent=`Перспектива: ${item.outlook}`;effectNode.className='news-effect'}
    else{const effect=Number(item.effect_percent??Number(item.effect_bp||0)/100);effectNode.textContent=`Влияние на ${item.symbol}: ${effect>=0?'+':''}${fmt(effect)}%`;effectNode.className=`news-effect ${effect<0?'negative':''}`}
    $('newsModal').classList.add('open');$('newsModal').setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
  }
  function closeNews(){
    $('newsModal').classList.remove('open');$('newsModal').setAttribute('aria-hidden','true');document.body.style.overflow='';
  }
  function fillSelect(id){
    const select=$(id);const previous=select.value;select.innerHTML='';
    for(const person of baseState?.participants||[]){
      const option=document.createElement('option');option.value=person.user_id;
      option.textContent=person.name+(person.username?` · @${person.username}`:'');select.appendChild(option);
    }
    if(!select.options.length){const option=document.createElement('option');option.value='';option.textContent='Нет других участников';select.appendChild(option)}
    if([...select.options].some(option=>option.value===previous))select.value=previous;
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
