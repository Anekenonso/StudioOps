/** Presentation helpers. Nothing here invents data it was not given. */

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

/** "2026-09-06T…" -> "SEPTEMBER 2026" for the brief metadata line. */
export function researchedLabel(iso?: string | null): string | null {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return `Researched ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

/** "2026-01-02" -> "2 January 2026". Returns null when the date is unknown. */
export function publishedLabel(value?: string | null): string | null {
  if (!value) return null
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return `${date.getDate()} ${MONTHS[date.getMonth()]} ${date.getFullYear()}`
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function durationLabel(ms?: number | null): string | null {
  if (!ms || ms < 0) return null
  if (ms < 1000) return `${ms} ms`
  const seconds = ms / 1000
  return seconds < 60 ? `${seconds.toFixed(1)}s` : `${Math.round(seconds / 60)} min`
}

/** "1 query" / "3 queries" — pass the irregular plural when "+s" is wrong. */
export function plural(count: number, singular: string, pluralForm?: string): string {
  return `${count} ${count === 1 ? singular : pluralForm || `${singular}s`}`
}

/** Short human label for a research category. */
export const CATEGORY_LABELS: Record<string, string> = {
  comparables: 'Comparables',
  market: 'Market',
  audience: 'Audience',
  competition: 'Competition',
  production: 'Production',
  distribution: 'Distribution',
  developments: 'Industry news',
  other: 'Industry press',
}

export function categoryLabel(category?: string | null): string {
  if (!category) return CATEGORY_LABELS.other
  return CATEGORY_LABELS[category] || category.replace(/_/g, ' ')
}

/**
 * Derive a working project title from free-text when the producer did not give
 * one. Kept obviously mechanical — the first clause, trimmed — so it reads as a
 * label rather than an invented name.
 */
export function deriveTitle(description: string): string {
  const text = description.replace(/\s+/g, ' ').trim()
  if (!text) return 'Untitled project'

  const firstClause = text.split(/(?<=[.!?])\s|[—–:;]/)[0] || text
  const words = firstClause
    .replace(/^(we|i|our team)\b[’']?(re| are| am)?\s*/i, '')
    .replace(/^(developing|making|producing|working on|building)\s+/i, '')
    .replace(/^(a|an|the)\s+/i, '')
    .split(' ')
    .filter(Boolean)

  const title = words.slice(0, 8).join(' ').replace(/[,.;:]$/, '')
  if (!title) return 'Untitled project'
  return title.charAt(0).toUpperCase() + title.slice(1)
}

export function trendSymbol(trend?: string | null): string | null {
  if (trend === 'up') return '↑'
  if (trend === 'down') return '↓'
  if (trend === 'flat') return '→'
  return null
}

export function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ')
}
