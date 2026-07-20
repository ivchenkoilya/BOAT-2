(()=>{
  'use strict';
  /* Compatibility shim.
     Hero skin selection is now server-synchronised by hero-skins-sync-v100.js.
     The old localStorage selector is intentionally disabled so it cannot open
     a competing modal or show a different portrait on another device. */
  document.documentElement.dataset.heroSkinsUi='server-v100';
})();
