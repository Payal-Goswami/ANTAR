import { AlertTriangle, ArrowRight, CircleCheck } from 'lucide-react';
export default function FlagList({ flags, undecided }) {
    const flagged = Object.entries(flags).filter(([, info]) => info.flag);
    if (flagged.length === 0) {
        return (<div className="empty-check">
        <CircleCheck size={17}/>
        <span>No review flags were detected in the training partition.</span>
      </div>);
    }
    return (<div className="flag-list">
      {flagged.map(([name, info]) => {
            const needsDecision = undecided.includes(name);
            const uniqueRatio = info.details.unique_ratio;
            return (<article className={`flag-row${needsDecision ? ' needs-decision' : ''}`} key={name}>
            <span className="flag-icon"><AlertTriangle size={16}/></span>
            <div className="flag-copy">
              <div className="flag-title-row">
                <strong>{name}</strong>
                <span className="flag-kind">{info.flag?.replaceAll('_', ' ')}</span>
                {typeof uniqueRatio === 'number' && <span className="flag-ratio">{(uniqueRatio * 100).toFixed(1)}% unique</span>}
              </div>
              <p>{info.reason}</p>
            </div>
            {needsDecision && <span className="decision-needed">Decision needed <ArrowRight size={13}/></span>}
          </article>);
        })}
    </div>);
}
