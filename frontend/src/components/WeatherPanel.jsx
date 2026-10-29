import { CloudRain } from 'lucide-react';
import { dateTime, mm } from '../format';
import ForecastChart from './ForecastChart';

export default function WeatherPanel({ weather, forecast, city }) {
  const ok = weather?.available;
  const hasPoint = ok && weather.lat != null && weather.lon != null;
  return (
    <article className="panel" aria-labelledby="weather-title">
      <div className="panelhead">
        <div>
          <small>CURRENT OBSERVATION</small>
          <h2 id="weather-title">{weather?.city || city} conditions</h2>
        </div>
        <span className="pill">{ok ? 'Connected' : 'Not connected'}</span>
      </div>
      {ok ? (
        <>
          <div className="weather">
            <div>
              <strong>
                {weather.temperature_c}°<small>C</small>
              </strong>
              <p>{weather.description}</p>
            </div>
            <CloudRain size={42} aria-hidden="true" />
          </div>
          <div className="weatherfacts">
            <div>
              Humidity <b>{weather.humidity_pct}%</b>
            </div>
            <div>
              Rainfall / 1h <b>{mm(weather.rainfall_mm_1h)}</b>
            </div>
          </div>
          <p className="subtle">Observed {dateTime(weather.observed_at)}</p>
          {hasPoint && (
            <p className="subtle">
              Location {weather.lat.toFixed(3)}, {weather.lon.toFixed(3)} ·{' '}
              <a
                href={`https://www.openstreetmap.org/?mlat=${weather.lat}&mlon=${weather.lon}#map=10/${weather.lat}/${weather.lon}`}
                target="_blank"
                rel="noopener noreferrer"
              >
                Open in OpenStreetMap
              </a>
            </p>
          )}
          <ForecastChart forecast={forecast} />
        </>
      ) : (
        <div className="empty">
          <CloudRain aria-hidden="true" />
          <b>Weather unavailable</b>
          <p>{weather?.message || 'See the message above, or check OPENWEATHER_API_KEY in backend/.env.'}</p>
        </div>
      )}
    </article>
  );
}
