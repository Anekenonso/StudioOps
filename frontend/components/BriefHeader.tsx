'use client'

import { useState } from 'react'

import { apiUrl } from '../lib/api'
import { durationLabel, plural, researchedLabel } from '../lib/format'
import type { ResearchResult } from '../lib/types'
import PrimaryButton from './PrimaryButton'

/** The brief masthead: what was researched, how, and how to take it away. */
export default function BriefHeader({ result }: { result: ResearchResult }) {
  const { project, report, research_metadata: meta } = result
  const [copied, setCopied] = useState<'idle' | 'copied' | 'failed'>('idle')

  const details = [
    project.format,
    project.genre,
    project.geography,
    researchedLabel(project.researched_at),
  ].filter(Boolean) as string[]

  const stats = [
    plural(meta.queries_run, 'live query', 'live queries'),
    plural(meta.unique_sources, 'source'),
    durationLabel(meta.total_duration_ms),
  ].filter(Boolean) as string[]

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied('copied')
    } catch {
      setCopied('failed')
    }
  }

  return (
    <header>
      <p className="eyebrow">Studio Brief</p>
      <h1 className="mt-3 text-hero font-semibold tracking-tight text-ink">{project.title}</h1>

      {details.length > 0 ? (
        <p className="mt-4 text-label uppercase tracking-[0.14em] text-muted">
          {details.join(' · ')}
        </p>
      ) : null}

      <div className="mt-7 flex flex-wrap items-center gap-3">
        {result.report_url_md ? (
          <PrimaryButton href={apiUrl(result.report_url_md)} download>
            Download brief
          </PrimaryButton>
        ) : null}
        {result.report_url_json ? (
          <PrimaryButton href={apiUrl(result.report_url_json)} variant="secondary" download>
            JSON
          </PrimaryButton>
        ) : null}
        <PrimaryButton variant="secondary" onClick={share}>
          {copied === 'copied' ? 'Link copied' : copied === 'failed' ? 'Copy the URL' : 'Share'}
        </PrimaryButton>
        <PrimaryButton href="/" variant="ghost">
          New research
        </PrimaryButton>
      </div>

      {stats.length > 0 ? (
        <p className="mt-5 text-support text-muted">{stats.join(' · ')}</p>
      ) : null}

      <Disclosure result={result} fallback={report.generated_by === 'fallback'} />
    </header>
  )
}

/**
 * Says plainly when the brief is not a full Gemini synthesis. A producer must
 * never mistake grouped search results for analysis.
 */
function Disclosure({ result, fallback }: { result: ResearchResult; fallback: boolean }) {
  const warnings = result.research_metadata.warnings || []
  const partial = result.status === 'partial'
  if (!fallback && !partial && warnings.length === 0) return null

  return (
    <div
      role="note"
      className="mt-7 rounded-lg border border-gold/40 bg-gold-soft/50 px-5 py-4 text-support text-ink"
    >
      <p className="font-medium">
        {fallback
          ? 'Gemini synthesis did not run for this brief.'
          : 'This brief is partial.'}
      </p>
      <p className="prose-body mt-1.5 text-muted">
        {fallback
          ? 'The sections below are grouped straight from the retrieved sources, with no model analysis. Every source is still real and linked.'
          : 'Some research steps did not finish, so the brief covers less ground than usual.'}
      </p>
      {warnings.length > 0 ? (
        <ul className="mt-3 space-y-1 text-muted">
          {warnings.map((warning) => (
            <li key={warning}>— {warning}</li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
