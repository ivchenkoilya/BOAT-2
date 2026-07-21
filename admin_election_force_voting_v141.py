from __future__ import annotations

import html
import time
from typing import Any

import admin_full_v124 as admin_full
import admin_government_market_v132 as admin_market
import government_v127 as gov


VERSION = "Reality 141 · Мгновенный переход к голосованию"
ACTION = "election_start_voting_now"
ELECTED_OFFICES = {"president", "deputy", "chair"}

PANEL_SCRIPT = r"""
(()=>{
  'use strict';
  if(window.__reality141ForceVoting)return;
  window.__reality141ForceVoting=true;

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
    clearTimeout(node.__reality141Timer);
    node.__reality141Timer=setTimeout(()=>node.className='toast',4200);
  }

  function install(){
    const screen=document.querySelector('[data-screen="government132"]');
    if(!screen||document.getElementById('reality141ForceVotingPanel'))return false;

    const panel=document.createElement('article');
    panel.id='reality141ForceVotingPanel';
    panel.className='panel';
    panel.innerHTML=`
      <div class="panel-title">
        <span>⚡</span>
        <div>
          <b>Начать голосование сейчас</b>
          <small>Мгновенно завершить выдвижение кандидатов без ожидания 24 часов</small>
        </div>
      </div>
      <div class="v132-field">
        <label>АКТИВНЫЕ ВЫБОРЫ НА ДОЛЖНОСТЬ</label>
        <select id="reality141VotingOffice">
          <option value="president">🦅 Президент реальности</option>
          <option value="deputy">🗳 Депутаты Госдумы</option>
          <option value="chair">🏛 Председатель Госдумы</option>
        </select>
      </div>
      <button class="v132-button gold" id="reality141StartVoting">
        ⚡ НАЧАТЬ ГОЛОСОВАНИЕ СЕЙЧАС
      </button>
      <div class="v132-note">
        Должен быть хотя бы один кандидат. Голосование продлится обычные 24 часа.
      </div>`;

    const electionPanel=
      screen.querySelector('#reality134ElectionPanel')||
      screen.querySelector('#v133ElectionNowPanel');
    if(electionPanel)electionPanel.insertAdjacentElement('afterend',panel);
    else{
      const hero=screen.querySelector('#v132GovHero');
      if(hero)hero.insertAdjacentElement('afterend',panel);
      else screen.prepend(panel);
    }
    return true;
  }

  async function confirmStart(title){
    const text=`Закрыть выдвижение «${title}» и прямо сейчас начать голосование?`;
    if(tg?.showConfirm)return new Promise(resolve=>tg.showConfirm(text,resolve));
    return window.confirm(text);
  }

  async function startVoting(){
    if(busy)return;
    const currentChat=chatId();
    if(currentChat>=0){
      toast('Сначала выбери групповую беседу.','error');
      return;
    }

    const select=document.getElementById('reality141VotingOffice');
    const officeKey=String(select?.value||'president');
    const title=String(select?.selectedOptions?.[0]?.textContent||'выборы');
    if(!(await confirmStart(title)))return;

    const button=document.getElementById('reality141StartVoting');
    busy=true;
    if(button){button.disabled=true;button.textContent='⏳ ПЕРЕВОДИМ В ГОЛОСОВАНИЕ...';}
    try{
      const response=await fetch('/admin-v132/api/action',{
        method:'POST',
        cache:'no-store',
        headers,
        body:JSON.stringify({
          action:'election_start_voting_now',
          chat_id:currentChat,
          user_id:0,
          office_key:officeKey
        })
      });
      const data=await response.json().catch(()=>({ok:false,reason:'Сервер вернул непонятный ответ.'}));
      if(!response.ok||!data.ok)throw new Error(data.reason||'Голосование не запущено.');
      toast(data.message||'Голосование запущено.');
      tg?.HapticFeedback?.notificationOccurred?.('success');
      setTimeout(()=>{
        document.querySelector('[data-v132-refresh]')?.click();
        document.getElementById('refreshButton')?.click();
      },250);
    }catch(error){
      toast(error?.message||'Голосование не запущено.','error');
      tg?.HapticFeedback?.notificationOccurred?.('error');
    }finally{
      busy=false;
      if(button){button.disabled=false;button.textContent='⚡ НАЧАТЬ ГОЛОСОВАНИЕ СЕЙЧАС';}
    }
  }

  document.addEventListener('click',event=>{
    if(event.target?.closest?.('#reality141StartVoting'))startVoting();
  });

  install();
  new MutationObserver(install).observe(document.documentElement,{childList:true,subtree:true});
  setInterval(install,1000);
})();
""".strip()


