'use client'

import { useId, useState } from 'react'

import { MAX_DESCRIPTION, type ResearchDraft } from '../lib/draft'
import { EXAMPLES } from '../lib/examples'
import { classNames } from '../lib/format'
import ExamplePrompt from './ExamplePrompt'
import PrimaryButton from './PrimaryButton'

const PLACEHOLDER =
  "Example: We're developing a Nigerian crime thriller set in Lagos. Research the current market, comparable films, audience trends, potential locations, distribution opportunities, and relevant production companies."

interface Props {
  draft: ResearchDraft
  onChange: (draft: ResearchDraft) => void
  onSubmit: () => void
  submitting?: boolean
  error?: string | null
  activeExample?: string | null
  onExample: (label: string) => void
}

/** The single premium input panel: describe the project, then start research. */
export default function ResearchInput({
  draft,
  onChange,
  onSubmit,
  submitting = false,
  error = null,
  activeExample = null,
  onExample,
}: Props) {
  const [detailsOpen, setDetailsOpen] = useState(false)
  const textareaId = useId()
  const errorId = useId()

  const set = <K extends keyof ResearchDraft>(key: K, value: ResearchDraft[K]) =>
    onChange({ ...draft, [key]: value })

  const used = draft.description.length
  const nearLimit = used > MAX_DESCRIPTION * 0.9

  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
      className="surface shadow-card"
    >
      <div className="p-5 sm:p-8">
        <label htmlFor={textareaId} className="block text-cardtitle font-semibold text-ink">
          What are you working on?
        </label>
        <p className="mt-1.5 text-support text-muted">
          Describe your project and what you want to understand.
        </p>

        <div
          className={classNames(
            'mt-5 rounded-lg border bg-canvas transition-colors duration-200',
            'focus-within:border-gold/70 focus-within:bg-card',
            error ? 'border-alert/40' : 'border-line',
          )}
        >
          <textarea
            id={textareaId}
            value={draft.description}
            onChange={(event) => set('description', event.target.value.slice(0, MAX_DESCRIPTION))}
            placeholder={PLACEHOLDER}
            rows={6}
            maxLength={MAX_DESCRIPTION}
            aria-invalid={error ? true : undefined}
            aria-describedby={error ? errorId : undefined}
            className="block w-full resize-y bg-transparent p-4 text-body text-ink outline-none placeholder:text-muted/70 sm:min-h-[9.5rem]"
          />
          <div className="flex items-center justify-between gap-3 border-t border-line/80 px-4 py-2.5">
            <span className="text-support text-muted">
              Gemini reads this before any search runs.
            </span>
            <span
              className={classNames(
                'text-support tabular-nums',
                nearLimit ? 'text-gold-deep' : 'text-muted',
              )}
            >
              {used} / {MAX_DESCRIPTION}
            </span>
          </div>
        </div>

        {error ? (
          <p id={errorId} role="alert" className="mt-3 text-support text-alert">
            {error}
          </p>
        ) : null}

        <div className="mt-6">
          <p className="text-support text-muted">Try an example</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <ExamplePrompt
                key={example.label}
                label={example.label}
                active={activeExample === example.label}
                onSelect={() => onExample(example.label)}
              />
            ))}
          </div>
        </div>

        {/* Optional refinements. Collapsed by default so the main input stays the focus. */}
        <div className="mt-7 border-t border-line pt-5">
          <button
            type="button"
            onClick={() => setDetailsOpen((open) => !open)}
            aria-expanded={detailsOpen}
            className="flex items-center gap-2 text-support text-muted transition-colors hover:text-ink"
          >
            <span
              aria-hidden
              className={classNames(
                'inline-block transition-transform duration-200',
                detailsOpen && 'rotate-90',
              )}
            >
              ›
            </span>
            Add project details
            <span className="text-muted/70">— optional, sharpens the research</span>
          </button>

          {detailsOpen ? (
            <div className="mt-5 grid animate-fade-up gap-4 sm:grid-cols-2">
              <Field
                label="Project title"
                value={draft.title}
                onChange={(value) => set('title', value)}
                placeholder="Lagos After Dark"
              />
              <Field
                label="Format"
                value={draft.format}
                onChange={(value) => set('format', value)}
                placeholder="Feature Film / TV Series / Documentary"
              />
              <Field
                label="Genre"
                value={draft.genre}
                onChange={(value) => set('genre', value)}
                placeholder="Crime Thriller"
              />
              <Field
                label="Territory"
                value={draft.geography}
                onChange={(value) => set('geography', value)}
                placeholder="Nigeria"
              />
              <Field
                label="Target audience"
                value={draft.audience}
                onChange={(value) => set('audience', value)}
                placeholder="Adults 18-34"
              />
              <div className="sm:col-span-2">
                <FieldLabel>Specific questions</FieldLabel>
                <textarea
                  value={draft.questions}
                  onChange={(event) => set('questions', event.target.value)}
                  rows={3}
                  placeholder={'One per line:\nWhich platforms are buying Nigerian drama?'}
                  className="mt-1.5 block w-full resize-y rounded-lg border border-line bg-canvas p-3 text-support text-ink outline-none transition-colors duration-200 placeholder:text-muted/70 focus:border-gold/70 focus:bg-card"
                />
                <p className="mt-1.5 text-support text-muted">
                  Each question is researched directly.
                </p>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="flex flex-col gap-4 border-t border-line bg-canvas/60 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-8 sm:py-6">
        <p className="text-support text-muted">
          Typically 20–60 seconds. You will see each search as it runs.
        </p>
        <PrimaryButton
          type="submit"
          size="lg"
          loading={submitting}
          className="w-full sm:w-auto"
        >
          {submitting ? 'Starting research…' : 'Start Research →'}
        </PrimaryButton>
      </div>
    </form>
  )
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <span className="text-support font-medium text-ink">{children}</span>
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  placeholder?: string
}) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id}>
        <FieldLabel>{label}</FieldLabel>
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="mt-1.5 block h-11 w-full rounded-lg border border-line bg-canvas px-3 text-support text-ink outline-none transition-colors duration-200 placeholder:text-muted/70 focus:border-gold/70 focus:bg-card"
      />
    </div>
  )
}
