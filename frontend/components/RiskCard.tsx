import { classNames } from '../lib/format'
import type { Risk } from '../lib/types'
import Citations from './Citations'

const SEVERITY_STYLES: Record<string, string> = {
  high: 'border-alert/40 bg-alert-soft text-alert',
  medium: 'border-gold/40 bg-gold-soft text-gold-deep',
  low: 'border-line bg-canvas text-muted',
}

/** A risk with its severity and the action the evidence suggests. */
export default function RiskCard({ item }: { item: Risk }) {
  const severity = SEVERITY_STYLES[item.severity] ? item.severity : 'medium'

  return (
    <article className="surface p-5 transition-shadow duration-200 hover:shadow-lift sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-cardtitle font-semibold text-ink">{item.title}</h3>
        <span
          className={classNames(
            'flex-none rounded border px-1.5 py-0.5 text-label uppercase tracking-wider',
            SEVERITY_STYLES[severity],
          )}
        >
          {severity} risk
        </span>
      </div>

      <p className="prose-body mt-2.5 text-support text-muted">{item.explanation}</p>

      {item.recommended_action ? (
        <p className="mt-4 border-t border-line pt-3.5 text-support text-ink">
          <span className="text-label uppercase tracking-wider text-muted/80">
            Recommended action
          </span>
          <span className="mt-1 block">{item.recommended_action}</span>
        </p>
      ) : null}

      <Citations ids={item.evidence_ids} />
    </article>
  )
}
