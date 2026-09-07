/**
 * The research form's state, its validation, and the mapping onto the API's
 * ProjectBrief. Kept out of the components so the input stays presentational.
 */

import { deriveTitle } from './format'
import type { ProjectBriefInput } from './types'

export interface ResearchDraft {
  description: string
  title: string
  format: string
  genre: string
  geography: string
  audience: string
  /** One research question per line. */
  questions: string
}

export const EMPTY_DRAFT: ResearchDraft = {
  description: '',
  title: '',
  format: '',
  genre: '',
  geography: '',
  audience: '',
  questions: '',
}

export const MAX_DESCRIPTION = 2000
const MIN_DESCRIPTION = 30

/** Returns a message to show the producer, or null when the draft is usable. */
export function validateDraft(draft: ResearchDraft): string | null {
  const description = draft.description.trim()
  if (!description) return 'Describe the project you want researched.'
  if (description.length < MIN_DESCRIPTION) {
    return 'Add a little more detail — a sentence or two about the project and what you want to understand.'
  }
  if (description.length > MAX_DESCRIPTION) {
    return `Trim the description to ${MAX_DESCRIPTION} characters.`
  }
  return null
}

const clean = (value: string): string | undefined => {
  const trimmed = value.trim()
  return trimmed ? trimmed : undefined
}

export function draftToBrief(draft: ResearchDraft): ProjectBriefInput {
  const description = draft.description.trim()
  return {
    title: clean(draft.title) ?? deriveTitle(description),
    description,
    format: clean(draft.format),
    genre: clean(draft.genre),
    geography: clean(draft.geography),
    target_audience: clean(draft.audience),
    research_questions: draft.questions
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean),
  }
}

/** Rebuild the form from a brief, so "Try Again" does not lose the producer's typing. */
export function briefToDraft(brief: ProjectBriefInput): ResearchDraft {
  return {
    description: brief.description || '',
    title: brief.title || '',
    format: brief.format || '',
    genre: brief.genre || '',
    geography: brief.geography || '',
    audience: brief.target_audience || '',
    questions: (brief.research_questions || []).join('\n'),
  }
}
