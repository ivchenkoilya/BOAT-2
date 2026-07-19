(()=>{
  "use strict";
  (window.__heistV92Patches||(window.__heistV92Patches=[])).push((source,replaceFunction)=>{
    const helpers=`  const SAFE_SPRITE_IMAGES={};
  function safeSpriteKey(safe){
    if(safe.tier===4)return "safe-vault";
    if(safe.tier===3)return "safe-elite";
    if(safe.tier===2){const zone=cellAt(safe.c,safe.r)?.zone;return ((safe.id+seed)%2===1||zone==="tech")?"safe-electronic":"safe-reinforced";}
    return "safe-common";
  }
  function loadSafeSpriteImages(){
    const urls=window.__HEIST_SAFE_ASSET_URLS__||{};
    for(const [key,url] of Object.entries(urls)){if(SAFE_SPRITE_IMAGES[key])continue;const image=new Image();image.decoding="async";image.src=url;SAFE_SPRITE_IMAGES[key]=image;}
  }
  loadSafeSpriteImages();
`;
    source=source.replace("  function buildObjects(){",helpers+"  function buildObjects(){");
    source=source.replace('stage.classList.add("cracking");','stage.classList.add("cracking");const focusKey=safeSpriteKey(safe),focus=$("safeFocus");if(focus)focus.dataset.safeSprite=focusKey;document.dispatchEvent(new CustomEvent("heist:safe-focus",{detail:{spriteKey:focusKey,tier:safe.tier,safeId:safe.id}}));');
    source=source.replace("if(safe.opened)return;safe.opened=true;","if(safe.opened)return;safe.openedAt=performance.now();safe.opened=true;");

    source=replaceFunction(source,"drawSafe","drawCamera",`  function drawSafe(safe,t){
    const p=screen(safe.x,safe.y),meta=SAFE_META[safe.tier],key=safeSpriteKey(safe),image=SAFE_SPRITE_IMAGES[key];
    const baseSize=key==="safe-vault"?116:key==="safe-elite"?92:key==="safe-electronic"?84:key==="safe-reinforced"?82:74;
    if(p.x<-baseSize||p.x>viewW+baseSize||p.y<hudSafe-baseSize||p.y>viewH+baseSize)return;
    const now=performance.now(),openProgress=safe.opened?clamp((now-(safe.openedAt||now))/920,0,1):0;
    if(safe.opened&&openProgress>=1)return;
    const distance=Math.hypot(player.x-safe.x,player.y-safe.y),near=!safe.opened&&distance<66;
    const pulse=.5+.5*Math.sin(t*2.35+safe.id*1.17),bob=safe.opened?0:Math.sin(t*1.75+safe.id*.9)*1.8;
    const tierScale=safe.tier===4?1.04:1,nearScale=near?1.085:1,openScale=1+openProgress*.42;
    const size=baseSize*tierScale*nearScale*openScale,alpha=safe.opened?Math.max(0,1-openProgress):1;
    ctx.save();ctx.translate(p.x,p.y+bob);ctx.globalAlpha=alpha;

    ctx.save();ctx.scale(1,0.34);ctx.fillStyle="rgba(0,0,0,"+(safe.opened?.28:.62)+")";ctx.shadowBlur=14;ctx.shadowColor="#000";ctx.beginPath();ctx.ellipse(0,size*1.18,size*.45,size*.18,0,0,Math.PI*2);ctx.fill();ctx.restore();

    const glowRadius=size*(safe.tier===4?.78:.68),glow=ctx.createRadialGradient(0,0,4,0,0,glowRadius);
    glow.addColorStop(0,meta.color+(near?"55":"38"));glow.addColorStop(.48,meta.color+(near?"24":"13"));glow.addColorStop(1,"transparent");ctx.fillStyle=glow;ctx.fillRect(-glowRadius,-glowRadius,glowRadius*2,glowRadius*2);

    if(safe.tier===4&&!safe.opened){ctx.save();ctx.rotate(t*.11);ctx.strokeStyle="#d986ff55";ctx.lineWidth=1.4;ctx.setLineDash([7,8]);ctx.beginPath();ctx.arc(0,0,size*.48,0,Math.PI*2);ctx.stroke();ctx.rotate(-t*.24);ctx.strokeStyle="#ffe28c44";ctx.beginPath();ctx.arc(0,0,size*.57,0,Math.PI*2);ctx.stroke();ctx.restore();}

    if(safe.opened){ctx.rotate(openProgress*.16);ctx.globalAlpha=alpha;ctx.shadowBlur=34*(1-openProgress);ctx.shadowColor=meta.color;}
    else{ctx.shadowBlur=near?28+10*pulse:14+6*pulse;ctx.shadowColor=meta.color;}

    if(image&&image.complete&&image.naturalWidth){
      if(!safe.opened){ctx.save();ctx.globalAlpha=.12+.07*pulse;ctx.scale(1.11,1.11);ctx.drawImage(image,-size/2,-size/2,size,size);ctx.restore();}
      ctx.drawImage(image,-size/2,-size/2,size,size);
    }else{
      const fallback=ctx.createLinearGradient(-size/2,-size/2,size/2,size/2);fallback.addColorStop(0,"#40342d");fallback.addColorStop(.55,"#141117");fallback.addColorStop(1,meta.color+"88");ctx.fillStyle=fallback;rounded(ctx,-size*.38,-size*.35,size*.76,size*.7,9);ctx.fill();ctx.strokeStyle=meta.color;ctx.lineWidth=3;ctx.stroke();ctx.beginPath();ctx.arc(0,0,size*.12,0,Math.PI*2);ctx.stroke();
    }
    ctx.shadowBlur=0;

    if(near){ctx.save();ctx.rotate(-t*.75);ctx.strokeStyle=meta.color;ctx.lineWidth=2;ctx.setLineDash([9,7]);ctx.globalAlpha=.72+.24*pulse;ctx.beginPath();ctx.arc(0,0,size*.57,0,Math.PI*2);ctx.stroke();ctx.setLineDash([]);for(let i=0;i<4;i++){const a=t*1.25+i*Math.PI/2,r=size*.63;ctx.fillStyle=i%2?"#fff0b0":meta.color;ctx.shadowBlur=10;ctx.shadowColor=meta.color;ctx.beginPath();ctx.arc(Math.cos(a)*r,Math.sin(a)*r,2.2,0,Math.PI*2);ctx.fill();}ctx.restore();}

    if(safe.opened){ctx.save();ctx.globalCompositeOperation="screen";for(let i=0;i<8;i++){const a=i*Math.PI/4+t*.35,r=size*(.18+openProgress*.62);ctx.strokeStyle=i%2?"#ffe6a5":"#d986ff";ctx.globalAlpha=(1-openProgress)*.7;ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(Math.cos(a)*size*.1,Math.sin(a)*size*.1);ctx.lineTo(Math.cos(a)*r,Math.sin(a)*r);ctx.stroke();}ctx.restore();}
    ctx.restore();
  }`);
    return source;
  });
})();
