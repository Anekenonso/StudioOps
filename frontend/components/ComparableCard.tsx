import type { ComparableTitle } from '../lib/types'
import Citations from './Citations'

/**
 * A comparable title. Year, genre, and market are only rendered when the
 * evidence supplied them — a missing field stays missing.
 */
export default function ComparableCard({ item }: { item: ComparableTitle }) {
  const meta = [item.year, item.genre, item.market].filter(Boolean) as string[]

  return (
    <article className="surface p-5 transition-shadow duration-200 hover:shadow-lift sm:p-6">
      <h3 className="text-cardtitle font-semibold text-ink">{item.title}</h3>
      {meta.length > 0 ? (
        <p className="mt-1.5 text-support italic text-muted">{meta.join(' · ')}</p>
      ) : null}
      <p className="prose-body mt-3 text-support text-muted">{item.insight}</p>
      <Citations ids={item.evidence_ids} />
    </article>
  )
}
