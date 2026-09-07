'use client'

import { useState } from 'react'

import { classNames } from '../lib/format'
import type { SectionNote } from '../lib/types'

interface Props {
  number: string
  title: string
  /** How many findings the section holds — shown so a thin section is obvious. */
  count?: number
  note?: SectionNote
  emptyMessage?: string
  children: React.ReactNode
}

/**
 * A numbered brief section. Collapsible on small screens so a producer can scan
 * the whole document on a phone.
 */
export default function BriefSection({
  number,
  title,
  count,
  note,
  emptyMessage = 'The live search did not return enough evidence for this section.',
  children,
}: Props) {
  const [open, setOpen] = useState(true)
  const isEmpty = count === 0

  return (
    <section className="scroll-mt-24 border-t border-line pt-8" id={`section-${number}`}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="group flex w-full items-baseline gap-4 text-left sm:pointer-events-none"
      >
        <span className="text-support font-medium tabular-nums text-gold-deep">{number}</span>
        <span className="flex-1">
          <span className="block text-section font-semibold text-ink">{title}</span>
        </span>
        {typeof count === 'number' ? (
          <span className="hidden text-support tabular-nums text-muted sm:inline">{count}</span>
        ) : null}
        <span
          aria-hidden
          className={classNames(
            'text-muted transition-transform duration-200 sm:hidden',
            open && 'rotate-90',
          )}
        >
          ›
        </span>
      </button>

      <div className={classNames('mt-5', open ? 'block' : 'hidden sm:block')}>
        {note?.insufficient_evidence ? (
          <p className="mb-5 rounded-lg border border-line bg-canvas px-4 py-3 text-support text-muted">
            {note.note}
          </p>
        ) : null}

        {isEmpty ? (
          <p className="text-support text-muted">{note?.note || emptyMessage}</p>
        ) : (
          children
        )}
      </div>
    </section>
  )
}
