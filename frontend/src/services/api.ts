// Client for the MIJHAR backend (backend/mijhar/api.py).
// Secrets: the reviewer key and the client API key are typed by the operator and held in React
// state only. They are NOT build-time variables: anything in a Vite bundle is public.
export const API_URL: string = (import.meta as any).env?.VITE_API_URL ?? 'http://127.0.0.1:8000';

export type WireDecision = 'approve' | 'reject' | 'revise';

export interface SignedOutcome {
  status: string;
  reportSha256: string;
  txHash?: string;
  timestamp?: string;
  reviewer?: string;
  error?: string;
}

export async function backendAvailable(): Promise<boolean> {
  try {
    const r = await fetch(`${API_URL}/healthz`, { signal: AbortSignal.timeout(2500) });
    return r.ok;
  } catch {
    return false;
  }
}

async function call(path: string, init: RequestInit): Promise<any> {
  const r = await fetch(`${API_URL}${path}`, init);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body?.detail ?? `HTTP ${r.status}`);
  return body;
}

/** Runs a real audit, then submits the human decision. The server signs it, the harness verifies it. */
export async function auditAndDecide(a: {
  text: string; filename: string; reviewer: string; reviewerKey: string; clientKey: string; decision: WireDecision;
}): Promise<SignedOutcome> {
  const job = await call('/v1/audits', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-API-Key': a.clientKey },
    body: JSON.stringify({ text: a.text, filename: a.filename, config: 'B' }),
  });
  if (!job.awaiting_human) throw new Error(job.error ?? `run stopped before the human gate (${job.status})`);
  const done = await call(`/v1/audits/${job.job_id}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Reviewer-Key': a.reviewerKey },
    body: JSON.stringify({ reviewer: a.reviewer, decision: a.decision, report_sha256: job.report_sha256 }),
  });
  return {
    status: done.status,
    reportSha256: job.report_sha256,
    txHash: done.commit?.tx_hash,
    timestamp: done.commit?.timestamp,
    reviewer: done.hitl?.reviewer,
    error: done.error ?? undefined,
  };
}
