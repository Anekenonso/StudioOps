'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { ApiError, fetchRun, subscribeToProgress } from './api'
import type { CompleteEvent, GeneratedBy, PlanTask, ProgressEvent, RunState } from './types'

/** One planned query and what actually happened to it. */
export interface SearchActivity {
  id: string
  label: string
  category: string
  query: string
  state: 'pending' | 'searching' | 'done' | 'failed'
  resultCount?: number
}

export interface RunView {
  planDone: boolean
  planner?: GeneratedBy
  reasoning?: string
  searchStarted: boolean
  searchDone: boolean
  collectDone: boolean
  synthesizeStarted: boolean
  /** The synthesize stage produced an outcome, successful or not. */
  synthesizeResolved: boolean
  /** Gemini did not analyse the evidence — the brief will say so. */
  synthesizeDegraded: boolean
  reportDone: boolean
  activities: SearchActivity[]
  totalResults?: number
  uniqueSources?: number
  duplicatesRemoved?: number
  queriesFailed?: number
  latestMessage: string
  errorMessage?: string
}

export type StepState = 'pending' | 'active' | 'done' | 'failed'

export interface Step {
  number: string
  label: string
  state: StepState
}

const eventKey = (event: ProgressEvent) =>
  `${event.at}|${event.stage}|${event.status}|${event.message}`

/** Fold the real progress events into everything the UI needs to render. */
export function deriveView(events: ProgressEvent[]): RunView {
  const view: RunView = {
    planDone: false,
    searchStarted: false,
    searchDone: false,
    collectDone: false,
    synthesizeStarted: false,
    synthesizeResolved: false,
    synthesizeDegraded: false,
    reportDone: false,
    activities: [],
    latestMessage: 'Starting research…',
  }

  const activities = new Map<string, SearchActivity>()

  const seedTasks = (tasks: PlanTask[] | undefined) => {
    for (const task of tasks || []) {
      if (!activities.has(task.id)) {
        activities.set(task.id, {
          id: task.id,
          label: task.label,
          category: task.category,
          query: task.query,
          state: 'pending',
        })
      }
    }
  }

  for (const event of events) {
    if (event.message) view.latestMessage = event.message

    switch (event.stage) {
      case 'plan':
        if (event.status === 'done') {
          view.planDone = true
          view.planner = event.planner
          view.reasoning = event.reasoning
          seedTasks(event.tasks)
        }
        break

      case 'search':
        if (event.status === 'active') view.searchStarted = true
        if (event.status === 'info' && event.task_id) {
          const existing = activities.get(event.task_id)
          const activity: SearchActivity = existing ?? {
            id: event.task_id,
            label: event.message,
            category: event.category || 'other',
            query: event.query || '',
            state: 'pending',
          }
          const hasCount = typeof event.result_count === 'number'
          activities.set(event.task_id, {
            ...activity,
            category: event.category || activity.category,
            query: event.query || activity.query,
            state: hasCount ? 'done' : 'searching',
            resultCount: hasCount ? event.result_count : activity.resultCount,
          })
        }
        if (event.status === 'done') {
          view.searchDone = true
          view.totalResults = event.results
          view.queriesFailed = event.queries_failed
          // A search that failed emits no completion event, so anything still
          // in flight when the stage closes did not come back.
          for (const [id, activity] of activities) {
            if (activity.state === 'pending' || activity.state === 'searching') {
              activities.set(id, { ...activity, state: 'failed' })
            }
          }
        }
        if (event.status === 'error') view.errorMessage = event.message
        break

      case 'collect':
        if (event.status === 'done') {
          view.collectDone = true
          view.uniqueSources = event.unique_sources
          view.duplicatesRemoved = event.duplicates_removed
        }
        break

      case 'synthesize':
        if (event.status === 'active') view.synthesizeStarted = true
        if (event.status === 'done') {
          view.synthesizeStarted = true
          view.synthesizeResolved = true
        }
        if (event.status === 'info' || event.status === 'error') {
          // Gemini unavailable, or nothing usable to analyse.
          view.synthesizeStarted = true
          view.synthesizeResolved = true
          view.synthesizeDegraded = true
        }
        break

      case 'report':
        if (event.status === 'done') view.reportDone = true
        break

      default:
        if (event.status === 'error') view.errorMessage = event.message
        break
    }

    if (event.status === 'error' && event.stage !== 'synthesize') {
      view.errorMessage = event.message
    }
  }

  view.activities = Array.from(activities.values())
  return view
}

