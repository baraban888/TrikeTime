const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function asJson(res) {
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} ${text}`.trim());
  }
  return res.json();
}

export async function getHistory() {
  return asJson(await fetch(`${API_BASE}/api/history`));
}

export async function createSessionNow() {
  // формат, который ждёт бэкенд: "YYYY-MM-DD HH:MM:SS"
  const now = new Date().toISOString().slice(0, 19).replace("T", " ");
  return asJson(
    await fetch(`${API_BASE}/api/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start_time: now, end_time: now }),
    })
  );
}


