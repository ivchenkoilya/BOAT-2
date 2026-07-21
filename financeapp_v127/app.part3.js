    const trades=investState?.trades||[];
    $('tradeHistory').innerHTML=trades.length?trades.map(item=>`<article class="trade-item"><div class="item-head"><div><b>${item.side==='buy'?'Покупка':'Продажа'} ${esc(item.symbol)}</b><small>${fmt(item.quantity)} шт. по ${fmt(item.price)} · комиссия ${fmt(item.fee)}</small></div><span class="${item.side==='buy'?'negative':'positive'}">${item.side==='buy'?'-':'+'}${fmt(item.side==='buy'?item.gross+item.fee:Math.max(0,item.gross-item.fee))}</span></div></article>`).join(''):empty('📈','Сделок пока нет','История покупок и продаж акций появится здесь.');
  }
  function renderAll(){
    updateHeader();['transferTarget','loanTarget','requestTarget'].forEach(fillSelect);updatePreviews();renderDebts();renderRequest();renderPlans();renderDeposits();renderMarket();renderHistory();$('loading').classList.add('hidden');
  }

  async function loadChart(silent=false){
    try{
      chartState=await api(`/finance-v127/api/chart?symbol=${encodeURIComponent(selectedStock)}&period=${selectedPeriod}`);drawChart(chartState.history||[]);
    }catch(error){$('chartEmpty').textContent=error.message;$('chartEmpty').style.display='grid';if(!silent)toast(error.message,'error')}
  }
  function drawChart(points){
    const emptyNode=$('chartEmpty'),line=$('chartLine'),area=$('chartArea'),grid=$('chartGrid');grid.innerHTML='';
    if(!points.length){line.setAttribute('d','');area.setAttribute('d','');emptyNode.textContent='Недостаточно данных для периода';emptyNode.style.display='grid';return}
    emptyNode.style.display='none';const width=640,height=250,padX=10,padY=18;const prices=points.map(p=>Number(p.price));let min=Math.min(...prices),max=Math.max(...prices);if(min===max){min-=1;max+=1}const range=max-min;
    for(let i=1;i<5;i++){const y=padY+(height-padY*2)*i/5;const path=document.createElementNS('http://www.w3.org/2000/svg','path');path.setAttribute('d',`M ${padX} ${y} H ${width-padX}`);path.setAttribute('stroke','#4b3860');path.setAttribute('stroke-opacity','.32');path.setAttribute('stroke-width','1');grid.appendChild(path)}
    const coords=points.map((point,index)=>{const x=padX+(width-padX*2)*(points.length===1?0:index/(points.length-1));const y=padY+(height-padY*2)*(1-(Number(point.price)-min)/range);return[x,y]});
    const d=coords.map((p,i)=>`${i?'L':'M'} ${p[0].toFixed(2)} ${p[1].toFixed(2)}`).join(' ');line.setAttribute('d',d);area.setAttribute('d',`${d} L ${coords[coords.length-1][0]} ${height-padY} L ${coords[0][0]} ${height-padY} Z`);
  }
  async function loadAll(silent=false){
    const refresh=$('refreshButton');if(!silent)refresh.classList.add('loading');
    try{
      const [base,history,request,invest]=await Promise.all([
        api('/finance-v114/api/state'),api('/finance-v114/api/history'),api('/finance-v118/api/request'),api('/finance-v127/api/state')
      ]);
      baseState=base;historyState=history;requestState=request;investState=invest;lastInvestmentLoad=Date.now();renderAll();await loadChart(true);
    }catch(error){$('loading').classList.add('hidden');toast(error.message,'error')}
    finally{refresh.classList.remove('loading')}
  }
  async function refreshInvestments(){
    if(document.hidden)return;
    try{investState=await api('/finance-v127/api/state');lastInvestmentLoad=Date.now();updateHeader();renderPlans();renderDeposits();renderMarket();renderHistory();await loadChart(true)}catch(_){/* next poll retries */}
  }
  function updateCountdown(){
    if(!investState)return;const tick=Number(investState.market_tick_seconds)||300;const serverNow=Number(investState.server_time)+(Date.now()-lastInvestmentLoad)/1000;const left=Math.max(0,tick-(Math.floor(serverNow)%tick));$('stockCountdown').textContent=`${Math.floor(left/60)}:${String(Math.floor(left%60)).padStart(2,'0')}`;
  }

  document.addEventListener('click',event=>{
    const nav=event.target.closest('[data-nav]');if(nav){openScreen(nav.dataset.nav);return}
    const quick=event.target.closest('[data-open]');if(quick){openScreen(quick.dataset.open);return}
    const chip=event.target.closest('.chips button[data-value]');if(chip){const wrap=chip.closest('.chips');wrap.querySelectorAll('button').forEach(n=>n.classList.remove('active'));chip.classList.add('active');$(wrap.dataset.chipTarget).value=chip.dataset.value;updatePreviews();return}
    const tab=event.target.closest('[data-loan-tab]');if(tab){document.querySelectorAll('[data-loan-tab]').forEach(n=>n.classList.toggle('active',n===tab));document.querySelectorAll('[data-loan-pane]').forEach(n=>n.classList.toggle('active',n.dataset.loanPane===tab.dataset.loanTab));return}
    const plan=event.target.closest('[data-plan]');if(plan){selectedPlan=plan.dataset.plan;renderPlans();return}
    const ticker=event.target.closest('[data-stock]');if(ticker){selectedStock=ticker.dataset.stock;renderMarket();loadChart(true);return}
    const period=event.target.closest('[data-period]');if(period){selectedPeriod=Number(period.dataset.period);document.querySelectorAll('[data-period]').forEach(n=>n.classList.toggle('active',n===period));loadChart();return}
    const repay=event.target.closest('[data-repay]');if(repay){const loan=(baseState?.debts||[]).find(item=>item.loan_id===repay.dataset.repay);if(!loan)return;const amount=repay.dataset.amount==='all'?loan.remaining:Number(repay.dataset.amount);confirmAction('Погасить долг?',`Кредитору будет переведено ${fmt(amount)} влияния.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'repay',loan_id:loan.loan_id,amount:repay.dataset.amount}}));return}
    const withdraw=event.target.closest('[data-withdraw-deposit]');if(withdraw){const deposit=(investState?.deposits||[]).find(item=>item.deposit_id===withdraw.dataset.withdrawDeposit);if(!deposit)return;confirmAction(deposit.matured?'Забрать вклад?':'Снять досрочно?',`На баланс поступит ${fmt(deposit.payout)} влияния. Условия досрочного закрытия применятся автоматически.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'deposit_withdraw',deposit_id:deposit.deposit_id}}));return}
  });
  ['transferAmount','transferTarget','loanAmount','loanInterest','loanDays','depositAmount','stockQuantity'].forEach(id=>$(id)?.addEventListener('input',updatePreviews));
  $('transferSubmit').addEventListener('click',()=>{const recipient_id=Number($('transferTarget').value),amount=Number($('transferAmount').value);confirmAction('Подтвердить перевод?',`${participantName('transferTarget')} получит ${fmt(amount)} влияния.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'transfer',recipient_id,amount}}))});
  $('loanSubmit').addEventListener('click',()=>{const borrower_id=Number($('loanTarget').value),amount=Number($('loanAmount').value),interest=Number($('loanInterest').value),days=Number($('loanDays').value);confirmAction('Опубликовать договор?',`${participantName('loanTarget')} получит предложение: ${fmt(amount)} под ${interest}% на ${days} дн.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'loan',borrower_id,amount,interest,days}}))});
  $('requestSubmit').addEventListener('click',()=>{const lender_id=Number($('requestTarget').value),amount=Number($('requestAmount').value),interest=Number($('requestInterest').value),days=Number($('requestDays').value);confirmAction('Опубликовать заявку?',`Запросить у ${participantName('requestTarget')} ${fmt(amount)} влияния под ${interest}% на ${days} дн.?`,()=>api('/finance-v118/api/request',{method:'POST',body:{lender_id,amount,interest,days}}))});
  $('depositSubmit').addEventListener('click',()=>{const plan=investState?.plans?.find(item=>item.key===selectedPlan),amount=Number($('depositAmount').value);if(!plan)return;confirmAction('Открыть вклад?',`${fmt(amount)} влияния будут заморожены на тарифе «${plan.title}».`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'deposit_open',plan_key:selectedPlan,amount}}))});
  $('stockBuy').addEventListener('click',()=>{const stock=stockBySymbol(),quantity=Number($('stockQuantity').value);if(!stock)return;confirmAction('Купить акции?',`Купить ${fmt(quantity)} акц. ${stock.symbol} по текущей цене ${fmt(stock.price)}? Комиссия — 1%.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'stock_buy',symbol:stock.symbol,quantity}}))});
  $('stockSell').addEventListener('click',()=>{const stock=stockBySymbol(),quantity=Number($('stockQuantity').value);if(!stock)return;confirmAction('Продать акции?',`Продать ${fmt(quantity)} акц. ${stock.symbol} по текущей цене ${fmt(stock.price)}? Комиссия — 1%.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'stock_sell',symbol:stock.symbol,quantity}}))});
  $('modalCancel').addEventListener('click',()=>{pendingAction=null;$('modal').classList.remove('open');$('modal').setAttribute('aria-hidden','true')});$('modalConfirm').addEventListener('click',runPending);$('refreshButton').addEventListener('click',()=>loadAll());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-lastInvestmentLoad>15000)refreshInvestments()});
  setInterval(updateCountdown,1000);setInterval(refreshInvestments,10000);loadAll();
})();
