import { useQuery } from '@tanstack/react-query'
import { Activity, ArrowLeft, Check, CircleAlert, Clock3, FileSearch, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPairs, getRun, getSummary } from '../api'
import { MODEL_LABELS } from '../format'
import DisagreementTable from '../components/DisagreementTable'
import MetricsTable from '../components/MetricsTable'
import PairDetail from '../components/PairDetail'
import PairTable from '../components/PairTable'
import QualityReport from '../components/QualityReport'
import RunConfiguration from '../components/RunConfiguration'
import SliceView from '../components/SliceView'
import StatusBanner from '../components/StatusBanner'

const STAGES = [
  { key: 'preparing', label: 'Preparing' },
  { key: 'training', label: 'Training' },
  { key: 'analysing', label: 'Comparing' },
  { key: 'completed', label: 'Complete' },
]

function RunProgress({ run }) {
  const modelEntries = Object.entries(run.models ?? {})
  const doneCount = modelEntries.filter(([, item]) => item.status === 'done').length
  const isRunning = run.state === 'running'
  const isFailed = run.state !== 'running' && run.state !== 'completed'
  const currentStage = STAGES.findIndex((stage) => stage.key === run.stage)
  const failedTitle = run.state === 'interrupted' ? 'Run interrupted' : 'Run failed'
  const heading = isRunning ? 'Comparison in progress' : isFailed ? failedTitle : 'Comparison complete'

  return (
    <div className="page-stack">
      <div className="page-intro run-intro">
        <div className="eyebrow"><span className="eyebrow-line" /> RUN <span className="eyebrow-divider">/</span> {run.run_id.slice(0, 8).toUpperCase()}</div>
        <div className="intro-row">
          <div>
            <h1>{heading}</h1>
            <p className="intro-copy">{run.config.display_filename} · {modelEntries.length} models</p>
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
            <span className={`heading-icon ${isFailed ? 'orange' : 'blue'}`}>
              {isRunning ? <RefreshCw size={17} className="spin" /> : isFailed ? <CircleAlert size={17} /> : <Check size={17} />}
            </span>
            <div><span className="section-kicker">RUN STATUS</span><h2>{heading}</h2></div>
          </div>
          {isRunning && <span className="polling-label"><span className="pulse-dot" />Live</span>}
        </div>

        {isFailed ? (
          <StatusBanner error={run.error ?? failedTitle} tone="error" />
        ) : (
          <div className="stage-track">
            {STAGES.map((stage, index) => {
              const done = run.state === 'completed' || index < currentStage
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
          <span>Stage</span><strong>{run.stage?.replaceAll('_', ' ') ?? 'queued'}</strong>
          <span className="progress-spacer" />
          <span>Models complete</span><strong>{doneCount} / {modelEntries.length}</strong>
        </div>
        <div className="model-status-list">
          {modelEntries.map(([key, item]) => (
            <div className={`model-status-row status-${item.status}`} key={key}>
              <span className="model-status-indicator">
                {item.status === 'done' ? <Check size={13} /> : item.status === 'failed' ? <CircleAlert size={13} /> : item.status === 'running' ? <RefreshCw size={13} className="spin" /> : <Clock3 size={13} />}
              </span>
              <strong>{MODEL_LABELS[key] ?? key}</strong>
              {item.fit_seconds !== undefined && <span className="fit-time">{item.fit_seconds.toFixed(2)} s</span>}
              <span className="status-word">{item.status}</span>
              {item.error && <small className="model-error">{item.error}</small>}
            </div>
          ))}
        </div>
      </section>
      <Link to="/history" className="button button-secondary back-to-data"><ArrowLeft size={14} /> Run history</Link>
    </div>
  )
}

function CompletedResults({ run }) {
  const [selectedId, setSelectedId] = useState('')
  const summaryQuery = useQuery({
    queryKey: ['summary', run.run_id],
    queryFn: () => getSummary(run.run_id),
  })
  const pairsQuery = useQuery({
    queryKey: ['pairs', run.run_id],
    queryFn: () => getPairs(run.run_id),
  })

  if (summaryQuery.isPending || pairsQuery.isPending) {
    return <div className="loading-page"><span className="spinner" /> Loading results…</div>
  }

  return (
    <div className="page-stack results-page">
      <div className="page-intro">
        <div className="eyebrow"><span className="eyebrow-line" /> RESULTS <span className="eyebrow-divider">/</span> {run.run_id.slice(0, 8).toUpperCase()}</div>
        <div className="intro-row">
          <div>
            <h1>Model comparison</h1>
            <p className="intro-copy">{run.config.display_filename} · {summaryQuery.data?.class_names?.length ?? 0} classes</p>
          </div>
          <span className="run-state-badge completed"><Check size={14} /> Complete</span>
        </div>
        <Link to="/history" className="back-link"><ArrowLeft size={14} /> Run history</Link>
      </div>

      {summaryQuery.error && <StatusBanner error={summaryQuery.error} tone="error" />}
      {pairsQuery.error && <StatusBanner error={pairsQuery.error} tone="error" />}

      {summaryQuery.data && (
        <section className="card results-section-card">
          <div className="section-heading">
            <div><span className="section-kicker">HELD-OUT TEST SET</span><h2>Model metrics</h2></div>
            <span className="quiet-tag">{Object.keys(summaryQuery.data.metrics).length} models</span>
          </div>
          <MetricsTable metrics={summaryQuery.data.metrics} classNames={summaryQuery.data.class_names} />
        </section>
      )}

      {summaryQuery.data && pairsQuery.data && (
        <>
          <section className="card results-section-card">
            <div className="section-heading">
              <div><span className="section-kicker">PAIRED TEST ROWS</span><h2>Model pairs</h2></div>
              <span className="quiet-tag">{pairsQuery.data.pairs.length} pairs</span>
            </div>
            <PairTable
              pairs={pairsQuery.data.pairs}
              selected={pairsQuery.data.pairs.find((pair) => `${pair.model_a}:${pair.model_b}` === selectedId) ?? pairsQuery.data.pairs[0]}
              onSelect={(pair) => setSelectedId(`${pair.model_a}:${pair.model_b}`)}
            />
            <p className="stat-note pair-note">Holm adjustment accounts for multiple pair tests. Significance is not practical importance; a non-significant result does not establish equality. McNemar reflects test-set uncertainty.</p>
          </section>

          {pairsQuery.data.pairs.length > 0 && (() => {
            const selectedPair = pairsQuery.data.pairs.find((pair) => `${pair.model_a}:${pair.model_b}` === selectedId) ?? pairsQuery.data.pairs[0]
            return (
              <>
                <PairDetail pair={selectedPair} metrics={summaryQuery.data.metrics} classNames={summaryQuery.data.class_names} />
                <DisagreementTable key={`${selectedPair.model_a}:${selectedPair.model_b}`} runId={run.run_id} pair={selectedPair} classNames={summaryQuery.data.class_names} />
                <SliceView runId={run.run_id} pair={selectedPair} features={summaryQuery.data.feature_columns} />
              </>
            )
          })()}
        </>
      )}

      {run.quality && <QualityReport report={run.quality} />}
      <RunConfiguration config={run.config} />
    </div>
  )
}

export default function RunResults() {
  const { runId = '' } = useParams()
  const runQuery = useQuery({
    queryKey: ['run', runId],
    queryFn: () => getRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (query) => query.state.data?.state === 'running' ? 2000 : false,
  })

  if (runQuery.isPending) {
    return <div className="loading-page"><span className="spinner" /> Loading run…</div>
  }
  if (runQuery.error) {
    return (
      <div className="page-stack">
        <StatusBanner error={runQuery.error} tone="error" />
        <div className="card empty-state">
          <FileSearch size={25} />
          <h1>Run not found</h1>
          <p>It may have been deleted, or the link is invalid.</p>
          <Link to="/history" className="button button-secondary"><ArrowLeft size={14} /> Run history</Link>
        </div>
      </div>
    )
  }

  const run = runQuery.data
  if (!run) return null
  return run.state === 'completed' ? <CompletedResults run={run} /> : <RunProgress run={run} />
}
