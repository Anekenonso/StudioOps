'use client'

import { createContext, useContext, useMemo } from 'react'

import { hostname } from '../lib/format'
import type { Source } from '../lib/types'

const SourceMapContext = createContext<Map<string, Source>>(new Map())

/** Makes the run's sources resolvable by id anywhere inside the brief. */
export function SourceMapProvider({
  sources,
  children,
}: {
  sources: Source[]
  children: React.ReactNode
}) {
  const map = useMemo(
    () => new Map(sources.map((source) => [source.id, source])),
    [sources],
  )
  return <SourceMapContext.Provider value={map}>{children}</SourceMapContext.Provider>
}

export function useSourceMap() {
  return useContext(SourceMapContext)
}

/**
 * The evidence trail under a claim. An id the backend could not resolve renders
 * as plain text rather than a dead link — better a visible gap than a fake one.
 */
export default function Citations({ ids }: { ids?: string[] }) {
  const map = useSourceMap()
  const unique = Array.from(new Set(ids || []))
  if (unique.length === 0) return null

  return (
    <p className="mt-3 flex flex-wrap items-center gap-1.5">
      <span className="text-label uppercase tracking-wider text-muted/80">Sources</span>
      {unique.map((id) => {
        const source = map.get(id)
        if (!source) {
          return (
            <span
              key={id}
              className="rounded border border-line px-1.5 py-0.5 text-label tabular-nums text-muted"
            >
              {id}
            </span>
          )
        }
        return (
          <a
            key={id}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            title={`${source.title} — ${source.publisher || hostname(source.url)}`}
            className="rounded border border-gold/40 bg-gold-soft/60 px-1.5 py-0.5 text-label tabular-nums text-gold-deep transition-colors duration-200 hover:border-gold hover:bg-gold-soft"
          >
            {id}
          </a>
        )
      })}
    </p>
  )
}
