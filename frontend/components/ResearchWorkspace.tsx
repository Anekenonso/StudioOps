'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'

import { ApiError, fetchConfig, GENERIC_ERROR, startResearch } from '../lib/api'
import {
  EMPTY_DRAFT,
  briefToDraft,
  draftToBrief,
  validateDraft,
  type ResearchDraft,
} from '../lib/draft'
import { EXAMPLES } from '../lib/examples'
import { loadLastBrief, saveLastBrief } from '../lib/session'
import type { ConfigStatus } from '../lib/types'
import ResearchInput from './ResearchInput'

/** Owns the form state and starts the run. The only stateful part of the home page. */
export default function ResearchWorkspace() {
  const router = useRouter()
  const [draft, setDraft] = useState<ResearchDraft>(EMPTY_DRAFT)
  const [activeExample, setActiveExample] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [config, setConfig] = useState<ConfigStatus | null>(null)

  // Restore the last brief so a producer returning from an error keeps their typing.
  useEffect(() => {
    const brief = loadLastBrief()
    if (brief) setDraft(briefToDraft(brief))
  }, [])

  useEffect(() => {
    let cancelled = false
    fetchConfig()
      .then((value) => {
        if (!cancelled) setConfig(value)
      })
      .catch(() => {
        // The banner is a courtesy; never block the form on it.
      })
    return () => {
      cancelled = true
    }
  }, [])

  const pickExample = (label: string) => {
    const example = EXAMPLES.find((item) => item.label === label)
    if (!example) return
    setDraft(example.draft)
    setActiveExample(label)
    setError(null)
  }

  const submit = async () => {
    const problem = validateDraft(draft)
    if (problem) {
      setError(problem)
      return
    }

    setError(null)
    setSubmitting(true)
    const brief = draftToBrief(draft)
    saveLastBrief(brief)

    try {
      const { run_id } = await startResearch(brief)
      router.push(`/research?run=${encodeURIComponent(run_id)}`)
    } catch (caught) {
      setSubmitting(false)
      setError(caught instanceof ApiError ? caught.message : GENERIC_ERROR)
    }
  }

  return (
    <div>
      <ConfigNotice config={config} />
      <ResearchInput
        draft={draft}
        onChange={(next) => {
          setDraft(next)
          setActiveExample(null)
        }}
        onSubmit={submit}
        submitting={submitting}
        error={error}
        activeExample={activeExample}
        onExample={pickExample}
      />
    </div>
  )
}

/** Tells the producer up front when an integration is missing, rather than after a thin brief. */
function ConfigNotice({ config }: { config: ConfigStatus | null }) {
  if (!config) return null

  const notices: string[] = []
  if (!config.parallel.configured) {
    notices.push(
      'Live web search is not configured on this deployment, so a run cannot retrieve sources yet.',
    )
  }
  if (!config.gemini.configured) {
    notices.push(
      'Gemini is not configured on this deployment. Research still runs, but the brief will be grouped from sources without model analysis.',
    )
  }
  if (notices.length === 0) return null

  return (
    <div
      role="note"
      className="mb-5 rounded-lg border border-gold/40 bg-gold-soft/50 px-5 py-4 text-support text-ink"
    >
      {notices.map((notice) => (
        <p key={notice} className="prose-body">
          {notice}
        </p>
      ))}
    </div>
  )
}
