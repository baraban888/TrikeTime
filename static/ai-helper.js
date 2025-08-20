// ============================
// TrikeTime AI Helper
// ============================

// Мини-классификатор активности (едет / перерыв / молотки)
// Работает прямо в браузере, без библиотек.
// Возвращает метку и вероятности.

const AI = (() => {

  // Веса «обучены» офлайн (фиктивные, но правдоподобные для демо).
  // Признаки: [bias, stopMin, contDriveMin, hourSin, hourCos, avgSpeed, lastIsDrive, lastIsBreak, lastIsWork]
  const W = {
    DRIVE:      [ 0.2, -1.2,  0.9,  0.1, -0.1,  2.0,  0.8, -0.6, -0.3 ],
    BREAK:      [-0.1,  1.6, -0.8, -0.2,  0.1, -2.5, -0.4,  1.2, -0.1 ],
    OTHER_WORK: [-0.1,  0.4, -0.2,  0.0,  0.0, -0.6, -0.2, -0.3,  0.9 ],
  };

  function features(ctx){
    const {
      stopMs = 0,            // простой (мс)
      contDriveMs = 0,       // непрерывное вождение (мс)
      hour = 12,             // час суток 0..23
      avgSpeedKmh = 0,       // средняя скорость
      lastType = null        // последняя активность
    } = ctx;

    const stopMin = stopMs / 60000;
    const contDriveMin = contDriveMs / 60000;

    const hourRad = 2 * Math.PI * hour / 24;
    const hourSin = Math.sin(hourRad);
    const hourCos = Math.cos(hourRad);

    const lastIsDrive = lastType === 'DRIVE' ? 1 : 0;
    const lastIsBreak = lastType === 'BREAK' ? 1 : 0;
    const lastIsWork  = lastType === 'OTHER_WORK' ? 1 : 0;

    return [1, stopMin, contDriveMin, hourSin, hourCos, avgSpeedKmh, lastIsDrive, lastIsBreak, lastIsWork];
  }

  function dot(w, x){ let s=0; for (let i=0;i<w.length;i++) s += w[i]*x[i]; return s; }

  function softmax(logits){
    const m = Math.max(...logits);
    const ex = logits.map(v=>Math.exp(v-m));
    const sum = ex.reduce((a,b)=>a+b,0);
    return ex.map(v=>v/sum);
  }

  function predict(ctx){
    const x = features(ctx);
    const classes = ['DRIVE','BREAK','OTHER_WORK'];
    const logits = [dot(W.DRIVE,x), dot(W.BREAK,x), dot(W.OTHER_WORK,x)];
    const probs = softmax(logits);
    const maxIdx = probs.indexOf(Math.max(...probs));
    return {
      label: classes[maxIdx],
      probs: {DRIVE:probs[0], BREAK:probs[1], OTHER_WORK:probs[2]}
    };
  }

  return { predict };
})();

// ============================
// Подсказки для водителя
// ============================

let lastSuggestionAt = 0;
const SUGGESTION_THRESHOLD = 0.68; // минимальная уверенность

function maybeSuggestSwitch(){
  const now = Date.now();

  // Составляем контекст для AI
  const ctx = {
    stopMs: window.current?.type !== 'DRIVE' && window.current?.startedAt ? now - window.current.startedAt : 0,
    contDriveMs: window.current?.type === 'DRIVE' && window.current?.startedAt ? now - window.current.startedAt : 0,
    hour: new Date().getHours(),
    avgSpeedKmh: 0, // можно прикрутить гео позже
    lastType: window.current?.type || null
  };

  const pred = AI.predict(ctx);

  const top = Math.max(pred.probs.DRIVE, pred.probs.BREAK, pred.probs.OTHER_WORK);

  // Не предлагать слишком часто (1 раз в 2 минуты) и не предлагать если режим совпадает
  if (top >= SUGGESTION_THRESHOLD && pred.label !== window.current?.type && (now - lastSuggestionAt > 120000)){
    lastSuggestionAt = now;
    showSuggestionBanner(pred.label, top);
  }
}

// Простая реализация баннера (можно заменить на красивый UI)
function showSuggestionBanner(label, conf){
  const map = {
    'DRIVE': 'Езда',
    'BREAK': 'Перерыв',
    'OTHER_WORK': 'Молотки',
  };
  const text = `Похоже, сейчас: ${map[label]} (${Math.round(conf*100)}%). Переключить?`;
  if (confirm(text)) {
    if (typeof start === 'function') start(label);
  }
}

// Проверяем каждые 30 сек
setInterval(maybeSuggestSwitch, 30000);
