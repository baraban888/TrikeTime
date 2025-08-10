// =============================
// МНОГОЯЗЫЧНОСТЬ TrikeTime
// =============================
const translations = {
    en: {
        title: "TrikeTime",
        status: "Shift not started",
        startShift: "Start Shift",
        clearHistory: "Clear History",
        downloadHistory: "Download History",
        historyTitle: "Shift History"
    },
    ru: {
        title: "TrikeTime",
        status: "Смена не начата",
        startShift: "Начать смену",
        clearHistory: "Очистить историю",
        downloadHistory: "Скачать историю",
        historyTitle: "История смен"
    },
    uk: {
        title: "TrikeTime",
        status: "Зміна не розпочата",
        startShift: "Почати зміну",
        clearHistory: "Очистити історію",
        downloadHistory: "Завантажити історію",
        historyTitle: "Історія змін"
    },
    pl: {
        title: "TrikeTime",
        status: "Zmiana nie rozpoczęta",
        startShift: "Rozpocznij zmianę",
        clearHistory: "Wyczyść historię",
        downloadHistory: "Pobierz historię",
        historyTitle: "Historia zmian"
    }
};

// Функция смены языка
// было: function setLanguage(lang) { ... }
window.setLanguage = function (lang) {
  localStorage.setItem('lang', lang);

  document.getElementById("title").innerText = translations[lang].title;
  document.getElementById("status").innerText = translations[lang].status;
  document.getElementById("shiftBtn").innerText = translations[lang].startShift;

  document.getElementById("historyTitle").innerText = translations[lang].historyTitle;
  document.getElementById("clearHistoryBtn").innerText = translations[lang].clearHistory;
  document.getElementById("downloadHistoryBtn").innerText = translations[lang].downloadHistory;
};

window.addEventListener('DOMContentLoaded', () => {
  const savedLang = localStorage.getItem('lang') || 'ru';
  window.setLanguage(savedLang);
});


// Загружаем сохранённый язык при старте
window.addEventListener('DOMContentLoaded', () => {
    const savedLang = localStorage.getItem('lang') || 'ru';
    setLanguage(savedLang);
});



