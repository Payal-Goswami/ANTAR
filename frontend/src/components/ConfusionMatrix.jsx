import { fmtStat } from '../format'

export default function ConfusionMatrix({ modelKey, metric, classNames, label }) {
  const matrix = metric?.confusion_matrix ?? []
  return (
    <div className="confusion-card">
      <div className="confusion-heading">
        <strong>{label}</strong>
        <span>{metric?.fit_seconds === undefined ? '' : `${metric.fit_seconds.toFixed(2)} s`}</span>
      </div>
      <div className="table-scroll">
        <table className="data-table confusion-table">
          <caption>Actual rows by predicted class · {modelKey}</caption>
          <thead>
            <tr>
              <th>Actual ↓ / Predicted →</th>
              {classNames.map((name) => <th key={name}>{name}</th>)}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, index) => (
              <tr key={classNames[index]}>
                <th scope="row">{classNames[index]}</th>
                {row.map((count, column) => (
                  <td className={index === column ? 'matrix-correct' : 'matrix-miss'} key={classNames[column]}>
                    {fmtStat(count, 0)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
