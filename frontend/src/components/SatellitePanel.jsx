import { useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { dateTime, percent } from '../format';

function Result({ result }) {
  const done = result.status === 'completed';
  return (
    <div className="result">
      <b>{done ? 'Segmentation completed' : 'No segmentation model available'}</b>
      <p>{result.message}</p>
      {result.image && (
        <small>
          {result.image.width}×{result.image.height} px · {result.image.format} · {result.image.channels} channel(s)
        </small>
      )}
      {done && (
        <>
          <img className="overlay" alt="Predicted flood mask overlaid on the uploaded image" src={`data:image/png;base64,${result.overlay_png_base64}`} />
          <p>
            Predicted flooded pixels: {result.mask.flooded_pixels.toLocaleString()} ({percent(result.mask.flooded_fraction)}) · model{' '}
            {result.model.name} {result.model.version} · {result.inference_ms} ms
          </p>
          <p>
            {result.area.available
              ? `Estimated flooded area: ${result.area.flooded_area_km2} km² (${result.area.crs})`
              : `Area not estimated: ${result.area.reason}`}
          </p>
        </>
      )}
    </div>
  );
}

export default function SatellitePanel({ analyses, onAnalyze, onError }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function submit(e) {
    e.preventDefault();
    if (!file) {
      onError('Choose an image first.');
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      setResult(await onAnalyze(file));
    } catch (err) {
      onError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="panel" id="satellite" aria-labelledby="sat-title">
      <small>EARTH OBSERVATION</small>
      <h2 id="sat-title">Satellite image analysis</h2>
      <p className="subtle">
        Images are validated first. Segmentation runs only when a trained model is installed; the result is a prediction for that image, not a forecast.
      </p>
      <form onSubmit={submit} className="upload">
        <label>
          <UploadCloud aria-hidden="true" />
          <b>{file?.name || 'Choose a satellite image'}</b>
          <small>PNG, JPG or TIFF · default limit 8 MB</small>
          <input
            type="file"
            accept=".png,.jpg,.jpeg,.tif,.tiff"
            onChange={(e) => {
              setFile(e.target.files?.[0] || null);
              setResult(null);
            }}
          />
        </label>
        <button disabled={busy}>{busy ? 'Analysing…' : 'Submit for analysis'}</button>
      </form>
      <div aria-live="polite">{result && <Result result={result} />}</div>

      <h3>Completed runs</h3>
      <div className="tablewrap">
        <table>
          <caption className="sr-only">Completed segmentation runs, newest first. Metadata only; images are not stored.</caption>
          <thead>
            <tr>
              <th scope="col">FILE</th>
              <th scope="col">SIZE</th>
              <th scope="col">MODEL</th>
              <th scope="col">FLOODED</th>
              <th scope="col">AREA</th>
              <th scope="col">TIME</th>
            </tr>
          </thead>
          <tbody>
            {analyses.slice(0, 8).map((a) => (
              <tr key={a.id}>
                <td>{a.filename}</td>
                <td>
                  {a.width}×{a.height}
                </td>
                <td>
                  {a.model_name} {a.model_version}
                </td>
                <td>{percent(a.flooded_fraction)}</td>
                <td>{a.flooded_area_km2 == null ? '—' : `${a.flooded_area_km2} km²`}</td>
                <td>{dateTime(a.created_at)}</td>
              </tr>
            ))}
            {!analyses.length && (
              <tr>
                <td colSpan="6">No completed segmentation runs yet.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </article>
  );
}
