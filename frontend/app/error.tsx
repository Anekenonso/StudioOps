'use client'

import PrimaryButton from '../components/PrimaryButton'

/**
 * The render-time error boundary. It deliberately shows generic copy: the caught
 * error may contain internals a producer should never see.
 */
export default function AppError({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="shell py-20 sm:py-24">
      <div className="max-w-prose">
        <p className="eyebrow">Something went wrong</p>
        <h1 className="mt-4 text-hero font-semibold tracking-tight text-ink">
          This screen didn&apos;t load.
        </h1>
        <p className="prose-body mt-5 text-body text-muted">
          Nothing was lost. Reload this view, or start a new research run.
        </p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <PrimaryButton onClick={reset}>Reload</PrimaryButton>
          <PrimaryButton href="/" variant="secondary">
            New research
          </PrimaryButton>
        </div>
      </div>
    </div>
  )
}
