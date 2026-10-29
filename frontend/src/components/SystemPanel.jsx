import { stateLabel } from '../format';

function Row({ name, good, text }) {
  return (
    <div className="component">
      <span>{name}</span>
      <b className={good ? 'good' : 'bad'}>{text}</b>
    </div>
  );
}

export default function SystemPanel({ online, weather, modelState }) {
  return (
    <article className="panel" aria-labelledby="system-title">
      <small>PROJECT STATUS</small>
      <h2 id="system-title">System components</h2>
      <Row name="REST API + database" good={online} text={online ? 'Connected' : 'Offline'} />
      <Row name="Weather provider" good={weather?.available} text={weather?.available ? 'Connected' : 'Not configured'} />
      <Row name="Satellite segmentation model" good={modelState === 'ready'} text={stateLabel(modelState)} />
      <Row name="AWS notification delivery" good={false} text="Not configured" />
      <p className="subtle">This dashboard shows no AI accuracy metrics because none have been measured.</p>
    </article>
  );
}
