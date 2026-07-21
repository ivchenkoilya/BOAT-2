from __future__ import annotations

from typing import Any

import admin_full_v124 as admin_full
import admin_government_market_v132 as admin_market
import government_v127 as gov


VERSION = "Reality 133 · Быстрый запуск выборов"

ELECTION_SCRIPT = r"""
(()=>{
  'use strict';

  const tg=window.Telegram?.WebApp;
  const headers={'Content-Type':'application/json','X-Telegram-Init-Data':tg?.initData||''};
  let busy=false;

  function selectedChatId(){
    const state=window.AdminFullV124?.state||{};
    return Number(state.selected_chat?.chat_id||localStorage.getItem('admin76Chat')||0);
  }

  function toast(text,type='success'){
    const node=document.getElementById('toast');
    if(!node)return;
    node.textContent=String(text||'Готово.');
    node.className=`toast show ${type}`;
    clearTimeout(node.__electionNowTimer);
    node.__electionNowTimer=setTimeout(()=>node.className='toast',3800);
  }

  function confirmLaunch(title){
    const text=`Начать выборы «${title}» прямо сейчас? В беседе сразу откроется этап выдвижения кандидатов.`;
    if(tg?.showConfirm){
      return new Promise(resolve=>tg.showConfirm(text,resolve));
    }
    return Promise.resolve(window.confirm(text));
  }

  function installPanel(){
    const screen=document.querySelector('[data-screen="government132"]');
    if(!screen||document.getElementById('v133ElectionNowPanel'))return false;

    const panel=document.createElement('article');
    panel.className='panel';
    panel.id='v133ElectionNowPanel';
    panel.innerHTML=`
      <div class="panel-title">
        <span>🗳</span>
        <div>
          <b>Провести выборы сейчас</b>
          <small>Администратор запускает выборы немедленно, не дожидаясь окончания срока действующей власти</small>
        </div>
      </div>
      <div class="v132-field">
        <label>КАКУЮ ДОЛЖНОСТЬ ВЫБИРАЕМ</label>
        <select id="v133ElectionOffice">
          <option value="president">🦅 Президент реальности</option>
          <option value="deputy">🗳 Депутаты Госдумы</option>
          <option value="chair">🏛 Председатель Госдумы</option>
        </select>
      </div>
      <button class="v132-button gold" id="v133ElectionNowButton">🗳 ПРОВЕСТИ ВЫБОРЫ СЕЙЧАС</button>
      <div class="v132-note">Этап выдвижения начнётся сразу. Голосование и подведение итогов продолжат работать автоматически по правилам государства.</div>
    `;

    const firstPanel=screen.querySelector('article.panel');
    if(firstPanel)firstPanel.insertAdjacentElement('beforebegin',panel);
    else screen.appendChild(panel);
    return true;
  }

  async function startElection(){
    if(busy)return;
    const chatId=selectedChatId();
    if(chatId>=0){
      toast('Сначала выбери групповую беседу.','error');
      return;
    }
    const select=document.getElementById('v133ElectionOffice');
    const officeKey=String(select?.value||'president');
    const title=String(select?.selectedOptions?.[0]?.textContent||'выборы');
    if(!(await confirmLaunch(title)))return;

    busy=true;
    const button=document.getElementById('v133ElectionNowButton');
    if(button){
      button.disabled=true;
      button.textContent='⏳ ЗАПУСКАЕМ ВЫБОРЫ...';
    }
    try{
      const response=await fetch('/admin-v132/api/action',{
        method:'POST',
        cache:'no-store',
        headers,
        body:JSON.stringify({
          action:'election_start_now',
          chat_id:chatId,
          user_id:0,
          office_key:officeKey
        })
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Выборы не запущены.');
      toast(data.message||'Выборы запущены.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      window.AdminReality132?.state&&setTimeout(()=>document.querySelector('[data-v132-refresh]')?.click(),250);
    }catch(error){
      toast(error?.message||'Выборы не запущены.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      busy=false;
      if(button){
        button.disabled=false;
        button.textContent='🗳 ПРОВЕСТИ ВЫБОРЫ СЕЙЧАС';
      }
    }
  }

  document.addEventListener('click',event=>{
    if(event.target?.closest?.('#v133ElectionNowButton'))startElection();
  });

  installPanel();
  const observer=new MutationObserver(()=>installPanel());
  observer.observe(document.documentElement,{childList:true,subtree:true});
  setInterval(installPanel,1200);
})();
""".strip()


def install_admin_election_now_v133(core: Any) -> None:
    if getattr(core, "_admin_election_now_v133_installed", False):
        return
    core._admin_election_now_v133_installed = True

    @core.web.middleware
    async def election_now_patch(request: Any, handler: Any):
        path = str(request.path or "")
        method = request.method.upper()

        if method == "GET" and path in {"/admin-v132", "/admin-v132/"}:
            source = admin_full._full_html()
            marker = "</body>"
            script = f"  <script>{ELECTION_SCRIPT}</script>\n"
            if "v133ElectionNowPanel" not in source:
                source = source.replace(marker, script + marker)
            return core.web.Response(
                text=source,
                content_type="text/html",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Admin-Center": "reality-133-election-now",
                },
            )

        if method != "POST" or path != "/admin-v132/api/action":
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

            bot = request.app["bot"]
            election_id = await gov._start_election(
                core,
                bot,
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
                {
                    "office_key": office_key,
                    "election_id": election_id,
                },
            )
            return core.web.json_response(
                {
                    "ok": True,
                    "message": message,
                    "election_id": election_id,
                }
            )
        except PermissionError as exc:
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=403)
        except Exception as exc:
            core.logging.exception("Ошибка немедленного запуска выборов Reality 133")
            return core.web.json_response({"ok": False, "reason": str(exc)}, status=400)

    previous_application = core.web.Application

    def application_with_election_now(*args: Any, **kwargs: Any):
        application = previous_application(*args, **kwargs)
        application.middlewares.insert(0, election_now_patch)
        return application

    core.web.Application = application_with_election_now
