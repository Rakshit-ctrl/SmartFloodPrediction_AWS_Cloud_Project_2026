import { Activity, Bell, CloudRain, Droplets, Satellite } from 'lucide-react';
import { mm } from '../format';

function Card({ icon, label, value, detail }) {
  return (
    <article className="stat">
      <div className="staticon" aria-hidden="true">
        {icon}
      </div>
      <small>{label}</small>
      <strong>{value}</strong>
      <p>{detail}</p>
    </article>
  );
}

export default function StatCards({ weather, risks, alerts, analyses }) {
  const latest = risks[0];
  const enabled = alerts.filter((a) => a.enabled).length;
  return (
    <section className="stats" aria-label="Key figures">
      <Card
        icon={<CloudRain />}
        label="RAIN / LAST HOUR"
        value={weather?.available ? mm(weather.rainfall_mm_1h) : '—'}
        detail={weather?.available ? 'OpenWeather observation' : 'Weather API unavailable'}
      />
      <Card
        icon={<Droplets />}
        label="LATEST DEMO RISK"
        value={latest ? `${latest.risk_score}/100` : '—'}
        detail={latest ? `${latest.location} · ${latest.risk_level}` : 'Create an assessment below'}
      />
      <Card icon={<Activity />} label="ASSESSMENTS SAVED" value={risks.length} detail="Stored in the database" />
      <Card icon={<Satellite />} label="SATELLITE RUNS" value={analyses.length} detail="Completed segmentations only" />
      <Card icon={<Bell />} label="ALERT RULES" value={alerts.length} detail={`${enabled} enabled · dry-run only`} />
    </section>
  );
}
