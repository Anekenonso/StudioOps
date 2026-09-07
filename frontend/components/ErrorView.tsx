'use client'

import { useEffect, useState } from 'react'
import { useSearchParams } from 'next/navigation'

import { GENERIC_ERROR } from '../lib/api'
import { loadError } from '../lib/session'
import PrimaryButton from './PrimaryButton'

const STAGE_COPY: Record<string, string> = {
  intake: 'The brief could not be read.',
  plan: 'The research plan could not be built.',
  search: 'The live web search did not return anything usable.',
  collect: 'The retrieved sources could not be organised.',
  synthesize: 'The evidence could not be analysed.',
  report: 'The brief could not be assembled.',
}

/** The failure screen. Honest about what stopped, silent about internals. */
export default function ErrorView() {
  const params = useSearchParams()
  const runId = params.get('run')
  const [message, setMessage] = useState<string>(GENERIC_ERROR)
  const [stage, setStage] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return
    const stored = loadError(runId)
    if (stored?.message) setMessage(stored.message)
    if (stored?.stage) setStage(stored.stage)
  }, [runId])

  const stageCopy = stage ? STAGE_COPY[stage] : null

  return (
    <div className="shell py-20 sm:py-24">
      <div className="max-w-prose">
        <p className="eyebrow">Research stopped</p>
        <h1 className="mt-4 text-hero font-semibold tracking-tight text-ink">
          We couldn&apos;t complete the research.
        </h1>
        <p className="prose-body mt-5 text-body text-muted">{message}</p>
        {stageCopy ? (
          <p className="prose-body mt-3 text-support text-muted">{stageCopy}</p>
        ) : null}

        <div className="mt-8 flex flex-wrap items-center gap-3">
          <PrimaryButton href="/">Try again</PrimaryButton>
          <PrimaryButton href="/#how-it-works" variant="ghost">
            How StudioOps works
          </PrimaryButton>
        </div>

        <p className="mt-8 text-support text-muted">
          Your brief is kept, so you can adjust it and run the research again.
          {runId ? (
            <>
              {' '}
              Run reference <span className="tabular-nums text-ink">{runId}</span>.
            </>
          ) : null}
        </p>
      </div>
    </div>
  )
}
