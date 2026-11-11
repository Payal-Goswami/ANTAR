import { useQuery } from '@tanstack/react-query'
import { ChartNoAxesColumn, FlaskConical } from 'lucide-react'
import { useState } from 'react'
import { getSlices } from '../api'
import { fmtPercent, MODEL_LABELS } from '../format'
import StatusBanner from './StatusBanner'

export default function SliceView({ runId, pair, features }) {
  const [featureName, setFeatureName] = useState('')
  const feature = featureName || features[0]?.name || ''
  const query = useQuery({
    queryKey: ['slices', runId, pair.model_a, pair.model_b, feature],
    queryFn: () => getSlices(runId, { a: pair.model_a, b: pair.model_b, feature }),
    enabled: Boolean(feature),
  })

  return (
    <section className="results-section-card" aria-labelledby="slices-title">
      <div className="section-heading">
        <div className="heading-with-icon">
          <span className="heading-icon orange"><ChartNoAxesColumn size={17} /></span>
          <div><span className="section-kicker">EXPLORATORY</span><h2 id="slices-title">Feature slices</h2></div>
        </div>
        <span className="quiet-tag">Test set</span>
      </div>
      <div className="slice-controls">
        <p className="muted-copy">Compare this pair across values of one feature.</p>
        <label className="field slice-feature-select">
          <span className="field-label">Feature</span>
          <select value={feature} onChange={(event) => setFeatureName(event.target.value)}>
            {features.map((item) => <option key={item.name} value={item.name}>{item.name}</option>)}
          </select>
        </label>
      </div>
      {query.error && <StatusBanner error={query.error} tone="error" />}
      {query.isPending ? (
        <div className="loading-inline"><span className="spinner" /> Loading slices…</div>
      ) : query.data?.slices.length ? (
        <div className="table-scroll">
          <table className="data-table results-table">
            <thead>
              <tr>
                <th>Slice</th><th>Rows</th>
                <th>{MODEL_LABELS[pair.model_a] ?? pair.model_a} accuracy</th>
                <th>{MODEL_LABELS[pair.model_b] ?? pair.model_b} accuracy</th>
                <th>A-only</th><th>B-only</th><th>Disagreements</th><th>Rate (95% CI)</th>
              </tr>
            </thead>
            <tbody>
              {query.data.slices.map((row) => (
                <tr className={row.low_support ? 'low-support' : ''} key={row.label}>
                  <td>{row.label}{row.low_support && <span className="support-tag">Low support</span>}</td>
                  <td>{row.n.toLocaleString()}</td>
                  <td>{fmtPercent(row.acc_a)}</td>
                  <td>{fmtPercent(row.acc_b)}</td>
                  <td>{row.b}</td>
                  <td>{row.c}</td>
                  <td>{row.disagreements}</td>
                  <td>{fmtPercent(row.disagreement_rate)} <small>({fmtPercent(row.wilson_low)}–{fmtPercent(row.wilson_high)})</small></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !query.error && <div className="results-empty"><FlaskConical size={16} />No slices available for this feature.</div>
      )}
      <p className="exploratory-note">Slices are exploratory. Small groups have low support and uncertain rates.</p>
    </section>
  )
}
