(()=>{
  "use strict";
  (window.__heistV90Patches||(window.__heistV90Patches=[])).push((source,replaceFunction)=>{
    source=replaceFunction(source,"updateDialTarget","dialAttempt",`  function updateDialTarget(){
    const zone=$("dialTarget"),needle=$("dialNeedle"),round=$("dialRound"),dir=$("dialDirection");
    if(zone){const start=crack.target-crack.window/2;zone.style.background="conic-gradient(from "+start+"deg,rgba(88,239,164,.96) 0deg "+crack.window+"deg,transparent "+crack.window+"deg 360deg)";}
    if(needle)needle.style.setProperty("--dial-angle",crack.needle+"deg");
    if(round)round.textContent="СЕКТОР "+(crack.round+1)+"/"+crack.rounds;
    if(dir)dir.textContent=crack.direction>0?"↻ СТРЕЛКА ПО ЧАСОВОЙ":"↺ СТРЕЛКА ПРОТИВ ЧАСОВОЙ";
  }`);
    return source;
  });
})();
