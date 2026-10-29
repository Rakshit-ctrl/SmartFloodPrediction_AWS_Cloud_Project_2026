import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe } from 'jest-axe';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from './App.jsx';
import { api } from './api';

vi.mock('./api', () => ({
  api: {
    health: vi.fn(), weather: vi.fn(), forecast: vi.fn(), risks: vi.fn(), addRisk: vi.fn(), alerts: vi.fn(),
    addAlert: vi.fn(), updAlert: vi.fn(), delAlert: vi.fn(), events: vi.fn(), analyses: vi.fn(), analyze: vi.fn(),
  },
}));

// jsdom has no layout, so recharts' ResponsiveContainer would render nothing; stub the chart primitives.
vi.mock('recharts', async () => {
  const React = await import('react');
  const Box = ({ children }) => React.createElement('div', { 'data-testid': 'recharts' }, children);
  const Nothing = () => null;
  return { ResponsiveContainer: Box, LineChart: Box, ComposedChart: Box, CartesianGrid: Nothing, XAxis: Nothing, YAxis: Nothing, Tooltip: Nothing, Legend: Nothing, Line: Nothing, Bar: Nothing, ReferenceLine: Nothing };
});

const T = '2026-10-27T10:00:00+00:00';
const risk = (id, score = 25.7, level = 'Low') => ({
  id, location: 'Chennai', rainfall_mm: 55, river_level_m: null, risk_score: score, risk_level: level,
  explanation: 'x', method: 'demo_heuristic_v1', validated: false, created_at: T,
});
const rule = (over = {}) => ({ id: 1, name: 'Rule A', location: 'Chennai', threshold: 70, enabled: true, created_at: T, ...over });
const WEATHER = {
  available: true, kind: 'current_observation', city: 'Chennai', country: 'IN', lat: 13.0827, lon: 80.2707, observed_at: T,
  temperature_c: 30.5, humidity_pct: 70, rainfall_mm_1h: null, rainfall_mm_3h: null, description: 'light rain',
};
const FORECAST = {
  available: true, kind: 'forecast', total_rainfall_mm_reported: 1.5,
  periods: [
    { time: '2026-10-27T12:00:00+00:00', temperature_c: 29, precipitation_probability: 0.6, rainfall_mm_3h: 1.5 },
    { time: '2026-10-27T15:00:00+00:00', temperature_c: 28, precipitation_probability: 0.2, rainfall_mm_3h: null },
  ],
};
const COMPLETED = {
  status: 'completed', message: 'Segmentation completed.', image: { width: 400, height: 300, format: 'PNG', channels: 3 },
  mask: { flooded_pixels: 60000, total_pixels: 120000, flooded_fraction: 0.5 }, overlay_png_base64: 'AAAA',
  model: { name: 'synthetic-demo', version: '1' }, inference_ms: 10.4,
  area: { available: false, reason: 'This image format carries no georeferencing; only GeoTIFF does.' },
};

function mockApi(over = {}) {
  const d = {
    health: { status: 'ok', model_configured: false, model_state: 'not_configured' },
    weather: WEATHER, forecast: FORECAST, risks: [], alerts: [], events: [], analyses: [], ...over,
  };
  for (const key of ['health', 'weather', 'forecast', 'risks', 'alerts', 'events', 'analyses']) {
    const v = d[key];
    api[key].mockImplementation(() => (v instanceof Error ? Promise.reject(v) : Promise.resolve(v)));
  }
}

async function renderApp(over) {
  mockApi(over);
  const view = render(<App />);
  await screen.findByRole('heading', { name: 'Climate risk overview' });
  await waitFor(() => expect(api.health).toHaveBeenCalled());
  return view;
}

beforeEach(() => vi.clearAllMocks());

