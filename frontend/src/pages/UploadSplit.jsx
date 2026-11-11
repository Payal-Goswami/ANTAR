import { useRef, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { ArrowDown, ArrowRight, Check, CloudUpload, FileSpreadsheet, FlaskConical, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ApiError, createSplit, uploadFile, uploadSample } from '../api';
import ClassTable from '../components/ClassTable';
import ProfileTable from '../components/ProfileTable';
import StatusBanner from '../components/StatusBanner';
export default function UploadSplit() {
    const fileInput = useRef(null);
    const [uploaded, setUploaded] = useState(null);
    const [split, setSplit] = useState(null);
    const [target, setTarget] = useState('');
    const [targetTokens, setTargetTokens] = useState('');
    const [seed, setSeed] = useState('42');
    const [testSize, setTestSize] = useState('0.2');
    const [error, setError] = useState(null);
    const [dragging, setDragging] = useState(false);
    const uploadMutation = useMutation({
        mutationFn: (file) => uploadFile(file),
        onSuccess: (result) => {
            setUploaded(result);
            setSplit(null);
            setTarget(result.header.includes('diagnosis') ? 'diagnosis' : result.header[0] ?? '');
            setError(null);
        },
        onError: setError,
    });
    const sampleMutation = useMutation({
        mutationFn: () => uploadSample('breast_cancer'),
        onSuccess: (result) => {
            setUploaded(result);
            setSplit(null);
            setTarget(result.header.includes('diagnosis') ? 'diagnosis' : result.header[0] ?? '');
            setError(null);
        },
        onError: setError,
    });
    const splitMutation = useMutation({
        mutationFn: () => {
            if (!uploaded)
                throw new Error('Upload a CSV before creating a split.');
            return createSplit(uploaded.upload_id, {
                target,
                target_missing_tokens: targetTokens.split(',').map((token) => token.trim()).filter(Boolean),
                seed: Number(seed),
                test_size: Number(testSize),
            });
        },
        onSuccess: (result) => {
            setSplit(result);
            setError(null);
        },
        onError: setError,
    });
    const busy = uploadMutation.isPending || sampleMutation.isPending;
    const handleFile = (file) => {
        setError(null);
        if (!file)
            return;
        if (!file.name.toLowerCase().endsWith('.csv')) {
            setError(new ApiError({ code: 'bad_csv', message: 'Choose a .csv file to continue.', details: {} }, 400));
            return;
        }
        uploadMutation.mutate(file);
    };
    const onFileChange = (event) => {
        handleFile(event.target.files?.[0]);
        event.target.value = '';
    };
    const onDrop = (event) => {
        event.preventDefault();
        setDragging(false);
        handleFile(event.dataTransfer.files[0]);
    };
    const onSplitSubmit = (event) => {
        event.preventDefault();
        setError(null);
        splitMutation.mutate();
    };
    const droppedRows = split?.dropped_missing_target ?? 0;
    const trimmedLabels = split?.trimmed_labels ?? 0;
    return (<div className="page-stack">
      <div className="page-intro">
        <div className="eyebrow"><span className="eyebrow-line"/> MODEL ANALYSIS <span className="eyebrow-divider">/</span> STEP 01</div>
        <div className="intro-row">
          <div>
            <h1>Start with your data.</h1>
            <p className="intro-copy">A clear, controlled comparison begins with one dataset and one fixed split.</p>
          </div>
          <div className="intro-mark"><FlaskConical size={21} strokeWidth={1.6}/></div>
        </div>
      </div>

      <div className="workflow-steps" aria-label="Analysis steps">
        <div className="workflow-step current"><span className="step-number">01</span><span>Dataset & split</span></div>
        <span className="workflow-connector"/>
        <div className="workflow-step"><span className="step-number">02</span><span>Review & setup</span></div>
        <span className="workflow-connector"/>
        <div className="workflow-step"><span className="step-number">03</span><span>Run analysis</span></div>
      </div>

      <StatusBanner error={error} tone="error"/>

      {!uploaded ? (<section className={`card upload-card${dragging ? ' dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true); }} onDragLeave={() => setDragging(false)} onDrop={onDrop}>
          <div className="upload-topline">
            <div>
              <span className="section-kicker">YOUR WORKSPACE, YOUR DATA</span>
              <h2>Bring in a dataset</h2>
              <p className="muted-copy">Choose a CSV from your computer or explore with the included sample.</p>
            </div>
            <div className="upload-symbol"><CloudUpload size={23} strokeWidth={1.65}/></div>
          </div>
          <button type="button" className="dropzone" onClick={() => fileInput.current?.click()} disabled={busy}>
            <span className="dropzone-icon"><FileSpreadsheet size={22}/></span>
            <span className="dropzone-title">{busy ? 'Preparing your dataset…' : 'Drop your CSV here, or browse'}</span>
            <span className="dropzone-subtitle">CSV format · up to 20 MB · stored locally for this analysis</span>
            <span className="browse-button">{busy ? <RefreshCw size={15} className="spin"/> : 'Browse files'}</span>
          </button>
          <input ref={fileInput} className="visually-hidden" type="file" accept=".csv,text/csv" onChange={onFileChange}/>
          <div className="upload-divider"><span /> <small>OR START WITH A SAMPLE</small> <span /></div>
          <div className="sample-row">
            <div className="sample-details">
              <span className="sample-icon"><FlaskConical size={17}/></span>
              <div><strong>Breast Cancer Wisconsin</strong><small>569 observations · 30 measured features · binary target</small></div>
            </div>
            <button type="button" className="button button-secondary" disabled={busy} onClick={() => { setError(null); sampleMutation.mutate(); }}>
              <Sparkles size={15}/> Try the sample <ArrowRight size={14}/>
            </button>
          </div>
          <div className="privacy-strip"><ShieldCheck size={15}/><span>Your file stays on this machine. Nothing is sent to a hosted service.</span></div>
        </section>) : (<div className="page-stack">
          <div className="uploaded-file-card">
            <span className="uploaded-file-icon"><FileSpreadsheet size={18}/></span>
            <div className="uploaded-file-copy">
              <strong>{uploaded.display_filename}</strong>
              <span>{uploaded.n_rows.toLocaleString()} rows <i /> {uploaded.n_cols} columns <i /> {formatBytes(uploaded.size_bytes)}</span>
            </div>
            <span className="file-ready"><Check size={14}/> Ready</span>
            <button type="button" className="text-button" onClick={() => { setUploaded(null); setSplit(null); setError(null); }}>Replace file</button>
          </div>

          <ProfileTable columns={uploaded.profile.columns} rows={uploaded.n_rows} totalColumns={uploaded.n_cols}/>

          <section className="card split-card" aria-labelledby="split-title">
            <div className="section-heading">
              <div>
                <span className="section-kicker">DEFINE THE EVALUATION</span>
                <h2 id="split-title">Choose a target and split</h2>
              </div>
              <span className="step-indicator"><span>02</span> of 03</span>
            </div>
            <p className="muted-copy split-lead">This partition is stored once and reused by every model. Feature decisions happen after the split is fixed.</p>

            <form className="split-form" onSubmit={onSplitSubmit}>
              <div className="form-grid">
                <label className="field">
                  <span className="field-label">Target column <span className="required">*</span></span>
                  <select value={target} onChange={(event) => { setTarget(event.target.value); setSplit(null); }} required>
                    {uploaded.header.map((column) => <option key={column} value={column}>{column}</option>)}
                  </select>
                  <small>The value you want the models to predict.</small>
                </label>
                <label className="field">
                  <span className="field-label">Target missing tokens <span className="optional">Optional</span></span>
                  <input value={targetTokens} onChange={(event) => { setTargetTokens(event.target.value); setSplit(null); }} placeholder="e.g. unknown, ?"/>
                  <small>Comma-separated values treated as missing labels.</small>
                </label>
                <label className="field">
                  <span className="field-label">Random seed</span>
                  <input type="number" value={seed} onChange={(event) => { setSeed(event.target.value); setSplit(null); }}/>
                  <small>Keep this fixed to reproduce the partition.</small>
                </label>
                <label className="field">
                  <span className="field-label">Test partition</span>
                  <select value={testSize} onChange={(event) => { setTestSize(event.target.value); setSplit(null); }}>
                    <option value="0.1">10% of labelled rows</option>
                    <option value="0.2">20% of labelled rows</option>
                    <option value="0.3">30% of labelled rows</option>
                    <option value="0.4">40% of labelled rows</option>
                  </select>
                  <small>Used only for the final model evaluation.</small>
                </label>
              </div>
              <div className="form-footer">
                <span className="fixed-note"><ShieldCheck size={14}/> The split is created before feature review.</span>
                <button type="submit" className="button button-primary" disabled={splitMutation.isPending || !target}>
                  {splitMutation.isPending ? <RefreshCw size={15} className="spin"/> : null}
                  {splitMutation.isPending ? 'Creating split…' : split ? 'Recreate split' : 'Create split'}
                  {!splitMutation.isPending && <ArrowRight size={15}/>}
                </button>
              </div>
            </form>

            {split && (<div className="split-result">
                <div className="result-summary">
                  <div className="result-check"><Check size={17}/></div>
                  <div>
                    <strong>Partition created and saved</strong>
                    <span>{split.n_labelled.toLocaleString()} labelled rows · {split.n_train.toLocaleString()} train · {split.n_test.toLocaleString()} test</span>
                  </div>
                </div>
                {(droppedRows > 0 || trimmedLabels > 0) && (<p className="data-note">
                    {droppedRows > 0 && `${droppedRows} rows dropped because the target was missing.`}
                    {droppedRows > 0 && trimmedLabels > 0 ? ' ' : ''}
                    {trimmedLabels > 0 && `${trimmedLabels} target labels were trimmed.`}
                  </p>)}
                {split.warnings.length > 0 && (<ul className="split-warnings">{split.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>)}
                <ClassTable classTable={split.class_table}/>
                <div className="continue-row">
                  <span><Check size={15}/> Same rows will be used to compare each selected model.</span>
                  <Link className="button button-primary" to={`/review/${uploaded.upload_id}/${split.split_id}`}>
                    Continue to review <ArrowRight size={15}/>
                  </Link>
                </div>
              </div>)}
          </section>
        </div>)}

      <div className="page-footnote"><ArrowDown size={14}/> Your choices are applied only after the split has been saved.</div>
    </div>);
}
function formatBytes(bytes) {
    if (bytes < 1024 * 1024)
        return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
