import type { Analysis, JobStep } from './types';

export type Progress = { steps: JobStep[]; step: string };

const API = import.meta.env.VITE_API_URL ?? '';

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API}${path}`, init);
  } catch {
    throw new BackendUnavailable();
  }
  if (res.status === 502 || res.status === 504) throw new BackendUnavailable();
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail ?? `Backend responded with ${res.status}.`);
  return body as T;
}

export class BackendUnavailable extends Error {
  constructor() {
    super('The FlowState backend is not running.');
  }
}

/** Start (or fetch from cache) an AI dataflow analysis and poll until it finishes. */
export async function analyzeWithBackend(
  repo: string,
  onProgress: (p: Progress) => void,
  isCancelled: () => boolean,
  refresh = false,
): Promise<Analysis> {
  type Start = { status: string; result?: Analysis; job_id?: string; steps?: JobStep[] };
  const start = await call<Start>('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo, refresh }),
  });
  if (start.result) return start.result;

  type Job = { status: string; step: string; steps: JobStep[]; error?: string; result?: Analysis };
  onProgress({ steps: start.steps ?? [], step: 'queued' });
  for (;;) {
    await new Promise((r) => setTimeout(r, 1000));
    if (isCancelled()) throw new Error('cancelled');
    const job = await call<Job>(`/api/jobs/${start.job_id}`);
    onProgress({ steps: job.steps, step: job.step });
    if (job.status === 'done' && job.result) return job.result;
    if (job.status === 'error') throw new Error(job.error ?? 'Analysis failed.');
  }
}
