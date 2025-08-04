let shiftStarted = false;
let startTime;
let timerInterval;

const startBtn = document.getElementById('startBtn');
const statusDiv = document.getElementById('status');
const timersDiv = document.getElementById('timers');
const workTime = document.getElementById('workTime');
const breakTime = document.getElementById('breakTime');
const shiftEndTime = document.getElementById('shiftEndTime');

startBtn.addEventListener('click', () => {
    if (!shiftStarted) {
        // Старт смены
        startShift();
    } else {
        // Завершение смены
        endShift();
    }
});

async function startShift() {
    try {
        const response = await fetch('/start_shift', { method: 'POST' });
        const data = await response.json();
        console.log('Смена начата:', data);

        shiftStarted = true;
        startTime = new Date();
        statusDiv.innerText = 'Смена идет...';
        startBtn.innerText = 'Закончить смену';
        timersDiv.style.display = 'block';

        timerInterval = setInterval(updateTimers, 1000);
    } catch (err) {
        console.error('Ошибка старта смены:', err);
    }
}

async function endShift() {
    try {
        const response = await fetch('/end_shift', { method: 'POST' });
        const data = await response.json();
        console.log('Смена завершена:', data);

        shiftStarted = false;
        clearInterval(timerInterval);
        statusDiv.innerText = 'Смена завершена';
        startBtn.innerText = 'Начать смену';
        timersDiv.style.display = 'none';
    } catch (err) {
        console.error('Ошибка завершения смены:', err);
    }
}

function updateTimers() {
    const now = new Date();
    const elapsed = Math.floor((now - startTime) / 1000);

    workTime.innerText = formatTime(elapsed);

    const breakLeft = Math.max(0, 45*60 - elapsed);
    breakTime.innerText = formatTime(breakLeft);

    const shiftLeft = Math.max(0, 9*3600 - elapsed);
    shiftEndTime.innerText = formatTime(shiftLeft);
}

function formatTime(sec) {
    const h = String(Math.floor(sec/3600)).padStart(2, '0');
    const m = String(Math.floor((sec%3600)/60)).padStart(2, '0');
    const s = String(sec%60).padStart(2, '0');
    return `${h}:${m}:${s}`;
}





