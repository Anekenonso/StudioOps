import { classNames } from '../lib/format'
import type { Step } from '../lib/useResearchRun'

/** The four-state stepper. Every state comes from a real backend event. */
export default function ResearchProgress({ steps }: { steps: Step[] }) {
  return (
    <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4" aria-label="Research progress">
      {steps.map((step) => (
        <li
          key={step.number}
          aria-current={step.state === 'active' ? 'step' : undefined}
          className={classNames(
            'flex items-center gap-3 rounded-lg border px-4 py-3.5 transition-colors duration-300',
            step.state === 'done' && 'border-gold/40 bg-gold-soft/50',
            step.state === 'active' && 'border-gold bg-card shadow-card',
            step.state === 'pending' && 'border-line bg-card/60',
            step.state === 'failed' && 'border-alert/40 bg-alert-soft/60',
          )}
        >
          <Marker state={step.state} />
          <div className="min-w-0">
            <p
              className={classNames(
                'truncate text-support font-medium',
                step.state === 'pending' ? 'text-muted' : 'text-ink',
              )}
            >
              {step.label}
            </p>
            <p className="text-label uppercase tracking-wider text-muted/80">
              {step.state === 'done'
                ? 'Complete'
                : step.state === 'active'
                  ? 'In progress'
                  : step.state === 'failed'
                    ? 'Failed'
                    : 'Waiting'}
            </p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function Marker({ state }: { state: Step['state'] }) {
  if (state === 'done') {
    return (
      <span
        aria-hidden
        className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-gold text-[0.75rem] font-semibold text-white"
      >
        ✓
      </span>
    )
  }

  if (state === 'failed') {
    return (
      <span
        aria-hidden
        className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-alert-soft text-[0.75rem] font-semibold text-alert"
      >
        !
      </span>
    )
  }

  if (state === 'active') {
    return (
      <span aria-hidden className="relative flex h-7 w-7 flex-none items-center justify-center">
        <span className="absolute inset-0 animate-pulse-ring rounded-full bg-gold/30" />
        <span className="h-2.5 w-2.5 rounded-full bg-gold" />
      </span>
    )
  }

  return (
    <span
      aria-hidden
      className="flex h-7 w-7 flex-none items-center justify-center rounded-full border border-line"
    >
      <span className="h-2 w-2 rounded-full bg-line" />
    </span>
  )
}
