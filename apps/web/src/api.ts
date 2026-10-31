import type { EngineInfo, Job, Plan, TrajectoryFile } from "./types";

/* Same-origin by default so dev goes through the Vite /v1 proxy (no CORS
 * needed). Set VITE_API_URL for preview/prod pointing at a reachable API. */
const BASE = import.meta.env.VITE_API_URL ?? "";

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${method} ${path}: HTTP ${res.status} ${text.slice(0, 200)}`);
  }
  return (await res.json()) as T;
}

export const api = {
  plan: (prompt: string) => req<Plan>("POST", "/v1/plan", { prompt }),
  engines: () => req<{ engines: EngineInfo[] }>("GET", "/v1/engines"),
  submit: (engine: string, params: Record<string, number>, seed: number, idempotency_key?: string) =>
    req<Job>("POST", "/v1/runs", { engine, params, seed, idempotency_key }),
  getRun: (id: string, signal?: AbortSignal) => req<Job>("GET", `/v1/runs/${id}`, undefined, signal),
  listRuns: () => req<{ runs: Job[] }>("GET", "/v1/runs"),
  trajectory: (id: string, stride = 1) =>
    req<TrajectoryFile>("GET", `/v1/runs/${id}/trajectory${stride > 1 ? `?stride=${stride}` : ""}`),
  bundle: (id: string) => req<Record<string, unknown>>("GET", `/v1/runs/${id}/bundle`),
};

export interface PollOptions {
  timeoutMs?: number;
  signal?: AbortSignal;
}

function abortError(): DOMException {
  return new DOMException("poll aborted", "AbortError");
}

function isAbortError(e: unknown): boolean {
  return e instanceof DOMException && e.name === "AbortError";
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(abortError());
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      cleanup();
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(timer);
      cleanup();
      reject(abortError());
    };
    const cleanup = () => signal?.removeEventListener("abort", onAbort);
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function pollRun(
  id: string,
  timeoutMsOrOpts: number | PollOptions = 600000,
): Promise<Job> {
  const opts: PollOptions =
    typeof timeoutMsOrOpts === "number" ? { timeoutMs: timeoutMsOrOpts } : timeoutMsOrOpts;
  const timeoutMs = opts.timeoutMs ?? 600000;
  const signal = opts.signal;
  const start = Date.now();
  let delay = 1000;
  let netFailures = 0;
  for (;;) {
    if (signal?.aborted) throw abortError();
    let job: Job;
    try {
      job = await api.getRun(id, signal);
    } catch (e) {
      if (signal?.aborted || isAbortError(e)) throw abortError();
      netFailures += 1;
      if (netFailures > 3) throw e;
      await sleep(delay, signal);
      delay = Math.min(5000, delay * 2);
      continue;
    }
    netFailures = 0;
    if (job.state === "completed" || job.state === "failed" || job.state === "cancelled") {
      return job;
    }
    if (Date.now() - start > timeoutMs) {
      throw new Error(`run ${id} timed out in ${job.state}`);
    }
    await sleep(delay, signal);
    delay = Math.min(5000, delay * 2);
  }
}
