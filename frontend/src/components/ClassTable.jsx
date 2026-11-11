export default function ClassTable({ classTable }) {
    return (<section className="card" aria-labelledby="class-table-title">
      <div className="section-heading">
        <div>
          <span className="section-kicker">STRATIFIED PARTITION</span>
          <h2 id="class-table-title">Class balance</h2>
        </div>
        <span className="quiet-tag">The split is now fixed</span>
      </div>
      <div className="table-scroll">
        <table className="data-table">
          <thead><tr><th>Class</th><th>Before</th><th>After</th><th>Train</th><th>Test</th></tr></thead>
          <tbody>
            {Object.entries(classTable).map(([label, counts]) => (<tr key={label}>
                <td className="class-label">{label}</td>
                <td>{counts.n_before.toLocaleString()}</td>
                <td>{counts.n_after.toLocaleString()}</td>
                <td>{counts.n_train.toLocaleString()}</td>
                <td>{counts.n_test.toLocaleString()}</td>
              </tr>))}
          </tbody>
        </table>
      </div>
    </section>);
}
