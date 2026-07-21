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
    const plans=investState?.plans||[];if(!plans.some(p=>p.key===selectedPlan)&&plans[0])selectedPlan=plans[0].key;
    const icons={flex:'💧',safe7:'🛡️',premium14:'💎',capital30:'👑'};
    $('planGrid').innerHTML=plans.map(plan=>`<button class="plan ${plan.key===selectedPlan?'active':''}" data-plan="${esc(plan.key)}" type="button"><span>${icons[plan.key]||'🏦'}</span><b>${esc(plan.title)}</b><small>${plan.key==='flex'?`${plan.daily_percent}% в сутки`:`${plan.term_days} дней`}</small><em>+${plan.yield_percent}%</em></button>`).join('');
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
    const stocks=investState?.stocks||[];if(!stocks.some(s=>s.symbol===selectedStock)&&stocks[0])selectedStock=stocks[0].symbol;
    $('tickerStrip').innerHTML=stocks.map(stock=>`<button class="ticker ${stock.symbol===selectedStock?'active':''}" data-stock="${esc(stock.symbol)}" type="button"><b>${stock.icon} ${esc(stock.symbol)}</b><small>${fmt(stock.price)} влияния</small><em class="${stock.change_percent>=0?'positive':'negative'}">${stock.change_percent>=0?'+':''}${stock.change_percent}%</em></button>`).join('');
  }
  function renderSelectedStock(){
    const stock=stockBySymbol();if(!stock)return;
    $('stockIcon').textContent=stock.icon;$('stockName').textContent=stock.name;$('stockSymbol').textContent=`${stock.symbol} · ${stock.risk} риск`;$('stockPrice').textContent=fmt(stock.price);
    const change=$('stockChange');change.textContent=`${stock.change_percent>=0?'+':''}${stock.change_percent}%`;change.className=stock.change_percent>=0?'positive':'negative';
    $('stockLow').textContent=fmt(stock.low);$('stockHigh').textContent=fmt(stock.high);$('stockVolume').textContent=fmt(stock.volume);
    const news=$('marketNews');news.innerHTML=stock.last_event?`<span>📰</span><div><b>${esc(stock.last_event)}</b><small>${stock.last_event_at?dateTime(stock.last_event_at):'Новость рынка'}</small></div>`:'<span>📰</span><div><b>Новостей пока нет</b><small>События рынка будут появляться здесь.</small></div>';
    const pos=stock.position;$('positionQuantity').textContent=`${fmt(pos.quantity)} акций`;$('positionValue').textContent=fmt(pos.value);
    const profit=$('positionProfit');profit.textContent=`${pos.profit>=0?'+':''}${fmt(pos.profit)}`;profit.className=pos.profit>=0?'positive':'negative';
    updateTradePreview();
  }
  function renderPortfolio(){
    const positions=(investState?.stocks||[]).filter(stock=>stock.position.quantity>0);
    $('portfolioList').innerHTML=positions.length?positions.map(stock=>`<article class="portfolio-item"><div class="item-head"><div><b>${stock.icon} ${esc(stock.name)}</b><small>${stock.symbol} · ${fmt(stock.position.quantity)} акций</small></div><span class="badge ${stock.position.profit<0?'danger':''}">${stock.position.profit>=0?'+':''}${fmt(stock.position.profit)}</span></div><div class="info-grid"><div><small>СРЕДНЯЯ ЦЕНА</small><b>${fmt(stock.position.average_price)}</b></div><div><small>ТЕКУЩАЯ</small><b>${fmt(stock.price)}</b></div><div><small>ВЛОЖЕНО</small><b>${fmt(stock.position.total_cost)}</b></div><div><small>СТОИМОСТЬ</small><b>${fmt(stock.position.value)}</b></div></div></article>`).join(''):empty('📊','Портфель пуст','Выбери акцию, укажи количество и нажми «Купить».');
  }
  function updateTradePreview(){
    const stock=stockBySymbol();if(!stock)return;const quantity=Math.max(1,Number($('stockQuantity').value)||1),gross=stock.price*quantity,fee=Math.max(1,Math.ceil(gross*(investState?.fee_percent||1)/100));
    $('tradeTotal').textContent=`Купить ${fmt(gross+fee)} · продать ${fmt(Math.max(0,gross-fee))}`;
  }
  function renderMarket(){renderTickers();renderSelectedStock();renderPortfolio();$('marketStatus').textContent=`Курс обновляется каждые ${Math.round((investState?.market_tick_seconds||300)/60)} мин.`}
  function renderHistory(){
    const items=historyState?.items||[];
    $('historyList').innerHTML=items.length?items.map(item=>`<article class="history-item"><div class="item-head"><div><b>${esc(item.title)}</b><small>${esc(item.other_name||item.detail||'Финансовая операция')} · ${dateTime(item.created_at)}</small></div><span class="${item.amount>=0?'positive':'negative'}">${item.amount>=0?'+':''}${fmt(item.amount)}</span></div></article>`).join(''):empty('🧾','История пуста','Переводы, займы и платежи появятся здесь.');
