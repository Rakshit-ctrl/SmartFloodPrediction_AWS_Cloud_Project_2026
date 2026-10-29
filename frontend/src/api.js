const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000';

function errorText(d, status) {
  if (typeof d?.detail === 'string') return d.detail;
  if (Array.isArray(d?.detail)) return d.detail.map((x) => x.msg).join('; ');
  return `Request failed (HTTP ${status})`;
}

async function req(path, opts = {}) {
  let r;
  try {
    r = await fetch(BASE + path, opts);
  } catch {
    throw new Error('Cannot reach the API. Is the backend running?');
  }
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(errorText(d, r.status));
  return d;
}

const send = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});
const q = encodeURIComponent;

export const api = {
  health: () => req('/api/health'),
  weather: (city) => req('/api/weather?city=' + q(city)),
  forecast: (city) => req('/api/weather/forecast?city=' + q(city)),
  risks: () => req('/api/risk-assessments'),
  addRisk: (p) => req('/api/risk-assessments', send('POST', p)),
  alerts: () => req('/api/alerts'),
  addAlert: (p) => req('/api/alerts', send('POST', p)),
  updAlert: (id, p) => req('/api/alerts/' + id, send('PUT', p)),
  delAlert: (id) => req('/api/alerts/' + id, { method: 'DELETE' }),
  events: () => req('/api/alert-events'),
  analyses: () => req('/api/satellite/analyses'),
  analyze: (file) => {
    const body = new FormData();
    body.append('file', file);
    return req('/api/satellite/analyze', { method: 'POST', body });
  },
};