def install_admin_election_force_voting_v141(core: Any) -> None:
    if getattr(core, "_admin_election_force_voting_v141_installed", False):
        return
    core._admin_election_force_voting_v141_installed = True
    core.ADMIN_ELECTION_FORCE_VOTING_VERSION = VERSION

    original_full_html = admin_full._full_html

    def full_html_with_force_voting() -> str:
        source = original_full_html()
        if "reality141ForceVotingPanel" not in source:
            source = source.replace(
                "</body>",
                f"  <script>{PANEL_SCRIPT}</script>\n</body>",
            )
        return source

    admin_full._full_html = full_html_with_force_voting

    original_start = core.start_webapp_server

    async def start_with_force_voting(bot: Any):
        original_runner = core.web.AppRunner

        @core.web.middleware
        async def force_voting_action(request: Any, handler: Any):
            path = str(request.path or "").rstrip("/")
            if request.method.upper() != "POST" or path != "/admin-v132/api/action":
                return await handler(request)

            try:
                data = await request.json()
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}

            if str(data.get("action") or "").strip().casefold() != ACTION:
                return await handler(request)

            try:
                admin = admin_market._auth(core, request)
                chat_id = admin_market._as_int(data.get("chat_id"))
                office_key = str(
                    data.get("office_key") or "president"
                ).strip().casefold()

                if chat_id >= 0:
                    raise ValueError("Сначала выбери групповую беседу.")
                if office_key not in ELECTED_OFFICES:
                    raise ValueError("Для этой должности выборы не проводятся.")

                conn = core.db._require_connection()
                cursor = await conn.execute(
                    """
                    SELECT * FROM government_elections_v127
                    WHERE chat_id=? AND office_key=?
                      AND phase IN ('nomination','voting')
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (int(chat_id), office_key),
                )
                election = await cursor.fetchone()
                if election is None:
                    raise ValueError(
                        "На эту должность сейчас нет активных выборов."
                    )
                if str(election["phase"]) == "voting":
                    raise ValueError("Голосование на эту должность уже идёт.")

                election_id = str(election["election_id"])
                cursor = await conn.execute(
                    """
                    SELECT COUNT(*) amount
                    FROM government_candidates_v127
                    WHERE election_id=?
                    """,
                    (election_id,),
                )
                count = int((await cursor.fetchone())["amount"])
                if count <= 0:
                    raise ValueError(
                        "Нельзя начать голосование: пока нет ни одного кандидата."
                    )

                now = int(time.time())
                voting_ends_at = now + int(gov.VOTING_SECONDS)
                cursor = await conn.execute(
                    """
                    UPDATE government_elections_v127
                    SET phase='voting',
                        nomination_ends_at=?,
                        voting_ends_at=?
                    WHERE election_id=? AND phase='nomination'
                    """,
                    (now, voting_ends_at, election_id),
                )
                await conn.commit()
                if int(cursor.rowcount or 0) <= 0:
                    raise ValueError(
                        "Этап выборов уже изменился. Обнови админ-панель."
                    )

                spec = gov.OFFICES[office_key]
                await gov._publish(
                    request.app["bot"],
                    chat_id,
                    "⚡ <b>ВЫДВИЖЕНИЕ ЗАВЕРШЕНО ДОСРОЧНО</b>\n\n"
                    f"Должность: {spec['emoji']} "
                    f"<b>{html.escape(str(spec['title']))}</b>\n"
                    f"Кандидатов: <b>{count}</b>\n\n"
                    "🗳 <b>ГОЛОСОВАНИЕ НАЧАЛОСЬ ПРЯМО СЕЙЧАС</b>\n"
                    f"Завершение: <b>{gov._date_text(voting_ends_at)}</b>\n\n"
                    "Один участник — один голос. Голосование доступно "
                    "в Mini App «Государство реальности».",
                )

                message = (
                    f"Голосование «{spec['title']}» началось. "
                    f"Кандидатов: {count}."
                )
                await admin_market._log_admin(
                    core,
                    int(admin.id),
                    chat_id,
                    0,
                    ACTION,
                    message,
                    {
                        "office_key": office_key,
                        "election_id": election_id,
                        "candidates": count,
                        "voting_ends_at": voting_ends_at,
                    },
                )
                return core.web.json_response(
                    {
                        "ok": True,
                        "message": message,
                        "election_id": election_id,
                        "voting_ends_at": voting_ends_at,
                    }
                )
            except PermissionError as exc:
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)},
                    status=403,
                )
            except Exception as exc:
                core.logging.exception(
                    "Ошибка досрочного запуска голосования Reality 141"
                )
                return core.web.json_response(
                    {"ok": False, "reason": str(exc)},
                    status=400,
                )

        def runner_with_force_voting(app: Any, *args: Any, **kwargs: Any):
            app.middlewares.insert(0, force_voting_action)
            return original_runner(app, *args, **kwargs)

        core.web.AppRunner = runner_with_force_voting
        try:
            return await original_start(bot)
        finally:
            core.web.AppRunner = original_runner

    core.start_webapp_server = start_with_force_voting
