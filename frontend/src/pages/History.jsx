import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Clock3, FileSearch, Trash2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { deleteRun, listRuns } from '../api'
import { fmtDate, MODEL_LABELS } from '../format'
import StatusBanner from '../components/StatusBanner'

export default function History() {
  const queryClient = useQueryClient()
  const runsQuery = useQuery({ queryKey: ['runs'], queryFn: listRuns })
  const deleteMutation = useMutation({
    mutationFn: deleteRun,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['runs'] }),
  })
  const runs = runsQuery.data?.runs ?? []

  const removeRun = (run) => {
    if (window.confirm(`Delete the run for "${run.display_filename}"? This cannot be undone.`)) {
      deleteMutation.mutate(run.run_id)
    }
  }

  return (
    <div className="page-stack">
      <div className="page-intro">
        <div className="eyebrow"><span className="eyebrow-line" /> WORKSPACE <span className="eyebrow-divider">/</span> HISTORY</div>
        <div className="intro-row">
          <div><h1>Run history</h1><p className="intro-copy">Saved comparisons on this device.</p></div>
          <div className="intro-mark"><Clock3 size={21} strokeWidth={1.6} /></div>
        </div>
      </div>

      {runsQuery.error && <StatusBanner error={runsQuery.error} tone="error" />}
      {deleteMutation.error && <StatusBanner error={deleteMutation.error} tone="error" />}

      {runsQuery.isPending ? (
        <div className="loading-page"><span className="spinner" /> Loading runs…</div>
      ) : runs.length ? (
        <section className="card history-card">
          <div className="section-heading">
            <div><span className="section-kicker">SAVED RUNS</span><h2>Comparisons</h2></div>
            <span className="quiet-tag">{runs.length} saved</span>
          </div>
          <div className="table-scroll">
            <table className="data-table results-table">
              <thead><tr><th>Dataset</th><th>Created</th><th>Models</th><th>Status</th><th /></tr></thead>
              <tbody>
                {runs.map((run) => {
                  const models = Object.keys(run.models ?? {}).filter((key) => key !== 'dummy')
                  const isDeleting = deleteMutation.isPending && deleteMutation.variables === run.run_id
                  return (
                    <tr key={run.run_id}>
                      <td className="class-label">{run.display_filename}</td>
                      <td>{fmtDate(run.created_at)}</td>
                      <td>{models.map((key) => MODEL_LABELS[key] ?? key).join(', ') || '—'}</td>
                      <td><span className={`run-state-badge compact ${run.state === 'interrupted' ? 'failed' : run.state}`}>{run.state}</span></td>
                      <td>
                        <div className="history-actions">
                          <Link to={`/runs/${run.run_id}`} className="table-link">Open <ArrowRight size={13} /></Link>
                          <button
                            type="button"
                            className="icon-button danger"
                            aria-label={`Delete run for ${run.display_filename}`}
                            title="Delete run"
                            disabled={run.state === 'running' || deleteMutation.isPending}
                            onClick={() => removeRun(run)}
                          >
                            {isDeleting ? <span className="spinner small" /> : <Trash2 size={14} />}
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </section>
      ) : (
        !runsQuery.error && (
          <div className="card empty-state">
            <FileSearch size={25} />
            <h2>No runs yet</h2>
            <p>Completed comparisons will appear here.</p>
            <Link to="/" className="button button-primary">New analysis <ArrowRight size={15} /></Link>
          </div>
        )
      )}
    </div>
  )
}
