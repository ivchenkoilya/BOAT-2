(()=>{
  'use strict';
  if(window.__governmentMandatesV143)return;
  window.__governmentMandatesV143=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  const esc=value=>String(value??'').replace(/[&<>'"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const fmt=value=>new Intl.NumberFormat('ru-RU').format(Number(value)||0);
  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'—';
  let snapshot=null;
  let activeMandate=null;
  let drawing=false;
  let hasInk=false;
  let lawRenderBusy=false;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__v143Timer);
    node.__v143Timer=setTimeout(()=>node.className='toast',3900);
  }

  function ensureUi(){
    const brand=document.querySelector('.brand small');
    if(brand)brand.textContent='REALITY 143';

    const nav=document.getElementById('bottomNav');
    if(nav&&!nav.querySelector('[data-tab="mandates"]')){
      const button=document.createElement('button');
      button.dataset.tab='mandates';
      button.innerHTML='<span>📜</span><small>Мандаты</small>';
      const laws=nav.querySelector('[data-tab="laws"]');
      laws?.insertAdjacentElement('afterend',button);
    }

    const stack=document.querySelector('.screen-stack');
    if(stack&&!stack.querySelector('[data-screen="mandates"]')){
      const section=document.createElement('section');
      section.className='screen';
      section.dataset.screen='mandates';
      section.innerHTML=`
        <div class="section-head"><div><small>ГОСУДАРСТВЕННЫЙ РЕЕСТР</small><h2>Мои мандаты</h2></div></div>
        <div id="mandateCurrent"></div>
        <article class="panel mandate-command-help">
          <div class="panel-title"><span>📣</span><div><b>Предъявление в беседе</b><small>Покажи полномочия и проверь подлинность документа</small></div></div>
          <code>/mandate</code><span> — свой мандат</span><br>
          <code>/mandate @username</code><span> — мандат другого участника</span>
        </article>
        <div class="section-head"><div><small>ИСТОРИЯ ВЛАСТИ</small><h2>Архив мандатов</h2></div></div>
        <div id="mandateArchive"></div>`;
      stack.appendChild(section);
    }

    const lawsScreen=document.querySelector('[data-screen="laws"]');
    if(lawsScreen&&!document.getElementById('foundationLawList')){
      const block=document.createElement('div');
      block.id='foundationLawsBlock';
      block.innerHTML=`
        <div class="section-head foundation-head"><div><small>НЕИЗМЕННАЯ ОСНОВА</small><h2>Основные законы государства</h2></div></div>
        <div id="foundationLawList"></div>
        <div class="section-head"><div><small>ПРИНЯТЫ ГОСДУМОЙ</small><h2>Новые действующие законы</h2></div></div>`;
      const lawList=document.getElementById('lawList');
      lawList?.insertAdjacentElement('beforebegin',block);
    }

    if(!document.getElementById('mandateModalV143')){
      document.body.insertAdjacentHTML('beforeend',`
        <div class="v143-modal" id="mandateModalV143" hidden>
          <section class="v143-sheet mandate-sheet">
            <button class="v143-close" data-v143-close="mandate">×</button>
            <div id="mandateDocumentV143"></div>
          </section>
        </div>
        <div class="v143-modal" id="lawModalV143" hidden>
          <section class="v143-sheet law-sheet-v143">
            <button class="v143-close" data-v143-close="law">×</button>
            <div id="lawDocumentV143"></div>
          </section>
        </div>`);
    }
    return Boolean(document.getElementById('mandateCurrent'));
  }

  async function fetchState(){
    if(!chatId)return;
    ensureUi();
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{cache:'no-store',headers});
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось загрузить государственный реестр.');
      snapshot=data;
      renderMandates();
      renderLaws();
    }catch(error){
      toast(error?.message||'Не удалось загрузить мандаты.','error');
    }
  }

  function statusBadge(item){
    const map={
      available:['gold','ДОСТУПЕН'],
      active:['green','ДЕЙСТВУЕТ'],
      expired:['','СРОК ЗАВЕРШЁН'],
      annulled:['red','АННУЛИРОВАН']
    };
    const value=map[item.status]||['',String(item.status||'')];
    return `<span class="badge ${value[0]}">${value[1]}</span>`;
  }

  function powersHtml(powers){
    return `<ul class="mandate-power-list">${(powers||[]).map(item=>`<li>${esc(item)}</li>`).join('')}</ul>`;
  }

  function mandateCard(item){
    const seat=Number(item.seat_no)>1?` · место ${fmt(item.seat_no)}`:'';
    const action=item.can_claim
      ?`<button class="action wide" data-claim-mandate data-office="${esc(item.office_key)}" data-seat="${Number(item.seat_no)||1}">✍️ ПОЛУЧИТЬ И ПОДПИСАТЬ МАНДАТ</button>`
      :`<button class="secondary wide" data-open-mandate="${esc(item.mandate_id)}">📜 ОТКРЫТЬ ДОКУМЕНТ</button>`;
    return `<article class="mandate-card-v143 ${esc(item.status)}">
      <div class="card-head"><div><b>${esc(item.emoji)} ${esc(item.office_title)}${seat}</b><small>Telegram ID ${Number(item.user_id)} · ${date(item.starts_at)} — ${date(item.ends_at)}</small></div>${statusBadge(item)}</div>
      ${item.mandate_no?`<div class="mandate-code-line"><span>Мандат №${String(Number(item.mandate_no)).padStart(6,'0')}</span><code>${esc(item.verification_code)}</code></div>`:'<p class="hint">Полномочия уже действуют, но официальный документ ещё не подписан.</p>'}
      ${action}
    </article>`;
  }

  function renderMandates(){
    if(!snapshot||!ensureUi())return;
    const list=Array.isArray(snapshot.mandates)?snapshot.mandates:[];
    const current=list.filter(item=>['available','active'].includes(item.status));
    const archive=list.filter(item=>['expired','annulled'].includes(item.status));
    const currentNode=document.getElementById('mandateCurrent');
    const archiveNode=document.getElementById('mandateArchive');
    if(currentNode)currentNode.innerHTML=current.length?current.map(mandateCard).join(''):'<div class="empty">У тебя сейчас нет государственной должности и доступного мандата.</div>';
    if(archiveNode)archiveNode.innerHTML=archive.length?archive.map(mandateCard).join(''):'<div class="empty">Архив пока пуст.</div>';
  }

  function lawMiniCard(law,foundation=false){
    const number=Number(law.number)||0;
    const meta=foundation
      ?'<span class="badge gold">ОСНОВНОЙ</span>'
      :'<span class="badge green">ДЕЙСТВУЕТ</span>';
    const summary=foundation?law.summary:(law.text||'');
    return `<article class="law-mini-v143">
      <div class="card-head"><div><b>⚖️ Закон №${number}</b><small>${foundation?'Основной закон · действует с основания государства':`Принят ${date(law.enacted_at)}`}</small></div>${meta}</div>
      <h3>${esc(law.title)}</h3>
      <p>${esc(String(summary||'').slice(0,170))}${String(summary||'').length>170?'…':''}</p>
      <button class="secondary wide" data-open-law="${foundation?'foundation':'regular'}:${foundation?number:esc(law.law_id)}">ОТКРЫТЬ ПОЛНЫЙ ТЕКСТ</button>
    </article>`;
  }

  function renderLaws(){
    if(!snapshot||lawRenderBusy||!ensureUi())return;
    lawRenderBusy=true;
    const foundation=Array.isArray(snapshot.foundation_laws)?snapshot.foundation_laws:[];
    const regular=Array.isArray(snapshot.laws)?snapshot.laws:[];
    const foundationNode=document.getElementById('foundationLawList');
    const lawList=document.getElementById('lawList');
    if(foundationNode)foundationNode.innerHTML=foundation.map(law=>lawMiniCard(law,true)).join('');
    if(lawList){
      lawList.dataset.v143='1';
      lawList.innerHTML=regular.length?regular.map(law=>lawMiniCard(law,false)).join(''):'<div class="empty">Новых законов, принятых Госдумой, пока нет.</div>';
    }
    queueMicrotask(()=>{lawRenderBusy=false;});
  }

  function findMandate(id){
    return (snapshot?.mandates||[]).find(item=>String(item.mandate_id)===String(id));
  }

  function openMandate(item,signing=false){
    if(!item)return;
    activeMandate=item;
    const modal=document.getElementById('mandateModalV143');
    const host=document.getElementById('mandateDocumentV143');
    if(!modal||!host)return;
    const number=item.mandate_no?String(Number(item.mandate_no)).padStart(6,'0'):'БУДЕТ ПРИСВОЕН ПОСЛЕ ПОДПИСИ';
    const signature=signing
      ?`<div class="signature-zone-v143"><label>ЭЛЕКТРОННАЯ ПОДПИСЬ ВЛАДЕЛЬЦА</label><canvas id="signatureCanvasV143" width="1000" height="300"></canvas><div class="signature-actions"><button class="secondary" data-clear-signature>ОЧИСТИТЬ</button><button class="positive" data-submit-signature>ПОДПИСАТЬ И ПОЛУЧИТЬ</button></div><small>Поставь подпись пальцем внутри поля. Она является игровой электронной подписью.</small></div>`
      :`<div class="signature-preview-v143"><small>ПОДПИСЬ ВЛАДЕЛЬЦА</small>${item.signature_data?`<img src="${item.signature_data}" alt="Электронная подпись">`:'<b>Подпись подтверждена реестром</b>'}</div>`;
    host.innerHTML=`
      <div class="mandate-document-v143">
        <div class="mandate-seal-v143">🏛</div>
        <small class="mandate-kicker-v143">ГОСУДАРСТВО РЕАЛЬНОСТИ · СИСТЕМА «ГЛАВНЫЙ ГЕРОЙ»</small>
        <h2>ГОСУДАРСТВЕННЫЙ МАНДАТ</h2>
        <div class="mandate-number-v143">№ ${number}</div>
        <div class="mandate-fields-v143">
          <div><small>ВЛАДЕЛЕЦ</small><b>Telegram ID ${Number(item.user_id)}</b></div>
          <div><small>ДОЛЖНОСТЬ</small><b>${esc(item.emoji)} ${esc(item.office_title)}</b></div>
          <div><small>НАЧАЛО ПОЛНОМОЧИЙ</small><b>${date(item.starts_at)}</b></div>
          <div><small>ОКОНЧАНИЕ ПОЛНОМОЧИЙ</small><b>${date(item.ends_at)}</b></div>
          <div><small>СТАТУС</small><b>${esc(item.status_title||item.status)}</b></div>
          <div><small>КОД ПРОВЕРКИ</small><b>${esc(item.verification_code||'будет создан после подписи')}</b></div>
        </div>
        <div class="mandate-rights-v143"><h3>Полномочия владельца</h3>${powersHtml(item.powers)}</div>
        <div class="mandate-law-v143"><b>⚖️ Закон Реальности №1 «О честной государственной власти»</b><p>Настоящий мандат подтверждает, что указанные полномочия получены через установленную системой процедуру, принадлежат только указанному Telegram ID и действуют исключительно в пределах срока и должности.</p></div>
        ${signature}
        <div class="mandate-stamp-v143">ПОДЛИННОСТЬ ПОДТВЕРЖДЕНА<br>ГОСУДАРСТВЕННЫМ РЕЕСТРОМ</div>
      </div>`;
    modal.hidden=false;
    document.body.classList.add('v143-modal-open');
    if(signing)installCanvas();
  }

  function installCanvas(){
    const canvas=document.getElementById('signatureCanvasV143');
    if(!canvas)return;
    const ctx=canvas.getContext('2d');
    ctx.lineWidth=8;
    ctx.lineCap='round';
    ctx.lineJoin='round';
    ctx.strokeStyle='#20160b';
    hasInk=false;
    const point=event=>{
      const rect=canvas.getBoundingClientRect();
      const source=event.touches?.[0]||event;
      return {x:(source.clientX-rect.left)*(canvas.width/rect.width),y:(source.clientY-rect.top)*(canvas.height/rect.height)};
    };
    const startDraw=event=>{event.preventDefault();drawing=true;const p=point(event);ctx.beginPath();ctx.moveTo(p.x,p.y);};
    const moveDraw=event=>{if(!drawing)return;event.preventDefault();const p=point(event);ctx.lineTo(p.x,p.y);ctx.stroke();hasInk=true;};
    const endDraw=()=>{drawing=false;ctx.closePath();};
    canvas.addEventListener('pointerdown',startDraw);
    canvas.addEventListener('pointermove',moveDraw);
    canvas.addEventListener('pointerup',endDraw);
    canvas.addEventListener('pointercancel',endDraw);
    canvas.addEventListener('pointerleave',endDraw);
  }

  async function submitSignature(){
    const canvas=document.getElementById('signatureCanvasV143');
    if(!canvas||!activeMandate||!hasInk){toast('Сначала поставь подпись пальцем.','error');return;}
    const button=document.querySelector('[data-submit-signature]');
    if(button){button.disabled=true;button.textContent='⏳ ОФОРМЛЯЕМ МАНДАТ...';}
    try{
      const response=await fetch('/government-v143/api/action',{
        method:'POST',cache:'no-store',headers,
        body:JSON.stringify({
          action:'mandate_sign',chat_id:chatId,
          office_key:activeMandate.office_key,
          seat_no:Number(activeMandate.seat_no)||1,
          signature_data:canvas.toDataURL('image/png')
        })
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Мандат не оформлен.');
      toast(data.message||'Мандат подписан.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      closeModal('mandate');
      await fetchState();
    }catch(error){
      toast(error?.message||'Мандат не оформлен.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      if(button){button.disabled=false;button.textContent='ПОДПИСАТЬ И ПОЛУЧИТЬ';}
    }
  }

  function openLaw(token){
    const [kind,id]=String(token||'').split(':');
    let law=null;
    let foundation=false;
    if(kind==='foundation'){
      foundation=true;
      law=(snapshot?.foundation_laws||[]).find(item=>Number(item.number)===Number(id));
    }else law=(snapshot?.laws||[]).find(item=>String(item.law_id)===String(id));
    if(!law)return;
    const modal=document.getElementById('lawModalV143');
    const host=document.getElementById('lawDocumentV143');
    const votes=law.votes||{};
    host.innerHTML=`
      <article class="law-document-v143">
        <small>${foundation?'ОСНОВНОЙ СВОД ГОСУДАРСТВА':'ДЕЙСТВУЮЩИЙ ЗАКОН ГОСДУМЫ'}</small>
        <h2>⚖️ ЗАКОН РЕАЛЬНОСТИ №${Number(law.number)}</h2>
        <h3>«${esc(law.title)}»</h3>
        <div class="law-status-v143"><span class="badge ${foundation?'gold':'green'}">${foundation?'ОСНОВНОЙ':'ДЕЙСТВУЕТ'}</span></div>
        <div class="law-full-text-v143">${esc(law.text).replace(/\n/g,'<br>')}</div>
        ${foundation?`<div class="law-meta-v143"><b>Основание:</b> действует с момента основания государства.<br><b>Режим:</b> защищённый основной закон.</div>`:`<div class="law-meta-v143"><b>Автор:</b> Telegram ID ${Number(law.author_id)||0}<br><b>Голосование:</b> ${Number(votes.yes)||0} за · ${Number(votes.no)||0} против · ${Number(votes.abstain)||0} воздержались<br><b>Подписал:</b> Telegram ID ${Number(law.signed_by)||0}<br><b>Вступил в силу:</b> ${date(law.enacted_at)}</div>`}
      </article>`;
    modal.hidden=false;
    document.body.classList.add('v143-modal-open');
  }

  function closeModal(type){
    const id=type==='law'?'lawModalV143':'mandateModalV143';
    const modal=document.getElementById(id);
    if(modal)modal.hidden=true;
    if(!document.querySelector('.v143-modal:not([hidden])'))document.body.classList.remove('v143-modal-open');
    activeMandate=null;drawing=false;hasInk=false;
  }

  document.addEventListener('click',event=>{
    const claim=event.target.closest('[data-claim-mandate]');
    if(claim){
      const item=(snapshot?.mandates||[]).find(row=>row.can_claim&&row.office_key===claim.dataset.office&&Number(row.seat_no)===Number(claim.dataset.seat));
      openMandate(item,true);return;
    }
    const open=event.target.closest('[data-open-mandate]');
    if(open){openMandate(findMandate(open.dataset.openMandate),false);return;}
    const law=event.target.closest('[data-open-law]');
    if(law){openLaw(law.dataset.openLaw);return;}
    const close=event.target.closest('[data-v143-close]');
    if(close){closeModal(close.dataset.v143Close);return;}
    if(event.target.matches('.v143-modal')){closeModal(event.target.id==='lawModalV143'?'law':'mandate');return;}
    if(event.target.closest('[data-clear-signature]')){
      const canvas=document.getElementById('signatureCanvasV143');
      canvas?.getContext('2d')?.clearRect(0,0,canvas.width,canvas.height);hasInk=false;return;
    }
    if(event.target.closest('[data-submit-signature]')){submitSignature();return;}
    if(event.target.closest('#refreshButton'))setTimeout(fetchState,300);
    if(event.target.closest('[data-tab="mandates"],[data-tab="laws"]'))setTimeout(fetchState,120);
  },true);

  ensureUi();
  fetchState();
  const lawList=document.getElementById('lawList');
  if(lawList)new MutationObserver(()=>{
    if(snapshot&&!lawRenderBusy&&lawList.dataset.v143!=='1')setTimeout(renderLaws,20);
    lawList.dataset.v143='';
  }).observe(lawList,{childList:true});
  new MutationObserver(ensureUi).observe(document.documentElement,{childList:true,subtree:true});
  setInterval(()=>{ensureUi();if(document.querySelector('[data-screen="mandates"].active'))fetchState();},30000);
})();
