(()=>{
'use strict';

const $=id=>document.getElementById(id);
const tg=window.Telegram?.WebApp;
const stage=$('stage');
const intro=$('intro');
const objective=$('objective');
const detail=$('objectiveDetail');
const locationLabel=$('location');
const clock=$('clock');
const caption=$('caption');
const staticFx=$('staticFx');

if(!stage||!objective)return;
document.body.classList.add('reality117');

const layer=document.createElement('div');
layer.id='horrorLayer';
layer.innerHTML=`
  <div class="h117-fog"></div>
  <div class="h117-shadow"><i></i></div>
  <div class="h117-face"><i></i><i></i></div>
  <div class="h117-hands"><i></i><i></i></div>
  <div class="h117-whisper"></div>
  <div class="h117-flash"></div>`;
stage.appendChild(layer);

const whisper=layer.querySelector('.h117-whisper');
const shadow=layer.querySelector('.h117-shadow');
const face=layer.querySelector('.h117-face');
const hands=layer.querySelector('.h117-hands');
const flash=layer.querySelector('.h117-flash');

let currentPhase='';
let scareTimer=0;
let audio=null;
let cameraRaf=0;
let cameraOverlay=null;
let originalClock='';
let started=false;

const phaseRules=[
  {
    key:'gate',match:/ДОЙДИ ДО ПРОХОДНОЙ/,
    text:'Все рабочие выходят с территории, но никто не разговаривает. Один человек стоит против потока и смотрит только на тебя.',
    location:'ДОРОГА К ALIVSPORT · КАМЕРА УЖЕ ВИДИТ ТЕБЯ'
  },
  {
    key:'post',match:/ДОЙДИ ДО ПОСТА|СЕСТЬ ЗА ПОСТ/,
    text:'В журнале твоя подпись уже стоит. Время приёма смены — 06:00. Рядом приписано: «не впускайте второго».',
    location:'ПОСТ ДЕЖУРНОГО · ВНУТРИ КТО-ТО ДЫШИТ'
  },
  {
    key:'machine4',match:/СТАНОК №4/,
    text:'Станок печатает на металле время твоей смерти. Каждая новая деталь показывает время на минуту раньше.',
    location:'ОСНОВНОЙ ЦЕХ · ОБОРУДОВАНИЕ НЕ ОСТАНОВЛЕНО'
  },
  {
    key:'anomaly',match:/НЕСООТВЕТСТВИЕ|ПРОВЕРЬ КАМЕРЫ/,
    text:'На CAM 07 стоит человек с твоим лицом. На соседней камере видно, что он находится прямо за креслом оператора.',
    location:'ПОСТ ДЕЖУРНОГО · НЕ ОБОРАЧИВАЙСЯ'
  },
  {
    key:'breaker',match:/ВОССТАНОВИ ПИТАНИЕ|ГЛАВНЫЙ ЩИТ/,
    text:'Свет погас только в той части цеха, где находишься ты. На камерах все лампы продолжают гореть.',
    location:'ЛИНИЯ 047 · ПИТАНИЕ ПОДАЁТСЯ НЕ СЮДА'
  },
  {
    key:'locker',match:/ШКАФЧИК|ЛИЧНЫЕ ВЕЩИ/,
    text:'В шкафчике лежит твоя одежда, мокрая и холодная. В кармане — ключ от двери, которую ты ещё не видел.',
    location:'ШКАФЧИК МАСТЕРА · ВНУТРИ ЕСТЬ МЕСТО ДЛЯ ТЕБЯ'
  },
  {
    key:'compressor',match:/КОМПРЕССОР/,
    text:'Стук идёт из герметичного ресивера. Манометр поднимается каждый раз, когда ты задерживаешь дыхание.',
    location:'КОМПРЕССОРНАЯ · ДАВЛЕНИЕ ИЗНУТРИ'
  },
  {
    key:'zeroCam',match:/НОВЫЙ КАНАЛ|ОТКРОЙ КАМЕРЫ/,
    text:'Появилась CAM 00. Она установлена внутри твоего шкафчика и показывает, как ты стоишь перед монитором.',
    location:'НЕИЗВЕСТНЫЙ КАНАЛ · ИСТОЧНИК РЯДОМ'
  },
  {
    key:'oldShop',match:/СТАРЫЙ ЦЕХ|ОТКРОЙ ДВЕРЬ/,
    text:'Из-за двери слышен твой голос. Он спокойно просит не открывать и считает до трёх раньше, чем ты успеваешь подумать.',
    location:'ЦЕХ №0 · ДВЕРЬ ОТКРЫВАЕТСЯ ИЗНУТРИ'
  },
  {
    key:'machine0',match:/СТАНОК №0|РУЧНОЙ ЗАПУСК/,
    text:'На панели нет кнопки запуска. Есть только кнопка «ПРИНЯТЬ ОПЕРАТОРА». Под ней уже горит твоё имя.',
    location:'ЦЕХ №0 · ОПЕРАТОР ОБНАРУЖЕН'
  },
  {
    key:'final',match:/ПЕРЕДАЙ СМЕНУ|ВЕРНИСЬ К ПОСТУ|ЗАВЕРШИ СМЕНУ/,
    text:'У проходной ждёт утренняя смена. У каждого рабочего твоё лицо, но только один из них моргает.',
    location:'06:00 · СМЕНА НЕ ЗАКАНЧИВАЕТСЯ'
  }
];

const noteLore={
  rules:{
    title:'Правила для сотрудника, который пришёл вторым',
    kind:'ЛИСТ, ПРИКЛЕЕННЫЙ ИЗНУТРИ ШКАФА',
    body:`1. Не отвечай, когда тебя зовут твоим голосом.\n2. После 23:47 не смотри на людей через стекло поста. Они замечают взгляд.\n3. Если на CAM 07 ты стоишь спиной — не оборачивайся в реальности.\n4. Три удара пресса означают, что один оператор уже принят.\n5. Никогда не произноси число сотрудников вслух. Завод исправит ошибку.\n6. Если читаешь шестой пункт — предыдущие пять уже не помогли.`
  },
  operator:{
    title:'Я пишу это до того, как найду записку',
    kind:'ПОЧЕРК СОВПАДАЕТ С ТВОИМ',
    body:`Я думал, что фигура копирует меня. Нет.\n\nОна была первой. Я копирую её каждый раз, когда принимаю смену.\n\nНе ремонтируй неисправности. Каждая починенная система возвращает ей часть тела: камеры — глаза, щит — свет, компрессор — дыхание, станок №0 — лицо.\n\nЕсли ты уже всё починил, не ищи выход. Ищи место, где оставишь эту записку.`
  },
  maintenance:{
    title:'Наряд №047: извлечение оператора',
    kind:'ДОКУМЕНТ НЕ ИМЕЕТ ДАТЫ СОЗДАНИЯ',
    body:`Объект: станок №0.\nОперация: извлечение оператора из внутренней полости.\n\nКоличество обнаруженных тел: 0.\nКоличество обнаруженных голосов: 12.\n\nПоследний голос назвал себя Ивчем и попросил передать смену.\n\nВнизу стоит свежая подпись. Чернила ещё тёплые.`
  },
  photo:{
    title:'Снимок сделан через шесть минут',
    kind:'ФОТОГРАФИЯ ИЗ БУДУЩЕГО',
    body:`На фотографии пост дежурного. Часы показывают время на шесть минут позже текущего.\n\nТы сидишь перед мониторами. За креслом стоит высокий человек без лица. Его руки лежат у тебя на плечах.\n\nНа следующем снимке кресло пустое.\n\nНа последнем снимке человек уже смотрит из-за объектива.`
  },
  radioLog:{
    title:'Запись рации, сделанная твоим ртом',
    kind:'КАНАЛ 047 · ГОЛОС НЕ ПРИНАДЛЕЖИТ РАЦИИ',
    body:`02:17 — «Пост, не отвечай мне».\n02:18 — «Я стою в старом цехе и вижу, как ты слушаешь эту запись».\n02:19 — четыре секунды тишины. Затем слышен твой будущий крик.\n02:20 — голос спокойно говорит: «Теперь ты знаешь, когда кричать».\n02:21 — звук подписи на бумаге.\n02:22 — «Смена принята».`
  },
  shiftMap:{
    title:'План, который меняется, пока ты не смотришь',
    kind:'СХЕМА ЭВАКУАЦИИ · ВЫХОД НЕ УКАЗАН',
    body:`Коридор к выходу нарисован замкнутым кругом.\n\nКрасная линия начинается у проходной, проходит через все места, где ты уже был, и заканчивается внутри контура твоего тела.\n\nС обратной стороны схема старого цеха. Вместо номера помещения написано: «ПОСТ ДЕЖУРНОГО».\n\nВ правом нижнем углу появляется новая стрелка. Она указывает за твою спину.`
  }
};

function initAudio(){
  if(audio)return;
  try{
    const ac=new(window.AudioContext||window.webkitAudioContext)();
    const master=ac.createGain();master.gain.value=.035;master.connect(ac.destination);
    const hum=ac.createOscillator(),humGain=ac.createGain();
    hum.type='sine';hum.frequency.value=43;humGain.gain.value=.45;
    hum.connect(humGain).connect(master);hum.start();
    audio={ac,master,hum,humGain};
  }catch(_){audio=null}
}

function sting(freq=70,duration=.45,volume=.15){
  initAudio();if(!audio)return;
  try{
    audio.ac.resume?.();
    const osc=audio.ac.createOscillator(),gain=audio.ac.createGain();
    osc.type='sawtooth';osc.frequency.setValueAtTime(freq,audio.ac.currentTime);
    osc.frequency.exponentialRampToValueAtTime(Math.max(22,freq*.36),audio.ac.currentTime+duration);
    gain.gain.setValueAtTime(volume,audio.ac.currentTime);
    gain.gain.exponentialRampToValueAtTime(.001,audio.ac.currentTime+duration);
    osc.connect(gain).connect(audio.master);osc.start();osc.stop(audio.ac.currentTime+duration);
  }catch(_){}
}

function vibrate(kind='medium'){
  try{tg?.HapticFeedback?.impactOccurred?.(kind)}catch(_){}
}

function showWhisper(text,seconds=3.2){
  whisper.textContent=text;
  whisper.classList.remove('show');void whisper.offsetWidth;whisper.classList.add('show');
  setTimeout(()=>whisper.classList.remove('show'),seconds*1000);
}

function staticBurst(strong=false){
  staticFx?.classList.add('show');
  flash.classList.toggle('strong',strong);flash.classList.add('show');
  setTimeout(()=>{staticFx?.classList.remove('show');flash.classList.remove('show','strong')},strong?850:380);
  sting(strong?53:88,strong?.7:.28,strong?.22:.1);vibrate(strong?'heavy':'medium');
}

function shadowPass(){
  shadow.classList.remove('show');void shadow.offsetWidth;shadow.classList.add('show');
  setTimeout(()=>shadow.classList.remove('show'),1800);
}

function faceFlash(){
  face.classList.add('show');hands.classList.add('show');staticBurst(true);
  setTimeout(()=>{face.classList.remove('show');hands.classList.remove('show')},310);
}

function phaseFromObjective(text){return phaseRules.find(rule=>rule.match.test(text))||null}

function applyPhase(){
  const text=objective.textContent||'';
  const rule=phaseFromObjective(text);
  if(!rule)return;
  if(detail&&detail.dataset.h117!==rule.key){detail.textContent=rule.text;detail.dataset.h117=rule.key}
  if(locationLabel)locationLabel.textContent=rule.location;
  if(currentPhase===rule.key)return;
  currentPhase=rule.key;
  document.body.dataset.horrorPhase=rule.key;
  if(['anomaly','breaker','locker','compressor','zeroCam','oldShop','machine0','final'].includes(rule.key))document.body.classList.add('horror-night');
  const phaseScares={
    post:['В журнале уже есть твоя подпись.','Ты пришёл не первым.'],
    machine4:['Станок остановлен. Звук резки продолжается.','НЕ СМОТРИ ВНУТРЬ'],
    anomaly:['CAM 07: ОБЪЕКТ ПОВЕРНУЛСЯ','Он услышал, что ты открыл камеры.'],
    breaker:['ЛИНИЯ 047 ПИТАЕТСЯ ОТ ТВОЕГО ПОСТА','Свет нужен не тебе.'],
    locker:['ВНУТРИ ШКАФЧИКА КТО-ТО СДЕЛАЛ ВДОХ','Не открывай его полностью.'],
    compressor:['ДАВЛЕНИЕ РАСТЁТ, КОГДА ТЫ ДЫШИШЬ','Он дышит вместе с тобой.'],
    zeroCam:['CAM 00 ПОДКЛЮЧЕНА','Эта камера находится слишком близко.'],
    oldShop:['ТВОЙ ГОЛОС: «НЕ ОТКРЫВАЙ»','Он знает, что ты всё равно откроешь.'],
    machine0:['ОПЕРАТОР ПРИНЯТ','Заводу не нужен второй.'],
    final:['УТРЕННЯЯ СМЕНА УЖЕ ВНУТРИ','Выбери, кто из вас останется.']
  };
  const scare=phaseScares[rule.key];
  if(scare){setTimeout(()=>{staticBurst(['anomaly','zeroCam','machine0','final'].includes(rule.key));showWhisper(scare[0],3.4);if(caption)caption.textContent=scare[1]},450)}
}

function patchNote(){
  const modal=$('noteModal');if(!modal||modal.classList.contains('hidden'))return;
  const title=$('noteTitle'),kind=$('noteKind'),body=$('noteBody');if(!title||!body)return;
  const raw=(title.textContent||'').toLowerCase();
  let key='';
  if(raw.includes('правил'))key='rules';
  else if(raw.includes('оператор')||raw.includes('следующую ночь'))key='operator';
  else if(raw.includes('наряд'))key='maintenance';
  else if(raw.includes('бригад')||raw.includes('фотограф')||raw.includes('снимок'))key='photo';
  else if(raw.includes('раци')||raw.includes('вызова 047'))key='radioLog';
  else if(raw.includes('план')||raw.includes('помещен'))key='shiftMap';
  const lore=noteLore[key];if(!lore||body.dataset.h117===key)return;
  title.textContent=lore.title;kind.textContent=lore.kind;body.textContent=lore.body;body.dataset.h117=key;
  setTimeout(()=>showWhisper('Некоторые буквы появились после того, как ты начал читать.',3.8),700);
}

function patchChoice(){
  const modal=$('choiceModal');if(!modal||modal.classList.contains('hidden'))return;
  const h=modal.querySelector('h1'),p=modal.querySelector('p');
  if(h)h.textContent='Кто из вас на самом деле закончил смену?';
  if(p)p.textContent='На проходной стоит человек с твоим лицом. Монитор показывает второго — он находится за твоим креслом и читает этот текст вместе с тобой.';
  const sign=$('signAgain'),refuse=$('refuseSign');
  if(sign){sign.querySelector('b').textContent='ПОДПИСАТЬ ЕГО ИМЕНЕМ';sign.querySelector('small').textContent='Оставить ему своё место снаружи'}
  if(refuse){refuse.querySelector('b').textContent='НЕ ПЕРЕДАВАТЬ СМЕНУ';refuse.querySelector('small').textContent='Остаться единственным оператором внутри'}
}

function patchEnding(){
  const modal=$('endingModal');if(!modal||modal.classList.contains('hidden')||modal.dataset.h117)return;
  modal.dataset.h117='1';
  const eyebrow=$('endingEyebrow'),title=$('endingTitle'),text=$('endingText'),quote=$('endingQuote');
  const signed=(title?.textContent||'').toLowerCase().includes('передал');
  if(signed){
    eyebrow.textContent='СМЕНА ПРИНЯТА · СОТРУДНИК НЕ НАЙДЕН';
    title.textContent='Снаружи вышел не ты';
    text.textContent='Дверь проходной открывается в тот же солнечный вечер. Толпа рабочих расступается перед человеком с твоим лицом. Ты остаёшься на мониторе CAM 00 и видишь, как он уходит домой. Когда экран гаснет, за стеклом поста кто-то садится в твоё кресло.';
    quote.textContent='«Спасибо, что закончил мою смену». Голос звучит изнутри тебя.';
  }else{
    eyebrow.textContent='ОТКАЗ НЕ ЗАРЕГИСТРИРОВАН';
    title.textContent='Завод оставил обоих';
    text.textContent='Ты не ставишь подпись. Все двери открываются одновременно, но за каждой находится тот же пост дежурного. На мониторах появляется изображение комнаты сверху: в ней два человека. Второй стоит слишком близко, чтобы камера могла его видеть.';
    quote.textContent='В журнале появляется новая строка: «Смену приняли: 2. Покинули объект: 0».';
  }
  setTimeout(faceFlash,650);
}

function ensureCameraOverlay(){
  const screen=document.querySelector('.cameraScreen');
  if(!screen)return null;
  if(cameraOverlay&&cameraOverlay.isConnected)return cameraOverlay;
  cameraOverlay=document.createElement('canvas');cameraOverlay.className='h117-camera-overlay';
  screen.appendChild(cameraOverlay);return cameraOverlay;
}

function drawCameraHorror(now){
  const modal=$('cameraModal');
  if(!modal||modal.classList.contains('hidden')){cancelAnimationFrame(cameraRaf);cameraRaf=0;return}
  const overlay=ensureCameraOverlay(),base=$('cameraFeed');if(!overlay||!base)return;
  const rect=base.getBoundingClientRect(),dpr=Math.min(2,devicePixelRatio||1);
  if(overlay.width!==Math.round(rect.width*dpr)||overlay.height!==Math.round(rect.height*dpr)){
    overlay.width=Math.round(rect.width*dpr);overlay.height=Math.round(rect.height*dpr);
  }
  const g=overlay.getContext('2d');g.setTransform(dpr,0,0,dpr,0,0);g.clearRect(0,0,rect.width,rect.height);
  const active=document.querySelector('#cameraControls button.active')?.textContent||'';
  const pulse=(Math.sin(now/160)+1)/2;
  g.fillStyle='rgba(255,255,255,.025)';for(let y=0;y<rect.height;y+=5)g.fillRect(0,y,rect.width,1);
  g.fillStyle='rgba(110,255,232,.045)';g.fillRect(8,(now/8)%rect.height,rect.width-16,8);
  g.strokeStyle='rgba(120,238,221,.22)';g.strokeRect(8,8,rect.width-16,rect.height-16);
  if(/07|ПОСТ/.test(active)){
    const x=rect.width*.72,y=rect.height*.76,s=Math.max(.65,rect.width/700);
    g.save();g.translate(x,y);g.fillStyle='rgba(0,0,0,.92)';g.beginPath();g.ellipse(0,-35*s,23*s,70*s,0,0,Math.PI*2);g.fill();g.beginPath();g.arc(0,-108*s,19*s,0,Math.PI*2);g.fill();
    g.shadowColor='#ff3155';g.shadowBlur=12;g.fillStyle=`rgba(255,55,84,${.65+pulse*.35})`;g.beginPath();g.arc(-6*s,-110*s,2.8*s,0,Math.PI*2);g.arc(6*s,-110*s,2.8*s,0,Math.PI*2);g.fill();g.restore();
    g.strokeStyle=`rgba(255,65,94,${.5+pulse*.45})`;g.lineWidth=2;g.strokeRect(x-38*s,y-145*s,76*s,151*s);
    g.fillStyle='#ff5b73';g.font='900 11px monospace';g.fillText('ЛИЦО: СОВПАДЕНИЕ 100%',rect.width*.45,rect.height-18);
  }
  if(/00/.test(active)){
    g.fillStyle=`rgba(255,48,76,${.15+pulse*.15})`;g.fillRect(rect.width*.2,rect.height*.17,rect.width*.6,5);
    g.fillStyle='#ff536e';g.font='900 12px monospace';g.fillText('КАМЕРА УСТАНОВЛЕНА ВНУТРИ ОПЕРАТОРА',rect.width*.12,rect.height*.92);
    for(let i=0;i<5;i++){const x=rect.width*(.22+i*.14);g.strokeStyle='rgba(0,0,0,.78)';g.lineWidth=7;g.beginPath();g.moveTo(x,0);g.lineTo(x+Math.sin(now/350+i)*12,rect.height*.25);g.stroke()}
  }
  cameraRaf=requestAnimationFrame(drawCameraHorror);
}

function startCameraLoop(){if(!cameraRaf)cameraRaf=requestAnimationFrame(drawCameraHorror)}

function randomScare(){
  if(!started||!intro?.classList.contains('hidden')||document.querySelector('.overlay:not(.hidden)'))return;
  const advanced=['anomaly','breaker','locker','compressor','zeroCam','oldShop','machine0','final'].includes(currentPhase);
  const roll=Math.random();
  if(roll<.25){showWhisper(advanced?['НЕ СМОТРИ НА СВОЮ ТЕНЬ','ОН ИДЁТ, КОГДА ТЫ СТОИШЬ','КАМЕРА ЗА ТВОЕЙ СПИНОЙ ВКЛЮЧЕНА','ТЫ СЛЫШИШЬ НЕ СВОЁ ДЫХАНИЕ'][Math.floor(Math.random()*4)]:'Кто-то вошёл следом за тобой.',2.8);sting(60,.35,.08)}
  else if(roll<.5)shadowPass();
  else if(roll<.68){originalClock=clock?.textContent||'';if(clock)clock.textContent='23:47';staticBurst(false);setTimeout(()=>{if(clock&&originalClock)clock.textContent=originalClock},850)}
  else if(roll<.82&&advanced)faceFlash();
  else{if(caption)caption.textContent=advanced?'Система сообщает: «В цехе на одного человека больше».':'У проходной все одновременно повернули головы.';staticBurst(false)}
}

function scheduleScare(){clearTimeout(scareTimer);scareTimer=setTimeout(()=>{randomScare();scheduleScare()},9000+Math.random()*9000)}

const observer=new MutationObserver(()=>{
  applyPhase();patchNote();patchChoice();patchEnding();
  const cameraModal=$('cameraModal');if(cameraModal&&!cameraModal.classList.contains('hidden'))startCameraLoop();
});
observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']});

$('start')?.addEventListener('click',()=>{started=true;initAudio();scheduleScare();setTimeout(()=>showWhisper('На территории уже зарегистрирован сотрудник с твоим именем.',3.8),1800)},{capture:true});
$('demo')?.addEventListener('click',()=>{started=true;initAudio();scheduleScare()},{capture:true});

const introTitle=intro?.querySelector('.eyebrow');if(introTitle)introTitle.textContent='REALITY 117 · HORROR CUT · В РАЗРАБОТКЕ';
const introText=intro?.querySelector('h1 + p');if(introText)introText.textContent='На заводе уже началась твоя смена. Камеры показывают, что ты внутри, хотя ты всё ещё стоишь у проходной.';
const cards=intro?.querySelectorAll('.features > div');
if(cards?.[0]){cards[0].querySelector('b').textContent='ТОЛПА НЕ УХОДИТ';cards[0].querySelector('span').textContent='Рабочие покидают завод снова и снова, но их количество не уменьшается'}
if(cards?.[1]){cards[1].querySelector('b').textContent='ЦЕХ №0';cards[1].querySelector('span').textContent='Помещение отсутствует на плане, но знает имя ночного оператора'}
if(cards?.[2]){cards[2].querySelector('b').textContent='КАМЕРЫ ПОМНЯТ';cards[2].querySelector('span').textContent='Записи показывают события раньше, чем они происходят'}

applyPhase();scheduleScare();
})();
