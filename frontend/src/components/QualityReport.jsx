import { ChevronDown, ClipboardList } from 'lucide-react';
function formatValue(value) {
    if (value === null || value === undefined)
        return 'Not applicable';
    if (Array.isArray(value))
        return value.length ? value.map(String).join(', ') : 'None';
    if (typeof value === 'object') {
        const entries = Object.entries(value);
        return entries.length
            ? entries.map(([key, item]) => `${key.replaceAll('_', ' ')}: ${formatValue(item)}`).join(' · ')
            : 'None';
    }
    if (typeof value === 'number')
        return Number.isInteger(value) ? value.toLocaleString() : value.toFixed(4);
    return String(value);
}
export default function QualityReport({ report }) {
    return (<section className="card quality-card" aria-labelledby="quality-title">
      <div className="section-heading">
        <div className="heading-with-icon">
          <span className="heading-icon slate"><ClipboardList size={17}/></span>
          <div>
            <span className="section-kicker">TRANSPARENT BY DESIGN</span>
            <h2 id="quality-title">Data quality report</h2>
          </div>
        </div>
        <span className="quiet-tag">6 report sections</span>
      </div>
      <div className="report-sections">
        {report.sections.map((section) => (<details className="report-section" key={section.id}>
            <summary>
              <span className="report-section-title">{section.id.replaceAll('_', ' ')}</span>
              <span className="source-badge">{section.source}</span>
              <ChevronDown size={15} className="report-chevron"/>
            </summary>
            <div className="report-items">
              {section.items.map((item, index) => (<div className="report-item" key={`${section.id}-${index}`}>
                  <strong>{item.message}</strong>
                  {typeof item.data === 'object' && item.data !== null
                    ? (<dl className="report-facts">
                        {Object.entries(item.data).map(([key, value]) => (<div key={key}>
                            <dt>{key.replaceAll('_', ' ')}</dt>
                            <dd>{formatValue(value)}</dd>
                          </div>))}
                      </dl>)
                    : <p>{formatValue(item.data)}</p>}
                </div>))}
            </div>
          </details>))}
      </div>
      {report.warnings.length > 0 && (<div className="report-warnings">
          <strong>Items to review</strong>
          <ul>{report.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul>
        </div>)}
    </section>);
}
