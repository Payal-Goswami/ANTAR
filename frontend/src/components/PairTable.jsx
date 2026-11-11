import { ArrowDownRight, ArrowUpRight, Minus } from 'lucide-react'
import { fmtPValue, fmtPercent, fmtStat, MODEL_LABELS } from '../format'

export default function PairTable({ pairs, selected, onSelect }) {
  return (
    <div className="table-scroll">
      <table className="data-table results-table pair-table">
        <thead>
          <tr>
            <th>Model A</th>
            <th>Model B</th>
            <th>Disagreement</th>
            <th>A-only wins</th>
            <th>B-only wins</th>
            <th>Accuracy gap</th>
            <th>Kappa</th>
            <th>McNemar p</th>
            <th>Holm p</th>
          </tr>
        </thead>
        <tbody>
          {pairs.map((pair) => {
            const isSelected = selected?.model_a === pair.model_a && selected?.model_b === pair.model_b
            const difference = Number(pair.accuracy_diff ?? 0)
            const DifferenceIcon = difference > 0 ? ArrowUpRight : difference < 0 ? ArrowDownRight : Minus
            return (
              <tr
                key={`${pair.model_a}-${pair.model_b}`}
                className={`pair-row${isSelected ? ' selected' : ''}`}
                aria-pressed={isSelected}
                aria-label={`${MODEL_LABELS[pair.model_a] ?? pair.model_a} versus ${MODEL_LABELS[pair.model_b] ?? pair.model_b}`}
                tabIndex={0}
                role="button"
                onClick={() => onSelect(pair)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    onSelect(pair)
                  }
                }}
              >
                <td>{MODEL_LABELS[pair.model_a] ?? pair.model_a}</td>
                <td>{MODEL_LABELS[pair.model_b] ?? pair.model_b}</td>
                <td>{fmtPercent(pair.disagreement_rate)}</td>
                <td>{pair.b}</td>
                <td>{pair.c}</td>
                <td className={difference > 0 ? 'metric-positive' : difference < 0 ? 'metric-negative' : ''}>
                  <span className="metric-difference"><DifferenceIcon size={13} />{fmtPercent(Math.abs(difference))}</span>
                </td>
                <td title={(pair.kappa_stat?.reason ?? (pair.kappa === null ? 'unavailable' : ''))?.replaceAll('_', ' ')}>
                  {fmtStat(pair.kappa_stat ?? { value: pair.kappa, reason: pair.kappa === null ? 'unavailable' : null })}
                </td>
                <td>{fmtPValue(pair.p_raw)}</td>
                <td className="holm-value">{fmtPValue(pair.p_holm)}</td>
              </tr>
            )
          })}
          {pairs.length === 0 && <tr><td colSpan="9">No successful model pairs to compare.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
