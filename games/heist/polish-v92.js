(()=>{
  "use strict";
  const $=id=>document.getElementById(id),focus=$("safeFocus"),door=$("safeDoor"),overlay=$("crackOverlay");
  if(!focus)return;
  let image=$("safeSpriteFocus");
  if(!image){image=document.createElement("img");image.id="safeSpriteFocus";image.className="safeSpriteFocus";image.alt="Сейф";image.decoding="async";image.draggable=false;focus.appendChild(image);}

  const showSprite=(key,tier)=>{
    const src=window.__HEIST_SAFE_ASSET_URLS__?.[key];if(!src)return;
    focus.dataset.safeSprite=key;focus.classList.remove("sprite-opening","sprite-shake");focus.classList.add("has-sprite");
    image.classList.remove("loaded");image.src=src;image.alt=tier===4?"Главное хранилище":tier===3?"Элитный сейф":tier===2?"Усиленный сейф":"Обычный сейф";
    image.onload=()=>{image.classList.add("loaded");};
  };

  document.addEventListener("heist:safe-focus",event=>showSprite(event.detail?.spriteKey,Number(event.detail?.tier)||1));

  if(door)new MutationObserver(()=>{
    if(door.classList.contains("shake")){focus.classList.remove("sprite-shake");void focus.offsetWidth;focus.classList.add("sprite-shake");setTimeout(()=>focus.classList.remove("sprite-shake"),380);}
    if(door.classList.contains("open")){focus.classList.remove("sprite-opening");void focus.offsetWidth;focus.classList.add("sprite-opening");}
  }).observe(door,{attributes:true,attributeFilter:["class"]});

  if(overlay)new MutationObserver(()=>{
    if(overlay.classList.contains("hidden")){focus.classList.remove("sprite-opening","sprite-shake");}
    else{const key=focus.dataset.safeSprite;if(key)showSprite(key,document.querySelector(".crackPanel")?.className.match(/tier(\d)/)?.[1]||1);}
  }).observe(overlay,{attributes:true,attributeFilter:["class"]});
})();
