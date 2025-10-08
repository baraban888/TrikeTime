import React, { useEffect, useMemo, useRef, useState } from "react";
import "../App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";
const INTERVAL_OPTIONS = [10, 30, 60, 300];         // варианты автообновления (сек)
const LS_INTERVAL_KEY = "tt_auto_refresh_sec";      // ключ для localStorage

export default function History() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");               // текст ошибки (желтая плашка)
  const [info, setInfo] = useState("");             // текст успеха (зелёная плашка)
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [online, setOnline] = useState(navigator.onLine);

  // загружаем интервал из localStorage (дефолт 30 сек)
  const [intervalSec, setIntervalSec] = useState(() => {
    const v = Number(localStorage.getItem(LS_INTERVAL_KEY));
    return INTERVAL_OPTIONS.includes(v) ? v : 30;
  });
  const [countdown, setCountdown] = useState(intervalSec);

  const intervalIdRef = useRef(null);
  const tickerIdRef = useRef(null);
  const fadeHidden = useMemo(() => ({ opacity: 0 }), []);

  // сохраняем выбранный интервал
  useEffect(() => {
    localStorage.setItem(LS_INTERVAL_KEY, String(intervalSec));
  }, [intervalSec]);

  // реагируем на события браузера online/offline
  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);

  // --- API ---
  const loadHistory = async () => {
    try {
      setErr("");
      setInfo("");
      setLoading(true);

      const res = await fetch(`${API_BASE}/api/history`);
      if (!res.ok) throw new Error(`history HTTP ${res.status}`);

      const data = await res.json();
      const safe = Array.isArray(data) ? data :
                   Array.isArray(data?.items) ? data.items : [];
      setRows(safe);
      setLastUpdated(new Date());
      setCountdown(intervalSec);
      setOnline(true); // успешно сходили — считаем онлайн
    } catch (e) {
      setRows([]);
      setErr(`Сервер тимчасово недоступний: ${e.message}`);
      setOnline(false);
      // авто-скрытие ошибки через 6 сек
      setTimeout(() => setErr(""), 6000);
    } finally {
      setLoading(false);
    }
  };

  const clearHistory = async () => {
    try {
      setErr("");
      const res = await fetch(`${API_BASE}/api/clear_history`, { method: "POST" });
      if (!res.ok) throw new Error(`clear_history HTTP ${res.status}`);

      setRows([]);
      setInfo("✅ Історію очищено");
      setLastUpdated(new Date());
      // авто-скрытие инфо через 5 сек
      setTimeout(() => setInfo(""), 5000);
    } catch (e) {
      setErr(`Помилка очищення: ${e.message}`);
      setTimeout(() => setErr(""), 6000);
    }
  };

  // --- автообновление по интервалу + обратный отсчёт ---
  useEffect(() => {
    loadHistory(); // стартуем сразу

    if (intervalIdRef.current) clearInterval(intervalIdRef.current);
    intervalIdRef.current = setInterval(loadHistory, intervalSec * 1000);

    if (tickerIdRef.current) clearInterval(tickerIdRef.current);
    setCountdown(intervalSec);
    tickerIdRef.current = setInterval(() => {
      setCountdown((c) => (c > 0 ? c - 1 : intervalSec));
    }, 1000);

    return () => {
      clearInterval(intervalIdRef.current);
      clearInterval(tickerIdRef.current);
    };
  }, [intervalSec]);

  return (
    <div className="container">
      {/* статус соединения */}
      <div className="status">
        <span className={`status-dot ${online ? "status-online" : "status-offline"}`} />
        {online ? "З’єднання з сервером: онлайн" : "З’єднання з сервером: офлайн"}
      </div>

      {/* Ошибка (жёлтая плашка) */}
      {err && (
        <div className="alert alert-warn" style={err ? {} : fadeHidden}>
          <span>⚠️ {err}</span>
          <button className="btn btn-warn" onClick={loadHistory}>
            Повторить
          </button>
        </div>
      )}

      {/* Успех (зелёная плашка, плавное исчезновение) */}
      {info && (
        <div className="alert alert-success" style={info ? {} : fadeHidden}>
          {info}
        </div>
      )}

      {/* Панель автообновления */}
      <div className="toolbar">
        <span className="meta">Автообновление:</span>
        <select
          className="select"
          value={intervalSec}
          onChange={(e) => setIntervalSec(Number(e.target.value))}
          title="Интервал автообновления"
        >
          {INTERVAL_OPTIONS.map((s) => (
            <option key={s} value={s}>{s} сек</option>
          ))}
        </select>
        <span className="meta">• Следующее через: {countdown}s</span>
        <button
          className={`link-btn ${online ? "" : "disabled"}`}
          onClick={online ? loadHistory : undefined}
          title={online ? "Обновить сейчас" : "Без з’єднання"}
          aria-disabled={!online}
        >
          Обновить сейчас
        </button>
      </div>

      {/* Индикатор загрузки */}
      {loading && (
        <div style={{ marginBottom: 8 }}>
          <span className="spinner" /> Загрузка…
        </div>
      )}

      {/* Последнее обновление */}
      <div className="meta" style={{ marginBottom: 8 }}>
        {lastUpdated ? `Оновлено: ${lastUpdated.toLocaleTimeString()}` : "Ще не оновлювалось"}
      </div>

      {/* Список записей */}
      <div>
        {(Array.isArray(rows) ? rows : []).map((r) => (
          <div key={r.id} className="list-item">
            <div><b>ID:</b> {r.id}</div>
            <div><b>Старт:</b> {r.start_time}</div>
            <div><b>Фініш:</b> {r.end_time ?? "—"}</div>
          </div>
        ))}

        {!loading && (!rows || rows.length === 0) && !err && !info && (
          <div className="meta">Поки що немає записів.</div>
        )}
      </div>

      {/* Очистка истории (выключается офлайн) */}
      <button
        className={`btn btn-danger ${online ? "" : "disabled"}`}
        onClick={online ? clearHistory : undefined}
        title={online ? "Удалить все записи из истории" : "Без з’єднання"}
        disabled={!online}
        style={{ marginTop: 16 }}
      >
        Очистить историю
      </button>
    </div>
  );
}
