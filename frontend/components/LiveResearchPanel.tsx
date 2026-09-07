import { categoryLabel, classNames, plural } from '../lib/format'
import type { RunView, SearchActivity } from '../lib/useResearchRun'

interface Props {
  view: RunView
  streamLost?: boolean
}

/**
 * The live research log. Every row is a query the backend actually planned, and
 * its state comes from real search events — nothing here is simulated.
 */
export default function LiveResearchPanel({ view, streamLost = false }: Props) {
  const { activities } = view

  return (
    <section className="surface overflow-hidden">
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-5 py-4 sm:px-6">
        <div className="flex items-center gap-2.5">
          <span aria-hidden className="relative flex h-2 w-2">
            {!view.searchDone ? (
              <span className="absolute inset-0 animate-pulse-ring rounded-full bg-gold/50" />
            ) : null}
            <span
              className={classNames(
                'h-2 w-2 rounded-full',
                view.searchDone ? 'bg-gold-deep' : 'bg-gold',
              )}
            />
          </span>
          <h2 className="text-cardtitle font-semibold text-ink">Live web research</h2>
        </div>
        <p className="text-support text-muted">
          {activities.length > 0
            ? `${plural(activities.length, 'query', 'queries')} planned`
            : 'Planning queries…'}
        </p>
      </header>

      <div className="px-5 py-4 sm:px-6">
        {view.reasoning ? (
          <p className="mb-4 max-w-prose text-support text-muted">{view.reasoning}</p>
        ) : null}

        {activities.length === 0 ? (
          <ul className="space-y-2.5" aria-hidden>
            {[0, 1, 2].map((row) => (
              <li key={row} className="skeleton h-12 rounded-lg" />
            ))}
          </ul>
        ) : (
          <ul className="divide-y divide-line/70">
            {activities.map((activity) => (
              <ActivityRow key={activity.id} activity={activity} />
            ))}
          </ul>
        )}

        <Footnote view={view} streamLost={streamLost} />
      </div>
    </section>
  )
}

function ActivityRow({ activity }: { activity: SearchActivity }) {
  return (
    <li className="flex items-start gap-3 py-3 animate-fade-in">
      <StateDot state={activity.state} />
      <div className="min-w-0 flex-1">
        <p className="text-support font-medium text-ink">{activity.label}</p>
        {activity.query ? (
          <p className="mt-0.5 truncate text-support text-muted" title={activity.query}>
            {activity.query}
          </p>
        ) : null}
      </div>
      <div className="flex flex-none flex-col items-end gap-0.5">
        <span className="text-label uppercase tracking-wider text-muted/80">
          {categoryLabel(activity.category)}
        </span>
        <span
          className={classNames(
            'text-support tabular-nums',
            activity.state === 'failed' ? 'text-alert' : 'text-muted',
          )}
        >
          {activity.state === 'done'
            ? plural(activity.resultCount ?? 0, 'result')
            : activity.state === 'searching'
              ? 'Searching…'
              : activity.state === 'failed'
                ? 'No results'
                : 'Queued'}
        </span>
      </div>
    </li>
  )
}

function StateDot({ state }: { state: SearchActivity['state'] }) {
  if (state === 'done') {
    return (
      <span
        aria-hidden
        className="mt-1 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-gold-soft text-[0.7rem] font-semibold text-gold-deep"
      >
        ✓
      </span>
    )
  }
  if (state === 'failed') {
    return (
      <span
        aria-hidden
        className="mt-1 flex h-5 w-5 flex-none items-center justify-center rounded-full bg-alert-soft text-[0.7rem] font-semibold text-alert"
      >
        —
      </span>
    )
  }
  if (state === 'searching') {
    return (
      <span
        aria-hidden
        className="relative mt-1 flex h-5 w-5 flex-none items-center justify-center"
      >
        <span className="absolute inset-0 animate-pulse-ring rounded-full bg-gold/25" />
        <span className="h-2 w-2 rounded-full bg-gold" />
      </span>
    )
  }
  return (
    <span
      aria-hidden
      className="mt-1 flex h-5 w-5 flex-none items-center justify-center rounded-full border border-line"
    >
      <span className="h-1.5 w-1.5 rounded-full bg-line" />
    </span>
  )
}

function Footnote({ view, streamLost }: { view: RunView; streamLost: boolean }) {
  const parts: string[] = []
  if (typeof view.totalResults === 'number') {
    parts.push(`${plural(view.totalResults, 'result')} retrieved`)
  }
  if (typeof view.uniqueSources === 'number') {
    parts.push(plural(view.uniqueSources, 'unique source'))
  }
  if (view.duplicatesRemoved) {
    parts.push(`${view.duplicatesRemoved} duplicates removed`)
  }

  if (parts.length === 0 && !streamLost) return null

  return (
    <div className="mt-4 border-t border-line/70 pt-3.5">
      {parts.length > 0 ? (
        <p className="text-support text-muted">{parts.join(' · ')}</p>
      ) : null}
      {streamLost ? (
        <p className="mt-1 text-support text-muted">
          Live updates paused — still checking on the run.
        </p>
      ) : null}
    </div>
  )
}
