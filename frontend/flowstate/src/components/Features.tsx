import './Features.css';

const features = [
  {
    title: 'Repo in, map out',
    body: 'Paste a URL. We parse imports, calls and data hand-offs across languages and lay them out as a clean, navigable graph.',
    tone: 'linear-gradient(135deg, var(--sky), var(--lilac))',
  },
  {
    title: 'Click to source',
    body: 'Every node is a doorway. Select a module, function or edge and land on the exact file and line it came from.',
    tone: 'linear-gradient(135deg, var(--lilac), var(--rose))',
  },
  {
    title: 'Follow the data',
    body: 'Trace a request from the route handler to the database and back. Highlight only the path that matters.',
    tone: 'linear-gradient(135deg, var(--rose), var(--peach))',
  },
  {
    title: 'Stays current',
    body: 'Re-index on every push. Diffs show up as soft highlights so reviewers see what moved, not just what changed.',
    tone: 'linear-gradient(135deg, var(--sage), var(--sky))',
  },
];

export default function Features() {
  return (
    <section className="features container" id="features">
      <div className="section-head">
        <p className="eyebrow">Features</p>
        <h2>
          Understand a codebase <span className="serif">in minutes,</span> not weeks.
        </h2>
      </div>
      <div className="feature-grid">
        {features.map((f) => (
          <article key={f.title} className="feature">
            <div className="feature-swatch" style={{ background: f.tone }} />
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
