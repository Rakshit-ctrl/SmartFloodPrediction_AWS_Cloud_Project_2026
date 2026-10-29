import { useState } from 'react';
import { dateTime, riskSeries } from '../format';
import RiskChart from './RiskChart';

export default function RiskPanel({ risks, onCreate }) {
  const [loc, setLoc] = useState('Chennai');
  const [rain, setRain] = useState('55');
  const [river, setRiver] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    try {
      await onCreate({ location: loc, rainfall_mm: Number(rain), river_level_m: river === '' ? null : Number(river) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="panel" id="history" aria-labelledby="risk-title">
      <small>ASSESSMENT WORKFLOW</small>
      <h2 id="risk-title">Create a risk assessment</h2>
      <form className="form" onSubmit={submit}>
        <label>
          Location
          <input value={loc} onChange={(e) => setLoc(e.target.value)} required maxLength={160} />
        </label>
        <label>
          Rainfall (mm)
          <input type="number" min="0" max="2000" step=".1" value={rain} onChange={(e) => setRain(e.target.value)} required />
        </label>
        <label>
          River level (m), optional
          <input type="number" min="0" max="1000" step=".01" value={river} onChange={(e) => setRiver(e.target.value)} />
        </label>
        <button disabled={busy}>{busy ? 'Saving…' : 'Calculate demo score'}</button>
      </form>
      <RiskChart data={riskSeries(risks)} />
      <div className="tablewrap">
        <table>
          <caption className="sr-only">Saved risk assessments, newest first</caption>
          <thead>
            <tr>
              <th scope="col">LOCATION</th>
              <th scope="col">SCORE</th>
              <th scope="col">LEVEL</th>
              <th scope="col">METHOD</th>
              <th scope="col">TIME</th>
            </tr>
          </thead>
          <tbody>
            {risks.slice(0, 8).map((r) => (
              <tr key={r.id}>
                <td>{r.location}</td>
                <td>{r.risk_score}</td>
                <td>
                  <span className={`risk ${r.risk_level.toLowerCase()}`}>{r.risk_level}</span>
                </td>
                <td>{r.validated ? 'Validated' : 'Demo heuristic'}</td>
                <td>{dateTime(r.created_at)}</td>
              </tr>
            ))}
            {!risks.length && (
              <tr>
                <td colSpan="5">No assessments saved yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}
