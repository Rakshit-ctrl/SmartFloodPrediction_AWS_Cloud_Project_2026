import { describe, expect, it } from 'vitest';
import { dateTime, forecastSeries, mm, percent, riskSeries, stateLabel } from './format';

describe('format helpers', () => {
  it('shows missing rain as "None reported", never 0', () => {
    expect(mm(null)).toBe('None reported');
    expect(mm(undefined)).toBe('None reported');
    expect(mm(0)).toBe('0 mm');
    expect(mm(2.1)).toBe('2.1 mm');
  });

  it('handles missing and invalid dates', () => {
    expect(dateTime(null)).toBe('—');
    expect(dateTime('not a date')).toBe('—');
    expect(dateTime('2026-10-27T10:00:00+00:00')).not.toBe('—');
  });

  it('orders risk history oldest to newest and caps the point count', () => {
    const risks = [3, 2, 1].map((id) => ({ id, created_at: `2026-10-2${id}T10:00:00+00:00`, risk_score: id * 10, risk_level: 'Low', location: 'X' }));
    expect(riskSeries(risks).map((p) => p.id)).toEqual([1, 2, 3]);
    expect(riskSeries(risks, 2).map((p) => p.id)).toEqual([2, 3]);
  });

  it('keeps unreported forecast rain as null and converts chance to percent', () => {
    const f = { periods: [
      { time: '2026-10-27T12:00:00+00:00', rainfall_mm_3h: 1.5, precipitation_probability: 0.6 },
      { time: '2026-10-27T15:00:00+00:00', precipitation_probability: 0.2 },
      { time: '2026-10-27T18:00:00+00:00', rainfall_mm_3h: 0 },
    ] };
    const s = forecastSeries(f);
    expect(s.map((p) => p.rain)).toEqual([1.5, null, 0]);
    expect(s.map((p) => p.chance)).toEqual([60, 20, null]);
    expect(forecastSeries(null)).toEqual([]);
  });

  it('formats model state and percentages', () => {
    expect(stateLabel('ready')).toBe('Ready');
    expect(stateLabel('weights_missing')).toBe('weights missing');
    expect(percent(0.5)).toBe('50.00%');
  });
});
