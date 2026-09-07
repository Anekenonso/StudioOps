'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'

import { ApiError, fetchResult, GENERIC_ERROR } from '../lib/api'
import { categoryLabel, durationLabel, plural } from '../lib/format'
import { loadError, loadResult, saveResult } from '../lib/session'
import type { ResearchResult } from '../lib/types'
import BriefHeader from './BriefHeader'
import BriefSection from './BriefSection'
import Citations, { SourceMapProvider } from './Citations'
import ComparableCard from './ComparableCard'
import InsightCard from './InsightCard'
import OpportunityCard from './OpportunityCard'
import PrimaryButton from './PrimaryButton'
import RiskCard from './RiskCard'
import SourceList from './SourceList'

/** The finished studio brief. Loads from the session hand-off, or refetches it. */
export default function BriefView() {
  const router = useRouter()
  const params = useSearchParams()
  const runId = params.get('run')
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) {
      router.replace('/')
      return
    }

    const stored = loadResult(runId)
    if (stored) {
      setResult(stored)
      return
    }

    // Reached by a shared or reloaded link: the backend is the source of truth.
    let cancelled = false
    fetchResult(runId)
      .then((fetched) => {
        if (cancelled) return
        if (fetched) {
          saveResult(runId, fetched)
          setResult(fetched)
          return
        }
        const failure = loadError(runId)
        setError(failure?.message || GENERIC_ERROR)
      })
      .catch((caught) => {
        if (cancelled) return
        setError(caught instanceof ApiError ? caught.message : GENERIC_ERROR)
      })

    return () => {
      cancelled = true
    }
  }, [runId, router])

  if (error) {
    return (
      <div className="shell py-16">
        <p className="eyebrow">Studio Brief</p>
        <h1 className="mt-3 text-section font-semibold text-ink">This brief is not available.</h1>
        <p className="prose-body mt-4 text-body text-muted">{error}</p>
        <div className="mt-7">
          <PrimaryButton href="/">Start new research</PrimaryButton>
        </div>
      </div>
    )
  }

  if (!result) {
    return (
      <div className="shell py-16" aria-busy>
        <div className="skeleton h-4 w-28 rounded" />
        <div className="skeleton mt-4 h-10 w-80 rounded" />
        <div className="skeleton mt-8 h-40 rounded-xl" />
      </div>
    )
  }

  const { report, plan, research_metadata: meta } = result

  return (
    <SourceMapProvider sources={report.sources}>
      <article className="shell py-14 sm:py-16">
        <BriefHeader result={result} />

        {report.executive_summary ? (
          <section className="mt-12 border-t border-line pt-8">
            <p className="eyebrow">Executive summary</p>
            <p className="prose-body mt-4 text-body text-ink">{report.executive_summary}</p>
          </section>
        ) : null}

        {report.key_opportunities.length > 0 ? (
          <section className="mt-10">
            <p className="eyebrow">Headlines</p>
            <ul className="mt-4 space-y-2.5">
              {report.key_opportunities.map((item) => (
                <li key={item} className="flex gap-3 text-body text-ink">
                  <span aria-hidden className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-gold" />
                  <span className="prose-body">{item}</span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}

        <div className="mt-14 space-y-12">
          <BriefSection
            number="01"
            title="Comparable Projects"
            count={report.comparable_titles.length}
            note={report.section_notes.comparable_titles}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.comparable_titles.map((item, index) => (
                <ComparableCard key={`${item.title}-${index}`} item={item} />
              ))}
            </div>
          </BriefSection>

          <BriefSection
            number="02"
            title="Market Landscape"
            count={report.market_signals.length}
            note={report.section_notes.market_signals}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.market_signals.map((item, index) => (
                <InsightCard
                  key={`${item.signal}-${index}`}
                  heading={item.signal}
                  body={item.detail}
                  metric={item.metric}
                  trend={item.trend}
                  evidenceIds={item.evidence_ids}
                />
              ))}
            </div>
          </BriefSection>

          <BriefSection
            number="03"
            title="Audience Intelligence"
            count={report.audience_insights.length}
            note={report.section_notes.audience_insights}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.audience_insights.map((item, index) => (
                <InsightCard
                  key={`${item.insight}-${index}`}
                  heading={item.insight}
                  body={item.detail}
                  evidenceIds={item.evidence_ids}
                />
              ))}
            </div>
          </BriefSection>

          <BriefSection
            number="04"
            title="Competitive Landscape"
            count={report.competitive_landscape.length}
            note={report.section_notes.competitive_landscape}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.competitive_landscape.map((item, index) => (
                <InsightCard
                  key={`${item.observation}-${index}`}
                  heading={item.observation}
                  body={item.detail}
                  footerLabel="Gap or opportunity"
                  footer={item.gap_or_opportunity}
                  evidenceIds={item.evidence_ids}
                />
              ))}
            </div>
          </BriefSection>

          <BriefSection
            number="05"
            title="Production Opportunities"
            count={report.production_opportunities.length}
            note={report.section_notes.production_opportunities}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.production_opportunities.map((item, index) => (
                <OpportunityCard key={`${item.title}-${index}`} item={item} />
              ))}
            </div>
          </BriefSection>

          <BriefSection
            number="06"
            title="Risks & Considerations"
            count={report.risks.length}
            note={report.section_notes.risks}
          >
            <div className="grid gap-4 md:grid-cols-2">
              {report.risks.map((item, index) => (
                <RiskCard key={`${item.title}-${index}`} item={item} />
              ))}
            </div>
          </BriefSection>

          {report.next_steps.length > 0 ? (
            <section className="border-t border-line pt-8">
              <div className="flex items-baseline gap-4">
                <span className="text-support font-medium tabular-nums text-gold-deep">07</span>
                <h2 className="text-section font-semibold text-ink">Recommended Next Steps</h2>
              </div>
              <ol className="mt-5 space-y-4">
                {report.next_steps.map((step, index) => (
                  <li key={`${step.step}-${index}`} className="surface p-5 sm:p-6">
                    <p className="text-support font-semibold text-ink">
                      <span className="mr-2 tabular-nums text-gold-deep">
                        {String(index + 1).padStart(2, '0')}
                      </span>
                      {step.step}
                    </p>
                    {step.rationale ? (
                      <p className="prose-body mt-2 text-support text-muted">{step.rationale}</p>
                    ) : null}
                  </li>
                ))}
              </ol>
            </section>
          ) : null}

          {report.evidence_gaps.length > 0 ? (
            <section className="border-t border-line pt-8">
              <div className="flex items-baseline gap-4">
                <span className="text-support font-medium tabular-nums text-gold-deep">08</span>
                <h2 className="text-section font-semibold text-ink">What We Could Not Confirm</h2>
              </div>
              <p className="prose-body mt-3 max-w-prose text-support text-muted">
                Stated plainly rather than filled in — these are the questions the live search did
                not answer.
              </p>
              <ul className="mt-5 space-y-2.5">
                {report.evidence_gaps.map((gap) => (
                  <li key={gap} className="flex gap-3 text-support text-ink">
                    <span aria-hidden className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-line" />
                    <span className="prose-body">{gap}</span>
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          <BriefSection
            number="09"
            title="Sources"
            count={report.sources.length}
            emptyMessage="No sources were retrieved, so nothing above is evidenced."
          >
            <p className="prose-body mb-5 max-w-prose text-support text-muted">
              {plural(report.sources.length, 'page')} retrieved from the live web. Every citation
              above links to one of them.
            </p>
            <SourceList sources={report.sources} />
          </BriefSection>
        </div>

        <ResearchTrail plan={plan} meta={meta} />
      </article>
    </SourceMapProvider>
  )
}

/** How the brief was produced. Collapsed, but never hidden. */
function ResearchTrail({
  plan,
  meta,
}: {
  plan: ResearchResult['plan']
  meta: ResearchResult['research_metadata']
}) {
  const summary = [
    `Planned by ${plan.generated_by}`,
    `synthesized by ${meta.synthesizer}`,
    plural(meta.queries_run, 'query', 'queries'),
    durationLabel(meta.total_duration_ms),
  ].filter(Boolean) as string[]

  return (
    <details className="mt-14 border-t border-line pt-8">
      <summary className="cursor-pointer text-support font-medium text-ink">
        How this brief was researched
        <span className="ml-2 font-normal text-muted">{summary.join(' · ')}</span>
      </summary>

      {plan.reasoning ? (
        <p className="prose-body mt-4 max-w-prose text-support text-muted">{plan.reasoning}</p>
      ) : null}

      <ul className="mt-5 divide-y divide-line/70">
        {plan.tasks.map((task) => (
          <li key={task.id} className="flex flex-wrap items-baseline gap-x-3 gap-y-1 py-3">
            <span className="text-label uppercase tracking-wider text-muted/80">
              {categoryLabel(task.category)}
            </span>
            <span className="min-w-0 flex-1 text-support text-ink">{task.query}</span>
            <span className="text-support tabular-nums text-muted">
              {task.error ? 'failed' : plural(task.result_count ?? 0, 'result')}
              {task.duration_ms ? ` · ${durationLabel(task.duration_ms)}` : ''}
            </span>
            <span className="w-full">
              <Citations ids={task.evidence_ids} />
            </span>
          </li>
        ))}
      </ul>
    </details>
  )
}
