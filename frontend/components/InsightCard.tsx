import { classNames, trendSymbol } from '../lib/format'
import Citations from './Citations'

interface Props {
  heading: string
  body: string
  /** A figure the source actually stated, e.g. "2x year on year". */
  metric?: string | null
  trend?: 'up' | 'down' | 'flat' | null
  footerLabel?: string
  footer?: string | null
  evidenceIds?: string[]
}

/** The general finding card: market signals, audience insights, competitive notes. */
export default function InsightCard({
  heading,
  body,
  metric,
  trend,
  footerLabel = 'Opportunity',
  footer,
  evidenceIds,
}: Props) {
  return (
    <article className="surface p-5 transition-shadow duration-200 hover:shadow-lift sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-cardtitle font-semibold text-ink">{heading}</h3>
        {trend ? (
          <span
            title={`Trend: ${trend}`}
            className={classNames(
              'flex-none rounded px-1.5 py-0.5 text-support',
              trend === 'up' && 'bg-gold-soft text-gold-deep',
              trend === 'down' && 'bg-alert-soft text-alert',
              trend === 'flat' && 'bg-navy-soft text-navy',
            )}
          >
            {trendSymbol(trend)}
          </span>
        ) : null}
      </div>

      {metric ? (
        <p className="mt-2 text-support font-medium tabular-nums text-gold-deep">{metric}</p>
      ) : null}

      <p className="prose-body mt-2.5 text-support text-muted">{body}</p>

      {footer ? (
        <p className="mt-4 border-t border-line pt-3.5 text-support text-ink">
          <span className="text-label uppercase tracking-wider text-muted/80">{footerLabel}</span>
          <span className="mt-1 block">{footer}</span>
        </p>
      ) : null}

      <Citations ids={evidenceIds} />
    </article>
  )
}