describe('weather', () => {
  it('labels the current observation and the forecast separately', async () => {
    await renderApp();
    expect(await screen.findByRole('heading', { name: /Chennai conditions/ })).toBeInTheDocument();
    expect(screen.getByText('CURRENT OBSERVATION')).toBeInTheDocument();
    expect(screen.getByText(/FORECAST \(NOT OBSERVED\)/)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Open in OpenStreetMap/ })).toHaveAttribute('rel', 'noopener noreferrer');
  });

  it('shows rain the provider did not report as "None reported", not 0', async () => {
    await renderApp();
    await screen.findByText(/Rainfall \/ 1h/);
    expect(screen.getAllByText('None reported').length).toBeGreaterThanOrEqual(2);
    expect(screen.queryByText('0 mm')).not.toBeInTheDocument();
  });

  it('keeps the rest of the dashboard working when weather fails', async () => {
    await renderApp({ weather: new Error('Location not found: Nowhereville'), forecast: new Error('Location not found: Nowhereville') });
    expect(await screen.findByRole('alert')).toHaveTextContent('Location not found: Nowhereville');
    expect(screen.getByText('Weather unavailable')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Create a risk assessment' })).toBeInTheDocument();
    expect(screen.getByText('API connected')).toBeInTheDocument();
  });

  it('shows the API as disconnected when the backend is down', async () => {
    mockApi({ health: new Error('Cannot reach the API. Is the backend running?') });
    render(<App />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Cannot reach the API');
    expect(screen.getByText('API disconnected')).toBeInTheDocument();
  });
});

describe('model status', () => {
  it('shows the real model state', async () => {
    await renderApp({ health: { status: 'ok', model_configured: false, model_state: 'weights_missing' } });
    expect(await screen.findByText('weights missing')).toBeInTheDocument();
  });
});

