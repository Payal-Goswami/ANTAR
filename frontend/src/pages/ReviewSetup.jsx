import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { ArrowLeft, ArrowRight, Check, CircleHelp, FileCheck2, LockKeyhole, RefreshCw, ShieldAlert, SlidersHorizontal } from 'lucide-react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ApiError, getModels, preflight, startRun } from '../api';
import FlagList from '../components/FlagList';
import QualityReport from '../components/QualityReport';
import StatusBanner from '../components/StatusBanner';
const DEFAULT_MODELS = ['logreg', 'rf', 'xgb'];
function parseTokens(value) {
    return value.split(',').map((token) => token.trim()).filter(Boolean);
}
export default function ReviewSetup() {
    const { uploadId = '', splitId = '' } = useParams();
    const navigate = useNavigate();
    const [missingTokens, setMissingTokens] = useState('');
    const [decisions, setDecisions] = useState({});
    const [models, setModels] = useState(DEFAULT_MODELS);
    const [independenceConfirmed, setIndependenceConfirmed] = useState(false);
    const [startError, setStartError] = useState(null);
    const initialQuery = useQuery({
        queryKey: ['preflight', uploadId, splitId],
        queryFn: () => preflight(uploadId, {
            split_id: splitId,
            missing_tokens: [],
            column_decisions: {},
        }),
        enabled: Boolean(uploadId && splitId),
    });
    const updateMutation = useMutation({
        mutationFn: async (input) => ({
            input,
            result: await preflight(uploadId, {
                split_id: splitId,
                missing_tokens: input.tokens,
                column_decisions: input.decisions,
            }),
        }),
    });
    const runMutation = useMutation({
        mutationFn: startRun,
        onSuccess: ({ run_id }) => navigate(`/runs/${run_id}`),
        onError: setStartError,
    });
    const report = updateMutation.data?.result ?? initialQuery.data;
    const currentInput = useMemo(() => JSON.stringify({ tokens: parseTokens(missingTokens), decisions }), [missingTokens, decisions]);
    const appliedInput = updateMutation.data
        ? JSON.stringify(updateMutation.data.input)
        : JSON.stringify({ tokens: [], decisions: {} });
    const reportIsCurrent = currentInput === appliedInput;
    const requiredDecisions = report?.undecided ?? [];
    const selectableModels = useQuery({
        queryKey: ['models'],
        queryFn: getModels,
    });
    const availableModels = selectableModels.data?.models.filter((model) => model.selectable) ?? [];
    const modelCountValid = models.length >= 2 && models.length <= 4;
    const canStart = Boolean(report) &&
        reportIsCurrent &&
        requiredDecisions.length === 0 &&
        modelCountValid &&
        (!report?.needs_independence_confirmation || independenceConfirmed) &&
        !runMutation.isPending;
    const refreshReport = () => {
        setStartError(null);
        updateMutation.mutate({
            tokens: parseTokens(missingTokens),
            decisions,
        });
    };
    const selectDecision = (column, value) => {
        setDecisions((current) => ({ ...current, [column]: value }));
    };
    const toggleModel = (key) => {
        setModels((current) => current.includes(key)
            ? current.filter((item) => item !== key)
            : [...current, key]);
    };
    const handleStart = () => {
        if (!report || !reportIsCurrent)
            return;
        setStartError(null);
        runMutation.mutate({
            upload_id: uploadId,
            split_id: splitId,
            missing_tokens: parseTokens(missingTokens),
            column_decisions: decisions,
            models,
            class_weight: false,
            independence_confirmed: independenceConfirmed,
        });
    };
    const startHint = !reportIsCurrent
        ? 'Update the report to apply your latest feature choices.'
        : requiredDecisions.length > 0
            ? 'Resolve every column that needs a decision.'
            : !modelCountValid
                ? 'Choose between two and four models.'
                : report?.needs_independence_confirmation && !independenceConfirmed
                    ? 'Confirm that the rows are independent.'
                    : null;
    if (!uploadId || !splitId) {
        return (<div className="card empty-state">
        <ShieldAlert size={25}/>
        <h1>Review link is incomplete</h1>
        <p>Return to the dataset step and create a split before reviewing features.</p>
        <Link to="/" className="button button-primary">Back to dataset setup <ArrowRight size={15}/></Link>
      </div>);
    }
    return (<div className="page-stack">
      <div className="page-intro review-intro">
        <div className="eyebrow"><span className="eyebrow-line"/> MODEL ANALYSIS <span className="eyebrow-divider">/</span> STEP 02</div>
        <Link to="/" className="back-link"><ArrowLeft size={14}/> Dataset & split</Link>
        <div className="intro-row">
          <div>
            <h1>Review before you run.</h1>
            <p className="intro-copy">Feature checks use the training partition only. Your held-out test rows remain untouched.</p>
          </div>
          <div className="intro-mark"><SlidersHorizontal size={21} strokeWidth={1.6}/></div>
        </div>
      </div>

      <div className="workflow-steps" aria-label="Analysis steps">
        <div className="workflow-step complete"><span className="step-number"><Check size={13}/></span><span>Dataset & split</span></div>
        <span className="workflow-connector complete"/>
        <div className="workflow-step current"><span className="step-number">02</span><span>Review & setup</span></div>
        <span className="workflow-connector"/>
        <div className="workflow-step"><span className="step-number">03</span><span>Run analysis</span></div>
      </div>

      <StatusBanner error={initialQuery.error} tone="error"/>
      <StatusBanner error={updateMutation.error} tone="error"/>
      <StatusBanner error={startError} tone="error"/>
      {startError instanceof ApiError && startError.code === 'busy' && (<StatusBanner message="A run is in progress. Wait for it to finish before starting another." tone="info"/>)}

      <section className="card review-card">
        <div className="section-heading">
          <div className="heading-with-icon">
            <span className="heading-icon blue"><FileCheck2 size={17}/></span>
            <div><span className="section-kicker">TRAIN PARTITION ONLY</span><h2>Feature review</h2></div>
          </div>
          <span className="quiet-tag">{report ? `${report.included.length} included` : 'Preparing report'}</span>
        </div>
        <p className="muted-copy">Review columns that look like identifiers, dates, long text or contain no training values. Nothing is removed automatically without being reported.</p>

        <div className="review-controls">
          <label className="field token-field">
            <span className="field-label">Feature missing tokens <span className="optional">Optional</span></span>
            <input value={missingTokens} onChange={(event) => setMissingTokens(event.target.value)} placeholder="e.g. unknown, ?"/>
            <small>Comma-separated, exact and case-sensitive after trimming.</small>
          </label>
          <button type="button" className="button button-secondary update-button" onClick={refreshReport} disabled={updateMutation.isPending || initialQuery.isPending}>
            {updateMutation.isPending ? <RefreshCw size={15} className="spin"/> : <RefreshCw size={15}/>}
            Update report
          </button>
        </div>

        {initialQuery.isPending ? (<div className="loading-inline"><span className="spinner"/> Computing train-only diagnostics…</div>) : report ? (<>
            <div className="flag-section">
              <div className="subsection-title"><strong>Flagged columns</strong><span>Review recommendations before continuing</span></div>
              <FlagList flags={report.flags} undecided={report.undecided}/>
            </div>
            {Object.entries(report.flags).some(([, info]) => info.flag && info.default_decision === 'undecided') && (<div className="decision-panel">
                <div className="decision-panel-heading">
                  <div><strong>Columns that need your decision</strong><span>Whole-number identifiers can be useful or misleading. Choose explicitly.</span></div>
                  {requiredDecisions.length > 0 && <span className="count-badge">{requiredDecisions.length} open</span>}
                </div>
                {Object.entries(report.flags)
                    .filter(([, info]) => info.flag && info.default_decision === 'undecided')
                    .map(([name, info]) => (<fieldset className={`decision-row${requiredDecisions.includes(name) ? ' decision-open' : ''}`} key={name}>
                      <legend>{name}<small>{info.reason}</small></legend>
                      <label className="radio-option">
                        <input type="radio" name={`decision-${name}`} checked={decisions[name] === 'include'} onChange={() => selectDecision(name, 'include')}/>
                        <span className="radio-dot"/> Include
                      </label>
                      <label className="radio-option">
                        <input type="radio" name={`decision-${name}`} checked={decisions[name] === 'exclude'} onChange={() => selectDecision(name, 'exclude')}/>
                        <span className="radio-dot"/> Exclude
                      </label>
                    </fieldset>))}
              </div>)}
            {Object.entries(report.flags).some(([, info]) => info.flag && info.default_decision === 'exclude' && info.flag !== 'all_missing') && (<div className="override-panel">
                <div className="subsection-title"><strong>Default exclusions</strong><span>These can be included if you have a reason to keep them.</span></div>
                {Object.entries(report.flags)
                    .filter(([, info]) => info.flag && info.default_decision === 'exclude' && info.flag !== 'all_missing')
                    .map(([name, info]) => (<label className="override-row" key={name}>
                      <span><strong>{name}</strong><small>{info.reason}</small></span>
                      <span className="switch-label">
                        <input type="checkbox" checked={decisions[name] === 'include'} onChange={(event) => setDecisions((current) => ({
                        ...current,
                        [name]: event.target.checked ? 'include' : 'exclude',
                    }))}/>
                        Include this column
                      </span>
                    </label>))}
              </div>)}
            {!reportIsCurrent && <p className="unsaved-note"><CircleHelp size={14}/> Your choices have changed. Update the report before starting.</p>}
          </>) : null}
      </section>

      {report && <QualityReport report={report.report}/>}

      <section className="card model-card">
        <div className="section-heading">
          <div className="heading-with-icon">
            <span className="heading-icon green"><SlidersHorizontal size={17}/></span>
            <div><span className="section-kicker">ONE PROTOCOL, MULTIPLE MODELS</span><h2>Choose models to compare</h2></div>
          </div>
          <span className={`model-count${modelCountValid ? '' : ' invalid'}`}>{models.length} of 4 selected</span>
        </div>
        <p className="muted-copy">The Dummy baseline is always included. Select two to four additional models; all share the same split and feature decisions.</p>
        {selectableModels.isPending ? (<div className="loading-inline"><span className="spinner"/> Loading model registry…</div>) : selectableModels.error ? (<StatusBanner error={selectableModels.error} tone="error"/>) : (<div className="model-grid">
            {availableModels.map((model) => {
                const checked = models.includes(model.key);
                return (<label className={`model-option${checked ? ' selected' : ''}`} key={model.key}>
                  <input type="checkbox" checked={checked} onChange={() => toggleModel(model.key)}/>
                  <span className="model-check">{checked && <Check size={13}/>}</span>
                  <span className="model-option-copy"><strong>{model.label}</strong><small>{model.key === 'logreg' ? 'Linear reference model' : model.key === 'tree' ? 'Single decision tree' : model.key === 'rf' ? 'Ensemble of decision trees' : 'Gradient-boosted trees'}</small></span>
                  <span className="model-code">{model.key.toUpperCase()}</span>
                </label>);
            })}
          </div>)}
        {!modelCountValid && <p className="validation-note">Select at least two and no more than four models to create a meaningful pairwise comparison.</p>}
      </section>

      {report?.needs_independence_confirmation && (<section className="independence-card">
          <span className="independence-icon"><LockKeyhole size={17}/></span>
          <div className="independence-copy"><strong>Confirm row independence</strong><p>A datetime-like feature is included. This tool uses a random stratified split, not a chronological or grouped split.</p></div>
          <label className="confirm-control"><input type="checkbox" checked={independenceConfirmed} onChange={(event) => setIndependenceConfirmed(event.target.checked)}/><span>I confirm rows are independent</span></label>
        </section>)}

      <div className="start-panel">
        <div className="start-explanation">
          <span className="start-icon"><CircleHelp size={17}/></span>
          <div><strong>Ready when your review is complete</strong><small>{startHint ?? 'Preprocessing will be fitted on training rows only.'}</small></div>
        </div>
        <button type="button" className="button button-primary start-button" onClick={handleStart} disabled={!canStart}>
          {runMutation.isPending ? <RefreshCw size={15} className="spin"/> : null}
          {runMutation.isPending ? 'Starting…' : 'Start comparison'}
          {!runMutation.isPending && <ArrowRight size={16}/>}
        </button>
      </div>
      <div className="page-footnote"><ShieldAlert size={14}/> The test partition remains held out until each selected model is ready.</div>
    </div>);
}
