import { CircleHelp, Clock3, Layers3, Plus, ScanLine } from 'lucide-react';
import { Navigate, NavLink, Route, Routes, useLocation } from 'react-router-dom';
import UploadSplit from './pages/UploadSplit';
import ReviewSetup from './pages/ReviewSetup';
import RunResults from './pages/RunResults';
import History from './pages/History';
const navigation = [
    { label: 'New analysis', to: '/', icon: Plus, activePaths: ['/'] },
    { label: 'Run history', to: '/history', icon: Clock3, activePaths: ['/history', '/runs/'] },
];
function Sidebar() {
    const location = useLocation();
    return (<aside className="sidebar">
      <NavLink className="brand" to="/" aria-label="Model Disagreement Explorer home">
        <span className="brand-mark"><Layers3 size={25} strokeWidth={1.7}/></span>
        <span className="brand-copy">
          <strong>MDE</strong>
          <small>Model Disagreement<br />Explorer</small>
        </span>
      </NavLink>

      <div className="sidebar-rule"/>
      <p className="nav-caption">WORKSPACE</p>
      <nav className="side-nav" aria-label="Main navigation">
        {navigation.map(({ label, to, icon: Icon, activePaths }) => {
            const active = activePaths.some((path) => path === '/' ? location.pathname === path : location.pathname.startsWith(path));
            return (<NavLink key={label} to={to} end className={`side-link${active ? ' active' : ''}`} aria-current={active ? 'page' : undefined}>
              <Icon size={17} strokeWidth={1.75}/>
              <span>{label}</span>
              {active && <span className="side-link-dot"/>}
            </NavLink>);
        })}
      </nav>

      <div className="sidebar-bottom">
        <div className="help-card">
          <div className="help-heading"><CircleHelp size={15}/> About this workspace</div>
          <p>Compare models on one held-out split. Inspect the cases where their predictions part ways.</p>
        </div>
        <div className="privacy-note"><span className="privacy-dot"/> Local workspace</div>
      </div>
    </aside>);
}
function PageFrame() {
    return (<div className="app-shell">
      <Sidebar />
      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            <ScanLine size={15}/>
            <span>ANALYSIS WORKSPACE</span>
          </div>
          <div className="topbar-right">
            <span className="local-indicator"><span className="privacy-dot"/> Private by design</span>
          </div>
        </header>
        <div className="page-content">
          <Routes>
            <Route path="/" element={<UploadSplit />}/>
            <Route path="/review/:uploadId/:splitId" element={<ReviewSetup />}/>
            <Route path="/runs/:runId" element={<RunResults />}/>
            <Route path="/history" element={<History />}/>
            <Route path="*" element={<Navigate to="/" replace/>}/>
          </Routes>
        </div>
      </main>
    </div>);
}
export default function App() {
    return <PageFrame />;
}