describe('risk assessments', () => {
  it('labels stored assessments as demo heuristics', async () => {
    await renderApp({ risks: [risk(1)] });
    const table = await screen.findByRole('table', { name: /Saved risk assessments/ });
    expect(within(table).getByText('Demo heuristic')).toBeInTheDocument();
  });

  it('explains when there is too little data for a chart, and draws one with two points', async () => {
    await renderApp({ risks: [risk(1)] });
    expect(await screen.findByText(/Save at least two assessments/)).toBeInTheDocument();
  });

  it('describes the chart for screen readers when it can be drawn', async () => {
    await renderApp({ risks: [risk(2, 60, 'Moderate'), risk(1)] });
    expect(await screen.findByRole('img', { name: /Line chart of 2 demo risk scores.*Latest 60 out of 100, Moderate/ })).toBeInTheDocument();
  });

  it('sends numbers to the API and reports dry-run alert matches', async () => {
    await renderApp();
    api.addRisk.mockResolvedValue({
      ...risk(5),
      triggered_alerts: [{ id: 9, alert_id: 1, alert_name: 'Rule A', location: 'Chennai', threshold: 20, risk_score: 25.7, created_at: T }],
    });
    await userEvent.click(screen.getByRole('button', { name: 'Calculate demo score' }));
    expect(api.addRisk).toHaveBeenCalledWith({ location: 'Chennai', rainfall_mm: 55, river_level_m: null });
    
    expect(screen.getByText(/Rule A · Chennai · score 25.7 ≥ 20/)).toBeInTheDocument();
  });

  it('shows API errors instead of failing silently', async () => {
    await renderApp();
    api.addRisk.mockRejectedValue(new Error('Rainfall must be at most 2000'));
    await userEvent.click(screen.getByRole('button', { name: 'Calculate demo score' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Rainfall must be at most 2000');
  });
});

describe('alert rules', () => {
  it('toggles a rule by sending the full rule', async () => {
    await renderApp({ alerts: [rule()] });
    api.updAlert.mockResolvedValue(rule({ enabled: false }));
    await userEvent.click(await screen.findByRole('button', { name: /Rule A: enabled/i }));
    expect(api.updAlert).toHaveBeenCalledWith(1, { name: 'Rule A', location: 'Chennai', threshold: 70, enabled: false });
    expect(await screen.findByRole('button', { name: /Rule A: disabled/i })).toHaveAttribute('aria-pressed', 'false');
  });

  it('deletes a rule', async () => {
    await renderApp({ alerts: [rule()] });
    api.delAlert.mockResolvedValue({ deleted: true });
    await userEvent.click(await screen.findByRole('button', { name: 'Delete rule Rule A' }));
    expect(api.delAlert).toHaveBeenCalledWith(1);
    await waitFor(() => expect(screen.queryByText('Rule A')).not.toBeInTheDocument());
  });

  
});

describe('satellite analysis', () => {
  const upload = async () => {
    const input = await screen.findByLabelText(/Choose a satellite image/);
    await userEvent.upload(input, new File(['x'], 'scene.png', { type: 'image/png' }));
    await userEvent.click(screen.getByRole('button', { name: 'Submit for analysis' }));
  };

  it('shows overlay, counts and the reason when no area can be computed', async () => {
    await renderApp();
    api.analyze.mockResolvedValue(COMPLETED);
    await upload();
    expect(await screen.findByRole('img', { name: /Predicted flood mask overlaid/ })).toHaveAttribute('src', 'data:image/png;base64,AAAA');
    expect(screen.getByText(/60,000 \(50.00%\)/)).toBeInTheDocument();
    expect(screen.getByText(/Area not estimated: This image format carries no georeferencing/)).toBeInTheDocument();
    await waitFor(() => expect(api.analyses).toHaveBeenCalledTimes(2)); // history refetched after a completed run
  });

  it('shows an estimated area when the API provides one', async () => {
    await renderApp();
    api.analyze.mockResolvedValue({ ...COMPLETED, area: { available: true, flooded_area_km2: 0.2048, crs: 'EPSG:32644' } });
    await upload();
    expect(await screen.findByText('Estimated flooded area: 0.2048 km² (EPSG:32644)')).toBeInTheDocument();
  });

  it('shows no mask when no model is installed', async () => {
    await renderApp();
    api.analyze.mockResolvedValue({ status: 'model_not_configured', message: 'The image is valid, but no segmentation model is available.', image: COMPLETED.image, mask: null });
    await upload();
    expect(await screen.findByText('No segmentation model available')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: /Predicted flood mask/ })).not.toBeInTheDocument();
    expect(api.analyses).toHaveBeenCalledTimes(1);
  });

  it('shows validation errors from the API', async () => {
    await renderApp();
    api.analyze.mockRejectedValue(new Error('The file is not a readable PNG, JPEG or TIFF image.'));
    await upload();
    expect(await screen.findByRole('alert')).toHaveTextContent('not a readable PNG');
  });

  it('asks for a file before submitting', async () => {
    await renderApp();
    await userEvent.click(await screen.findByRole('button', { name: 'Submit for analysis' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Choose an image first.');
    expect(api.analyze).not.toHaveBeenCalled();
  });

  it('lists completed runs from the database', async () => {
    await renderApp({ analyses: [{ id: 1, filename: 'scene.png', width: 400, height: 300, model_name: 'm', model_version: '1', flooded_fraction: 0.5, flooded_area_km2: null, created_at: T }] });
    const table = await screen.findByRole('table', { name: /Completed segmentation runs/ });
    expect(within(table).getByText('scene.png')).toBeInTheDocument();
    expect(within(table).getByText('50.00%')).toBeInTheDocument();
    expect(within(table).getByText('—')).toBeInTheDocument();
  });
});

describe('accessibility', () => {
  it('gives every button an accessible name', async () => {
    await renderApp({ alerts: [rule()], risks: [risk(1)] });
    await screen.findByRole('button', { name: /Rule A: enabled/i });
    for (const b of screen.getAllByRole('button')) expect(b).toHaveAccessibleName();
  });

  it('has a skip link, one main landmark and one h1', async () => {
    await renderApp();
    expect(screen.getByRole('link', { name: 'Skip to main content' })).toHaveAttribute('href', '#main');
    expect(screen.getAllByRole('main')).toHaveLength(1);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
  });

  it('has no axe violations (populated dashboard)', async () => {
    const { container } = await renderApp({ risks: [risk(2, 60, 'Moderate'), risk(1)], alerts: [rule()], analyses: [], events: [] });
    await screen.findByRole('img', { name: /Line chart/ });
    expect(await axe(container)).toHaveNoViolations();
  });

  it('has no axe violations (empty / error state)', async () => {
    mockApi({ health: new Error('Cannot reach the API. Is the backend running?') });
    const { container } = render(<App />);
    await screen.findByRole('alert');
    expect(await axe(container)).toHaveNoViolations();
  });
});
