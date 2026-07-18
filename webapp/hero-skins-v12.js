(()=>{
  'use strict';
  /* Compatibility shim.
     The old version intercepted every data-modal="heroes" button and mixed
     the squad with skins. Reality 52 keeps the sections separate; the actual
     eight-slot skins screen is controlled by raid-ux-v19.js. */
  document.documentElement.dataset.heroSkinsUi='reality52';
})();
