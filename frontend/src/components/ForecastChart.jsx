import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { forecastSeries } from '../format';

const AXIS = '#9aaabf';
const TOOLTIP = { background: '#0b1929', border: '1px solid #2a3d53', color: '#e8eef8' };

export default function ForecastChart({ forecast }) {
  if (!forecast?.available) return null;
  const data = forecastSeries(forecast);
  const total = forecast.total_rainfall_mm_reported;
  return (
    <section className="forecast" aria-label="Forecast, not observed">
      <small>
        FORECAST (NOT OBSERVED) · next {data.length * 3} h ·{' '}
        {total == null ? 'no rain volume reported' : `reported rain total ${total} mm`}
      </small>
      <div
        className="chartbox"
        role="img"
        aria-label={`Combined chart of forecast rain per 3 hours and rain chance for the next ${data.length * 3} hours. The table below has the same values.`}
      >
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={data} margin={{ top: 8, right: 4, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#26374c" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke={AXIS} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis yAxisId="mm" stroke={AXIS} tick={{ fontSize: 11 }} width={44} />
            <YAxis yAxisId="pct" orientation="right" domain={[0, 100]} stroke={AXIS} tick={{ fontSize: 11 }} width={40} />
            <Tooltip contentStyle={TOOLTIP} />
            <Legend />
            <Bar yAxisId="mm" dataKey="rain" name="Rain per 3 h (mm)" fill="#4bd0de" />
            <Line yAxisId="pct" dataKey="chance" name="Rain chance (%)" stroke="#f0bf70" dot={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <details>
        <summary>Forecast table</summary>
        <div className="tablewrap">
          <table>
            <caption className="sr-only">Forecast by 3-hour period. A dash means the provider did not report a value.</caption>
            <thead>
              <tr>
                <th scope="col">TIME</th>
                <th scope="col">TEMP</th>
                <th scope="col">RAIN CHANCE</th>
                <th scope="col">RAIN / 3H</th>
              </tr>
            </thead>
            <tbody>
              {forecast.periods.map((p, i) => (
                <tr key={p.time}>
                  <td>{data[i].time}</td>
                  <td>{p.temperature_c}°C</td>
                  <td>{data[i].chance == null ? '—' : `${data[i].chance}%`}</td>
                  <td>{p.rainfall_mm_3h == null ? '—' : `${p.rainfall_mm_3h} mm`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </section>
  );
}
