from __future__ import annotations

import html
from typing import Any

import admin_full_v124 as admin_full
import admin_government_market_v132 as admin_market
import government_v127 as gov


VERSION = "Reality 134 · Кнопка выборов в основном интерфейсе"

BUTTON_SCRIPT = r"""
(()=>{
  'use strict';
  if(window.__reality134ElectionButton)return;
  window.__reality134ElectionButton=true;

  const tg=window.Telegram?.WebApp;
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  let busy=false;

  const chatId=()=>Number(
    window.AdminFullV124?.state?.selected_chat?.chat_id||
    localStorage.getItem('admin76Chat')||0
  );

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__election134Timer);
    node.__election134Timer=setTimeout(()=>node.className='toast',4000);
  }

  function install(){
    const screen=document.querySelector('[data-screen="government132"]');
    if(!screen||document.getElementById('reality134ElectionPanel'))return false;

    const panel=document.createElement('article');
    panel.id='reality134ElectionPanel';
    panel.className='panel';
    panel.innerHTML=`
      <div class="panel-title">
        <span>🗳</span>
        <div>
          <b>Провести выборы сейчас</b>
          <small>Немедленный запуск выборов в выбранной беседе</small>
        </div>
      </div>
      <div class="v132-field">
        <label>ДОЛЖНОСТЬ</label>
        <select id="reality134ElectionOffice">
          <option value="president">🦅 Президент реальности</option>
          <option value="deputy">🗳 Депутаты Госдумы</option>
          <option value="chair">🏛 Председатель Госдумы</option>
        </select>
      </div>
      <button class="v132-button gold" id="reality134ElectionStart">
        🗳 ПРОВЕСТИ ВЫБОРЫ СЕЙЧАС
      </button>
      <div class="v132-note">
        После нажатия в беседе сразу откроется этап выдвижения кандидатов.
      </div>`;

    const hero=screen.querySelector('#v132GovHero');
    if(hero)hero.insertAdjacentElement('afterend',panel);
    else screen.prepend(panel);
    return true;
  }

  async function confirmStart(title){
    const text=`Запустить выборы «${title}» прямо сейчас?`;
    if(tg?.showConfirm)return new Promise(resolve=>tg.showConfirm(text,resolve));
    return window.confirm(text);
  }

  async function start(){
    if(busy)return;
    const currentChat=chatId();
    if(currentChat>=0){
      toast('Сначала выбери групповую беседу.','error');
      return;
    }

    const select=document.getElementById('reality134ElectionOffice');
    const officeKey=String(select?.value||'president');
    const title=String(select?.selectedOptions?.[0]?.textContent||'Президент реальности');
    if(!(await confirmStart(title)))return;

    const button=document.getElementById('reality134ElectionStart');
    busy=true;
    if(button){button.disabled=true;button.textContent='⏳ ЗАПУСКАЕМ...';}
    try{
      const response=await fetch('/admin-v132/api/action',{
        method:'POST',
        cache:'no-store',
        headers,
        body:JSON.stringify({
          action:'election_start_now',
          chat_id:currentChat,
          user_id:0,
          office_key:officeKey
        })
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Выборы не запущены.');
      toast(data.message||'Выборы запущены.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
    }catch(error){
      toast(error?.message||'Выборы не запущены.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      busy=false;
      if(button){button.disabled=false;button.textContent='🗳 ПРОВЕСТИ ВЫБОРЫ СЕЙЧАС';}
    }
  }

  document.addEventListener('click',event=>{
    if(event.target?.closest?.('#reality134ElectionStart'))start();
  });

  install();
  new MutationObserver(install).observe(document.documentElement,{childList:true,subtree:true});
  setInterval(install,1000);
})();
""".strip()


def install_admin_election_button_hotfix_v134(core: Any) -> None:
    if getattr(core, "_admin_election_button_hotfix_v134_installed", False):
        return
    core._admin_election_button_hotfix_v134_installed = True

    original_full_html = admin_full._full_html

    def full_html_with_election_button() -> str:
        source = original_full_html()
        if "reality134ElectionPanel" not in source:
            source = source.replace(
                "</body>",
                f"  <script>{BUTTON_SCRIPT}</script>\n</body>",
            )
        return source

    admin_full._full_html = full_html_with_election_button

    @core.web.middleware
    async def election_action_hotfix(request: Any, handler: Any):
        if request.method.upper() != "POST" or str(request.path or "") != "/admin-v132/api/action":
            return await handler(request)

        try:
            data = await request.json()
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}

        if str(data.get("action") or "") != "election_start_now":
            return await handler(request)

        try:
            admin = admin_market._auth(core, request)
            chat_id = admin_market._as_int(data.get("chat_id"))
            office_key = str(data.get("office_key") or "president")
            if chat_id >= 0:
                raise ValueError("Выбери групповую беседу.")
            if office_key not in {"president", "deputy", "chair"}:
                raise ValueError("Для этой должности выборы не проводятся.")

            election_id = await gov._start_election(
                core,
                request.app["bot"],
                chat_id,
                office_key,
                int(admin.id),
            )
            spec = gov.OFFICES[office_key]
            message = f"Выборы «{spec['title']}» запущены. Этап выдвижения открыт."
            await admin_market._log_admin(
                core,
                int(admin.id),
                chat_id,
                0,
                "election_start_now",
                message,
                {"office_key": office_key, "election_id": election_id},
            )
            return core.web.json_response(
                {"ok": True, "message": message, "election_id": election_id}
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка запуска выборов Reality 134")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    previous_application = core.web.Application

    def application_with_election_hotfix(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, election_action_hotfix)
        return application

    core.web.Application = application_with_election_hotfix
