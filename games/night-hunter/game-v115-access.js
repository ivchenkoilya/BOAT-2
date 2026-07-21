(()=>{
'use strict';
const TEST_PIN='6767';
const GAME_SCRIPT='/games/night-hunter/escape-v118.js?v=1187';
const STYLE='/games/night-hunter/style-v118.css?v=1187';
const shell=`<main class="factoryApp" id="factoryApp">
    <header class="factoryTopbar">
      <button class="backButton" id="backButton" type="button">← ИГРЫ</button>
      <div class="factoryBrand">
        <b>СБЕЖАТЬ С ЗАВОДА</b>
        <small id="zoneLabel">ALIV GYM · НАЧАЛО СМЕНЫ</small>
      </div>
      <div class="scoreBox"><small>ОЧКИ</small><b id="scoreValue">0</b></div>
    </header>

    <section class="gameStage" id="gameStage">
      <canvas id="factoryCanvas" aria-label="Игра Сбежать с завода"></canvas>
      <div class="stageShade"></div>

      <div class="hudPanel">
        <div class="timeCard"><small>ВРЕМЯ</small><b id="gameClock">08:00</b></div>
        <div class="objectiveCard">
          <small>ТЕКУЩАЯ ЗАДАЧА</small>
          <b id="objectiveTitle">ЗАЙДИ НА ЗАВОД</b>
          <span id="objectiveText">Сегодня нужно закрыть 50 заказов, чтобы отец постарался отпустить тебя в выходной.</span>
        </div>
      </div>

      <div class="ordersCard">
        <div><small>ЗАКАЗЫ</small><b><span id="ordersDone">0</span>/<span id="ordersTotal">50</span></b></div>
        <div class="ordersProgress"><i id="ordersBar"></i></div>
        <span id="currentOrder">Стойка приседа напольная</span>
      </div>

      <div class="phoneToast" id="phoneToast">
        <small id="phoneSender">ДРУЗЬЯ</small>
        <b id="phoneMessage">Палатки уже нашли. Ты с нами?</b>
      </div>

      <div class="joystick" id="joystick" aria-label="Джойстик">
        <div class="joystickRing"></div>
        <div class="joystickKnob" id="joystickKnob"></div>
      </div>

      <button class="actionButton hidden" id="actionButton" type="button">
        <span id="actionIcon">✋</span>
        <b id="actionLabel">ДЕЙСТВИЕ</b>
        <small id="actionHint">ПОДОЙДИ БЛИЖЕ</small>
      </button>

      <button class="runButton" id="runButton" type="button"><span>🏃</span><b>БЕГ</b></button>
    </section>
  </main>

  <div class="overlay" id="introOverlay">
    <section class="introCard">
      <div class="poster">
        <div class="posterSun"></div>
        <div class="posterFactory"></div>
        <div class="posterWorker"></div>
        <div class="posterFence"></div>
      </div>
      <div class="eyebrow">REALITY 118 · STANDALONE FACTORY ESCAPE</div>
      <h1>Сбежать с завода:<br>50 заказов до свободы</h1>
      <p>Полный рабочий день оператора ЧПУ на ALIV GYM. Каждый раз, когда ты заканчиваешь заказы, отец приносит новые.</p>
      <div class="featureGrid">
        <div><b>08:00–17:00</b><span>Весь день с реальными участками производства</span></div>
        <div><b>ОТЕЦ И ШВАРЦ</b><span>Давление начальства и непредсказуемый сварщик</span></div>
        <div><b>4 КОНЦОВКИ</b><span>Ворота, баня, провал или вечная переработка</span></div>
      </div>

      <div class="pinBox" id="pinBox">
        <b>ВНУТРЕННЕЕ ТЕСТИРОВАНИЕ</b>
        <span>Введите PIN владельца проекта</span>
        <div class="pinRow">
          <input id="pinInput" type="password" inputmode="numeric" maxlength="4" placeholder="••••" autocomplete="off">
          <button id="pinButton" type="button">ВОЙТИ</button>
        </div>
        <small id="pinHint">PIN-код состоит из 4 цифр.</small>
      </div>

      <button class="primaryButton" id="startButton" type="button" disabled>СНАЧАЛА ВВЕДИТЕ PIN</button>
      <div class="loadError" id="loadError"></div>
    </section>
  </div>

  <div class="overlay hidden" id="dialogOverlay">
    <section class="dialogCard">
      <div class="characterPortrait" id="dialogPortrait"><span id="dialogPortraitText">О</span></div>
      <div class="dialogContent">
        <small id="dialogRole">ОТЕЦ · ДИРЕКТОР</small>
        <h2 id="dialogName">Отец</h2>
        <p id="dialogText"></p>
        <div class="dialogChoices" id="dialogChoices"></div>
        <button class="primaryButton" id="dialogContinue" type="button">ПОНЯЛ</button>
      </div>
    </section>
  </div>

  <div class="overlay hidden" id="workOverlay">
    <section class="workCard">
      <div class="workHead">
        <div><small id="workDepartment">ЛАЗЕРНЫЙ УЧАСТОК</small><b id="workTitle">РАСКРОЙ ДЕТАЛЕЙ</b></div>
        <span id="workCounter">0/6</span>
      </div>
      <p id="workDescription"></p>
      <div class="workBoard" id="workBoard"></div>
      <div class="workProgress"><i id="workBar"></i></div>
      <small class="workHint" id="workHint">Нажимай на подсвеченные элементы.</small>
    </section>
  </div>

  <div class="overlay hidden" id="routeOverlay">
    <section class="routeCard">
      <div class="eyebrow">16:35 · ОНИ УЕХАЛИ</div>
      <h1>Работа никогда не закончится сама</h1>
      <p>Отец оставил ещё три срочных заказа и уехал вместе с дядей Шварцем. Решай, что делать дальше.</p>
      <div class="routeGrid">
        <button id="routeBath" type="button"><b>🧖 ЧЕРЕЗ БАНЮ</b><span>Забрать ключ в шкафчике отца и уйти через двор</span></button>
        <button id="routeGate" type="button"><b>🚧 ЧЕРЕЗ ВОРОТА</b><span id="gateRouteHint">Нужна помощь дяди Шварца</span></button>
        <button id="routeWork" type="button"><b>⚙️ ОСТАТЬСЯ РАБОТАТЬ</b><span>Закрыть ещё три заказа и отказаться от поездки</span></button>
      </div>
    </section>
  </div>

  <div class="overlay hidden" id="endingOverlay">
    <section class="endingCard">
      <div class="endingIcon" id="endingIcon">🏕️</div>
      <div class="eyebrow" id="endingEyebrow">КОНЦОВКА</div>
      <h1 id="endingTitle">Ты выбрался</h1>
      <p id="endingText"></p>
      <blockquote id="endingQuote"></blockquote>
      <div class="resultGrid">
        <div><small>ЗАКАЗЫ</small><b id="resultOrders">50</b></div>
        <div><small>ОЧКИ</small><b id="resultScore">0</b></div>
        <div><small>ВРЕМЯ</small><b id="resultTime">16:58</b></div>
      </div>
      <button class="primaryButton" id="restartButton" type="button">НАЧАТЬ СМЕНУ ЗАНОВО</button>
      <button class="secondaryButton" id="gamesButton" type="button">В ИГРОВОЙ ЦЕНТР</button>
    </section>
  </div>`;

document.title='Сбежать с завода: 50 заказов до свободы';
document.querySelectorAll('link[rel="stylesheet"]').forEach(link=>link.remove());
const style=document.createElement('link');style.rel='stylesheet';style.href=STYLE;document.head.appendChild(style);
document.body.innerHTML=shell;

const input=document.getElementById('pinInput');
const button=document.getElementById('pinButton');
const hint=document.getElementById('pinHint');
const start=document.getElementById('startButton');
const error=document.getElementById('loadError');
let loading=false;

function setHint(text,state=''){
  if(!hint)return;
  hint.textContent=text;
  hint.classList.remove('ok','bad');
  if(state)hint.classList.add(state);
}
function loadGame(){
  return new Promise((resolve,reject)=>{
    if(window.__FACTORY_ESCAPE_READY__&&window.FactoryEscape){resolve();return;}
    const existing=document.querySelector(`script[data-factory-escape="${GAME_SCRIPT}"]`);
    if(existing){window.addEventListener('factory-escape-ready',resolve,{once:true});return;}
    const script=document.createElement('script');
    script.src=GAME_SCRIPT;
    script.dataset.factoryEscape=GAME_SCRIPT;
    script.onload=()=>window.__FACTORY_ESCAPE_READY__?resolve():reject(new Error('Новый игровой движок загрузился без сигнала готовности.'));
    script.onerror=()=>reject(new Error('Не удалось загрузить новый проект «Сбежать с завода».'));
    document.body.appendChild(script);
  });
}
async function unlock(){
  if(loading)return;
  const value=(input?.value||'').replace(/\D/g,'').slice(0,4);
  if(value!==TEST_PIN){setHint('Неверный PIN-код.','bad');if(input){input.value='';input.focus();}return;}
  loading=true;if(input)input.disabled=true;if(button)button.disabled=true;if(start){start.disabled=true;start.textContent='ЗАГРУЗКА НОВОЙ ИГРЫ…';}
  setHint('PIN принят. Загружаем отдельный игровой движок…');
  try{
    await loadGame();
    if(!window.FactoryEscape?.start)throw new Error('Функция запуска новой игры не найдена.');
    if(start){start.disabled=false;start.textContent='НАЧАТЬ РАБОЧИЙ ДЕНЬ';start.onclick=()=>window.FactoryEscape.start();}
    setHint('Новая игра готова. Старый Night Hunter не загружается.','ok');
  }catch(err){
    loading=false;if(input)input.disabled=false;if(button)button.disabled=false;if(start){start.disabled=true;start.textContent='ОШИБКА ЗАГРУЗКИ';}
    const message=err?.message||'Ошибка загрузки новой игры.';setHint(message,'bad');if(error)error.textContent=message;
  }
}
input?.addEventListener('input',()=>{input.value=input.value.replace(/\D/g,'').slice(0,4);if(input.value.length===4)setHint('Нажмите «Войти».');});
input?.addEventListener('keydown',e=>{if(e.key==='Enter')unlock();});
button?.addEventListener('click',unlock);
input?.focus();
})();