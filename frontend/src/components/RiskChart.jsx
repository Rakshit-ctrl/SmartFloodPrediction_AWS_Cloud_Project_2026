import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';

const AXIS = '#9aaabf';
const TOOLTIP = { background: '#0b1929', border: '1px solid #2a3d53', color: '#e8eef8' };

export default function RiskChart({ data }) {
  if (data.length < 2) {
    return <p className="subtle">Save at least two assessments to see the score trend.</p>;
  }
  const latest = data[data.length - 1];
  return (
    <figure className="chart">
      <figcaption>Demo risk score, last {data.length} assessments (illustrative heuristic, not a forecast)</figcaption>
      <div
        className="chartbox"
        role="img"
        aria-label={`Line chart of ${data.length} demo risk scores from oldest to newest. Latest ${latest.score} out of 100, ${latest.level}. The table below lists the same values.`}
      >
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid stroke="#26374c" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke={AXIS} tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis domain={[0, 100]} stroke={AXIS} tick={{ fontSize: 11 }} width={36} />
            <Tooltip contentStyle={TOOLTIP} />
            <ReferenceLine y={35} stroke="#f0bf70" strokeDasharray="4 4" label={{ value: 'Moderate ≥35', fill: '#f0bf70', fontSize: 11, position: 'insideTopLeft' }} />
            <ReferenceLine y={70} stroke="#ff9aa5" strokeDasharray="4 4" label={{ value: 'High ≥70', fill: '#ff9aa5', fontSize: 11, position: 'insideTopLeft' }} />
            <Line dataKey="score" name="Demo score" stroke="#56d7e5" strokeWidth={2} dot />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
