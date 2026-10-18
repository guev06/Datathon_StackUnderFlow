import { buildGraph } from '../lib/analyze';

// A small fictional storefront used when no repo is given (or GitHub is unreachable).
const sources: { path: string; content: string }[] = [
  {
    path: 'src/server.ts',
    content: `import express from 'express';
import { router } from './api/routes';
import { logger } from './lib/logger';
import { connect } from './db/client';

export async function start(port = 3000) {
  await connect();
  const app = express();
  app.use(express.json());
  app.use('/api', router);
  app.listen(port, () => logger.info(\`listening on \${port}\`));
}

start();
`,
  },
  {
    path: 'src/api/routes.ts',
    content: `import { Router } from 'express';
import { requireAuth } from '../auth/middleware';
import { createOrder, listOrders } from '../orders/orders.service';
import { getProduct } from '../catalog/catalog.service';

export const router = Router();

router.get('/products/:id', async (req, res) => {
  res.json(await getProduct(req.params.id));
});

router.post('/orders', requireAuth, async (req, res) => {
  res.status(201).json(await createOrder(req.user, req.body.items));
});

router.get('/orders', requireAuth, async (req, res) => {
  res.json(await listOrders(req.user.id));
});
`,
  },
  {
    path: 'src/auth/middleware.ts',
    content: `import { verifyToken } from './tokens';
import { findUser } from '../users/users.repo';

export async function requireAuth(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  const claims = token && verifyToken(token);
  if (!claims) return res.status(401).end();
  req.user = await findUser(claims.sub);
  next();
}
`,
  },
  {
    path: 'src/auth/tokens.ts',
    content: `import { config } from '../lib/config';

export function verifyToken(token: string) {
  try {
    const [, payload] = token.split('.');
    const claims = JSON.parse(atob(payload));
    return claims.iss === config.issuer ? claims : null;
  } catch {
    return null;
  }
}
`,
  },
  {
    path: 'src/users/users.repo.ts',
    content: `import { db } from '../db/client';

export async function findUser(id: string) {
  return db.query('select * from users where id = $1', [id]);
}
`,
  },
  {
    path: 'src/orders/orders.service.ts',
    content: `import { db } from '../db/client';
import { publish } from '../events/queue';
import { priceItems } from '../catalog/pricing';

export async function createOrder(user, items) {
  const total = await priceItems(items);
  const order = await db.insert('orders', {
    userId: user.id,
    items,
    total,
  });
  publish('order.created', order);
  return order;
}

export async function listOrders(userId: string) {
  return db.query('select * from orders where user_id = $1', [userId]);
}
`,
  },
  {
    path: 'src/catalog/catalog.service.ts',
    content: `import { db } from '../db/client';
import { cache } from '../lib/cache';

export async function getProduct(id: string) {
  return cache.wrap(\`product:\${id}\`, () =>
    db.query('select * from products where id = $1', [id]),
  );
}
`,
  },
  {
    path: 'src/catalog/pricing.ts',
    content: `import { getProduct } from './catalog.service';

export async function priceItems(items: { id: string; qty: number }[]) {
  let total = 0;
  for (const item of items) {
    const product = await getProduct(item.id);
    total += product.price * item.qty;
  }
  return total;
}
`,
  },
  {
    path: 'src/events/queue.ts',
    content: `import { logger } from '../lib/logger';
import { sendReceipt } from '../notifications/email';

const handlers = { 'order.created': [sendReceipt] };

export function publish(topic: string, payload: unknown) {
  logger.info(\`event \${topic}\`);
  for (const h of handlers[topic] ?? []) h(payload);
}
`,
  },
  {
    path: 'src/notifications/email.ts',
    content: `import { config } from '../lib/config';
import { logger } from '../lib/logger';

export async function sendReceipt(order) {
  logger.info(\`sending receipt for \${order.id}\`);
  await fetch(config.mailerUrl, { method: 'POST', body: JSON.stringify(order) });
}
`,
  },
  {
    path: 'src/db/client.ts',
    content: `import { config } from '../lib/config';
import { logger } from '../lib/logger';

export const db = {
  async query(sql: string, params: unknown[]) { /* ... */ },
  async insert(table: string, row: object) { /* ... */ },
};

export async function connect() {
  logger.info(\`connecting to \${config.databaseUrl}\`);
}
`,
  },
  {
    path: 'src/lib/cache.ts',
    content: `const store = new Map();

export const cache = {
  async wrap(key: string, fn: () => Promise<unknown>) {
    if (!store.has(key)) store.set(key, await fn());
    return store.get(key);
  },
};
`,
  },
  {
    path: 'src/lib/config.ts',
    content: `export const config = {
  issuer: process.env.JWT_ISSUER,
  databaseUrl: process.env.DATABASE_URL,
  mailerUrl: process.env.MAILER_URL,
};
`,
  },
  {
    path: 'src/lib/logger.ts',
    content: `export const logger = {
  info: (msg: string) => console.log(\`[info] \${msg}\`),
  error: (msg: string) => console.error(\`[error] \${msg}\`),
};
`,
  },
];

export const demoGraph = buildGraph(
  { owner: 'acme', repo: 'shop', branch: 'main', source: 'demo', truncated: false },
  sources,
);
