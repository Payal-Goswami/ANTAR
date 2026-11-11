import { useQuery } from '@tanstack/react-query';
import { ArrowRight, Clock3, FileSearch } from 'lucide-react';
import { Link } from 'react-router-dom';
import { listRuns } from '../api';
import StatusBanner from '../components/StatusBanner';
export default function History() {
    const runsQuery = useQuery({
        queryKey: ['runs'],
        queryFn: listRuns,
    });
    const runs = runsQuery.data?.runs ?? [];
    return (<div className="page-stack">
      <div className="page-intro">
        <div className="eyebrow"><span className="eyebrow-line"/> WORKSPACE <span className="eyebrow-divider">/</span> HISTORY</div>
        <div className="intro-row">
          <div><h1>Past analyses.</h1><p className="intro-copy">Runs are stored locally so you can return to their status and configuration.</p></div>
          <div className="intro-mark"><Clock3 size={21} strokeWidth={1.6}/></div>
        </div>
      </div>
      {runsQuery.error && <StatusBanner error={runsQuery.error} tone="error"/>}
      {runsQuery.isPending ? (<div className="loading-page"><span className="spinner"/> Loading saved runs…</div>) : runs.length ? (<section className="card history-card">
          <div className="section-heading"><div><span className="section-kicker">LOCAL RUNS</span><h2>Recent analyses</h2></div><span className="quiet-tag">{runs.length} saved</span></div>
          <div className="table-scroll">
            <table className="data-table">
              <thead><tr><th>Dataset</th><th>Created</th><th>Status</th><th /></tr></thead>
              <tbody>
                {runs.map((run) => (<tr key={run.run_id}>
                    <td className="class-label">{run.display_filename}</td>
                    <td>{run.created_at ? new Date(run.created_at).toLocaleString() : '—'}</td>
                    <td><span className={`run-state-badge compact ${run.state}`}>{run.state}</span></td>
                    <td><Link to={`/runs/${run.run_id}`} className="table-link">Open <ArrowRight size={13}/></Link></td>
                  </tr>))}
              </tbody>
            </table>
          </div>
        </section>) : (<div className="card empty-state">
          <FileSearch size={25}/>
          <h2>No saved runs yet</h2>
          <p>Once a comparison finishes, it will appear here with its status and dataset details.</p>
          <Link to="/" className="button button-primary">Create an analysis <ArrowRight size={15}/></Link>
        </div>)}
    </div>);
}
