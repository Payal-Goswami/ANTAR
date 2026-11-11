import { ChevronDown, Settings2 } from 'lucide-react'
import { MODEL_LABELS } from '../format'

export default function RunConfiguration({ config }) {
  const models = (config.models ?? []).map((key) => MODEL_LABELS[key] ?? key)
  return (
    <details className="card configuration-card">
      <summary className="configuration-summary">
        <span className="heading-icon slate"><Settings2 size={16} /></span>
        <span><strong>Run configuration</strong><small>{config.display_filename} · seed {config.seed} · {Math.round(config.test_size * 100)}% test</small></span>
        <ChevronDown size={16} className="report-chevron" />
      </summary>
      <dl className="configuration-grid">
        <div><dt>Dataset</dt><dd>{config.display_filename}</dd></div>
        <div><dt>Target</dt><dd>{config.target}</dd></div>
        <div><dt>Split seed</dt><dd>{config.seed}</dd></div>
        <div><dt>Test size</dt><dd>{Math.round(config.test_size * 100)}%</dd></div>
        <div><dt>Models</dt><dd>{models.join(', ')}</dd></div>
        <div><dt>Included features</dt><dd>{config.included_columns?.length ?? config.feature_columns?.length ?? 0}</dd></div>
        <div><dt>Excluded features</dt><dd>{config.excluded_columns?.length ?? 0}</dd></div>
        <div><dt>Run ID</dt><dd className="run-id-value">{config.run_id}</dd></div>
      </dl>
    </details>
  )
}
