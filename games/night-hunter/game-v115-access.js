(()=>{
'use strict';

const TEST_PIN='6767';
const UNLOCK_KEY='allGamesDevUnlocked';
const LEGACY_UNLOCK_KEY='nightHunterDevUnlocked';
const STABLE_GAME='/games/night-hunter/game-v113.js?v=116';
let loading=false;

function loadScript(src){
  return new Promise((resolve,reject)=>{
    const existing=document.querySelector(`script[data-night-hunter-src="${src}"]`);
    if(existing){resolve();return}
    const script=document.createElement('script');
    script.src=src;
    script.dataset.nightHunterSrc=src;
    script.onload=resolve;
    script.onerror=()=>reject(new Error('Не удалось загрузить тестовую версию.'));
    document.body.appendChild(script);
  });
}

function initEarlyAccess(){
  const start=document.getElementById('start');
  const demo=document.getElementById('demo');
  const error=document.getElementById('startError');
  const box=document.getElementById('earlyAccessBox');
  const input=document.getElementById('devPinInput');
  const button=document.getElementById('devPinButton');
  const hint=document.getElementById('devPinHint');

  if(start){
    start.classList.remove('loading');
    start.disabled=true;
    start.textContent='РАННИЙ ДОСТУП · 25 ИЮЛЯ';
  }
  demo?.classList.add('hidden');
  if(error){error.textContent='';error.style.display='none'}

  const setHint=(text,state='')=>{
    if(!hint)return;
    hint.textContent=text;
    hint.classList.remove('ok','bad','loading');
    if(state)hint.classList.add(state);
  };

  const launchTest=async()=>{
    if(loading)return;
    loading=true;
    if(start){start.disabled=true;start.textContent='ЗАГРУЗКА ТЕСТОВОЙ ВЕРСИИ…'}
    if(input)input.disabled=true;
    if(button)button.disabled=true;
    setHint('PIN принят. Загружаем стабильную тестовую сборку…','loading');

    try{
      await loadScript(STABLE_GAME);
      box?.classList.add('unlocked');
      setHint('Тестовый доступ открыт.','ok');
      setTimeout(()=>box?.classList.add('hiddenAccess'),700);
    }catch(err){
      loading=false;
      if(start){start.disabled=true;start.textContent='РАННИЙ ДОСТУП · 25 ИЮЛЯ'}
      if(input)input.disabled=false;
      if(button)button.disabled=false;
      setHint(err.message||'Ошибка загрузки тестовой версии.','bad');
    }
  };

  const unlock=()=>{
    const value=(input?.value||'').replace(/\D/g,'').slice(0,4);
    if(value!==TEST_PIN){
      setHint('Неверный PIN-код.','bad');
      if(input){input.value='';input.focus()}
      return;
    }
    localStorage.setItem(UNLOCK_KEY,'1');
    localStorage.removeItem(LEGACY_UNLOCK_KEY);
    launchTest();
  };

  input?.addEventListener('input',()=>{
    input.value=input.value.replace(/\D/g,'').slice(0,4);
    if(input.value.length===4)setHint('Нажмите «Тестовый вход».');
  });
  input?.addEventListener('keydown',event=>{if(event.key==='Enter')unlock()});
  button?.addEventListener('click',unlock);

  if(localStorage.getItem(LEGACY_UNLOCK_KEY)==='1')localStorage.setItem(UNLOCK_KEY,'1');
  if(localStorage.getItem(UNLOCK_KEY)==='1')launchTest();
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initEarlyAccess);
else initEarlyAccess();
})();