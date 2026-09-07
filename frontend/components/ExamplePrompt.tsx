'use client'

import { classNames } from '../lib/format'

/** A single "try an example" pill. Clicking it fills the research input. */
export default function ExamplePrompt({
  label,
  onSelect,
  active = false,
}: {
  label: string
  onSelect: () => void
  active?: boolean
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={classNames(
        'rounded-full border px-3.5 py-2 text-support transition-all duration-200 ease-out',
        active
          ? 'border-gold bg-gold-soft text-ink'
          : 'border-line bg-card text-muted hover:-translate-y-[1px] hover:border-gold/60 hover:text-ink',
      )}
    >
      {label}
    </button>
  )
}
