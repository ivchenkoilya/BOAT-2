from __future__ import annotations

from typing import Any

import government_treasury_contributions_v150 as contributions


def _patched_contribution_script(source: str) -> str:
    source = source.replace(
        'max="${Number(data.max_amount)||1000000}"',
        'max="${Math.max(Number(data.min_amount)||100,Number(data.available_balance)||0)}"',
    )
    source = source.replace(
        "if(!Number.isFinite(amount)||amount<100||amount>1000000){",
        "if(!Number.isFinite(amount)||amount<100){",
    )
    source = source.replace(
        "toast('Размер вклада должен быть от 100 до 1 000 000 влияния.','error');",
        "toast('Минимальный вклад — 100 влияния. Максимум ограничен только твоим балансом.','error');",
    )
    source = source.replace(
        "  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';",
        "  const date=value=>value?new Date(Number(value)*1000).toLocaleString('ru-RU',{day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'}):'—';\n  const contributionRequestId=()=>crypto?.randomUUID?.()||`treasury-${Date.now()}-${Math.random().toString(36).slice(2)}`;",
    )
    source = source.replace(
        "body:JSON.stringify({chat_id:chatId,amount,fund_key:values.fund_key||'general',note:values.note||''})",
        "body:JSON.stringify({chat_id:chatId,amount,fund_key:values.fund_key||'state_treasury',note:values.note||'',request_id:contributionRequestId()})",
    )
    source = source.replace(
        "  const observer=new MutationObserver(scheduleEnsure);\n  observer.observe(document.documentElement,{subtree:true,childList:true});\n",
        "  window.addEventListener('pageshow',scheduleEnsure);\n",
    )
    return source


def install_government_reality_v179_safety(core: Any) -> None:
    if getattr(core, "_government_reality_v179_safety_installed", False):
        return
    core._government_reality_v179_safety_installed = True

    @core.web.middleware
    async def treasury_asset_v179(request: Any, handler: Any):
        if (
            request.method.upper() == "GET"
            and str(request.path or "") == "/government-v150/treasury-contributions-v150.js"
        ):
            return core.web.Response(
                text=_patched_contribution_script(
                    contributions.ASSET_JS.read_text(encoding="utf-8")
                ),
                content_type="application/javascript",
                charset="utf-8",
                headers={
                    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
                    "Pragma": "no-cache",
                    "Expires": "0",
                    "X-Government-Reality": "179-treasury-safety",
                },
            )
        return await handler(request)

    previous_application = core.web.Application

    def application_v179_safety(*args: Any, **kwargs: Any):
        app = previous_application(*args, **kwargs)
        app.middlewares.insert(0, treasury_asset_v179)
        return app

    core.web.Application = application_v179_safety
