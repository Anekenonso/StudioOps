import { categoryLabel, hostname, publishedLabel } from '../lib/format'
import type { Source } from '../lib/types'

const SNIPPET_LIMIT = 260

function trim(text: string): string {
  const clean = text.replace(/\s+/g, ' ').trim()
  if (clean.length <= SNIPPET_LIMIT) return clean
  return `${clean.slice(0, SNIPPET_LIMIT).trimEnd()}…`
}

/**
 * The evidence list. Each entry is a page the Parallel search actually returned,
 * with the excerpt it was cited from — the producer can verify every claim.
 */
export default function SourceList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) {
    return (
      <p className="text-support text-muted">
        No sources were retrieved for this run, so nothing above is evidenced.
      </p>
    )
  }

  return (
    <ol className="divide-y divide-line">
      {sources.map((source) => {
        const meta = [
          source.publisher || hostname(source.url),
          publishedLabel(source.published_date),
        ].filter(Boolean) as string[]
        const categories = Array.from(new Set(source.categories || []))

        return (
          <li key={source.id} id={`source-${source.id}`} className="scroll-mt-24 py-4 first:pt-0">
            <div className="flex items-baseline gap-3">
              <span className="flex-none rounded border border-gold/40 bg-gold-soft/60 px-1.5 py-0.5 text-label tabular-nums text-gold-deep">
                {source.id}
              </span>
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="link-underline text-support font-medium text-ink"
              >
                {source.title || hostname(source.url)}
              </a>
            </div>

            <p className="mt-1.5 pl-[3.1rem] text-support text-muted">
              {meta.join(' · ')}
              {meta.length > 0 ? ' · ' : ''}
              <span className="text-muted/80">{hostname(source.url)}</span>
            </p>

            {source.snippet ? (
              <p className="prose-body mt-2 pl-[3.1rem] text-support text-muted">
                {trim(source.snippet)}
              </p>
            ) : null}

            {categories.length > 0 ? (
              <p className="mt-2 pl-[3.1rem] text-label uppercase tracking-wider text-muted/80">
                Retrieved for {categories.map((category) => categoryLabel(category)).join(', ')}
              </p>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
