export const mm = (v) => (v == null ? 'None reported' : `${v} mm`);

export function dateTime(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString();
}

const shortFmt = { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' };
const dayFmt = { weekday: 'short', hour: '2-digit', minute: '2-digit' };

/** Risk history for the chart: oldest to newest, at most `limit` points. The API returns newest first. */
export function riskSeries(risks, limit = 20) {
  return risks
    .slice(0, limit)
    .reverse()
    .map((r) => ({
      id: r.id,
      time: new Date(r.created_at).toLocaleString([], shortFmt),
      score: r.risk_score,
      level: r.risk_level,
      location: r.location,
    }));
}

/** Forecast points for the chart. Unreported rain stays null (a gap), never 0. */
export function forecastSeries(forecast) {
  return (forecast?.periods || []).map((p) => ({
    time: new Date(p.time).toLocaleString([], dayFmt),
    rain: p.rainfall_mm_3h ?? null,
    chance: p.precipitation_probability == null ? null : Math.round(p.precipitation_probability * 100),
  }));
}

export const stateLabel = (s) => (s === 'ready' ? 'Ready' : s.split('_').join(' '));

export const percent = (fraction) => `${(fraction * 100).toFixed(2)}%`;
