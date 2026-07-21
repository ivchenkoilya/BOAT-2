(()=>{
'use strict';

const TEST_PIN='6767';
const STABLE_GAME='/games/night-hunter/game-v116.js?v=118';
const ESCAPE_SCRIPT='/games/night-hunter/escape-v118.js?v=118';
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

function waitReady(){
  return new Promise((resolve,reject)=>{
    if(window.__NIGHT_HUNTER_READY__){resolve();return}
    if(window.__NIGHT_HUNTER_LOAD_ERROR__){reject(new Error(window.__NIGHT_HUNTER_LOAD_ERROR__));return}
    const cleanup=()=>{
      clearTimeout(timer);
      window.removeEventListener('night-hunter-ready',ready);
      window.removeEventListener('night-hunter-error',failed);
    };
    const ready=()=>{cleanup();resolve()};
    const failed=event=>{cleanup();reject(new Error(event.detail||'Ошибка подготовки Reality 118.'))};
    const timer=setTimeout(()=>{cleanup();reject(new Error('Тестовая версия загружалась слишком долго.'))},28000);
    window.addEventListener('night-hunter-ready',ready,{once:true});
    window.addEventListener('night-hunter-error',failed,{once:true});
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
  const status=document.querySelector('.developmentStatus');
  const card=document.querySelector('#intro .introCard');

  if(card){
    card.style.maxHeight='calc(100dvh - 24px)';
    card.style.overflowY='auto';
    card.style.overscrollBehavior='contain';
  }
  if(status&&box)status.insertAdjacentElement('afterend',box);

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
    window.__NIGHT_HUNTER_READY__=false;
    window.__NIGHT_HUNTER_LOAD_ERROR__='';
    if(start){start.disabled=true;start.textContent='ЗАГРУЗКА ESCAPE CUT…'}
    if(input)input.disabled=true;
    if(button)button.disabled=true;
    setHint('PIN принят. Загружаем рабочий день и побег с ALIV GYM…','loading');

    try{
      await loadScript(STABLE_GAME);
      await waitReady();
      await loadScript(ESCAPE_SCRIPT);
      if(!window.__NIGHT_HUNTER_ESCAPE_READY__)throw new Error('Сюжет побега не успел подготовиться.');
      if(start&&!start.classList.contains('hidden'))start.disabled=false;
      box?.classList.add('unlocked');
      setHint('Reality 118: Escape Cut готова. Можно начинать рабочий день.','ok');
      setTimeout(()=>box?.classList.add('hiddenAccess'),900);
    }catch(err){
      loading=false;
      if(start){start.disabled=true;start.textContent='ОШИБКА ЗАГРУЗКИ'}
      if(input)input.disabled=false;
      if(button)button.disabled=false;
      setHint(err.message||'Ошибка загрузки тестовой версии.','bad');
      if(error){error.textContent=err.message||'Ошибка загрузки тестовой версии.';error.style.display='block'}
    }
  };

  const unlock=()=>{
    const value=(input?.value||'').replace(/\D/g,'').slice(0,4);
    if(value!==TEST_PIN){
      setHint('Неверный PIN-код.','bad');
      if(input){input.value='';input.focus()}
      return;
    }
    launchTest();
  };

  input?.addEventListener('input',()=>{
    input.value=input.value.replace(/\D/g,'').slice(0,4);
    if(input.value.length===4)setHint('Нажмите «Тестовый вход».');
  });
  input?.addEventListener('keydown',event=>{if(event.key==='Enter')unlock()});
  button?.addEventListener('click',unlock);
  input?.focus();
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',initEarlyAccess);
else initEarlyAccess();
})();