  function smoothPath(coords){
    if(!coords.length)return'';
    if(coords.length===1)return`M ${coords[0].x} ${coords[0].y}`;
    let path=`M ${coords[0].x.toFixed(2)} ${coords[0].y.toFixed(2)}`;
    for(let index=0;index<coords.length-1;index++){
      const p0=coords[Math.max(0,index-1)],p1=coords[index],p2=coords[index+1],p3=coords[Math.min(coords.length-1,index+2)];
      const cp1x=p1.x+(p2.x-p0.x)/6,cp1y=p1.y+(p2.y-p0.y)/6;
      const cp2x=p2.x-(p3.x-p1.x)/6,cp2y=p2.y-(p3.y-p1.y)/6;
      path+=` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
    }
    return path;
  }
  function nearestPointByTime(points,time){
    let best=0,distance=Infinity;
    for(let index=0;index<points.length;index++){
      const current=Math.abs(Number(points[index].time)-Number(time));
      if(current<distance){distance=current;best=index}
    }
    return best;
  }
  function resetChartInspector(){
    lastChartIndex=-1;$('chartInspector').classList.remove('visible');$('chartInspector').setAttribute('aria-hidden','true');
    $('chartCrosshair').style.display='none';$('chartPoint').style.display='none';$('chartPriceTag').style.display='none';$('chartWrap').classList.remove('interacting');
  }
  function drawChart(points,events=[]){
    const emptyNode=$('chartEmpty'),line=$('chartLine'),area=$('chartArea'),grid=$('chartGrid'),markers=$('chartEventMarkers');
    grid.innerHTML='';markers.innerHTML='';resetChartInspector();
    if(!points.length){line.setAttribute('d','');area.setAttribute('d','');emptyNode.textContent='Недостаточно данных для периода';emptyNode.style.display='grid';return}
    emptyNode.style.display='none';
    const width=640,height=300,padX=16,padTop=20,padBottom=42,priceBottom=238;
    const prices=points.map(point=>Number(point.price));let min=Math.min(...prices),max=Math.max(...prices);if(min===max){min-=1;max+=1}const range=max-min;
    const maxVolume=Math.max(1,...points.map(point=>Number(point.volume)||0));
    for(let index=1;index<5;index++){
      const y=padTop+(priceBottom-padTop)*index/5;const path=document.createElementNS('http://www.w3.org/2000/svg','path');
      path.setAttribute('d',`M ${padX} ${y} H ${width-padX}`);path.setAttribute('stroke','#4b3860');path.setAttribute('stroke-opacity','.28');path.setAttribute('stroke-width','1');grid.appendChild(path);
    }
    const coords=points.map((point,index)=>{
      const x=padX+(width-padX*2)*(points.length===1?0:index/(points.length-1));
      const y=padTop+(priceBottom-padTop)*(1-(Number(point.price)-min)/range);
      return{x,y,point,index};
    });
    const barWidth=Math.max(1,Math.min(5,(width-padX*2)/Math.max(1,points.length)*.72));
    for(let index=0;index<coords.length;index++){
      const coord=coords[index],volume=Number(coord.point.volume)||0,barHeight=Math.max(1,30*volume/maxVolume);const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
      rect.setAttribute('x',(coord.x-barWidth/2).toFixed(2));rect.setAttribute('y',(height-9-barHeight).toFixed(2));rect.setAttribute('width',barWidth.toFixed(2));rect.setAttribute('height',barHeight.toFixed(2));rect.setAttribute('rx','1');
      const previous=index?Number(points[index-1].price):Number(points[index].price);rect.setAttribute('fill',Number(coord.point.price)>=previous?'#56c98e':'#ff617f');rect.setAttribute('fill-opacity','.52');grid.appendChild(rect);
    }
    const path=smoothPath(coords),trend=Number(points.at(-1).price)>=Number(points[0].price),stroke=trend?'#d394ff':'#ff718f';
    line.setAttribute('d',path);line.setAttribute('stroke',stroke);area.setAttribute('fill',trend?'url(#chartFillUp)':'url(#chartFillDown)');area.setAttribute('d',`${path} L ${coords.at(-1).x.toFixed(2)} ${priceBottom} L ${coords[0].x.toFixed(2)} ${priceBottom} Z`);

    const eventCoords=[];
    for(const item of events){
      const pointIndex=nearestPointByTime(points,item.event_at);const coord=coords[pointIndex];
      if(!coord||Math.abs(Number(points[pointIndex].time)-Number(item.event_at))>Math.max(300,selectedPeriod/80))continue;
      const group=document.createElementNS('http://www.w3.org/2000/svg','g');const negative=Number(item.effect_bp)<0;const government=String(item.source_type||'').startsWith('government');
      group.setAttribute('class',`chart-event-marker ${government?'government':''} ${negative?'negative':''}`);group.setAttribute('transform',`translate(${coord.x.toFixed(2)} ${(coord.y-18).toFixed(2)})`);
      const circle=document.createElementNS('http://www.w3.org/2000/svg','circle');circle.setAttribute('r','11');
      const text=document.createElementNS('http://www.w3.org/2000/svg','text');text.setAttribute('x','0');text.setAttribute('y','5');text.setAttribute('text-anchor','middle');text.textContent=government?'🏛':'📰';
      group.append(circle,text);markers.appendChild(group);eventCoords.push({x:coord.x,y:coord.y-18,item});
    }
    chartModel={points,coords,events,eventCoords,width,height,padX,padTop,padBottom};
    $('stockLow').textContent=fmt(Math.min(...prices));$('stockHigh').textContent=fmt(Math.max(...prices));$('stockVolume').textContent=fmt(points.reduce((sum,point)=>sum+(Number(point.volume)||0),0));
  }
  function chartIndexFromClient(clientX){
    const rect=$('stockChart').getBoundingClientRect();const svgX=Math.max(0,Math.min(chartModel.width,(clientX-rect.left)/Math.max(1,rect.width)*chartModel.width));
    const ratio=(svgX-chartModel.padX)/Math.max(1,chartModel.width-chartModel.padX*2);return Math.max(0,Math.min(chartModel.points.length-1,Math.round(ratio*(chartModel.points.length-1))));
  }
  function showChartPoint(index,haptic=true){
    const coord=chartModel.coords[index],point=chartModel.points[index];if(!coord||!point)return;
    const first=Number(chartModel.points[0].price)||1,change=(Number(point.price)-first)*100/first;
    $('chartCrosshair').setAttribute('x1',coord.x);$('chartCrosshair').setAttribute('x2',coord.x);$('chartCrosshair').style.display='block';
    $('chartPoint').setAttribute('cx',coord.x);$('chartPoint').setAttribute('cy',coord.y);$('chartPoint').style.display='block';
    const tagX=Math.max(43,Math.min(chartModel.width-43,coord.x)),tagY=Math.max(4,coord.y-48);$('chartPriceTag').setAttribute('transform',`translate(${tagX-41} ${tagY})`);$('chartPriceTagText').textContent=fmt(point.price);$('chartPriceTag').style.display='block';
    $('inspectPrice').textContent=fmt(point.price);const changeNode=$('inspectChange');changeNode.textContent=`${change>=0?'+':''}${fmt(change)}%`;changeNode.className=change>=0?'positive':'negative';$('inspectTime').textContent=dateTime(point.time);$('inspectVolume').textContent=fmt(point.volume||0);
    $('chartInspector').classList.add('visible');$('chartInspector').setAttribute('aria-hidden','false');$('chartWrap').classList.add('interacting');
    if(haptic&&lastChartIndex!==index&&Math.abs(lastChartIndex-index)>1)tg?.HapticFeedback?.selectionChanged?.();lastChartIndex=index;
  }
  function nearestEventAtClient(clientX){
    const rect=$('stockChart').getBoundingClientRect(),svgX=(clientX-rect.left)/Math.max(1,rect.width)*chartModel.width;
    let best=null,distance=Infinity;for(const event of chartModel.eventCoords){const current=Math.abs(event.x-svgX);if(current<distance){distance=current;best=event}}
    return distance<=18?best:null;
  }
  function pointerDown(event){
    if(!chartModel.points.length)return;chartInteracting=true;pointerMoved=false;pointerStartX=event.clientX;$('chartHitArea').setPointerCapture?.(event.pointerId);showChartPoint(chartIndexFromClient(event.clientX));event.preventDefault();
  }
  function pointerMove(event){
    if(!chartInteracting)return;if(Math.abs(event.clientX-pointerStartX)>5)pointerMoved=true;showChartPoint(chartIndexFromClient(event.clientX));event.preventDefault();
  }
  function pointerUp(event){
    if(!chartInteracting)return;showChartPoint(chartIndexFromClient(event.clientX),false);const marker=nearestEventAtClient(event.clientX);chartInteracting=false;$('chartHitArea').releasePointerCapture?.(event.pointerId);if(marker&&!pointerMoved){openNews(marker.item.news_id);tg?.HapticFeedback?.impactOccurred?.('light')}event.preventDefault();
  }
  async function loadChart(silent=false){
    try{
      chartState=await api(`/finance-v127/api/chart?symbol=${encodeURIComponent(selectedStock)}&period=${selectedPeriod}`);drawChart(chartState.history||[],chartState.events||[]);
    }catch(error){$('chartEmpty').textContent=error.message;$('chartEmpty').style.display='grid';if(!silent)toast(error.message,'error')}
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
    if(document.hidden||chartInteracting)return;
    try{investState=await api('/finance-v127/api/state');lastInvestmentLoad=Date.now();updateHeader();renderPlans();renderDeposits();renderMarket();renderHistory();await loadChart(true)}catch(_){/* Следующий опрос повторит попытку. */}
  }
  function updateCountdown(){
    if(!investState)return;const tick=Number(investState.market_tick_seconds)||60;const serverNow=Number(investState.server_time)+(Date.now()-lastInvestmentLoad)/1000;const left=Math.max(0,tick-(Math.floor(serverNow)%tick));$('stockCountdown').textContent=tick<=60?`${Math.max(0,Math.ceil(left))} сек.`:`${Math.floor(left/60)}:${String(Math.floor(left%60)).padStart(2,'0')}`;
  }

  document.addEventListener('click',event=>{
    const newsTarget=event.target.closest('[data-news-id]');if(newsTarget){openNews(newsTarget.dataset.newsId);return}
    const nav=event.target.closest('[data-nav]');if(nav){openScreen(nav.dataset.nav);return}
    const quick=event.target.closest('[data-open]');if(quick){openScreen(quick.dataset.open);return}
    const chip=event.target.closest('.chips button[data-value]');if(chip){const wrap=chip.closest('.chips');wrap.querySelectorAll('button').forEach(node=>node.classList.remove('active'));chip.classList.add('active');$(wrap.dataset.chipTarget).value=chip.dataset.value;updatePreviews();return}
    const tab=event.target.closest('[data-loan-tab]');if(tab){document.querySelectorAll('[data-loan-tab]').forEach(node=>node.classList.toggle('active',node===tab));document.querySelectorAll('[data-loan-pane]').forEach(node=>node.classList.toggle('active',node.dataset.loanPane===tab.dataset.loanTab));return}
    const plan=event.target.closest('[data-plan]');if(plan){selectedPlan=plan.dataset.plan;renderPlans();return}
    const ticker=event.target.closest('[data-stock]');if(ticker){selectedStock=ticker.dataset.stock;resetChartInspector();renderMarket();loadChart(true);return}
    const period=event.target.closest('[data-period]');if(period){selectedPeriod=Number(period.dataset.period);document.querySelectorAll('[data-period]').forEach(node=>node.classList.toggle('active',node===period));resetChartInspector();loadChart();return}
    const repay=event.target.closest('[data-repay]');if(repay){const loan=(baseState?.debts||[]).find(item=>item.loan_id===repay.dataset.repay);if(!loan)return;const amount=repay.dataset.amount==='all'?loan.remaining:Number(repay.dataset.amount);confirmAction('Погасить долг?',`Кредитору будет переведено ${fmt(amount)} влияния.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'repay',loan_id:loan.loan_id,amount:repay.dataset.amount}}));return}
    const withdraw=event.target.closest('[data-withdraw-deposit]');if(withdraw){const deposit=(investState?.deposits||[]).find(item=>item.deposit_id===withdraw.dataset.withdrawDeposit);if(!deposit)return;confirmAction(deposit.matured?'Забрать вклад?':'Снять досрочно?',`На баланс поступит ${fmt(deposit.withdraw_payout??deposit.payout)} влияния. Условия досрочного закрытия применятся автоматически.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'deposit_withdraw',deposit_id:deposit.deposit_id}}));return}
  });
  ['transferAmount','transferTarget','loanAmount','loanInterest','loanDays','depositAmount','stockQuantity'].forEach(id=>$(id)?.addEventListener('input',updatePreviews));
  $('transferSubmit').addEventListener('click',()=>{const recipient_id=Number($('transferTarget').value),amount=Number($('transferAmount').value);confirmAction('Подтвердить перевод?',`${participantName('transferTarget')} получит ${fmt(amount)} влияния.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'transfer',recipient_id,amount}}))});
  $('loanSubmit').addEventListener('click',()=>{const borrower_id=Number($('loanTarget').value),amount=Number($('loanAmount').value),interest=Number($('loanInterest').value),days=Number($('loanDays').value);confirmAction('Опубликовать договор?',`${participantName('loanTarget')} получит предложение: ${fmt(amount)} под ${interest}% на ${days} дн.`,()=>api('/finance-v114/api/action',{method:'POST',body:{action:'loan',borrower_id,amount,interest,days}}))});
  $('requestSubmit').addEventListener('click',()=>{const lender_id=Number($('requestTarget').value),amount=Number($('requestAmount').value),interest=Number($('requestInterest').value),days=Number($('requestDays').value);confirmAction('Опубликовать заявку?',`Запросить у ${participantName('requestTarget')} ${fmt(amount)} влияния под ${interest}% на ${days} дн.?`,()=>api('/finance-v118/api/request',{method:'POST',body:{lender_id,amount,interest,days}}))});
  $('depositSubmit').addEventListener('click',()=>{const plan=investState?.plans?.find(item=>item.key===selectedPlan),amount=Number($('depositAmount').value);if(!plan)return;confirmAction('Открыть вклад?',`${fmt(amount)} влияния будут заморожены на тарифе «${plan.title}».`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'deposit_open',plan_key:selectedPlan,amount}}))});
  $('stockBuy').addEventListener('click',()=>{const stock=stockBySymbol(),quantity=Number($('stockQuantity').value);if(!stock)return;confirmAction('Купить акции?',`Купить ${fmt(quantity)} акц. ${stock.symbol} по текущей цене ${fmt(stock.price)}? Комиссия — 1%.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'stock_buy',symbol:stock.symbol,quantity}}))});
  $('stockSell').addEventListener('click',()=>{const stock=stockBySymbol(),quantity=Number($('stockQuantity').value);if(!stock)return;confirmAction('Продать акции?',`Продать ${fmt(quantity)} акц. ${stock.symbol} по текущей цене ${fmt(stock.price)}? Комиссия — 1%.`,()=>api('/finance-v127/api/action',{method:'POST',body:{action:'stock_sell',symbol:stock.symbol,quantity}}))});
  $('modalCancel').addEventListener('click',()=>{pendingAction=null;$('modal').classList.remove('open');$('modal').setAttribute('aria-hidden','true')});$('modalConfirm').addEventListener('click',runPending);$('refreshButton').addEventListener('click',()=>loadAll());
  $('newsClose').addEventListener('click',closeNews);$('newsDone').addEventListener('click',closeNews);$('newsModal').addEventListener('click',event=>{if(event.target===$('newsModal'))closeNews()});
  $('chartHitArea').addEventListener('pointerdown',pointerDown);$('chartHitArea').addEventListener('pointermove',pointerMove);$('chartHitArea').addEventListener('pointerup',pointerUp);$('chartHitArea').addEventListener('pointercancel',()=>{chartInteracting=false});
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&Date.now()-lastInvestmentLoad>15000)refreshInvestments()});
  setInterval(updateCountdown,1000);setInterval(refreshInvestments,10000);loadAll();
})();
