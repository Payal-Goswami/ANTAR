import { fmtStat, MODEL_LABELS } from '../format'

const METRICS = [
  ['accuracy', 'Accuracy'],
  ['macro_precision', 'Macro precision'],
  ['macro_recall', 'Macro recall'],
  ['macro_f1', 'Macro F1'],
  ['roc_auc', 'ROC-AUC'],
]

export default function MetricsTable({ metrics, classNames }) {
  const entries = Object.entries(metrics ?? {})
  return (
    <div className="table-scroll">
      <table className="data-table results-table">
        <thead>
          <tr>
            <th>Model</th>
            {METRICS.map(([, label]) => <th key={label}>{label}</th>)}
            <th>Fit time</th>
          </tr>
        </thead>
        <tbody>
          {entries.map(([key, result]) => (
            <tr key={key}>
              <td>
                <span className="model-name-cell">
                  {MODEL_LABELS[key] ?? key}
                  {key === 'dummy' && <span className="baseline-tag">Baseline</span>}
                </span>
              </td>
              {METRICS.map(([metric]) => (
                <td key={metric} title={metric === 'roc_auc' ? result[metric]?.reason?.replaceAll('_', ' ') : undefined}>
                  {fmtStat(result[metric])}
                </td>
              ))}
              <td>{result.fit_seconds === undefined ? '—' : `${result.fit_seconds.toFixed(2)} s`}</td>
            </tr>
          ))}
          {entries.length === 0 && (
            <tr><td colSpan={METRICS.length + 2}>No model metrics are available.</td></tr>
          )}
        </tbody>
      </table>
      <p className="table-footnote">Scores use the held-out test set. {classNames.length} target classes.</p>
    </div>
  )
}
