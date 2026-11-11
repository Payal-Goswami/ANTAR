import { lazy, Suspense } from 'react'
import { fmtPercent, fmtPValue, MODEL_LABELS } from '../format'
import ConfusionMatrix from './ConfusionMatrix'

const BucketsChart = lazy(() => import('./BucketsChart'))

const BUCKET_LABELS = [
  ['both_right', 'Both correct'],
  ['both_wrong', 'Both wrong'],
  ['only_a', 'Only A correct'],
  ['only_b', 'Only B correct'],
]

export default function PairDetail({ pair, metrics, classNames }) {
  const modelA = metrics[pair.model_a]
  const modelB = metrics[pair.model_b]
  return (
    <section className="results-section-card pair-detail" aria-labelledby="pair-detail-title">
      <div className="section-heading">
        <div className="heading-with-icon">
          <span className="heading-icon slate"><span className="pair-glyph">A/B</span></span>
          <div>
            <span className="section-kicker">SELECTED COMPARISON</span>
            <h2 id="pair-detail-title">{MODEL_LABELS[pair.model_a] ?? pair.model_a} <span className="title-vs">vs</span> {MODEL_LABELS[pair.model_b] ?? pair.model_b}</h2>
          </div>
        </div>
        <span className="quiet-tag">{pair.disagreement_count.toLocaleString()} disagreements</span>
      </div>

      <div className="pair-detail-grid">
        <div className="bucket-summary">
          <div className="subsection-title"><strong>Correctness buckets</strong><span>Same held-out rows</span></div>
          <div className="bucket-list">
            {BUCKET_LABELS.map(([key, label]) => (
              <div className="bucket-row" key={key}>
                <span>{label}</span>
                <strong>{pair.buckets[key].toLocaleString()}</strong>
              </div>
            ))}
          </div>
          <div className="bucket-rates">
            <span>Disagreement rate</span><strong>{fmtPercent(pair.disagreement_rate)}</strong>
            <span>Exact McNemar p</span><strong>{fmtPValue(pair.p_raw)}</strong>
            <span>Holm-adjusted p</span><strong>{fmtPValue(pair.p_holm)}</strong>
          </div>
          <Suspense fallback={<div className="chart-loading">Preparing chart…</div>}>
            <BucketsChart buckets={pair.buckets} />
          </Suspense>
        </div>
        <div className="class-disagreement">
          <div className="subsection-title"><strong>Disagreement by actual class</strong><span>Label-wise test rows</span></div>
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Actual class</th><th>Rows</th><th>Disagreements</th><th>Rate</th></tr></thead>
              <tbody>
                {classNames.map((name, index) => {
                  const row = pair.per_true_class[index] ?? pair.per_true_class[String(index)]
                  return (
                    <tr key={name}>
                      <td className="class-label">{name}</td>
                      <td>{row?.rows ?? 0}</td>
                      <td>{row?.disagreements ?? 0}</td>
                      <td>{fmtPercent(row?.rate)}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <p className="stat-note">Statistical significance is not practical importance. A non-significant result does not show the models are equal. McNemar reflects test-set sampling uncertainty.</p>
        </div>
      </div>

      <div className="matrix-grid">
        <ConfusionMatrix modelKey={pair.model_a} label={MODEL_LABELS[pair.model_a] ?? pair.model_a} metric={modelA} classNames={classNames} />
        <ConfusionMatrix modelKey={pair.model_b} label={MODEL_LABELS[pair.model_b] ?? pair.model_b} metric={modelB} classNames={classNames} />
      </div>
    </section>
  )
}
