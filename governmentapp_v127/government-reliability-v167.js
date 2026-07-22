(()=>{
  'use strict';
  if(window.__governmentReliabilityV167)return;
  window.__governmentReliabilityV167=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||params.get('startapp')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  let state=window.__governmentStateV167||null;
  let refreshing=false;
  let refreshTimer=0;
  let lastContributionKick=0;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__v167Timer);
    node.__v167Timer=setTimeout(()=>node.className='toast',4200);
  }

  function markVersion(){
    const brand=document.querySelector('.brand small');
    if(brand&&brand.textContent!=='REALITY 167')brand.textContent='REALITY 167';
  }

  function refreshButton(){return document.getElementById('refreshButton')}

  function beginRefresh(){
    const button=refreshButton();
    refreshing=true;
    window.__governmentForceNextStateV167=true;
    if(button){button.classList.add('refreshing-v167');button.setAttribute('aria-busy','true');button.disabled=true}
    clearTimeout(refreshTimer);
    refreshTimer=setTimeout(()=>finishRefresh(false),27000);
  }

  function finishRefresh(success=true){
    const button=refreshButton();
    refreshing=false;
    clearTimeout(refreshTimer);
    if(button){button.classList.remove('refreshing-v167');button.removeAttribute('aria-busy');button.disabled=false}
    if(!success)toast('Обновление не завершилось. Показаны последние доступные данные.','error');
  }

  function treasuryActive(){
    return Boolean(document.querySelector('.screen[data-screen="treasury"]')?.classList.contains('active'));
  }

  function ensureContributionPanel(){
    if(!treasuryActive()||document.getElementById('treasuryContributionV150'))return;
    const now=Date.now();
    if(now-lastContributionKick<3500)return;
    lastContributionKick=now;
    const button=refreshButton();
    if(button&&!refreshing)button.click();
  }

  function ensureModal(){
    let modal=document.getElementById('lawAmendmentModalV167');
    if(modal)return modal;
    modal=document.createElement('div');
    modal.id='lawAmendmentModalV167';
    modal.className='law-amendment-modal-v167';
    modal.hidden=true;
    modal.innerHTML=`<section class="law-amendment-sheet-v167">
      <div class="law-amendment-head-v167"><div><small>ПРЕЗИДЕНТСКАЯ ПОПРАВКА</small><h3 id="lawAmendmentHeadingV167">Новая редакция закона</h3></div><button type="button" data-law-amend-close>×</button></div>
      <form id="lawAmendmentFormV167">
        <input type="hidden" name="law_id">
        <div class="field"><label>НОВОЕ НАЗВАНИЕ</label><input name="new_title" minlength="5" maxlength="120" required></div>
        <div class="field"><label>НОВАЯ РЕДАКЦИЯ</label><textarea name="new_text" minlength="10" maxlength="1200" required></textarea></div>
        <div class="field"><label>ОБОСНОВАНИЕ ИЗМЕНЕНИЙ</label><textarea name="reason" minlength="10" maxlength="1200" placeholder="Почему действующий текст нужно изменить" required></textarea></div>
        <p class="hint">Поправка не вступает в силу сразу: депутаты голосуют, затем президент подписывает документ. Для специальных законов меняется формулировка, а ставки и суммы — отдельным профильным законом.</p>
        <button class="action wide" type="submit">🏛 ПЕРЕДАТЬ НОВУЮ РЕДАКЦИЮ В ГОСДУМУ</button>
      </form>
    </section>`;
    document.body.appendChild(modal);
    return modal;
  }

  function openLawModal(lawId){
    const law=(state?.laws||[]).find(item=>String(item.law_id)===String(lawId));
    if(!law)return toast('Закон не найден в текущем состоянии. Обнови страницу.','error');
    const modal=ensureModal();
    const form=modal.querySelector('form');
    form.elements.law_id.value=String(law.law_id||'');
    form.elements.new_title.value=String(law.title||'');
    form.elements.new_text.value=String(law.text||'');
    form.elements.reason.value='';
    const heading=modal.querySelector('#lawAmendmentHeadingV167');
    if(heading)heading.textContent=`Новая редакция закона №${Number(law.number)||''}`;
    modal.hidden=false;
    requestAnimationFrame(()=>modal.classList.add('open'));
  }

  function closeLawModal(){
    const modal=document.getElementById('lawAmendmentModalV167');
    if(!modal)return;
    modal.classList.remove('open');
    setTimeout(()=>{modal.hidden=true},180);
  }

  function patchLawCards(){
    markVersion();
    if(!state?.permissions?.can_amend_laws)return;
    const cards=[...document.querySelectorAll('#lawList .law-card')];
    const laws=Array.isArray(state.laws)?state.laws:[];
    cards.forEach((card,index)=>{
      const law=laws[index];
      if(!law?.can_amend||card.querySelector('[data-law-amend]'))return;
      const footer=document.createElement('div');
      footer.className='law-amend-actions-v167';
      footer.innerHTML=`<button class="action wide" type="button" data-law-amend="${esc(law.law_id)}">✍️ ПРЕДЛОЖИТЬ НОВУЮ РЕДАКЦИЮ</button>${Number(law.revision_count)>0?`<small>Редакций принято: ${Number(law.revision_count)}</small>`:''}`;
      card.appendChild(footer);
    });
  }

  async function submitAmendment(form){
    const data=Object.fromEntries(new FormData(form).entries());
    const button=form.querySelector('button[type="submit"]');
    if(button)button.disabled=true;
    try{
      const response=await fetch('/government-v127/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({
          action:'create_bill',chat_id:chatId,bill_type:'law_amendment',
          title:'Новая редакция действующего закона',
          description:String(data.reason||''),
          payload:{law_id:String(data.law_id||''),new_title:String(data.new_title||''),new_text:String(data.new_text||'')}
        })
      });
      const result=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!result.ok)throw new Error(result.reason||'Поправка не создана.');
      closeLawModal();
      toast('Новая редакция закона передана в Госдуму.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      setTimeout(()=>{
        const duma=document.querySelector('[data-tab="duma"]');
        if(duma)duma.click();
        const refresh=refreshButton();
        if(refresh)refresh.click();
      },220);
    }catch(error){
      toast(error.message||'Поправка не создана.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{if(button)button.disabled=false}
  }

  document.addEventListener('government:state',event=>{
    state=event.detail||state;
    finishRefresh(true);
    markVersion();
    setTimeout(patchLawCards,80);
    setTimeout(()=>{if(treasuryActive())ensureContributionPanel()},160);
  });
  document.addEventListener('government:state-stale',()=>toast('Сервер отвечает медленно — показаны последние полученные данные.','error'));

  document.addEventListener('click',event=>{
    const refresh=event.target.closest?.('#refreshButton');
    if(refresh){beginRefresh();return}
    const treasury=event.target.closest?.('[data-tab="treasury"]');
    if(treasury)setTimeout(ensureContributionPanel,280);
    const laws=event.target.closest?.('[data-tab="laws"]');
    if(laws)setTimeout(patchLawCards,80);
    const amend=event.target.closest?.('[data-law-amend]');
    if(amend){event.preventDefault();openLawModal(amend.dataset.lawAmend);return}
    if(event.target.closest?.('[data-law-amend-close]')){closeLawModal();return}
    const modal=event.target.closest?.('#lawAmendmentModalV167');
    if(modal&&event.target===modal)closeLawModal();
  },true);

  document.addEventListener('submit',event=>{
    if(event.target.id!=='lawAmendmentFormV167')return;
    event.preventDefault();
    event.stopImmediatePropagation();
    submitAmendment(event.target);
  },true);

  document.addEventListener('keydown',event=>{if(event.key==='Escape')closeLawModal()});
  markVersion();
  ensureModal();
  if(state){setTimeout(patchLawCards,80);setTimeout(ensureContributionPanel,220)}
})();
