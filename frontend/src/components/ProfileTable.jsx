import { FileSpreadsheet } from 'lucide-react';
export default function ProfileTable({ columns, rows, totalColumns }) {
    return (<section className="card profile-card" aria-labelledby="profile-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">FILE OVERVIEW</span>
          <h2 id="profile-title">Dataset profile</h2>
        </div>
        <div className="profile-summary">
          <span><strong>{rows.toLocaleString()}</strong> rows</span>
          <span className="summary-separator"/>
          <span><strong>{totalColumns}</strong> columns</span>
        </div>
      </div>
      <div className="table-scroll">
        <table className="data-table profile-table">
          <thead>
            <tr><th>Column</th><th>Inferred type</th><th>Missing</th></tr>
          </thead>
          <tbody>
            {columns.map((column) => (<tr key={column.name}>
                <td><span className="column-name"><FileSpreadsheet size={14}/>{column.name}</span></td>
                <td><span className={`type-pill ${column.kind === 'numeric' ? 'numeric' : 'categorical'}`}>{column.kind}</span></td>
                <td>{column.missing_pct.toFixed(2)}%</td>
              </tr>))}
          </tbody>
        </table>
      </div>
      <p className="table-footnote">Types are inferred from the full file for schema reporting. The profile does not make feature-selection decisions.</p>
    </section>);
}