/** The four states from the UI spec, driven by real backend stages. */
export function deriveSteps(view: RunView): Step[] {
  const searchState: StepState = view.collectDone
    ? 'done'
    : view.searchDone
      ? 'active'
      : view.searchStarted
        ? 'active'
        : 'pending'

  return [
    {
      number: '01',
      label: 'Understanding brief',
      state: view.planDone ? 'done' : 'active',
    },
    {
      number: '02',
      label: 'Searching the web',
      state: view.planDone ? searchState : 'pending',
    },
    {
      number: '03',
      label: 'Analyzing findings',
      state: view.synthesizeResolved
        ? 'done'
        : view.synthesizeStarted
          ? 'active'
          : 'pending',
    },
    {
      number: '04',
      label: 'Building studio brief',
      state: view.reportDone ? 'done' : view.synthesizeResolved ? 'active' : 'pending',
    },
  ]
}

interface Options {
  runId: string | null
  onFinished: (event: CompleteEvent) => void
  onFailure: (message: string, stage?: string) => void
}

const POLL_INTERVAL_MS = 2500

/**
 * Subscribe to a run's progress. Falls back to polling if the browser drops the
 * event stream, so a proxy timeout never leaves the screen frozen.
 */
export function useResearchRun({ runId, onFinished, onFailure }: Options) {
  const [events, setEvents] = useState<ProgressEvent[]>([])
  const [streamLost, setStreamLost] = useState(false)
  const seen = useRef(new Set<string>())
  const settled = useRef(false)

  // Keep the callbacks in refs: the effect must not re-subscribe when a parent
  // re-renders with new closures.
  const finishedRef = useRef(onFinished)
  const failureRef = useRef(onFailure)
  finishedRef.current = onFinished
  failureRef.current = onFailure

  const append = useCallback((event: ProgressEvent) => {
    const key = eventKey(event)
    if (seen.current.has(key)) return
    seen.current.add(key)
    setEvents((current) => [...current, event])
  }, [])

  useEffect(() => {
    if (!runId) return
    settled.current = false

    const close = subscribeToProgress(runId, {
      onEvent: append,
      onComplete: (event) => {
        if (settled.current) return
        settled.current = true
        if (event.status === 'failed') {
          failureRef.current(event.error || '', 'unknown')
        } else {
          finishedRef.current(event)
        }
      },
      onStreamLost: () => setStreamLost(true),
    })

    return () => close()
  }, [runId, append])

  // Polling fallback, active only once the stream is gone.
  useEffect(() => {
    if (!runId || !streamLost) return

    let cancelled = false
    const timer = setInterval(async () => {
      try {
        const run = await fetchRun(runId)
        if (cancelled || settled.current) return
        if (run.status === 'failed') {
          settled.current = true
          failureRef.current(run.error || '', run.error_stage || undefined)
        } else if (run.status !== 'running') {
          settled.current = true
          finishedRef.current({
            stage: 'complete',
            status: run.status as RunState,
            run_id: run.run_id,
            error: null,
          })
        }
      } catch (error) {
        if (cancelled) return
        settled.current = true
        const message = error instanceof ApiError ? error.message : ''
        failureRef.current(message, undefined)
      }
    }, POLL_INTERVAL_MS)

    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [runId, streamLost])

  const view = useMemo(() => deriveView(events), [events])
  const steps = useMemo(() => deriveSteps(view), [view])

  return { view, steps, streamLost, eventCount: events.length }
}
