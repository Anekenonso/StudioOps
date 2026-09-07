/**
 * The only place that talks to the backend.
 *
 * UI components never call fetch directly, and never see a raw error: the
 * backend already maps failures onto safe messages, and anything unexpected is
 * replaced here with a generic one.
 */

import type {
  CompleteEvent,
  ConfigStatus,
  ProgressEvent,
  ProjectBriefInput,
  ResearchResult,
  RunStatus,
} from './types'

/**
 * Empty by default: requests go to this origin and next.config.mjs proxies them
 * to FastAPI. Set NEXT_PUBLIC_API_BASE_URL to call a deployed backend directly.
 */
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/$/, '')

export const GENERIC_ERROR = "We couldn't complete the research. Please try again."

export function apiUrl(path: string): string {
  if (!path) return path
  return `${API_BASE}${path.startsWith('/') ? path : `/${path}`}`
}

export class ApiError extends Error {
  readonly runId?: string
  readonly stage?: string
  readonly statusCode: number

  constructor(message: string, statusCode: number, runId?: string, stage?: string) {
    super(message || GENERIC_ERROR)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.runId = runId
    this.stage = stage
  }
}

/** Pull a safe message out of a FastAPI error body, whatever its shape. */
async function toApiError(response: Response): Promise<ApiError> {
  let detail: unknown
  try {
    const body = await response.json()
    detail = (body as { detail?: unknown })?.detail
  } catch {
    detail = undefined
  }

  if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
    const shaped = detail as { message?: string; run_id?: string; stage?: string }
    return new ApiError(
      shaped.message || GENERIC_ERROR,
      response.status,
      shaped.run_id,
      shaped.stage,
    )
  }

  if (Array.isArray(detail)) {
    // 422 from Pydantic: tell the user what to fix without echoing internals.
    return new ApiError(
      'That brief is missing something we need. Add a bit more detail and try again.',
      response.status,
    )
  }

  return new ApiError(GENERIC_ERROR, response.status)
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(apiUrl(path), { headers: { accept: 'application/json' } })
  } catch {
    throw new ApiError('We lost the connection to StudioOps. Please try again.', 0)
  }
  if (!response.ok) throw await toApiError(response)
  return (await response.json()) as T
}

/** Start a run in the background. Returns immediately with a run id. */
export async function startResearch(
  brief: ProjectBriefInput,
): Promise<{ run_id: string; status: string }> {
  let response: Response
  try {
    response = await fetch(apiUrl('/api/v1/research/async'), {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(brief),
    })
  } catch {
    throw new ApiError('We couldn’t reach StudioOps. Check the connection and try again.', 0)
  }

  if (!response.ok) throw await toApiError(response)
  return (await response.json()) as { run_id: string; status: string }
}

export function fetchRun(runId: string): Promise<RunStatus> {
  return getJson<RunStatus>(`/api/v1/research/${encodeURIComponent(runId)}`)
}

export function fetchConfig(): Promise<ConfigStatus> {
  return getJson<ConfigStatus>('/api/v1/config')
}

export interface ProgressHandlers {
  onEvent: (event: ProgressEvent) => void
  onComplete: (event: CompleteEvent) => void
  /** Called when the stream is permanently closed by the browser. */
  onStreamLost: () => void
}

/**
 * Subscribe to the run's real progress events.
 *
 * The backend replays everything already emitted when a subscriber connects, so
 * arriving late (or reconnecting) still yields the full timeline.
 */
export function subscribeToProgress(runId: string, handlers: ProgressHandlers): () => void {
  const source = new EventSource(apiUrl(`/api/v1/research/${encodeURIComponent(runId)}/events`))
  let closed = false

  const close = () => {
    if (closed) return
    closed = true
    source.close()
  }

  source.addEventListener('progress', (raw) => {
    try {
      handlers.onEvent(JSON.parse((raw as MessageEvent).data) as ProgressEvent)
    } catch {
      /* A malformed frame is not worth tearing the stream down for. */
    }
  })

  source.addEventListener('complete', (raw) => {
    try {
      handlers.onComplete(JSON.parse((raw as MessageEvent).data) as CompleteEvent)
    } catch {
      handlers.onStreamLost()
    } finally {
      close()
    }
  })

  source.onerror = () => {
    // readyState CONNECTING means the browser is retrying on its own; only a
    // CLOSED stream needs the polling fallback.
    if (source.readyState === EventSource.CLOSED) {
      close()
      handlers.onStreamLost()
    }
  }

  return close
}

/** Resolve the finished result for a run, or null while it is still running. */
export async function fetchResult(runId: string): Promise<ResearchResult | null> {
  const run = await fetchRun(runId)
  if (run.status === 'failed') {
    throw new ApiError(run.error || GENERIC_ERROR, 502, run.run_id, run.error_stage || undefined)
  }
  return run.result ?? null
}
