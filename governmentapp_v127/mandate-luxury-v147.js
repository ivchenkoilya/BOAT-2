(()=>{
  'use strict';
  if(window.__governmentMandateLuxuryV147)return;
  window.__governmentMandateLuxuryV147=true;

  const tg=window.Telegram?.WebApp;
  const params=new URLSearchParams(location.search);
  const start=String(tg?.initDataUnsafe?.start_param||params.get('tgWebAppStartParam')||'');
  const chatId=Number(params.get('chat_id')||(start.startsWith('government_')?start.slice(11):0));
  const headers={'X-Telegram-Init-Data':tg?.initData||''};
  let ownerLabel='';
  let applyFrame=0;

  function telegramDisplayName(){
    const user=tg?.initDataUnsafe?.user||{};
    const full=[user.first_name,user.last_name].filter(Boolean).join(' ').trim();
    if(full)return full;
    if(user.username)return `@${String(user.username).replace(/^@/,'')}`;
    return '';
  }

  function scheduleApply(){
    cancelAnimationFrame(applyFrame);
    applyFrame=requestAnimationFrame(applyLuxury);
  }

  async function loadOwner(){
    if(!chatId)return;
    try{
      const response=await fetch(`/government-v127/api/state?chat_id=${encodeURIComponent(chatId)}`,{
        cache:'no-store',headers
      });
      const data=await response.json();
      if(!response.ok||!data?.ok)return;
      const mandateOwner=(data.mandates||[]).find(item=>item.owner_label)?.owner_label;
      ownerLabel=telegramDisplayName()||mandateOwner||data.mandate_owner_label||'';
      scheduleApply();
    }catch(_error){}
  }

  function replaceOwnerInCards(){
    if(!ownerLabel)return;
    document.querySelectorAll('.mandate-card-v143 .card-head small').forEach(node=>{
      const text=String(node.textContent||'');
      if(!text.startsWith('Telegram ID '))return;
      const separator=text.indexOf(' · ');
      const next=separator>=0?`${ownerLabel}${text.slice(separator)}`:ownerLabel;
      if(node.textContent!==next)node.textContent=next;
    });
  }

  function replaceOwnerInDocument(documentNode){
    if(!ownerLabel)return;
    documentNode.querySelectorAll('.mandate-fields-v143>div').forEach(field=>{
      const label=field.querySelector('small');
      const value=field.querySelector('b');
      if(label&&value&&String(label.textContent||'').trim()==='ВЛАДЕЛЕЦ'&&value.textContent!==ownerLabel){
        value.textContent=ownerLabel;
      }
    });
  }

  function inkBounds(ctx,width,height){
    let image;
    try{image=ctx.getImageData(0,0,width,height);}catch(_error){return null;}
    const data=image.data;
    let minX=width,minY=height,maxX=-1,maxY=-1;
    for(let y=0;y<height;y++){
      for(let x=0;x<width;x++){
        const index=(y*width+x)*4;
        if(data[index+3]>24){
          if(x<minX)minX=x;if(x>maxX)maxX=x;
          if(y<minY)minY=y;if(y>maxY)maxY=y;
        }
      }
    }
    if(maxX<minX||maxY<minY)return null;
    return {x:minX,y:minY,w:maxX-minX+1,h:maxY-minY+1};
  }

  function centerSignatureCanvas(canvas){
    if(!canvas||canvas.dataset.v147Centered==='1')return;
    const ctx=canvas.getContext('2d');
    if(!ctx)return;
    const bounds=inkBounds(ctx,canvas.width,canvas.height);
    if(!bounds)return;
    const copy=document.createElement('canvas');
    copy.width=canvas.width;copy.height=canvas.height;
    copy.getContext('2d').drawImage(canvas,0,0);
    const maxWidth=canvas.width*.72;
    const maxHeight=canvas.height*.58;
    const scale=Math.min(maxWidth/bounds.w,maxHeight/bounds.h,1.18);
    const drawW=bounds.w*scale;
    const drawH=bounds.h*scale;
    const drawX=(canvas.width-drawW)/2;
    const drawY=(canvas.height-drawH)/2;
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.drawImage(copy,bounds.x,bounds.y,bounds.w,bounds.h,drawX,drawY,drawW,drawH);
    canvas.dataset.v147Centered='1';
  }

  function centerStoredSignature(image){
    if(!image||image.dataset.v147Centered==='1')return;
    image.dataset.v147Centered='1';
    const run=()=>{
      try{
        const source=document.createElement('canvas');
        source.width=image.naturalWidth||1000;
        source.height=image.naturalHeight||300;
        const sourceCtx=source.getContext('2d');
        sourceCtx.drawImage(image,0,0,source.width,source.height);
        const bounds=inkBounds(sourceCtx,source.width,source.height);
        if(!bounds)return;
        const target=document.createElement('canvas');
        target.width=1000;target.height=300;
        const targetCtx=target.getContext('2d');
        const scale=Math.min(680/bounds.w,170/bounds.h,1.25);
        const width=bounds.w*scale;
        const height=bounds.h*scale;
        targetCtx.drawImage(source,bounds.x,bounds.y,bounds.w,bounds.h,(1000-width)/2,(300-height)/2,width,height);
        image.src=target.toDataURL('image/png');
      }catch(_error){}
    };
    if(image.complete)run();else image.addEventListener('load',run,{once:true});
  }

  function decorateDocument(documentNode){
    documentNode.classList.add('mandate-luxury-v147');
    if(!documentNode.querySelector('.mandate-crown-v147')){
      documentNode.insertAdjacentHTML('afterbegin',
        '<div class="mandate-crown-v147" aria-hidden="true"><i></i><span>✦</span><i></i></div>'+
        '<div class="mandate-ribbon-v147">ОФИЦИАЛЬНЫЙ ДОКУМЕНТ</div>'
      );
    }
    if(!documentNode.querySelector('.mandate-footer-v147')){
      documentNode.insertAdjacentHTML('beforeend',
        '<div class="mandate-footer-v147"><span>Выдан государственным реестром</span><b>СИСТЕМА «ГЛАВНЫЙ ГЕРОЙ»</b></div>'
      );
    }
    replaceOwnerInDocument(documentNode);
    documentNode.querySelectorAll('.signature-preview-v143 img').forEach(centerStoredSignature);
  }

  function applyLuxury(){
    const brand=document.querySelector('.brand small');
    if(brand&&brand.textContent!=='REALITY 147')brand.textContent='REALITY 147';
    replaceOwnerInCards();
    document.querySelectorAll('.mandate-document-v143').forEach(decorateDocument);
  }

  document.addEventListener('pointerdown',event=>{
    const canvas=event.target.closest?.('#signatureCanvasV143');
    if(canvas)delete canvas.dataset.v147Centered;
  },true);

  document.addEventListener('click',event=>{
    if(event.target.closest('[data-clear-signature]')){
      setTimeout(()=>{
        const canvas=document.getElementById('signatureCanvasV143');
        if(canvas)delete canvas.dataset.v147Centered;
      },0);
    }
    if(event.target.closest('[data-submit-signature]')){
      centerSignatureCanvas(document.getElementById('signatureCanvasV143'));
    }
  },true);

  const observer=new MutationObserver(scheduleApply);
  observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true});

  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden)loadOwner();
  });
  window.addEventListener('focus',loadOwner);
  loadOwner();
  scheduleApply();
})();
