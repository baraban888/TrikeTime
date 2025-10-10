// src/components/History.jsx
import React, { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

// --- утилиты -------------------------------------------------
function toArray(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.items)) return data.items;
  return [];
}

async function safeText(res) {
  try {
    return (await res.text()).slice(0, 300);
  } catch {
    return "";
  }
}

async function post(url, body = null) {
  const res = await fetch(`${API_BASE}${url}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : null,
  });
  return res;
}

// --- компонент -----------------------------------------------
export default function History() {
  // состояние UI
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const [info, setInfo] = useState("");
  const [loading, setLoading] = useState(false);

  // загрузка истории
  async function loadHistory() {
    try {
      setErr("");
      setLoading(true);
      const res = await fetch(`${API_BASE}/api/history`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRows(toArray(data));
    } catch (e) {
      setRows([]);
      setErr(`Ошибка: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }

  // обработчики кнопок
  async function onDrive() {
    setInfo("");
    setErr("");
    const res = await post(`/api/start_shift`);
    if (res.ok) {
      setInfo("Смена открыта.");
      loadHistory();
    } else {
      const t = await safeText(res);
      setErr(`Старт не удался (HTTP ${res.status})${t ? " — " + t : ""}`);
    }
  }

  async function onRest() {
    setInfo("");
    setErr("");
    const res = await post(`/api/stop_shift`);
    if (res.ok) {
      setInfo("Смена закрыта.");
      loadHistory();
    } else if (res.status === 409) {
      // нет открытой смены — это не критичная ошибка
      setInfo("Нет открытой смены — отдых уже активен.");
    } else {
      const t = await safeText(res);
      setErr(`Стоп не удался (HTTP ${res.status})${t ? " — " + t : ""}`);
    }
  }

  // «Др. работы» пока выключена — показываем вежливое сообщение.
  async function onOtherWork() {
  setInfo("");
  setErr("");
  const res = await post(`/api/start_shift`);
  if (res.ok) {
    setInfo("Начата смена: другие работы.");
    loadHistory();
  } else {
    const t = await safeText(res);
    setErr(`Не удалось начать (HTTP ${res.status})${t ? " — " + t : ""}`);
  }
}


  async function onClear() {
    setInfo("");
    setErr("");
    const res = await post(`/api/clear_history`);
    if (res.ok) {
      setInfo("История очищена.");
      loadHistory();
    } else {
      const t = await safeText(res);
      setErr(`Не удалось очистить (HTTP ${res.status})${t ? " — " + t : ""}`);
    }
  }

  function onDownload() {
    // просто открываем прямую ссылку на CSV
    window.location.href = `${API_BASE}/api/download_history`;
  }

  useEffect(() => {
    loadHistory();
  }, []);

  // --- РАЗМЕТКА: максимально близко к текущей странице --------
  return (
    <div className="container" style={{ maxWidth: 820, margin: "0 auto" }}>
      {/* верхний информационный/ошибочный блок, стили мягкие, чтобы вписаться */}
      {err && (
        <div
          className="alert alert-warn"
          style={{
            background: "#fff3cd",
            border: "1px solid #ffecb5",
            color: "#664d03",
            borderRadius: 10,
            padding: "10px 12px",
            margin: "8px 0",
          }}
        >
          ⚠️ {err}
        </div>
      )}
      {info && (
        <div
          className="alert alert-info"
          style={{
            background: "#d1e7dd",
            border: "1px solid #badbcc",
            color: "#0f5132",
            borderRadius: 10,
            padding: "10px 12px",
            margin: "8px 0",
          }}
        >
          ℹ️ {info}
        </div>
      )}

      {/* Блок «Ручное переключение»: три кнопки как у тебя сейчас */}
      <div
        className="panel"
        style={{
          background: "#fff",
          border: "1px solid #eee",
          borderRadius: 16,
          padding: 16,
          marginTop: 8,
        }}
      >
        <div
          className="controls"
          style={{
            display: "flex",
            gap: 12,
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          <button className="btn" onClick={onDrive}>
            Езда
          </button>
          <button className="btn" onClick={onRest}>
            Отдых
          </button>
          <button className="btn" onClick={onOtherWork}>
            Др. работы
          </button>

          {/* справа — сервисные кнопки, как в твоей версии */}
          <div style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={onDownload}>
            Скачать историю
          </button>
          <button className="btn btn-warn" onClick={onClear}>
            Очистить историю
          </button>
        </div>
      </div>

      {/* Последние записи */}
      <div style={{ marginTop: 18 }}>
        <h3 style={{ fontWeight: 600, fontSize: 18, marginBottom: 8 }}>
          Последние записи
        </h3>

        {loading && <div style={{ opacity: 0.8 }}>Загрузка…</div>}

        {!loading && rows.length === 0 && !err && (
          <div style={{ color: "#6c757d" }}>Поки що немає записів.</div>
        )}

        {(Array.isArray(rows) ? rows : []).map((r) => (
          <div
            key={r.id}
            style={{
              border: "1px solid #eee",
              borderRadius: 12,
              padding: 12,
              marginBottom: 10,
              background: "#fff",
            }}
          >
            <div>
              <b>ID:</b> {r.id}
            </div>
            <div>
              <b>Старт:</b> {r.start_time}
            </div>
            <div>
              <b>Финиш:</b> {r.end_time ?? "—"}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
