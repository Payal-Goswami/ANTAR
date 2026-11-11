import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowLeft, Check, CircleAlert, Clock3, FileSearch, RefreshCw } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getRun } from '../api'
import StatusBanner from '../components/StatusBanner'

const STAGES = [
  { key: 'preparing', label: 'Preparing data' },
  { key: 'training', label: 'Training models' },
  { key: 'analysing', label: 'Comparing predictions' },
  { key: 'completed', label: 'Run complete' },
]

export default function RunResults() {
  const { runId = '' } = useParams()
  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) =>
      query.state.data?.state === 'running' ? 2000 : false,
  })

  if (runQuery.isPending) {
    return <div className="loading-page"><span className="spinner" /> Loading run status…</div>
  }
  if (runQuery.error) {
    return (
      <div className="page-stack">
        <StatusBanner error={runQuery.error} tone="error" />
        <div className="card empty-state">
          <FileSearch size={25} />
          <h1>Run not available</h1>
          <p>This run may have been removed or its status could not be loaded.</p>
          <Link to="/" className="button button-secondary"><ArrowLeft size={14} /> New analysis</Link>
        </div>
      </div>
    )
  }

  const run = runQuery.data
  if (!run) return null
  const currentStage = STAGES.findIndex((stage) => stage.key === run.stage)
  const modelEntries = Object.entries(run.models ?? {})
  const completedModels = modelEntries.filter(([, item]) => item.status === 'done').length
  const isRunning = run.state === 'running'
  const isFailed = run.state === 'failed'

  return (
    <div className="page-stack">
      <div className="page-intro">
        <div className="eyebrow"><span className="eyebrow-line" /> RUN MONITOR <span className="eyebrow-divider">/</span> {runId.slice(0, 8).toUpperCase()}</div>
        <div className="intro-row">
          <div>
            <h1>{isRunning ? 'Your comparison is running.' : isFailed ? 'This run needs attention.' : 'Run complete.'}</h1>
            <p className="intro-copy">{run.config.display_filename} <span className="inline-divider">·</span> {modelEntries.length} models in the run, including the baseline</p>
          </div>
          <span className={`run-state-badge ${isRunning ? 'running' : isFailed ? 'failed' : 'completed'}`}>
            {isRunning ? <Activity size={14} /> : isFailed ? <CircleAlert size={14} /> : <Check size={14} />}
            {run.state}
          </span>
        </div>
      </div>

      <section className="card run-progress-card">
        <div className="section-heading">
          <div className="heading-with-icon">
            <span className={`heading-icon ${isFailed ? 'orange' : 'blue'}`}>{isRunning ? <RefreshCw size={17} className="spin" /> : isFailed ? <CircleAlert size={17} /> : <Check size={17} />}</span>
            <div><span className="section-kicker">LIVE RUN STATUS</span><h2>{isRunning ? 'Working through the analysis' : isFailed ? 'Run stopped' : 'Analysis finished'}</h2></div>
          </div>
          <span className="polling-label"><span className={isRunning ? 'pulse-dot' : 'static-dot'} />{isRunning ? 'Refreshing every 2 seconds' : 'Status saved locally'}</span>
        </div>

        {isFailed ? (
          <StatusBanner error={run.error ?? 'The run failed.'} tone="error" />
        ) : (
          <div className="stage-track">
            {STAGES.map((stage, index) => {
              const done = !isFailed && (run.state === 'completed' || index < currentStage)
              const active = isRunning && index === currentStage
              return (
                <div className={`stage-item${done ? ' done' : ''}${active ? ' active' : ''}`} key={stage.key}>
                  <span className="stage-node">{done ? <Check size={13} /> : index + 1}</span>
                  <span className="stage-label">{stage.label}</span>
                </div>
              )
            })}
          </div>
        )}

        <div className="progress-summary">
          <span>Current stage</span>
          <strong>{run.stage?.replaceAll('_', ' ') ?? 'queued'}</strong>
          <span className="progress-spacer" />
          <span>Models finished</span>
          <strong>{completedModels} / {modelEntries.length}</strong>
        </div>
        <div className="model-status-list">
          {modelEntries.map(([key, item]) => (
            <div className={`model-status-row status-${item.status}`} key={key}>
              <span className="model-status-indicator">
                {item.status === 'done' ? <Check size={13} /> : item.status === 'failed' ? <CircleAlert size={13} /> : item.status === 'running' ? <RefreshCw size={13} className="spin" /> : <Clock3 size={13} />}
              </span>
              <strong>{key === 'dummy' ? 'Dummy baseline' : key === 'logreg' ? 'Logistic regression' : key === 'tree' ? 'Decision tree' : key === 'rf' ? 'Random forest' : 'XGBoost'}</strong>
              {item.fit_seconds !== undefined && <span className="fit-time">{item.fit_seconds.toFixed(2)} s</span>}
              <span className="status-word">{item.status}</span>
              {item.error && <small className="model-error">{item.error}</small>}
            </div>
          ))}
        </div>
      </section>

      {run.state === 'completed' && (
        <section className="completion-note">
          <span className="completion-icon"><Check size={16} /></span>
          <div><strong>Predictions and diagnostics are ready.</strong><p>The detailed metrics, pair comparisons and slice exploration arrive in the Results workspace.</p></div>
          <Link to="/" className="button button-secondary">Start another analysis</Link>
        </section>
      )}
      {isFailed && <Link to="/" className="button button-secondary back-to-data"><ArrowLeft size={14} /> Return to dataset setup</Link>}
      {isRunning && <p className="polling-note">You can leave this page open. Progress is stored on the server and will resume when you return to this link.</p>}
    </div>
  )
}
