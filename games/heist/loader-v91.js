(()=>{
  "use strict";
  const VERSION="91";
  const patches=[1,2,3,4,5].map(n=>"/games/heist/patch-v88-"+n+".js").concat([
    "/games/heist/patch-v90.js",
    "/games/heist/patch-v90-hotfix.js",
    "/games/heist/patch-v91.js"
  ]);
  const post=[
    "/games/heist/enhance-v83.js",
    "/games/heist/ui-v86.js",
    "/games/heist/polish-v87.js",
    "/games/heist/polish-v88.js",
    "/games/heist/polish-v91.js"
  ];
  const loadScript=src=>new Promise((resolve,reject)=>{const s=document.createElement("script");s.src=src+"?v="+VERSION;s.onload=resolve;s.onerror=reject;document.body.appendChild(s)});
  const replaceFunction=(source,name,nextName,replacement)=>{const pattern=new RegExp("  function "+name+"\\([^]*?\\n  function "+nextName);if(!pattern.test(source)){console.warn("Heist v91: function "+name+" not patched");return source}return source.replace(pattern,replacement+"\n  function "+nextName)};
  const boot=async()=>{
    try{
      window.__heistV88Patches=[];window.__heistV90Patches=[];window.__heistV91Patches=[];
      for(const src of patches)await loadScript(src);
      const response=await fetch("/games/heist/game.js?v="+VERSION,{cache:"no-store"});
      if(!response.ok)throw new Error("HTTP "+response.status);
      let source=await response.text();
      for(const patch of window.__heistV88Patches)source=patch(source,replaceFunction);
      for(const patch of window.__heistV90Patches)source=patch(source,replaceFunction);
      for(const patch of window.__heistV91Patches)source=patch(source,replaceFunction);
      const blob=new Blob([source],{type:"text/javascript"}),url=URL.createObjectURL(blob),script=document.createElement("script");
      script.src=url;
      script.onload=async()=>{URL.revokeObjectURL(url);for(const src of post){try{await loadScript(src)}catch(error){console.error("Heist post-script failed",src,error)}}};
      script.onerror=async error=>{console.error("Heist v91 transformed game failed",error);URL.revokeObjectURL(url);await loadScript("/games/heist/game.js?v=91")};
      document.body.appendChild(script);
    }catch(error){console.error("Heist v91 loader failed",error);await loadScript("/games/heist/game.js?v=91")}
  };
  boot();
})();
