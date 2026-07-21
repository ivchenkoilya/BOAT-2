(()=>{
'use strict';

const TEST_PIN='6767';
const STABLE_GAME='/games/night-hunter/game-v113.js?v=118';
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
    const ready=()=>{clearTimeout(timer);resolve()};
    const timer=setTimeout(()=>{
      window.removeEventListener('night-hunter-ready',ready);
      reject(new Error('Тестовая версия загружалась слишком долго.'));
    },20000);
    window.addEventListener('night-hunter-ready',ready,{once:true});
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
    if(start){start.disabled=true;start.textContent='ЗАГРУЗКА ТЕСТОВОЙ ВЕРСИИ…'}
    if(input)input.disabled=true;
    if(button)button.disabled=true;
    setHint('PIN принят. Подготавливаем стабильную тестовую сборку…','loading');

    try{
      await loadScript(STABLE_GAME);
      await waitReady();
      if(start&&!start.classList.contains('hidden'))start.disabled=false;
      box?.classList.add('unlocked');
      setHint('Тестовая сборка готова. Можно начинать смену.','ok');
      setTimeout(()=>box?.classList.add('hiddenAccess'),900);
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
