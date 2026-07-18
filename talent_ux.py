from __future__ import annotations

from pathlib import Path
from typing import Any

from aiohttp import web


UX_STYLE = r"""
<style id="talent-ux-v4-style">
.brand .kicker,.brand h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.brand h1{font-size:18px!important}.controls #zin,.controls #zout{display:none!important}.controls{right:10px!important}.card{position:relative}.talent-close-x{position:absolute;right:13px;top:13px;z-index:5;width:38px;height:38px;border-radius:13px;border:1px solid #ffffff1c;background:#171022d9;color:#fff;display:grid;place-items:center;font-size:18px;font-weight:900;box-shadow:0 8px 20px #0006}.talent-close-x:active{transform:scale(.94)}.node svg,.cardicon svg,.tab svg,.emblem svg{filter:drop-shadow(0 5px 9px #0007);stroke-linecap:round;stroke-linejoin:round}.node{border-radius:27px!important;background:radial-gradient(circle at 28% 18%,#ffffff2e,transparent 34%),linear-gradient(145deg,#49336d,#100a20)!important}.node:before{content:"";position:absolute;inset:7px;border-radius:20px;border:1px solid #ffffff10;pointer-events:none}.cardicon,.emblem{background:radial-gradient(circle at 28% 18%,#ffffff2e,transparent 35%),linear-gradient(145deg,rgba(var(--rgb),.74),#7d45c766)!important}.hint{font-size:9px!important}.sheet.show{pointer-events:auto!important}.sheet.show .card{pointer-events:auto!important}
</style>
"""

UX_SCRIPT = r"""
<script id="talent-ux-v4-script">
(function(){
  const tg=window.Telegram?.WebApp;
  const $=s=>document.querySelector(s);
  const user=tg?.initDataUnsafe?.user;
  const brand=$('.brand');
  if(brand){
    const kicker=brand.querySelector('.kicker');
    const title=brand.querySelector('h1');
    const full=user?[user.first_name,user.last_name].filter(Boolean).join(' ').trim():'';
    const username=user?.username?'@'+user.username:'';
    if(title) title.textContent=full||username||'Игрок Telegram';
    if(kicker) kicker.textContent=username||'ДРЕВО РАЗВИТИЯ';
  }

  const sheet=$('#sheet');
  const close=$('#close');
  function forceClose(e){
    if(e){e.preventDefault();e.stopPropagation();}
    sheet?.classList.remove('show');
  }
  ['click','pointerup','touchend'].forEach(evt=>close?.addEventListener(evt,forceClose,{passive:false,capture:true}));
  if(sheet){
    const card=sheet.querySelector('.card');
    if(card&&!card.querySelector('.talent-close-x')){
      const x=document.createElement('button');
      x.type='button';x.className='talent-close-x';x.textContent='✕';x.setAttribute('aria-label','Закрыть');
      ['click','pointerup','touchend'].forEach(evt=>x.addEventListener(evt,forceClose,{passive:false}));
      card.prepend(x);
    }
    sheet.addEventListener('click',e=>{if(e.target===sheet)forceClose(e)});
  }

  const viewport=$('#viewport');
  const hint=$('#hint');
  if(hint) hint.textContent='Двигай одним пальцем • Масштабируй двумя пальцами';
  if(viewport){
    let startDistance=0,lastDistance=0,mid={x:0,y:0};
    const dist=t=>Math.hypot(t[0].clientX-t[1].clientX,t[0].clientY-t[1].clientY);
    const midpoint=t=>({x:(t[0].clientX+t[1].clientX)/2,y:(t[0].clientY+t[1].clientY)/2});
    viewport.addEventListener('touchstart',e=>{
      if(e.touches.length===2){
        startDistance=lastDistance=dist(e.touches);mid=midpoint(e.touches);e.preventDefault();e.stopImmediatePropagation();
      }
    },{passive:false,capture:true});
    viewport.addEventListener('touchmove',e=>{
      if(e.touches.length===2){
        const now=dist(e.touches);mid=midpoint(e.touches);
        const delta=now-lastDistance;lastDistance=now;
        viewport.dispatchEvent(new WheelEvent('wheel',{deltaY:delta>0?-80:80,clientX:mid.x,clientY:mid.y,bubbles:true,cancelable:true}));
        e.preventDefault();e.stopImmediatePropagation();
      }
    },{passive:false,capture:true});
    viewport.addEventListener('touchend',e=>{if(e.touches.length<2){startDistance=0;lastDistance=0}},{passive:true,capture:true});
  }

  const icons={
    'Острый язык':'<svg viewBox="0 0 48 48" fill="none"><path d="M29 6 42 19 23 38l-8-2 2-8L29 6Z" fill="currentColor"/><path d="m16 30 4 4-9 9-4-4 9-9Z" fill="currentColor" opacity=".8"/><path d="m31 11 6 6" stroke="white" stroke-opacity=".55" stroke-width="2.5"/></svg>',
    'Больное место':'<svg viewBox="0 0 48 48" fill="none"><circle cx="22" cy="26" r="15" stroke="currentColor" stroke-width="4.5"/><circle cx="22" cy="26" r="8" stroke="currentColor" stroke-width="3.5"/><circle cx="22" cy="26" r="2.5" fill="currentColor"/><path d="m29 19 11-11M33 8h7v7" stroke="currentColor" stroke-width="4"/></svg>',
    'Толстая кожа':'<svg viewBox="0 0 48 48" fill="none"><path d="M24 5 40 11v12c0 10-6 18-16 22C14 41 8 33 8 23V11l16-6Z" fill="currentColor"/><path d="m17 24 5 5 10-11" stroke="white" stroke-opacity=".8" stroke-width="4"/></svg>',
    'Богатая добыча':'<svg viewBox="0 0 48 48" fill="none"><path d="M7 18h34v22H7V18Z" fill="currentColor"/><path d="M10 10h28l3 8H7l3-8Z" fill="currentColor" opacity=".72"/><path d="M7 26h34" stroke="white" stroke-opacity=".42" stroke-width="3"/><rect x="21" y="22" width="6" height="10" rx="2" fill="#180f27"/></svg>'
  };
  function refreshIcons(){
    document.querySelectorAll('.nodewrap').forEach(w=>{
      const name=w.querySelector('.name')?.textContent?.trim();
      const node=w.querySelector('.node');
      if(name&&icons[name]&&node) node.innerHTML=icons[name]+(node.querySelector('.lvl')?.outerHTML||'')+(node.querySelector('.lock')?.outerHTML||'');
    });
    const cardTitle=$('#cardtitle')?.textContent?.trim();
    if(cardTitle&&icons[cardTitle]&&$('#cardicon')) $('#cardicon').innerHTML=icons[cardTitle];
  }
  const observer=new MutationObserver(refreshIcons);
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
  setTimeout(refreshIcons,100);
})();
</script>
"""


def install_ux(core: Any) -> None:
    if getattr(core, "_talent_ux_installed", False):
        return
    core._talent_ux_installed = True

    original_file_response = core.web.FileResponse

    def enhanced_file_response(path: Any, *args: Any, **kwargs: Any):
        resolved = Path(path)
        if resolved.name == "index.html" and resolved.parent.name == "talent_app":
            text = resolved.read_text(encoding="utf-8")
            text = text.replace("</head>", UX_STYLE + "\n</head>")
            text = text.replace("</body>", UX_SCRIPT + "\n</body>")
            return web.Response(text=text, content_type="text/html")
        return original_file_response(path, *args, **kwargs)

    core.web.FileResponse = enhanced_file_response
