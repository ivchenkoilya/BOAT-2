  function ensurePortfolioUI(){
    if(!$('financeV129Style')){
      const style=document.createElement('style');style.id='financeV129Style';style.textContent=`
        .bottom-nav{grid-template-columns:repeat(6,1fr)}.bottom-nav button{padding-left:0;padding-right:0}.bottom-nav small{font-size:6.5px}
        .company-profile-button{width:100%;display:flex;align-items:center;justify-content:space-between;gap:10px;margin:11px 0 2px;padding:12px 13px;border:1px solid #5e3d75;border-radius:14px;background:linear-gradient(145deg,#251532,#130d1a);color:#fff;text-align:left}.company-profile-button span{font-size:21px}.company-profile-button b,.company-profile-button small{display:block}.company-profile-button b{font-size:11px}.company-profile-button small{font-size:8px;color:#a89caf;margin-top:3px}.company-profile-button i{font-style:normal;color:#d4a0fa;font-size:18px}
        .portfolio-hero-v129{padding:19px;border:1px solid #60427a;border-radius:24px;background:radial-gradient(circle at 100% 0,rgba(182,110,255,.25),transparent 44%),linear-gradient(150deg,#241531,#0d0a13);box-shadow:0 18px 50px rgba(0,0,0,.24)}.portfolio-hero-v129 small,.portfolio-hero-v129 b,.portfolio-hero-v129 em{display:block}.portfolio-hero-v129>small{font-size:8px;letter-spacing:.12em;color:#cba2e8}.portfolio-hero-v129> b{font-size:31px;margin-top:7px;letter-spacing:-.04em}.portfolio-hero-v129>em{font-style:normal;font-size:11px;margin-top:7px}.portfolio-allocation{display:grid;grid-template-columns:repeat(3,1fr);gap:7px;margin-top:15px}.portfolio-allocation div{padding:10px;border-radius:13px;background:#0b0810;border:1px solid #3b2b49}.portfolio-allocation small{font-size:6px;color:#93889b}.portfolio-allocation b{font-size:11px;margin-top:4px}
        .portfolio-actions{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:11px 0}.portfolio-actions button{min-height:68px;border:1px solid #40304d;border-radius:17px;background:#17121c;color:#fff}.portfolio-actions span,.portfolio-actions b{display:block}.portfolio-actions span{font-size:22px}.portfolio-actions b{font-size:9px;margin-top:5px}
        .asset-section-v129{margin-top:18px}.asset-title-v129{display:flex;justify-content:space-between;align-items:end;margin:0 2px 9px}.asset-title-v129 b,.asset-title-v129 small{display:block}.asset-title-v129 b{font-size:19px}.asset-title-v129 small{font-size:8px;color:#9d929f;margin-top:3px}.asset-title-v129 strong{text-align:right;font-size:14px}.asset-row-v129{display:grid;grid-template-columns:46px minmax(0,1fr) auto;gap:11px;align-items:center;padding:12px 2px;border-bottom:1px solid #241b2c}.asset-logo-v129{width:43px;height:43px;display:grid;place-items:center;border-radius:50%;background:#241632;border:1px solid #5b3c72;font-size:20px}.asset-copy-v129{min-width:0}.asset-copy-v129 b,.asset-copy-v129 small{display:block}.asset-copy-v129 b{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.asset-copy-v129 small{font-size:8px;color:#8e8494;margin-top:4px}.asset-value-v129{text-align:right}.asset-value-v129 b,.asset-value-v129 small{display:block}.asset-value-v129 b{font-size:12px}.asset-value-v129 small{font-size:8px;margin-top:4px}.portfolio-event-strip{display:flex;gap:9px;overflow:auto;scrollbar-width:none}.portfolio-event-strip::-webkit-scrollbar{display:none}.portfolio-event-card{flex:0 0 210px;padding:13px;border:1px solid #40304d;border-radius:17px;background:#17121c}.portfolio-event-card span,.portfolio-event-card b,.portfolio-event-card small{display:block}.portfolio-event-card span{font-size:21px}.portfolio-event-card b{font-size:11px;margin-top:9px}.portfolio-event-card small{font-size:8px;color:#a89caf;margin-top:5px;line-height:1.4}
        .loan-limits-note{padding:11px 12px;margin:0 0 11px;border:1px solid #4a375b;border-radius:14px;background:#100c16;color:#b7aabd;font-size:8px;line-height:1.5}.loan-limits-note b{color:#f4d681}
        @media(max-width:370px){.bottom-nav small{font-size:5.5px}.bottom-nav span{font-size:17px}.portfolio-allocation{grid-template-columns:1fr 1fr}.portfolio-allocation div:last-child{grid-column:1/-1}}
      `;document.head.appendChild(style);
    }
    for(const id of ['loanAmount','requestAmount']){const input=$(id);if(input){input.max='100000';input.step='100'}}
    const loanSection=document.querySelector('[data-screen="loan"]');
    if(loanSection&&!loanSection.querySelector('.loan-limits-note')){
      const note=document.createElement('div');note.className='loan-limits-note';note.innerHTML='<b>Новые лимиты долга:</b> Декорация 5 000 · Пыль 10 000 · Массовка 25 000 · Второстепенная роль 50 000 · Главный герой 100 000.';
      loanSection.querySelector('.segmented')?.after(note);
    }
    const depositQuick=document.querySelector('.quick[data-open="deposits"] small');if(depositQuick)depositQuick.textContent='До 14% всего за 10 дней';
    const quickGrid=document.querySelector('[data-screen="home"] .quick-grid');
    if(quickGrid&&!quickGrid.querySelector('[data-open="portfolio"]'))quickGrid.insertAdjacentHTML('beforeend','<button class="quick primary" data-open="portfolio" type="button"><span>💼</span><b>Портфель</b><small>Все активы и общий результат</small><i>›</i></button>');
    const marketCard=document.querySelector('[data-screen="market"] .market-card');
    if(marketCard&&!$('companyProfileButton')){
      const button=document.createElement('button');button.id='companyProfileButton';button.className='company-profile-button';button.type='button';button.dataset.newsId='company:EGO';button.innerHTML='<span>🏢</span><span><b>О компании</b><small>Чем занимается, перспективы и риски</small></span><i>›</i>';
      marketCard.querySelector('.stock-head')?.after(button);
    }
    const inlinePortfolio=$('portfolioList');if(inlinePortfolio){inlinePortfolio.style.display='none';if(inlinePortfolio.previousElementSibling)inlinePortfolio.previousElementSibling.style.display='none'}
    if(!document.querySelector('[data-screen="portfolio"]')){
      const screen=document.createElement('section');screen.className='screen';screen.dataset.screen='portfolio';screen.innerHTML=`
        <div class="section-heading"><div><small>МОИ АКТИВЫ</small><b>Портфель</b></div><em>Обновляется вместе с рынком</em></div>
        <article class="portfolio-hero-v129"><small>ОБЩИЙ КАПИТАЛ</small><b id="portfolioGrandTotal">0</b><em id="portfolioGrandProfit">Результат: 0</em><div class="portfolio-allocation"><div><small>АКЦИИ</small><b id="portfolioAllocationStocks">0%</b></div><div><small>ВКЛАДЫ</small><b id="portfolioAllocationDeposits">0%</b></div><div><small>СВОБОДНО</small><b id="portfolioAllocationFree">0%</b></div></div></article>
        <div class="portfolio-actions"><button data-open="market" type="button"><span>↗</span><b>РЫНОК</b></button><button data-open="history" type="button"><span>◷</span><b>ИСТОРИЯ</b></button><button data-open="deposits" type="button"><span>◔</span><b>ВКЛАДЫ</b></button></div>
        <section class="asset-section-v129"><div class="asset-title-v129"><div><b>Акции</b><small id="portfolioStocksShare">0% капитала</small></div><strong id="portfolioStocksValue">0</strong></div><div id="portfolioStockRows"></div></section>
        <section class="asset-section-v129"><div class="asset-title-v129"><div><b>Вклады</b><small id="portfolioDepositsShare">0% капитала</small></div><strong id="portfolioDepositsValue">0</strong></div><div id="portfolioDepositRows"></div></section>
        <section class="asset-section-v129"><div class="asset-title-v129"><div><b>Свободное влияние</b><small id="portfolioFreeShare">0% капитала</small></div><strong id="portfolioFreeValue">0</strong></div></section>
        <section class="asset-section-v129"><div class="asset-title-v129"><div><b>Выплаты и события</b><small>Ближайшие поступления</small></div></div><div class="portfolio-event-strip" id="portfolioEvents"></div></section>`;
      document.querySelector('main.app')?.appendChild(screen);
    }
    const nav=document.querySelector('.bottom-nav');
    if(nav&&!nav.querySelector('[data-nav="portfolio"]'))nav.insertAdjacentHTML('beforeend','<button data-nav="portfolio" type="button"><span>💼</span><small>Портфель</small></button>');
  }
  function updatePreviews(){
    if(!baseState)return;
    const transferAmount=Math.max(0,Number($('transferAmount').value)||0);
    $('transferPreviewName').textContent=participantName('transferTarget');$('transferPreviewAmount').textContent=fmt(transferAmount);
    $('transferPreviewLeft').textContent=fmt(Math.max(0,Number(baseState.player.points)-transferAmount));
    const amount=Math.max(0,Number($('loanAmount').value)||0),interest=Math.max(0,Number($('loanInterest').value)||0),days=Math.max(0,Number($('loanDays').value)||0);
    $('loanPreviewAmount').textContent=fmt(amount);$('loanPreviewDue').textContent=fmt(Math.ceil(amount*(100+interest)/100));$('loanPreviewDays').textContent=`${days} дн.`;
    const plan=investState?.plans?.find(item=>item.key===selectedPlan),depositAmount=Math.max(0,Number($('depositAmount').value)||0);
    if(plan){
      const payout=Math.floor(depositAmount*(100+Number(plan.yield_percent))/100);
      $('depositPreviewPlan').textContent=plan.title;$('depositPreviewAmount').textContent=fmt(depositAmount);$('depositPreviewPayout').textContent=fmt(payout);$('depositPreviewTerm').textContent=`${plan.term_days} дн.`;
    }
    updateTradePreview();
  }
  function empty(icon,title,copy){return `<div class="empty"><span>${icon}</span><b>${esc(title)}</b><small>${esc(copy)}</small></div>`}
  function dealMarkup(item,borrower){
    const overdue=item.status==='overdue';const paid=Math.max(0,Number(item.total_due)-Number(item.remaining));const progress=Math.min(100,Math.round(paid*100/Math.max(1,Number(item.total_due))));
    const buttons=borrower?`<div class="repay-grid"><button data-repay="${esc(item.loan_id)}" data-amount="100" type="button">100</button><button data-repay="${esc(item.loan_id)}" data-amount="${Math.max(1,Math.ceil(item.remaining/2))}" type="button">ПОЛОВИНА</button><button data-repay="${esc(item.loan_id)}" data-amount="all" type="button">ВСЁ</button></div>`:'';
    return `<article class="deal ${overdue?'overdue':''}"><div class="item-head"><div><b>${borrower?'Кредитор':'Заёмщик'}: ${esc(item.other_name)}</b><small>Договор #${esc(item.token||item.loan_id.slice(0,6))}</small></div><span class="badge ${overdue?'danger':''}">${overdue?'ПРОСРОЧЕН':'АКТИВЕН'}</span></div><div class="progress"><i style="width:${progress}%"></i></div><div class="info-grid"><div><small>ОСТАЛОСЬ</small><b>${fmt(item.remaining)}</b></div><div><small>СРОК</small><b>${esc(item.time_text)}</b></div><div><small>СУММА</small><b>${fmt(item.principal)}</b></div><div><small>ПРОЦЕНТ</small><b>${fmt(item.interest)}%</b></div></div>${buttons}</article>`;
  }
  function renderDebts(){
    const debts=baseState?.debts||[],owed=baseState?.owed||[];
    $('debtsList').innerHTML=debts.length?debts.map(item=>dealMarkup(item,true)).join(''):empty('✅','Активных долгов нет','Можно пользоваться финансовыми операциями без ограничений.');
    $('owedList').innerHTML=owed.length?owed.map(item=>dealMarkup(item,false)).join(''):empty('🤝','Тебе никто не должен','Выданные займы появятся в этом разделе.');
  }
  function renderRequest(){
    const pending=requestState?.pending;const node=$('pendingRequest');
    if(!pending){node.innerHTML='';$('requestSubmit').disabled=false;return}
    node.innerHTML=`<article class="deposit-item"><div class="item-head"><div><b>Активная заявка</b><small>Кредитор: ${esc(pending.lender_name)}</small></div><span class="badge warn">ОЖИДАЕТ</span></div><div class="info-grid"><div><small>СУММА</small><b>${fmt(pending.amount)}</b></div><div><small>ВЕРНУТЬ</small><b>${fmt(pending.total_due)}</b></div><div><small>ПРОЦЕНТ</small><b>${fmt(pending.interest)}%</b></div><div><small>СРОК</small><b>${fmt(pending.days)} дн.</b></div></div></article>`;
    $('requestSubmit').disabled=true;
  }
  function renderPlans(){
    const plans=investState?.plans||[];if(!plans.some(plan=>plan.key===selectedPlan)&&plans[0])selectedPlan=plans[0].key;
    const icons={flex:'💧',safe7:'⚡',premium14:'💎',capital30:'👑'};
    $('planGrid').innerHTML=plans.map(plan=>`<button class="plan ${plan.key===selectedPlan?'active':''}" data-plan="${esc(plan.key)}" type="button"><span>${icons[plan.key]||'🏦'}</span><b>${esc(plan.title)}</b><small>${plan.key==='flex'?`${plan.daily_percent}% в сутки · до ${plan.term_days} дн.`:`${plan.term_days} дней`}</small><em>+${plan.yield_percent}%</em></button>`).join('');
    updatePreviews();
  }
  function renderDeposits(){
    const items=investState?.deposits||[];
    $('depositList').innerHTML=items.length?items.map(item=>{
      const now=investState.server_time,remaining=Math.max(0,item.matures_at-now),days=Math.ceil(remaining/86400);
      return `<article class="deposit-item"><div class="item-head"><div><b>${esc(item.title)}</b><small>Открыт ${dateTime(item.started_at)}</small></div><span class="badge ${item.matured?'':'warn'}">${item.matured?'ГОТОВ':'ЕЩЁ '+days+' ДН.'}</span></div><div class="info-grid"><div><small>ВЛОЖЕНО</small><b>${fmt(item.principal)}</b></div><div><small>ПРИ СНЯТИИ</small><b>${fmt(item.withdraw_payout??item.payout)}</b></div><div><small>ДОХОД</small><b class="positive">+${fmt(item.interest)}</b></div><div><small>ДАТА</small><b>${dateTime(item.matures_at)}</b></div></div><small class="helper">${esc(item.early_note)}</small><button class="small-button" data-withdraw-deposit="${esc(item.deposit_id)}" ${item.can_withdraw?'':'disabled'} type="button">${item.matured?'ЗАБРАТЬ ВКЛАД':'СНЯТЬ ДОСРОЧНО'}</button></article>`;
    }).join(''):empty('🏦','Активных вкладов нет','Выбери тариф выше и положи влияние под процент.');
  }
  function stockBySymbol(symbol=selectedStock){return investState?.stocks?.find(item=>item.symbol===symbol)}
  function renderTickers(){
    const stocks=investState?.stocks||[];if(!stocks.some(stock=>stock.symbol===selectedStock)&&stocks[0])selectedStock=stocks[0].symbol;
    $('tickerStrip').innerHTML=stocks.map(stock=>`<button class="ticker ${stock.symbol===selectedStock?'active':''}" data-stock="${esc(stock.symbol)}" type="button"><b>${stock.icon} ${esc(stock.symbol)}</b><small>${fmt(stock.price)} влияния</small><em class="${stock.change_percent>=0?'positive':'negative'}">${stock.change_percent>=0?'+':''}${fmt(stock.change_percent)}%</em></button>`).join('');
  }
  function newsIcon(item){
    if(item?.source_type==='government_law')return '🏛️';
    if(item?.source_type==='government_decision')return '🛑';
    if(item?.source_type==='government_action')return '💼';
    return '📰';
  }
  function renderSelectedStock(){
    const stock=stockBySymbol();if(!stock)return;
    $('stockIcon').textContent=stock.icon;$('stockName').textContent=stock.name;$('stockSymbol').textContent=`${stock.symbol} · ${stock.risk} риск`;$('stockPrice').textContent=fmt(stock.price);
    const profileButton=$('companyProfileButton');if(profileButton)profileButton.dataset.newsId=`company:${stock.symbol}`;
    const change=$('stockChange');change.textContent=`${stock.change_percent>=0?'+':''}${fmt(stock.change_percent)}%`;change.className=stock.change_percent>=0?'positive':'negative';
    const pos=stock.position;$('positionQuantity').textContent=`${fmt(pos.quantity)} акций`;$('positionValue').textContent=fmt(pos.value);
    const profit=$('positionProfit');profit.textContent=`${pos.profit>=0?'+':''}${fmt(pos.profit)}`;profit.className=pos.profit>=0?'positive':'negative';
    const newsButton=$('marketNews'),latest=stock.latest_news;
    if(latest){newsButton.disabled=false;newsButton.dataset.newsId=latest.news_id;newsButton.innerHTML=`<span>${newsIcon(latest)}</span><div><b>${esc(latest.title)}</b><small>${esc(latest.summary)} · ${dateTime(latest.source_at||latest.event_at)}</small></div><i>›</i>`}
    else{newsButton.disabled=true;delete newsButton.dataset.newsId;newsButton.innerHTML='<span>📰</span><div><b>Новостей пока нет</b><small>События рынка будут появляться здесь.</small></div><i>›</i>'}
    updateTradePreview();
  }
  function renderNewsFeed(){
    const items=(investState?.news||[]).filter(item=>item.symbol===selectedStock).slice(0,10);
    $('marketNewsFeed').innerHTML=items.length?items.map(item=>{const effect=Number(item.effect_percent??Number(item.effect_bp||0)/100);return `<button class="news-item" data-news-id="${esc(item.news_id)}" type="button"><span class="news-icon">${newsIcon(item)}</span><span class="news-copy"><b>${esc(item.title)}</b><small>${esc(item.summary)}</small><em>${esc(item.category)} · ${dateTime(item.source_at||item.event_at)}</em></span><span class="news-effect-pill ${effect<0?'negative':''}">${effect>=0?'+':''}${fmt(effect)}%</span></button>`}).join(''):empty('🗞️','Новостей по компании пока нет','Законы, решения правительства и события компании появятся здесь автоматически.');
  }
  function renderPortfolio(){
    const positions=(investState?.stocks||[]).filter(stock=>stock.position.quantity>0);
    $('portfolioList').innerHTML=positions.length?positions.map(stock=>`<article class="portfolio-item"><div class="item-head"><div><b>${stock.icon} ${esc(stock.name)}</b><small>${stock.symbol} · ${fmt(stock.position.quantity)} акций</small></div><span class="badge ${stock.position.profit<0?'danger':''}">${stock.position.profit>=0?'+':''}${fmt(stock.position.profit)}</span></div><div class="info-grid"><div><small>СРЕДНЯЯ ЦЕНА</small><b>${fmt(stock.position.average_price)}</b></div><div><small>ТЕКУЩАЯ</small><b>${fmt(stock.price)}</b></div><div><small>ВЛОЖЕНО</small><b>${fmt(stock.position.total_cost)}</b></div><div><small>СТОИМОСТЬ</small><b>${fmt(stock.position.value)}</b></div></div></article>`).join(''):empty('📊','Портфель пуст','Выбери акцию, укажи количество и нажми «Купить».');
  }
  function renderPortfolioScreen(){
    if(!baseState||!investState||!$('portfolioGrandTotal'))return;
    const free=Number(baseState.player.points)||0,stocks=Number(investState.totals.portfolio)||0,deposits=Number(investState.totals.deposits)||0,total=Math.max(0,free+stocks+deposits);
    const stockProfit=Number(investState.totals.portfolio_profit)||0,depositProfit=(investState.deposits||[]).reduce((sum,item)=>sum+(Number(item.interest)||0),0),result=stockProfit+depositProfit;
    const share=value=>total>0?Math.round(value*10000/total)/100:0;
    $('portfolioGrandTotal').textContent=fmt(total);$('portfolioGrandProfit').textContent=`Результат: ${result>=0?'+':''}${fmt(result)}`;$('portfolioGrandProfit').className=result>=0?'positive':'negative';
    $('portfolioAllocationStocks').textContent=`${fmt(share(stocks))}%`;$('portfolioAllocationDeposits').textContent=`${fmt(share(deposits))}%`;$('portfolioAllocationFree').textContent=`${fmt(share(free))}%`;
    $('portfolioStocksValue').textContent=fmt(stocks);$('portfolioStocksShare').textContent=`${fmt(share(stocks))}% капитала`;$('portfolioDepositsValue').textContent=fmt(deposits);$('portfolioDepositsShare').textContent=`${fmt(share(deposits))}% капитала`;$('portfolioFreeValue').textContent=fmt(free);$('portfolioFreeShare').textContent=`${fmt(share(free))}% капитала`;
    const positions=(investState.stocks||[]).filter(stock=>stock.position.quantity>0);
    $('portfolioStockRows').innerHTML=positions.length?positions.map(stock=>`<article class="asset-row-v129"><span class="asset-logo-v129">${stock.icon}</span><span class="asset-copy-v129"><b>${esc(stock.name)}</b><small>${fmt(stock.position.quantity)} шт. · ${fmt(stock.price)} за акцию</small></span><span class="asset-value-v129"><b>${fmt(stock.position.value)}</b><small class="${stock.position.profit>=0?'positive':'negative'}">${stock.position.profit>=0?'+':''}${fmt(stock.position.profit)}</small></span></article>`).join(''):empty('📈','Акций пока нет','Купленные компании появятся здесь.');
    $('portfolioDepositRows').innerHTML=(investState.deposits||[]).length?investState.deposits.map(item=>`<article class="asset-row-v129"><span class="asset-logo-v129">🏦</span><span class="asset-copy-v129"><b>${esc(item.title)}</b><small>${fmt(item.principal)} вложено · до ${dateTime(item.matures_at)}</small></span><span class="asset-value-v129"><b>${fmt(item.payout)}</b><small class="positive">+${fmt(item.interest)}</small></span></article>`).join(''):empty('🏦','Вкладов пока нет','Открой быстрый вклад сроком до 10 дней.');
    const events=(investState.deposits||[]).slice().sort((a,b)=>a.matures_at-b.matures_at).slice(0,5);
    $('portfolioEvents').innerHTML=events.length?events.map(item=>`<article class="portfolio-event-card"><span>💰</span><b>${esc(item.title)} — выплата ${fmt(item.payout)}</b><small>${item.matured?'Можно забрать сейчас':`Ожидается ${dateTime(item.matures_at)}`}</small></article>`).join(''):'<article class="portfolio-event-card"><span>📅</span><b>Ближайших выплат нет</b><small>После открытия вклада здесь появится дата поступления.</small></article>';
  }
  function updateTradePreview(){
    const stock=stockBySymbol();if(!stock)return;const quantity=Math.max(1,Number($('stockQuantity').value)||1),gross=stock.price*quantity,fee=Math.max(1,Math.ceil(gross*(investState?.fee_percent||1)/100));
    $('tradeTotal').textContent=`Купить ${fmt(gross+fee)} · продать ${fmt(Math.max(0,gross-fee))}`;
  }
  function renderMarket(){renderTickers();renderSelectedStock();renderNewsFeed();const tick=Math.max(1,Number(investState?.market_tick_seconds)||60);$('marketStatus').textContent=tick===60?'Курс обновляется каждую минуту':`Обновление раз в ${Math.round(tick/60)} мин.`}
  function renderHistory(){
    const items=historyState?.items||[];
    $('historyList').innerHTML=items.length?items.map(item=>`<article class="history-item"><div class="item-head"><div><b>${esc(item.title)}</b><small>${esc(item.other_name||item.detail||'Финансовая операция')} · ${dateTime(item.created_at)}</small></div><span class="${item.amount>=0?'positive':'negative'}">${item.amount>=0?'+':''}${fmt(item.amount)}</span></div></article>`).join(''):empty('🧾','История пуста','Переводы, займы и платежи появятся здесь.');
    const trades=investState?.trades||[];
    $('tradeHistory').innerHTML=trades.length?trades.map(item=>`<article class="trade-item"><div class="item-head"><div><b>${item.side==='buy'?'Покупка':'Продажа'} ${esc(item.symbol)}</b><small>${fmt(item.quantity)} шт. по ${fmt(item.price)} · комиссия ${fmt(item.fee)}</small></div><span class="${item.side==='buy'?'negative':'positive'}">${item.side==='buy'?'-':'+'}${fmt(item.side==='buy'?item.gross+item.fee:Math.max(0,item.gross-item.fee))}</span></div></article>`).join(''):empty('📈','Сделок пока нет','История покупок и продаж акций появится здесь.');
  }
  function renderAll(){
    ensurePortfolioUI();updateHeader();['transferTarget','loanTarget','requestTarget'].forEach(fillSelect);updatePreviews();renderDebts();renderRequest();renderPlans();renderDeposits();renderMarket();renderPortfolio();renderPortfolioScreen();renderHistory();$('loading').classList.add('hidden');
  }
