export const MODEL_LABELS = {
  dummy: 'Dummy baseline',
  logreg: 'Logistic regression',
  tree: 'Decision tree',
  rf: 'Random forest',
  xgb: 'XGBoost',
}

export function fmtStat(stat, digits = 3) {
  if (typeof stat === 'number') return Number.isFinite(stat) ? stat.toFixed(digits) : 'undefined'
  if (!stat || stat.value === null || stat.value === undefined) {
    const reason = stat?.reason?.replaceAll('_', ' ')
    return reason ? `undefined · ${reason}` : 'undefined'
  }
  return Number.isFinite(stat.value) ? Number(stat.value).toFixed(digits) : 'undefined'
}

export function fmtPercent(value, digits = 1) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function fmtPValue(value) {
  if (value === null || value === undefined || !Number.isFinite(Number(value))) return 'undefined'
  if (Number(value) < 0.0001) return '< 0.0001'
  return Number(value).toFixed(4)
}

export function fmtDate(value) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '—' : date.toLocaleString()
}

export function formatValue(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'number') return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4)
  return String(value)
}
