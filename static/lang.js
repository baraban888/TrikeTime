const translations = {
    EN: { title: "TrikeTime", status: "Shift not started", startBtn: "Start Shift", historyTitle: "Shift History", clearHistoryBtn: "Clear History", downloadHistoryBtn: "Download History (CSV)" },
    RU: { title: "TrikeTime", status: "Смена не начата", startBtn: "Начать смену", historyTitle: "История смен", clearHistoryBtn: "Очистить историю", downloadHistoryBtn: "Скачать историю (CSV)" },
    UA: { title: "TrikeTime", status: "Зміна не розпочата", startBtn: "Почати зміну", historyTitle: "Історія змін", clearHistoryBtn: "Очистити історію", downloadHistoryBtn: "Завантажити історію (CSV)" },
    PL: { title: "TrikeTime", status: "Zmiana nie rozpoczęta", startBtn: "Rozpocznij zmianę", historyTitle: "Historia zmian", clearHistoryBtn: "Wyczyść historię", downloadHistoryBtn: "Pobierz historię (CSV)" }
};
function setLanguage(lang) {
    if (!translations[lang]) return;
    document.getElementById("title").textContent = translations[lang].title;
    document.getElementById("status").textContent = translations[lang].status;
    document.getElementById("startBtn").textContent = translations[lang].startBtn;
    document.getElementById("historyTitle").textContent = translations[lang].historyTitle;
    document.getElementById("clearHistoryBtn").textContent = translations[lang].clearHistoryBtn;
    document.getElementById("downloadHistoryBtn").textContent = translations[lang].downloadHistoryBtn;
    localStorage.setItem("lang", lang);
}
document.addEventListener("DOMContentLoaded", () => {
    const savedLang = localStorage.getItem("lang") || "RU";
    setLanguage(savedLang);
});
