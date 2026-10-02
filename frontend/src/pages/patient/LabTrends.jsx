function TrendChart({ series }) {
  const w = 560
  const h = 140
  const pad = 30
  const values = series.points.map((p) => p.value)
  const [lo, hi] = series.range
  const min = Math.min(...values, lo) * 0.9
  const max = Math.max(...values, hi) * 1.1
  const xStep = (w - pad * 2) / (series.points.length - 1 || 1)
  const yFor = (v) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2)
  const xFor = (i) => pad + i * xStep

  const linePath = series.points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i)} ${yFor(p.value)}`).join(' ')
  const rangeTop = yFor(hi)
  const rangeBottom = yFor(lo)
  const lastAbnormal = values[values.length - 1] < lo || values[values.length - 1] > hi

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 6 }}>
        <div className="card-title" style={{ margin: 0 }}>{series.test}</div>
        <div className={'stat-delta' + (lastAbnormal ? ' warn' : '')} style={{ fontSize: 12.5 }}>
          Latest: {values[values.length - 1]} {series.unit} {lastAbnormal ? '· out of range' : '· in range'}
        </div>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} width="100%" height={h}>
        <rect x={pad} y={rangeTop} width={w - pad * 2} height={Math.max(rangeBottom - rangeTop, 0)} fill="var(--teal-soft)" opacity="0.6" />
        <line x1={pad} y1={h - pad} x2={w - pad} y2={h - pad} stroke="var(--line)" strokeWidth="1" />
        <path d={linePath} fill="none" stroke="var(--amber)" strokeWidth="2.5" />
        {series.points.map((p, i) => (
          <circle key={i} cx={xFor(i)} cy={yFor(p.value)} r="4" fill={p.value < lo || p.value > hi ? 'var(--red)' : 'var(--teal)'} />
        ))}
        {series.points.map((p, i) => (
          <text key={i} x={xFor(i)} y={h - 8} fontSize="10" fill="var(--text-muted)" textAnchor="middle">
            {p.date}
          </text>
        ))}
      </svg>
      <div className="muted" style={{ fontSize: 12 }}>
        Reference range: {lo}–{hi} {series.unit}
      </div>
    </div>
  )
}

export default function LabTrends({ series }) {
  if (!series.length) {
    return <div className="card muted">No lab results indexed for this patient yet.</div>
  }
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {series.map((s) => (
        <TrendChart key={s.test} series={s} />
      ))}
    </div>
  )
}
