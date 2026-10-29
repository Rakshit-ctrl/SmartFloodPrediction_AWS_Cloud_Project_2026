import { useState } from 'react';
import { Bell, Trash2 } from 'lucide-react';
import { dateTime } from '../format';

export default function AlertsPanel({ alerts, events, onCreate, onToggle, onDelete }) {
  const [name, setName] = useState('Heavy rainfall watch');
  const [loc, setLoc] = useState('Chennai');
  const [threshold, setThreshold] = useState('70');

  function submit(e) {
    e.preventDefault();
    onCreate({ name, location: loc, threshold: Number(threshold), enabled: true });
  }

  return (
    <section className="panel" id="alerts" aria-labelledby="alerts-title">
      <div className="panelhead">
        <div>
          <small>NOTIFICATION WORKFLOW</small>
          <h2 id="alerts-title">Alert rules</h2>
        </div>
        <span className="pill">Dry-run only</span>
      </div>
      <form className="alertform" onSubmit={submit}>
        <label>
          Rule name
          <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={120} />
        </label>
        <label>
          Location
          <input value={loc} onChange={(e) => setLoc(e.target.value)} required maxLength={160} />
        </label>
        <label>
          Threshold (0–100)
          <input type="number" min="0" max="100" value={threshold} onChange={(e) => setThreshold(e.target.value)} required />
        </label>
        <button>Add rule</button>
      </form>
      <ul className="rules">
        {alerts.map((a) => (
          <li className="alertrow" key={a.id}>
            <Bell aria-hidden="true" />
            <div>
              <b>{a.name}</b>
              <small>
                {a.location} · threshold {a.threshold}/100
              </small>
            </div>
            <button
              type="button"
              className="toggle"
              aria-pressed={a.enabled}
              aria-label={`${a.name}: ${a.enabled ? 'enabled' : 'disabled'}. Press to ${a.enabled ? 'disable' : 'enable'}`}
              onClick={() => onToggle(a)}
            >
              {a.enabled ? 'Enabled' : 'Disabled'}
            </button>
            <button type="button" className="delete" aria-label={`Delete rule ${a.name}`} onClick={() => onDelete(a)}>
              <Trash2 size={16} aria-hidden="true" />
            </button>
          </li>
        ))}
      </ul>
      {!alerts.length && <p className="subtle">No alert rules yet.</p>}
      <p className="subtle">
        Saving a rule does not send a notification. Rules are checked in dry-run mode against demo scores when an assessment is saved; SNS delivery is not implemented.
      </p>
      {events.length > 0 && (
        <div className="events">
          <h3>Dry-run trigger log (no notifications sent)</h3>
          <ul>
            {events.slice(0, 5).map((e) => (
              <li key={e.id}>
                {e.alert_name} · {e.location} · score {e.risk_score} ≥ {e.threshold} · {dateTime(e.created_at)}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
