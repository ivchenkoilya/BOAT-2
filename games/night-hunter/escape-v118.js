(()=>{
'use strict';

const $=id=>document.getElementById(id);
const objective=$('objective');
const detail=$('objectiveDetail');
const locationLabel=$('location');
const clock=$('clock');
const stage=$('stage');
const tg=window.Telegram?.WebApp;
if(!objective||!stage)return;

document.body.classList.remove('reality117');
document.body.classList.add('reality118');

const orders=[
  'Стойка приседа напольная','Жим ногами + гакк-присед','Супер Гакс 3 в 1','Гравитрон',
  'Бицепс-машина','Машина Смита','Стойки под штангу','Скамья Скотта',
  'Горизонтальная тяга','Кроссовер','Силовая рама','Комплект деталей для сборки'
];

const story={
  gate:{time:'08:00',title:'ЗАЙДИ НА ЗАВОД',detail:'Сегодня нужно закрыть 50 заказов. Отец сказал, что потом постарается отпустить тебя в выходной.',place:'ДОРОГА К ALIV GYM',done:0,father:'Не тяни время. Сегодня пятьдесят заказов, потом посмотрим насчёт выходного.',friend:'Выезд завтра. Палатки и мангал уже нашли.'},
  post:{time:'08:10',title:'ПОЛУЧИ СПИСОК ЗАКАЗОВ',detail:'Отец уже ждёт у поста с распечаткой. Список длиннее, чем вчера.',place:'ПОСТ ДЕЖУРНОГО',done:2,father:'Начни со стоек и Гакса. Закончишь — подойду, скажу дальше.'},
  machine4:{time:'09:35',title:'ВЫРЕЖИ ПЕРВУЮ ПАРТИЮ',detail:'Размести детали и закрой первые позиции: стойки, Гакс и Машину Смита.',place:'УЧАСТОК ЧПУ · ЛАЗЕР',done:12,father:'Нормально. Только не расслабляйся — там ещё восемь позиций добавились.'},
  anomaly:{time:'11:15',title:'ПРОВЕРЬ НОВЫЙ СПИСОК',detail:'Ты закончил первую партию, но отец уже положил рядом новую стопку заказов.',place:'ПОСТ ДЕЖУРНОГО · КОНТРОЛЬ ЗАКАЗОВ',done:18,father:'Я же говорил: закончил одно — берись за следующее. Что встал?'},
  breaker:{time:'12:05',title:'ВОССТАНОВИ ПИТАНИЕ ЛАЗЕРА',detail:'Во время обеда линия отключилась. Пока остальные в комнате отдыха, нужно быстро вернуть станок в работу.',place:'ГЛАВНЫЙ ЩИТ',done:22,friend:'Мы закупаем еду. Тебя считать? Не пропадай.'},
  locker:{time:'13:25',title:'ЗАЙДИ В КОМНАТУ ОТДЫХА',detail:'На обеде здесь сидят отец, дядя Шварц, красильщик и помощник сборщика. В шкафчике отца лежит ключ от двери во двор.',place:'КОМНАТА ОТДЫХА',done:27,father:'Обед закончен. Пиздуй к станку, там срочные детали.'},
  compressor:{time:'14:40',title:'ЗАКРОЙ СРОЧНЫЕ ПОЗИЦИИ',detail:'Компрессор просел, а заказы продолжают копиться. Нужно удержать давление и закончить ещё одну партию.',place:'КОМПРЕССОРНАЯ',done:36,father:'Ещё немного. Потом, может быть, отпущу. Но сначала закрой всё, что лежит у лазера.'},
  zeroCam:{time:'16:20',title:'ПРОВЕРЬ, КТО ОСТАЁТСЯ',detail:'До конца смены пятнадцать минут. Отец снова принёс несколько заказов и собирается уезжать.',place:'ПОСТ ДЕЖУРНОГО · 16:20',done:44,father:'Мы со Шварцем сейчас поедем. Доделаешь остаток — позвонишь. Только не вздумай бросить.'},
  oldShop:{time:'16:35',title:'ДОЖДИСЬ, ПОКА ОНИ УЕДУТ',detail:'Отец и дядя Шварц покинули завод. Ворота закрыты, но ключ от двора остался в незапертом шкафчике отца.',place:'ЦЕХ ALIV GYM · ОНИ УЕХАЛИ',done:47,friend:'Мы уже собираем вещи. Ты точно едешь с нами?'},
  machine0:{time:'16:45',title:'ЗАБЕРИ КЛЮЧ И ИДИ К БАНЕ',detail:'Дверь в баню находится за лазерным станком. Через неё можно выйти во двор и открыть наружную дверь.',place:'ДВЕРЬ ЗА ЛАЗЕРНЫМ СТАНКОМ',done:49,phone:'ОТЕЦ: Ты там не ушёл? Заказов ещё три штуки нашёл.'},
  final:{time:'16:58',title:'СБЕГИ С ЗАВОДА',detail:'До официального конца смены две минуты. Выбирай: рискнуть воротами или уйти через баню и двор.',place:'ПОСЛЕДНИЙ ШАНС',done:50,friend:'Мы ждём ответ. Через пять минут выезжаем без тебя.'}
};

const phaseMatchers=[
  ['final',/ПЕРЕДАЙ СМЕНУ|ВЕРНИСЬ К ПОСТУ|ЗАВЕРШИ СМЕНУ/],
  ['machine0',/СТАНОК №0|РУЧНОЙ ЗАПУСК/],
  ['oldShop',/СТАРЫЙ ЦЕХ|ОТКРОЙ ДВЕРЬ/],
  ['zeroCam',/НОВЫЙ КАНАЛ|ОТКРОЙ КАМЕРЫ/],
  ['compressor',/КОМПРЕССОР/],
  ['locker',/ШКАФЧИК|ЛИЧНЫЕ ВЕЩИ/],
  ['breaker',/ВОССТАНОВИ ПИТАНИЕ|ГЛАВНЫЙ ЩИТ/],
  ['anomaly',/НЕСООТВЕТСТВИЕ|ПРОВЕРЬ КАМЕРЫ/],
  ['machine4',/СТАНОК №4/],
  ['post',/ДОЙДИ ДО ПОСТА|СЕСТЬ ЗА ПОСТ/],
  ['gate',/ДОЙДИ ДО ПРОХОДНОЙ/]
];

const layer=document.createElement('div');
layer.className='escape118-layer';
layer.innerHTML=`
  <div class="e118-orders"><small>ЗАКАЗЫ ALIV GYM</small><b><span id="e118Done">0</span>/50</b><em id="e118Order">Подготовка смены</em></div>
  <div class="e118-phone" id="e118Phone"><small>СООБЩЕНИЕ</small><b id="e118PhoneFrom">ДРУЗЬЯ</b><p id="e118PhoneText"></p></div>
  <div class="e118-father" id="e118Father"><div class="e118-man"></div><section><small>ОТЕЦ</small><p id="e118FatherText"></p></section></div>
  <div class="e118-shvarts" id="e118Shvarts"><div class="e118-bigman"></div><section><small>ДЯДЯ ШВАРЦ</small><p>Ну что, турист, работать будем или отпуск выпрашивать?</p><div><button id="e118Ask">Сказать про палатки</button><button id="e118Silent">Промолчать</button></div></section></div>`;
stage.appendChild(layer);

const doneEl=$('e118Done'),orderEl=$('e118Order');
const phone=$('e118Phone'),phoneFrom=$('e118PhoneFrom'),phoneText=$('e118PhoneText');
const father=$('e118Father'),fatherText=$('e118FatherText');
const shvarts=$('e118Shvarts');
let currentKey='';
let shvartsHelp=false;
let firstStart=true;

function buzz(type='medium'){
  try{tg?.HapticFeedback?.impactOccurred?.(type)}catch(_){}
}

function showPhone(text,from='ДРУЗЬЯ'){
  phoneFrom.textContent=from;phoneText.textContent=text;
  phone.classList.remove('show');void phone.offsetWidth;phone.classList.add('show');
  buzz('light');setTimeout(()=>phone.classList.remove('show'),4200);
}

function showFather(text){
  fatherText.textContent=text;father.classList.remove('show');void father.offsetWidth;father.classList.add('show');
  buzz('medium');setTimeout(()=>father.classList.remove('show'),4300);
}

function showShvarts(){
  if(shvarts.dataset.used)return;
  shvarts.dataset.used='1';shvarts.classList.add('show');buzz('heavy');
}

$('e118Ask').onclick=()=>{
  shvartsHelp=true;
  shvarts.querySelector('p').textContent='Ладно. Я ничего не видел. Но через ворота не лезь — отец узнает. Иди через баню.';
  setTimeout(()=>shvarts.classList.remove('show'),3000);
};
$('e118Silent').onclick=()=>{
  shvartsHelp=false;
  shvarts.querySelector('p').textContent='Молчишь — значит работать хочешь. Ключи от ворот у меня. Даже не думай.';
  setTimeout(()=>shvarts.classList.remove('show'),3000);
};

function detectKey(text){
  for(const [key,re] of phaseMatchers)if(re.test(text))return key;
  return currentKey||'gate';
}

function applyStory(){
  const raw=objective.textContent||'';
  const key=detectKey(raw);
  const scene=story[key];
  if(!scene)return;

  const phaseChanged=currentKey!==key;
  if(objective.textContent!==scene.title)objective.textContent=scene.title;
  if(detail&&detail.textContent!==scene.detail)detail.textContent=scene.detail;
  if(locationLabel&&locationLabel.textContent!==scene.place)locationLabel.textContent=scene.place;
  if(clock&&clock.textContent!==scene.time)clock.textContent=scene.time;
  if(doneEl.textContent!==String(scene.done))doneEl.textContent=String(scene.done);
  const orderName=orders[Math.min(orders.length-1,Math.floor(scene.done/5))];
  if(orderEl.textContent!==orderName)orderEl.textContent=orderName;

  if(!phaseChanged)return;
  currentKey=key;
  document.body.dataset.escapePhase=key;

  if(scene.father)setTimeout(()=>showFather(scene.father),700);
  if(scene.friend)setTimeout(()=>showPhone(scene.friend),1700);
  if(scene.phone)setTimeout(()=>showPhone(scene.phone,'ОТЕЦ'),1200);
  if(key==='zeroCam')setTimeout(showShvarts,2400);
  if(key==='oldShop')setTimeout(()=>showPhone(shvartsHelp?'Шварц оставил дверь к бане открытой. Не задерживайся.':'Ворота заперты. Придётся идти через комнату отдыха и баню.','СИСТЕМА'),2100);
  if(key==='final')setTimeout(prepareEscapeChoice,900);
}

function rewriteIntro(){
  const intro=$('intro');if(!intro)return;
  const eyebrow=intro.querySelector('.eyebrow');if(eyebrow)eyebrow.textContent='REALITY 118 · ESCAPE CUT';
  const title=intro.querySelector('h1');if(title)title.innerHTML='Сбежать с завода:<br>50 заказов до свободы';
  const p=intro.querySelector('h1+p');if(p)p.textContent='Полный рабочий день оператора ЧПУ на ALIV GYM. Отец обещает постараться отпустить тебя в выходной, но каждый законченный заказ превращается в несколько новых.';
  const features=intro.querySelectorAll('.features>div');
  if(features[0])features[0].innerHTML='<b>ВЕСЬ РАБОЧИЙ ДЕНЬ</b><span>С 8:00 до 17:00: заказы, обед, новые поручения и давление начальства</span>';
  if(features[1])features[1].innerHTML='<b>50 РЕАЛЬНЫХ ЗАКАЗОВ</b><span>Гакс, Машина Смита, Гравитрон, стойки, кроссовер и другие тренажёры</span>';
  if(features[2])features[2].innerHTML='<b>ПОБЕГ ЧЕРЕЗ БАНЮ</b><span>Шкафчик отца, ключ от двора, дверь за лазером и несколько концовок</span>';
}

function rewriteNotes(){
  const modal=$('noteModal');if(!modal)return;
  if(modal.classList.contains('hidden')){modal.dataset.escapeRewritten='';return}
  const title=$('noteTitle'),kind=$('noteKind'),body=$('noteBody');
  if(!title||!body||modal.dataset.escapeRewritten)return;
  const original=title.textContent;
  modal.dataset.escapeRewritten='1';
  if(/Правила|инструкц/i.test(original)){
    kind.textContent='РАСПЕЧАТКА ИЗ 1С';title.textContent='Заказы, которые «точно последние»';
    body.textContent='1. Стойка приседа напольная — 4 шт.\n2. Жим ногами + гакк-присед — 3 шт.\n3. Супер Гакс 3 в 1 — 2 шт.\n4. Гравитрон — 4 шт.\n5. Машина Смита — 5 шт.\n6. Стойки под штангу — 8 шт.\n\nВнизу ручкой отца: «Закончишь — подойди. Есть ещё работа».';
  }else if(/оператора|оставляю|шкаф/i.test(original)){
    kind.textContent='ЗАПИСКА В КОМНАТЕ ОТДЫХА';title.textContent='План выхода через баню';
    body.textContent='Ключ от двери во двор лежит в незапертом шкафчике отца.\n\nДверь в баню находится за лазерным станком. Из бани можно выйти во двор, затем открыть наружную дверь.\n\nЧерез ворота идти опаснее: второй комплект ключей у дяди Шварца.';
  }else{
    kind.textContent='РАБОЧИЙ ДОКУМЕНТ';title.textContent='Остаток смены';
    body.textContent='Выполнено почти всё. Сверху добавлены ещё позиции.\n\nСообщение от друзей: «Мы скоро выезжаем. Ты с нами?»\n\nРешение простое, но принять его труднее любого заказа: закончить работу невозможно. Нужно уйти самому.';
  }
}

function rewriteCamera(){
  const modal=$('cameraModal');if(!modal)return;
  if(modal.classList.contains('hidden')){modal.dataset.escapeRewritten='';return}
  if(modal.dataset.escapeRewritten)return;
  modal.dataset.escapeRewritten='1';
  const title=$('cameraTitle'),status=$('cameraStatus');
  if(title)title.textContent=currentKey==='zeroCam'?'ПРОВЕРКА ВЫЕЗДА НАЧАЛЬСТВА':'КОНТРОЛЬ ПРОИЗВОДСТВА';
  if(status)status.textContent=currentKey==='zeroCam'?'На камере видно: отец и дядя Шварц готовятся уезжать. Дождись 16:35.':'Проверь участки и вернись к заказам.';
}

function prepareEscapeChoice(){
  const modal=$('choiceModal');if(!modal)return;
  const head=modal.querySelector('.eyebrow'),h1=modal.querySelector('h1'),p=modal.querySelector('p');
  if(head)head.textContent='16:58 · РЕШЕНИЕ';
  if(h1)h1.textContent='Как сбежать с завода?';
  if(p)p.textContent='Отец уже звонит, друзья собираются уезжать. Ворота ближе, но ключи у отца и Шварца. Безопасный путь — через баню, если ты забрал ключ из шкафчика.';
  const a=$('signAgain'),b=$('refuseSign');
  if(a){a.innerHTML='<b>ЧЕРЕЗ БАНЮ</b><small>За лазерным станком → двор → наружная дверь</small>';a.onclick=()=>finishEscape('sauna')}
  if(b){b.innerHTML='<b>ЧЕРЕЗ ВОРОТА</b><small>Попытаться уговорить Шварца или рискнуть без ключа</small>';b.onclick=()=>finishEscape('gate')}
}

function finishEscape(route){
  $('choiceModal')?.classList.add('hidden');
  const ending=$('endingModal');if(!ending)return;
  const eyebrow=$('endingEyebrow'),title=$('endingTitle'),text=$('endingText'),quote=$('endingQuote'),reward=$('reward');
  let good=false;
  if(route==='sauna'){
    good=true;
    eyebrow.textContent='17:03 · ТЫ ВЫШЕЛ СО ДВОРА';
    title.textContent='Выходной ты взял сам';
    text.textContent='Ты прошёл через комнату отдыха, забрал ключ из шкафчика отца, вышел через баню во двор и закрыл дверь снаружи. Телефон звонит снова, но впервые за весь день ты не берёшь трубку.';
    quote.textContent='Сообщение от друзей: «Красавчик. Ждём у магазина».';
  }else if(shvartsHelp){
    good=true;
    eyebrow.textContent='17:01 · ВОРОТА ОТКРЫТЫ';
    title.textContent='Шварц сделал вид, что не заметил';
    text.textContent='Дядя Шварц оставил тебе возможность выйти через ворота. Уже на улице он пишет одно сообщение: «Отцу скажу, что станок встал».';
    quote.textContent='Иногда самый крупный человек на заводе оказывается единственным, кто понимает.';
  }else{
    eyebrow.textContent='17:00 · ПОПЫТКА ПОБЕГА';
    title.textContent='Ключей от ворот нет';
    text.textContent='Ты дёргаешь ворота, но они закрыты. За спиной раздаётся знакомый голос — отец вернулся за документами и увидел тебя у выхода.';
    quote.textContent='«Пиздуй пахать, простофиля».';
  }
  if(reward)reward.textContent=good?'Концовка открыта: СВОБОДНЫЙ ВЫХОДНОЙ':'Концовка открыта: РАБОТА В ВЫХОДНЫЕ';
  const again=$('again');if(again)again.textContent=good?'ПРОЙТИ ДРУГИМ ПУТЁМ':'ПОПРОБОВАТЬ СБЕЖАТЬ СНОВА';
  ending.classList.remove('hidden');
}

const observer=new MutationObserver(()=>{
  applyStory();rewriteNotes();rewriteCamera();
});
observer.observe(document.body,{subtree:true,childList:true,characterData:true,attributes:true,attributeFilter:['class']});

rewriteIntro();
applyStory();

const start=$('start');
start?.addEventListener('click',()=>{
  if(!firstStart)return;firstStart=false;
  setTimeout(()=>showPhone('Выезд завтра утром. Только не дай себя снова оставить на выходные.'),1800);
},{capture:true});

window.__NIGHT_HUNTER_ESCAPE_READY__=true;
})();