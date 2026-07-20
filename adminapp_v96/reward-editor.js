(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  let installed=false;

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=text;
    node.className=`toast show ${type}`;
    clearTimeout(node.__rewardTimer);
    node.__rewardTimer=setTimeout(()=>node.className='toast',3400);
  }

  function install(){
    const select=document.getElementById('v96EventSelect');
    if(!select||document.getElementById('v96RewardEditor'))return;
    installed=true;
    const editor=document.createElement('div');
    editor.id='v96RewardEditor';
    editor.innerHTML=`
      <div class="v96-reward-title"><span>⚖️</span><div><b>Множители наград</b><small>Меняют награды текущего события перед их выдачей</small></div></div>
      <div class="v96-reward-grid">
        <label><span>Влияние</span><input id="v96InfluenceMultiplier" type="number" min="0" max="5" step="0.1" value="1"></label>
        <label><span>Очки Древа</span><input id="v96TreeMultiplier" type="number" min="0" max="5" step="0.1" value="1"></label>
      </div>
      <button class="v96-reward-save" id="v96SaveRewards" type="button">💾 СОХРАНИТЬ НАГРАДЫ</button>
      <p>Пример: ×1.5 превратит +200 влияния в +300. Значение ×0 отключает соответствующую награду.</p>`;
    select.insertAdjacentElement('afterend',editor);
    const style=document.createElement('style');
    style.textContent=`
      #v96RewardEditor{margin:9px 0 12px;padding:12px;border:1px solid #574268;border-radius:15px;background:linear-gradient(150deg,#171020,#0c0811)}
      .v96-reward-title{display:flex;gap:9px;align-items:center}.v96-reward-title>span{font-size:21px}.v96-reward-title b,.v96-reward-title small{display:block}.v96-reward-title b{font-size:12px}.v96-reward-title small{font-size:8px;color:#8f8297;margin-top:2px}
      .v96-reward-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px}.v96-reward-grid label{padding:8px;border:1px solid #3d2d48;border-radius:11px;background:#0a070e}.v96-reward-grid span{display:block;font-size:8px;color:#a696b0;margin-bottom:5px}.v96-reward-grid input{width:100%;border:0;outline:0;background:transparent;color:#f2d797;font-size:19px;font-weight:900;text-align:center}
      .v96-reward-save{width:100%;min-height:43px;margin-top:8px;border:1px solid #786092;border-radius:11px;background:linear-gradient(180deg,#3a2850,#21162e);color:#f0e3f8;font-size:10px;font-weight:900}#v96RewardEditor p{margin:7px 2px 0;color:#807386;font-size:8px;line-height:1.4}
      @media(max-width:370px){.v96-reward-grid{grid-template-columns:1fr}}
    `;
    document.head.appendChild(style);
    sync();
  }

  function sync(){
    const data=window.RealityEventsV96?.state?.reward_override;
    if(!data)return;
    const influence=document.getElementById('v96InfluenceMultiplier');
    const tree=document.getElementById('v96TreeMultiplier');
    if(influence&&document.activeElement!==influence)influence.value=Number(data.influence_multiplier??1).toFixed(1).replace(/\.0$/,'');
    if(tree&&document.activeElement!==tree)tree.value=Number(data.tree_multiplier??1).toFixed(1).replace(/\.0$/,'');
  }

  async function save(){
    const runtime=window.RealityEventsV96;
    const chatId=Number(runtime?.chatId||localStorage.getItem('admin76Chat')||0);
    if(!chatId){toast('Сначала выбери беседу.','error');return}
    if(!runtime?.state?.event){toast('Сначала запусти событие.','error');return}
    const influence=Number(document.getElementById('v96InfluenceMultiplier')?.value||1);
    const tree=Number(document.getElementById('v96TreeMultiplier')?.value||1);
    if(!Number.isFinite(influence)||!Number.isFinite(tree)||influence<0||tree<0||influence>5||tree>5){
      toast('Допустимое значение — от 0 до 5.','error');return;
    }
    const button=document.getElementById('v96SaveRewards');
    button.disabled=true;button.textContent='СОХРАНЯЕМ…';
    try{
      const response=await fetch('/events-v96/api/action',{
        method:'POST',
        headers:{'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''},
        body:JSON.stringify({action:'event_reward_settings',chat_id:chatId,influence_multiplier:influence,tree_multiplier:tree})
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Некорректный ответ сервера.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Не удалось сохранить награды.');
      toast(data.message||'Награды обновлены.','success');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      document.getElementById('v96Refresh')?.click();
    }catch(error){toast(error.message||'Не удалось сохранить награды.','error')}
    finally{button.disabled=false;button.textContent='💾 СОХРАНИТЬ НАГРАДЫ'}
  }

  document.addEventListener('click',event=>{
    if(event.target.closest('#v96SaveRewards'))save();
  },true);

  document.addEventListener('DOMContentLoaded',()=>{
    const observer=new MutationObserver(()=>{if(!installed)install();sync()});
    observer.observe(document.body,{childList:true,subtree:true});
    install();setInterval(sync,1000);
  });
})();
