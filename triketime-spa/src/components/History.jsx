// src/components/History.jsx
import { useEffect, useState } from "react";

// Преобразуем "YYYY-MM-DD HH:MM:SS[+00:00]" в локальную дату/время
function fmt(dt) {
  if (!dt) return "—";
  // Превратим "2025-09-17 10:00:00" в ISO-вид
  const iso = dt.includes("T") ? dt : dt.replace(" ", "T");
  const d = new Date(iso);
  if (isNaN(d)) return dt; // если что-то экзотическое — показываем как есть

  return d.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function duration(start, end) {
  if (!start || !end) return "—";
  const a = new Date((start.includes("T") ? start : start.replace(" ", "T")));
  const b = new Date((end.includes("T") ? end : end.replace(" ", "T")));
  const ms = Math.max(0, b - a);
  const m = Math.round(ms / 60000);
  const h = Math.floor(m / 60);
  const mm = String(m % 60).padStart(2, "0");
  return `${h}:${mm}`;
}

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:5000";

export default function History() {
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");

  async function loadHistory() {
    try {
      setErr("");
      const res = await fetch(`${API_BASE}/api/history`);
      if (!res.ok) throw new Error(`History HTTP ${res.status}`);
      const data = await res.json();
      setRows(data);
    } catch (e) {
      setErr(`Ошибка загрузки: ${e.message}`);
    }
  }

  async function createSessionNow() {
    try {
      setErr("");
      const nowIso = new Date().toISOString(); // временно start=end=сейчас
      const res = await fetch(`${API_BASE}/api/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ start_time: nowIso, end_time: nowIso }),
      });
      if (!res.ok) throw new Error(`Create HTTP ${res.status}`);
      await res.json();
      await loadHistory(); // обновим таблицу
    } catch (e) {
      setErr(`Ошибка создания: ${e.message}`);
    }
  }

  useEffect(() => {
    loadHistory();
  }, []);

  return (
    <div style={{ padding: 24, fontFamily: "system-ui, Arial, sans-serif" }}>
      <h1 style={{ fontSize: 48, margin: "16px 0 24px" }}>История смен</h1>

      <button onClick={createSessionNow} style={{ padding: "6px 12px" }}>
        Создать смену (сейчас)
      </button>

      {err && (
        <div style={{ color: "crimson", marginTop: 12 }}>
          {err}
        </div>
      )}

      <table
        style={{
          marginTop: 16,
          borderCollapse: "collapse",
          minWidth: 420,
          fontSize: 14,
        }}
      >
        <thead>
          <tr>
            <th style={{ border: "1px solid #ccc", padding: 8 }}>ID</th>
            <th style={{ border: "1px solid #ccc", padding: 8 }}>Начало</th>
            <th style={{ border: "1px solid #ccc", padding: 8 }}>Конец</th>
            <th style={{ border: "1px solid #ccc", padding: 8 }}>Dlitelnost</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id}>
              <td style={{ border: "1px solid #ccc", padding: 8 }}>{r.id}</td>
              <td style={{ border: "1px solid #ccc", padding: 8 }}>{fmt(r.start_time)}</td>
              <td style={{ border: "1px solid #ccc", padding: 8 }}>{fmt(r.end_time)}</td>
              <td style={{ border: "1px solid #ccc", padding: 8 }}>{duration(r.start_time, r.end_time)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
