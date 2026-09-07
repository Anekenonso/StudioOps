/**
 * Hand-off between the three screens without a database or an account.
 *
 * sessionStorage only: it dies with the tab, which is exactly the V1 scope. The
 * backend remains the source of truth — every read here has a fetch fallback.
 */

import type { ProjectBriefInput, ResearchResult } from './types'

const BRIEF_KEY = 'studioops:last-brief'
const resultKey = (runId: string) => `studioops:result:${runId}`
const errorKey = (runId: string) => `studioops:error:${runId}`

export interface StoredError {
  message: string
  stage?: string
}

function read<T>(key: string): T | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.sessionStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : null
  } catch {
    return null
  }
}

function write(key: string, value: unknown): void {
  if (typeof window === 'undefined') return
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* Private mode or a full quota: the backend can still serve this. */
  }
}

export const saveLastBrief = (brief: ProjectBriefInput) => write(BRIEF_KEY, brief)
export const loadLastBrief = () => read<ProjectBriefInput>(BRIEF_KEY)

export const saveResult = (runId: string, result: ResearchResult) =>
  write(resultKey(runId), result)
export const loadResult = (runId: string) => read<ResearchResult>(resultKey(runId))

export const saveError = (runId: string, error: StoredError) => write(errorKey(runId), error)
export const loadError = (runId: string) => read<StoredError>(errorKey(runId))
