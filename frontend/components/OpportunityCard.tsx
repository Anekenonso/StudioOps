import { categoryLabel } from '../lib/format'
import type { Opportunity } from '../lib/types'
import Citations from './Citations'

/** A production or distribution opportunity the evidence supports. */
export default function OpportunityCard({ item }: { item: Opportunity }) {
  return (
    <article className="surface p-5 transition-shadow duration-200 hover:shadow-lift sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-cardtitle font-semibold text-ink">{item.title}</h3>
        {item.category ? (
          <span className="flex-none rounded border border-line px-1.5 py-0.5 text-label uppercase tracking-wider text-muted">
            {categoryLabel(item.category)}
          </span>
        ) : null}
      </div>
      <p className="prose-body mt-2.5 text-support text-muted">{item.detail}</p>
      <Citations ids={item.evidence_ids} />
    </article>
  )
}
