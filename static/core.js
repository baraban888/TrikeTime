// ===== TrikeTime core state =====
window.current = { type: null, startedAt: null };
window.events = JSON.parse(localStorage.getItem('tt_events') || '[]');

function start(type){
  stop(); // закроем прошлую активность, если есть
  window.current = { type, startedAt: Date.now() };
  persist();
  renderStatus();
}

function stop(){
  if (!window.current.type) return;
  window.events.push({ type: window.current.type, start: window.current.startedAt, end: Date.now() });
  window.current = { type: null, startedAt: null };
  persist();
  recompute();  // пересчёт лимитов/подсказок/жетонов
  renderStatus();
}

function persist(){
  localStorage.setItem('tt_events', JSON.stringify(window.events));
  localStorage.setItem('tt_current', JSON.stringify(window.current));
}

// при загрузке подтягиваем состояние
window.current = JSON.parse(localStorage.getItem('tt_current') || 'null') || window.current;
window.events  = JSON.parse(localStorage.getItem('tt_events')  || '[]');

// ===== агрегаторы =====
function durationMs(type, sinceMidnight=true){
  const rangeStart = sinceMidnight ? new Date(new Date().setHours(0,0,0,0)).getTime() : 0;
  const now = Date.now();
  let sum = 0;
  for (const e of window.events) {
    if (e.type !== type) continue;
    const s = Math.max(e.start, rangeStart);
    const en = e.end ?? now;
    if (en > s) sum += en - s;
  }
  if (window.current.type === type && window.current.startedAt >= rangeStart){
    sum += now - window.current.startedAt;
  }
  return sum;
}

function recompute(){
  const driveToday = durationMs('DRIVE');
  const otherToday = durationMs('OTHER_WORK');
  const workToday  = driveToday + otherToday;

  // непрерывное вождение до перерыва
  const contDrive = computeContinuousDrive(window.events, window.current);

  // правила/подсказки
  if (contDrive >= 4.5*60*60*1000) notify('Нужен перерыв 45 мин');
  if (msToHours(driveToday) > 9 && !tokenUsed('drive10-1','drive10-2')){
    promptUseToken10();
  }

  // TODO: недельные агрегаты и логика «жетонов 9/24» при закрытии дня/недели

  // обновим UI
  const el = document.getElementById('tt-summary');
  if (el){
    el.textContent =
      `Езда сегодня: ${fmtH(driveToday)} | Молотки: ${fmtH(otherToday)} | Работа всего: ${fmtH(workToday)} | Без перерыва за рулём: ${fmtH(contDrive)}`;
  }
}

// ===== helpers =====
function msToHours(ms){ return ms/3600000; }
function fmtH(ms){
  const h = Math.floor(ms/3600000);
  const m = Math.floor((ms%3600000)/60000);
  return `${h}ч ${String(m).padStart(2,'0')}м`;
}

function notify(msg){
  // простая заглушка — замени на свой тост/баннер
  console.log('[TT notify]', msg);
  const n = document.getElementById('tt-notify');
  if (n){ n.textContent = msg; n.style.display = 'block'; setTimeout(()=>n.style.display='none', 5000); }
}

function tokenUsed(...keys){
  // свяжи с твоими кружками-жетонами (класс .used)
  return keys.some(k => {
    const el = document.querySelector(`[data-key="${k}"]`);
    return el && el.classList.contains('used');
  });
}

function promptUseToken10(){
  const el = document.querySelector('[data-key="drive10-1"]') || document.querySelector('[data-key="drive10-2"]');
  if (!el) return;
  if (confirm('Превышено 9ч за рулём. Списать жетон 10ч?')){
    el.classList.add('used');
    // при необходимости — сохранить состояние жетонов в localStorage
  }
}

// непрерывное вождение (упрощённо: от последнего BREAK/REST/остановки DRIVE)
function computeContinuousDrive(events, current){
  const now = Date.now();
  let t = 0;
  // идём с конца массива и суммируем подряд идущий DRIVE до первого разрыва
  for (let i = events.length-1; i >= 0; i--){
    const e = events[i];
    if (e.type === 'DRIVE'){
      t += (e.end ?? now) - e.start;
    } else if (e.type === 'BREAK' || e.type === 'REST_DAILY' || e.type === 'REST_WEEKLY' || e.type === 'OTHER_WORK'){
      break; // разрыв непрерывности
    }
  }
  if (current.type === 'DRIVE'){
    t += now - current.startedAt;
  }
  return t;
}

// ===== привязка к кнопкам на странице =====
// Предполагаем, что у тебя есть кнопки с такими id:
// #btn-drive, #btn-work, #btn-availability, #btn-break, #btn-stop
window.addEventListener('DOMContentLoaded', () => {
  const byId = id => document.getElementById(id);
  byId('btn-drive')       && byId('btn-drive').addEventListener('click',      ()=>start('DRIVE'));
  byId('btn-work')        && byId('btn-work').addEventListener('click',       ()=>start('OTHER_WORK'));
  byId('btn-availability')&& byId('btn-availability').addEventListener('click',()=>start('AVAILABILITY'));
  byId('btn-break')       && byId('btn-break').addEventListener('click',      ()=>start('BREAK'));
  byId('btn-stop')        && byId('btn-stop').addEventListener('click',       stop);

  renderStatus();
  recompute();
});

// простой статус в UI (элемент #tt-status и #tt-summary опциональны)
function renderStatus(){
  const s = document.getElementById('tt-status');
  if (!s) return;
  if (!window.current.type) s.textContent = 'Статус: —';
  else {
    const mins = Math.floor((Date.now() - window.current.startedAt)/60000);
    const map = {DRIVE:'Езда', OTHER_WORK:'Молотки', AVAILABILITY:'Ожидание', BREAK:'Перерыв'};
    s.textContent = `Статус: ${map[window.current.type]} • ${mins} мин`;
  }
}
