export default function Confidence({ score }) {
  const pct = Math.round(score * 100)
  const level = pct >= 85 ? 'high' : pct >= 65 ? 'mid' : 'low'
  return (
    <span className={'conf conf-' + level}>
      <span className="conf-dot" />
      {pct}%
    </span>
  )
}
