(()=>{
  'use strict';
  const overlay=document.getElementById('welcomeOverlay');
  const close=document.getElementById('welcomeClose');
  if(!overlay||!close)return;
  const show=()=>{
    overlay.classList.add('show');
    overlay.setAttribute('aria-hidden','false');
    document.body.style.overflow='hidden';
    window.Telegram?.WebApp?.HapticFeedback?.notificationOccurred?.('warning');
  };
  const hide=()=>{
    overlay.classList.remove('show');
    overlay.setAttribute('aria-hidden','true');
    document.body.style.overflow='';
  };
  close.addEventListener('click',hide);
  overlay.addEventListener('click',e=>{if(e.target===overlay)hide();});
  setTimeout(show,350);
})();
