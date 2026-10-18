import PreviewWindow from './PreviewWindow';
import './HowItWorks.css';

const steps = [
  { n: '01', title: 'Connect a repo', body: 'Paste a GitHub URL or install the app on your organisation.' },
  { n: '02', title: 'AI reads it', body: 'Functions and calls are indexed, then IBM Granite writes the dataflow and maps every step to real code.' },
  { n: '03', title: 'Explore the flow', body: 'Pan, filter and click through. Play the flow step by step; every step opens its source.' },
];

export default function HowItWorks() {
  return (
    <section className="how" id="how">
      <div className="container how-inner">
        <div>
          <div className="section-head">
            <p className="eyebrow">How it works</p>
            <h2>
              Three steps <span className="serif">to clarity.</span>
            </h2>
          </div>
          <ol className="steps">
            {steps.map((s) => (
              <li key={s.n}>
                <span className="step-n mono">{s.n}</span>
                <div>
                  <h3>{s.title}</h3>
                  <p>{s.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
        <PreviewWindow title="terminal" className="how-terminal">
          <pre className="mono">
            <span className="t-faint">$</span> flowstate index github.com/acme/shop{'\n'}
            <span className="t-faint">→</span> cloning ............... done{'\n'}
            <span className="t-faint">→</span> parsing 1,284 files ... done{'\n'}
            <span className="t-faint">→</span> resolving 4,912 edges . done{'\n'}
            {'\n'}
            <span className="t-ok">✓</span> map ready at <span className="t-link">flowstate.dev/acme/shop</span>
          </pre>
        </PreviewWindow>
      </div>
    </section>
  );
}
