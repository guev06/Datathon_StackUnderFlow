import PreviewWindow from './PreviewWindow';
import './HeroPreviews.css';

const flowNodes = [
  { id: 'a', x: 20, y: 20, label: 'api/routes.ts', c: 'var(--sky)' },
  { id: 'b', x: 150, y: 20, label: 'auth.ts', c: 'var(--lilac)' },
  { id: 'c', x: 20, y: 90, label: 'orders.service', c: 'var(--rose)' },
  { id: 'd', x: 150, y: 90, label: 'db/client.ts', c: 'var(--peach)' },
  { id: 'e', x: 85, y: 155, label: 'events.queue', c: 'var(--sage)' },
];
const flowEdges: [string, string][] = [['a', 'b'], ['a', 'c'], ['c', 'd'], ['b', 'd'], ['c', 'e']];

function MiniFlow() {
  const pos = Object.fromEntries(flowNodes.map((n) => [n.id, n]));
  return (
    <svg viewBox="0 0 260 195" className="mini-flow">
      {flowEdges.map(([s, t]) => {
        const a = pos[s], b = pos[t];
        return (
          <path
            key={s + t}
            d={`M${a.x + 45} ${a.y + 13} C ${a.x + 45} ${(a.y + b.y) / 2 + 13}, ${b.x + 45} ${(a.y + b.y) / 2 + 13}, ${b.x + 45} ${b.y + 13}`}
            className="mini-edge"
          />
        );
      })}
      {flowNodes.map((n) => (
        <g key={n.id} transform={`translate(${n.x} ${n.y})`} className={n.id === 'c' ? 'mini-node active' : 'mini-node'}>
          <rect width="90" height="26" rx="7" fill="#fff" stroke="var(--border-strong)" />
          <rect width="4" height="26" rx="2" fill={n.c} />
          <text x="11" y="17">{n.label}</text>
        </g>
      ))}
    </svg>
  );
}

function CodePeek() {
  const lines = [
    ['42', 'export async function createOrder(req) {'],
    ['43', '  const user = await auth.verify(req);'],
    ['44', '  const order = await db.orders.insert({'],
    ['45', '    userId: user.id, items: req.body.items,'],
    ['46', '  });'],
    ['47', '  queue.publish("order.created", order);'],
    ['48', '  return order;'],
  ];
  return (
    <pre className="code-peek mono">
      {lines.map(([n, l]) => (
        <div key={n} className={n === '44' ? 'hl' : undefined}>
          <span className="ln">{n}</span>
          {l}
        </div>
      ))}
    </pre>
  );
}

function Trace() {
  const steps = [
    { label: 'POST /orders', tone: 'var(--sky)' },
    { label: 'auth.verify()', tone: 'var(--lilac)' },
    { label: 'orders.createOrder()', tone: 'var(--rose)' },
    { label: 'db.orders.insert()', tone: 'var(--peach)' },
    { label: 'queue.publish()', tone: 'var(--sage)' },
  ];
  return (
    <ol className="trace">
      {steps.map((s, i) => (
        <li key={s.label} style={{ animationDelay: `${i * 0.35}s` }}>
          <span className="trace-dot" style={{ background: s.tone }} />
          <span className="mono">{s.label}</span>
        </li>
      ))}
    </ol>
  );
}

export default function HeroPreviews() {
  return (
    <div className="hero-previews" aria-hidden>
      <PreviewWindow title="dataflow · acme/shop" className="hp hp-flow">
        <MiniFlow />
      </PreviewWindow>
      <PreviewWindow title="orders.service.ts:44" className="hp hp-code">
        <CodePeek />
      </PreviewWindow>
      <PreviewWindow title="trace · request path" className="hp hp-trace">
        <Trace />
      </PreviewWindow>
      <div className="hp hp-stat">
        <span className="stat-dot" />
        Indexed <strong>1,284 files</strong> in 3.2s
      </div>
    </div>
  );
}
