const translations = {
    EN: { title: "TrikeTime", status: "Shift not started", startBtn: "Start Shift", historyTitle: "Shift History", clearHistoryBtn: "Clear History", downloadHistoryBtn: "Download History (CSV)",shiftRunning: "Shift running:", },
    RU: { title: "TrikeTime", status: "Смена не начата", startBtn: "Начать смену", historyTitle: "История смен", clearHistoryBtn: "Очистить историю", downloadHistoryBtn: "Скачать историю (CSV)",shiftRunning: "Смена идёт:", },
    UA: { title: "TrikeTime", status: "Зміна не розпочата", startBtn: "Почати зміну", historyTitle: "Історія змін", clearHistoryBtn: "Очистити історію", downloadHistoryBtn: "Завантажити історію (CSV)",shiftRunning: "Зміна триває:", },
    PL: { title: "TrikeTime", status: "Zmiana nie rozpoczęta", startBtn: "Rozpocznij zmianę", historyTitle: "Historia zmian", clearHistoryBtn: "Wyczyść historię", downloadHistoryBtn: "Pobierz historię (CSV)",shiftRunning: "Zmiana trwa:", }
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
let timerInterval;
let shiftStartTime;

function formatTime(seconds) {
    const h = String(Math.floor(seconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((seconds % 3600) / 60)).padStart(2, '0');
    const s = String(seconds % 60).padStart(2, '0');
    return `${h}:${m}:${s}`;
}

function startTimer(startTime) {
    shiftStartTime = new Date(startTime);
    timerInterval = setInterval(() => {
        const now = new Date();
        const elapsedSeconds = Math.floor((now - shiftStartTime) / 1000);
        const currentLang = localStorage.getItem("lang") || "RU";
document.getElementById("status").textContent =
    `${translations[currentLang].shiftRunning} ${formatTime(elapsedSeconds)}`;
    }, 1000);
}

function stopTimer() {
    clearInterval(timerInterval);
    document.getElementById("status").textContent = "Смена завершена";
    localStorage.removeItem("shiftStartTime");
}

document.addEventListener("DOMContentLoaded", () => {
    const savedLang = localStorage.getItem("lang") || "RU";
    setLanguage(savedLang);
    const savedStartTime = localStorage.getItem("shiftStartTime");
if (savedStartTime) {
    startTimer(savedStartTime);
}

document.getElementById("startBtn").addEventListener("click", () => {
    fetch("/start_shift", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            localStorage.setItem("shiftStartTime", data.start_time);
            startTimer(data.start_time);
        });
});

// Если будет кнопка завершения смены
document.getElementById("endShiftBtn")?.addEventListener("click", () => {
    fetch("/end_shift", { method: "POST" })
        .then(() => stopTimer());
});

});


    // Начать смену
    document.getElementById("startBtn").addEventListener("click", () => {
        fetch("/start_shift", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                document.getElementById("status").textContent = "Смена начата";
                console.log("Смена начата:", data);
            });
    });

    // Очистить историю
    document.getElementById("clearHistoryBtn").addEventListener("click", () => {
        fetch("/clear_history", { method: "POST" })
            .then(res => res.json())
            .then(data => {
                console.log("История очищена:", data);
                alert("История очищена");
            });
    });

    // Скачать историю
    document.getElementById("downloadHistoryBtn").addEventListener("click", () => {
        window.location.href = "/download_history";
    });

