import { useEffect, useState } from 'react';
import { RefreshCw, ShieldAlert } from 'lucide-react';
import { api } from './api';
import AlertsPanel from './components/AlertsPanel';
import { MobileNav, Sidebar, useActiveSection } from './components/Navigation';
import Notice from './components/Notice';
import RiskPanel from './components/RiskPanel';
import SatellitePanel from './components/SatellitePanel';
import StatCards from './components/StatCards';
import SystemPanel from './components/SystemPanel';
import WeatherPanel from './components/WeatherPanel';

export default function App() {
  const [city, setCity] = useState('Chennai');
  const [online, setOnline] = useState(false);
  const [modelState, setModelState] = useState('not_configured');
  const [weather, setWeather] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [risks, setRisks] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [events, setEvents] = useState([]);
  const [analyses, setAnalyses] = useState([]);
  const [note, setNote] = useState(null);
  const active = useActiveSection();

  const notify = (text, kind = 'info') => setNote(text ? { text, kind } : null);
  const fail = (e) => notify(e.message, 'error');

  async function refreshWeather() {
    const [w, f] = await Promise.allSettled([api.weather(city), api.forecast(city)]);
    if (w.status === 'fulfilled') {
      setWeather(w.value);
    } else {
      setWeather(null);
      notify(w.reason.message, 'error');
    }
    setForecast(f.status === 'fulfilled' ? f.value : null);
  }

  // Each resource loads independently so one failure never blanks the dashboard.
  async function load() {
    const [h, r, a, ev, an] = await Promise.allSettled([api.health(), api.risks(), api.alerts(), api.events(), api.analyses()]);
    if (h.status === 'fulfilled') {
      setOnline(h.value.status === 'ok');
      setModelState(h.value.model_state || 'not_configured');
    } else {
      setOnline(false);
      notify(`${h.reason.message} Start the backend and refresh.`, 'error');
    }
    if (r.status === 'fulfilled') setRisks(r.value);
    if (a.status === 'fulfilled') setAlerts(a.value);
    if (ev.status === 'fulfilled') setEvents(ev.value);
    if (an.status === 'fulfilled') setAnalyses(an.value);
    if (h.status === 'fulfilled') await refreshWeather();
  }

  useEffect(() => {
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function createRisk(payload) {
    try {
      const r = await api.addRisk(payload);
      const triggered = r.triggered_alerts || [];
      setRisks((p) => [r, ...p]);
      setEvents((p) => [...triggered, ...p]);
      notify(
        triggered.length
          ? `Demo score saved. ${triggered.length} alert rule(s) matched (dry-run: no notification sent).`
          : 'Demo score saved; this is not a validated flood forecast.',
      );
    } catch (e) {
      fail(e);
    }
  }

  async function createAlert(payload) {
    try {
      const a = await api.addAlert(payload);
      setAlerts((p) => [a, ...p]);
      
    } catch (e) {
      fail(e);
    }
  }

  async function toggleAlert(a) {
    try {
      const u = await api.updAlert(a.id, { name: a.name, location: a.location, threshold: a.threshold, enabled: !a.enabled });
      setAlerts((p) => p.map((x) => (x.id === u.id ? u : x)));
    } catch (e) {
      fail(e);
    }
  }

  async function deleteAlert(a) {
    try {
      await api.delAlert(a.id);
      setAlerts((p) => p.filter((x) => x.id !== a.id));
    } catch (e) {
      fail(e);
    }
  }

  async function analyze(file) {
    const result = await api.analyze(file);
    if (result.status === 'completed') {
      api.analyses().then(setAnalyses).catch(fail);
    }
    return result;
  }

  return (
    <div className="layout">
      <a className="skip" href="#main">
        Skip to main content
      </a>
      <Sidebar online={online} active={active} />
      <main id="main" tabIndex={-1}>
        <MobileNav active={active} />
        <div className="topbar">
          <span>
            Workspace / <b>Overview</b>
          </span>
          <span className="status">
            ● LOCAL PROTOTYPE
            <button type="button" className="icon" aria-label="Refresh all data" onClick={load}>
              <RefreshCw size={15} aria-hidden="true" />
            </button>
          </span>
        </div>

        <section className="heading" id="overview" aria-labelledby="page-title">
          <div>
            <small>FLOOD MONITORING / DASHBOARD</small>
            <h1 id="page-title">Climate risk overview</h1>
            <p>Monitor weather, review demo assessments, and inspect satellite imagery.</p>
          </div>
          <form
            className="city"
            onSubmit={(e) => {
              e.preventDefault();
              refreshWeather();
            }}
          >
            <input aria-label="City for weather" value={city} onChange={(e) => setCity(e.target.value)} maxLength={100} />
            <button>Update weather</button>
          </form>
        </section>

        <Notice note={note} onDismiss={() => setNote(null)} />
        <div className="warning" role="note">
          <ShieldAlert size={18} aria-hidden="true" />
          <span>
            <b>Prototype only:</b> risk scores are illustrative heuristics and satellite segmentation runs only when a trained model is installed. Do not use for emergency decisions.
          </span>
        </div>

        <StatCards weather={weather} risks={risks} alerts={alerts} analyses={analyses} />

        <section className="columns">
          <WeatherPanel weather={weather} forecast={forecast} city={city} />
          <SystemPanel online={online} weather={weather} modelState={modelState} />
        </section>

        <section className="columns lower">
          <RiskPanel risks={risks} onCreate={createRisk} />
          <SatellitePanel analyses={analyses} onAnalyze={analyze} onError={(m) => notify(m, 'error')} />
        </section>

        <AlertsPanel alerts={alerts} events={events} onCreate={createAlert} onToggle={toggleAlert} onDelete={deleteAlert} />

        <footer>
          FloodSignal · Climate Risk Prototype <span>Not for emergency or operational use</span>
        </footer>
      </main>
    </div>
  );
}
