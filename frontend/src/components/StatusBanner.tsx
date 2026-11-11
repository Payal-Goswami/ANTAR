import { AlertCircle, CheckCircle2, Info } from 'lucide-react'
import { ApiError } from '../api'

type Props = {
  error?: unknown
  message?: string
  tone?: 'error' | 'success' | 'info'
}

export default function StatusBanner({ error, message, tone = 'info' }: Props) {
  if (!error && !message) return null

  const apiError = error instanceof ApiError ? error : null
  const errorMessage =
    typeof error === 'string'
      ? error
      : error instanceof Error
        ? error.message
        : undefined
  const title = apiError?.message ?? errorMessage ?? message ?? 'Something went wrong.'
  const classes = `status-banner ${tone}`
  const Icon = tone === 'error' ? AlertCircle : tone === 'success' ? CheckCircle2 : Info
  const columns = apiError?.details.columns
  const offenders =
    (apiError?.details.offending_classes as Record<string, Record<string, number>> | undefined) ??
    (apiError?.details.undersized_classes as Record<string, number> | undefined)

  return (
    <div className={classes} role={tone === 'error' ? 'alert' : 'status'}>
      <Icon size={18} />
      <div className="status-content">
        <p>{title}</p>
        {apiError?.code === 'decision_required' && Array.isArray(columns) && (
          <div className="status-detail">Choose a decision for: {columns.join(', ')}</div>
        )}
        {offenders && Object.keys(offenders).length > 0 && (
          <ul className="status-offenders">
            {Object.entries(offenders).map(([name, counts]) => (
              <li key={name}>
                <strong>{name}</strong>
                {'n_test' in counts
                  ? ` — ${counts.n_rows} rows, ${counts.n_train} train, ${counts.n_test} test`
                  : ` — ${counts} rows`}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
