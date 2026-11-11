import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight, Rows3 } from 'lucide-react'
import { useState } from 'react'
import { getDisagreements } from '../api'
import { formatValue, fmtPercent, MODEL_LABELS } from '../format'
import StatusBanner from './StatusBanner'

const BUCKET_OPTIONS = [
  ['all', 'All disagreements'],
  ['only_a', 'Only A correct'],
  ['only_b', 'Only B correct'],
  ['both_wrong_diff', 'Both wrong, different labels'],
]

export default function DisagreementTable({ runId, pair, classNames }) {
  const [bucket, setBucket] = useState('all')
  const [trueClass, setTrueClass] = useState('')
  const [page, setPage] = useState(1)
  const query = useQuery({
    queryKey: ['disagreements', runId, pair.model_a, pair.model_b, bucket, trueClass, page],
    queryFn: () => getDisagreements(runId, {
      a: pair.model_a,
      b: pair.model_b,
      bucket,
      trueClass,
      page,
      pageSize: 25,
    }),
    placeholderData: (previousData) => previousData,
  })

  const updateFilter = (setter) => (event) => {
    setter(event.target.value)
    setPage(1)
  }
  const result = query.data
  const totalPages = result ? Math.max(1, Math.ceil(result.total / result.page_size)) : 1
  const featureNames = result?.rows?.[0] ? Object.keys(result.rows[0].features) : []

  return (
    <section className="results-section-card" aria-labelledby="disagreements-title">
      <div className="section-heading">
        <div className="heading-with-icon">
          <span className="heading-icon blue"><Rows3 size={17} /></span>
          <div><span className="section-kicker">ROW-LEVEL REVIEW</span><h2 id="disagreements-title">Disagreements</h2></div>
        </div>
        <span className="quiet-tag">{result ? `${result.total.toLocaleString()} rows` : 'Test set'}</span>
      </div>
      <div className="filter-bar">
        <label className="field filter-field">
          <span className="field-label">Bucket</span>
          <select value={bucket} onChange={updateFilter(setBucket)}>
            {BUCKET_OPTIONS.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </label>
        <label className="field filter-field">
          <span className="field-label">Actual class</span>
          <select value={trueClass} onChange={updateFilter(setTrueClass)}>
            <option value="">All classes</option>
            {classNames.map((name) => <option key={name} value={name}>{name}</option>)}
          </select>
        </label>
      </div>

      {query.error && <StatusBanner error={query.error} tone="error" />}
      {query.isPending ? (
        <div className="loading-inline"><span className="spinner" /> Loading rows…</div>
      ) : result?.rows.length ? (
        <>
          <div className="table-scroll disagreement-scroll">
            <table className="data-table results-table disagreement-table">
              <thead>
                <tr>
                  <th>Row</th>
                  {featureNames.map((name) => <th key={name}>{name}</th>)}
                  <th>Actual</th>
                  <th>{MODEL_LABELS[pair.model_a] ?? pair.model_a}</th>
                  <th>Confidence</th>
                  <th>{MODEL_LABELS[pair.model_b] ?? pair.model_b}</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row) => (
                  <tr key={row.row_id}>
                    <td>{row.row_id.toLocaleString()}</td>
                    {featureNames.map((name) => <td key={name}>{formatValue(row.features[name])}</td>)}
                    <td className="class-label">{row.y_true}</td>
                    <td>{row.pred_a}</td>
                    <td>{fmtPercent(row.prob_a, 0)}</td>
                    <td>{row.pred_b}</td>
                    <td>{fmtPercent(row.prob_b, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <span>{result.total ? `${((page - 1) * result.page_size + 1).toLocaleString()}–${Math.min(page * result.page_size, result.total).toLocaleString()} of ${result.total.toLocaleString()}` : '0 rows'}</span>
            <div>
              <button className="button button-secondary" type="button" disabled={page <= 1 || query.isFetching} onClick={() => setPage((current) => current - 1)} aria-label="Previous page"><ArrowLeft size={14} /> Previous</button>
              <span className="page-count">Page {page} of {totalPages}</span>
              <button className="button button-secondary" type="button" disabled={page >= totalPages || query.isFetching} onClick={() => setPage((current) => current + 1)} aria-label="Next page">Next <ArrowRight size={14} /></button>
            </div>
          </div>
        </>
      ) : (
        !query.error && <div className="results-empty">No rows match these filters.</div>
      )}
    </section>
  )
}
