'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { ApiError, fetchResult, GENERIC_ERROR } from '../lib/api'
import { loadLastBrief, saveError, saveResult } from '../lib/session'
import { useResearchRun } from '../lib/useResearchRun'
import LiveResearchPanel from './LiveResearchPanel'
import PrimaryButton from './PrimaryButton'
import ResearchProgress from './ResearchProgress'

/**
 * The live run screen. Everything on it is driven by the backend's own progress
 * events — there is no simulated timeline.
 */
export default function ResearchLive() {
  const router = useRouter()
  const params = useSearchParams()
  const runId = params.get('run')
  const [projectTitle, setProjectTitle] = useState<string | null>(null)

  useEffect(() => {
    setProjectTitle(loadLastBrief()?.title || null)
  }, [])

  // A direct hit on /research with no run id has nothing to show.
  useEffect(() => {
    if (!runId) router.replace('/')
  }, [runId, router])

  const fail = useCallback(
    (id: string, message: string, stage?: string) => {
      saveError(id, { message: message || GENERIC_ERROR, stage })
      router.replace(`/error?run=${encodeURIComponent(id)}`)
    },
    [router],
  )

  const onFinished = useCallback(async () => {
    if (!runId) return
    try {
      const result = await fetchResult(runId)
      if (!result) {
        fail(runId, GENERIC_ERROR)
        return
      }
      saveResult(runId, result)
      router.replace(`/brief?run=${encodeURIComponent(runId)}`)
    } catch (caught) {
      fail(runId, caught instanceof ApiError ? caught.message : GENERIC_ERROR)
    }
  }, [runId, router, fail])

  const onFailure = useCallback(
    (message: string, stage?: string) => {
      if (!runId) return
      fail(runId, message, stage)
    },
    [runId, fail],
  )

  const { view, steps, streamLost } = useResearchRun({ runId, onFinished, onFailure })

  return (
    <div className="shell py-14 sm:py-16">
      <header className="max-w-prose">
        <p className="eyebrow">Researching</p>
        <h1 className="mt-3 text-section font-semibold tracking-tight text-ink">
          {projectTitle || 'Your project'}
        </h1>
        <p aria-live="polite" className="prose-body mt-4 text-body text-muted">
          {view.latestMessage}
        </p>
      </header>

      <div className="mt-9">
        <ResearchProgress steps={steps} />
      </div>

      <div className="mt-8">
        <LiveResearchPanel view={view} streamLost={streamLost} />
      </div>

      <div className="mt-9 flex flex-wrap items-center gap-4">
        <PrimaryButton href="/" variant="ghost">
          Start over
        </PrimaryButton>
        <p className="text-support text-muted">
          The brief opens on its own when the research completes.
        </p>
      </div>
    </div>
  )
}
