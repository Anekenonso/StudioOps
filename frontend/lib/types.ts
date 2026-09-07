/**
 * Types mirroring the FastAPI response models in backend/models/.
 *
 * Optional/nullable fields are typed as such deliberately: the backend leaves a
 * field null rather than inventing a value, and the UI must render that absence
 * honestly instead of printing "unknown" as if it were data.
 */

export type Stage = 'intake' | 'plan' | 'search' | 'collect' | 'synthesize' | 'report'
export type EventStatus = 'active' | 'done' | 'error' | 'info'
export type RunState = 'running' | 'completed' | 'partial' | 'failed'
export type GeneratedBy = 'gemini' | 'fallback'

export interface ProgressEvent {
  run_id: string
  stage: Stage
  status: EventStatus
  message: string
  at: string
  /** Present on plan/search/collect/report events. */
  tasks?: PlanTask[]
  task_id?: string
  category?: string
  query?: string
  result_count?: number
  planner?: GeneratedBy
  reasoning?: string
  unique_sources?: number
  duplicates_removed?: number
  queries_run?: number
  queries_failed?: number
  results?: number
  run_status?: RunState
  sources?: number
  duration_ms?: number
  model?: string | null
  reason?: string
  title?: string
}

export interface CompleteEvent {
  stage: 'complete'
  status: RunState
  run_id: string
  error: string | null
}

export interface ProjectBriefInput {
  title: string
  description: string
  format?: string
  genre?: string
  target_audience?: string
  geography?: string
  budget_tier?: string
  production_stage?: string
  research_questions?: string[]
}

export interface PlanTask {
  id: string
  category: string
  question: string
  query: string
  label: string
  result_count?: number
  duration_ms?: number
  evidence_ids?: string[]
  error?: string | null
}

export interface ResearchPlan {
  reasoning: string
  generated_by: GeneratedBy
  tasks: PlanTask[]
}

export interface Source {
  id: string
  title: string
  url: string
  publisher?: string | null
  published_date?: string | null
  snippet: string
  excerpts: string[]
  categories: string[]
  queries: string[]
  relevance: number
}

interface Cited {
  evidence_ids: string[]
}

export interface ComparableTitle extends Cited {
  title: string
  year?: string | null
  genre?: string | null
  market?: string | null
  insight: string
}

export interface MarketSignal extends Cited {
  signal: string
  detail: string
  metric?: string | null
  trend?: 'up' | 'down' | 'flat' | null
}

export interface AudienceInsight extends Cited {
  insight: string
  detail: string
}

export interface CompetitiveInsight extends Cited {
  observation: string
  detail: string
  gap_or_opportunity?: string | null
}

export interface Opportunity extends Cited {
  title: string
  category?: string | null
  detail: string
}

export interface Risk extends Cited {
  title: string
  severity: 'low' | 'medium' | 'high'
  explanation: string
  recommended_action: string
}

export interface NextStep {
  step: string
  rationale: string
}

export interface SectionNote {
  insufficient_evidence: boolean
  note: string
}

export type SectionKey =
  | 'comparable_titles'
  | 'market_signals'
  | 'audience_insights'
  | 'competitive_landscape'
  | 'production_opportunities'
  | 'risks'

export interface StudioBrief {
  executive_summary: string
  key_opportunities: string[]
  comparable_titles: ComparableTitle[]
  market_signals: MarketSignal[]
  audience_insights: AudienceInsight[]
  competitive_landscape: CompetitiveInsight[]
  production_opportunities: Opportunity[]
  risks: Risk[]
  next_steps: NextStep[]
  evidence_gaps: string[]
  sources: Source[]
  section_notes: Partial<Record<SectionKey, SectionNote>>
  generated_by: GeneratedBy
}

export interface ProjectSummary {
  title: string
  format?: string | null
  genre?: string | null
  geography?: string | null
  target_audience?: string | null
  researched_at?: string | null
}

export interface ResearchMetadata {
  queries_run: number
  queries_failed: number
  sources_reviewed: number
  unique_sources: number
  search_duration_ms: number
  synthesis_duration_ms: number
  total_duration_ms: number
  planner: GeneratedBy
  synthesizer: GeneratedBy
  warnings: string[]
}

export interface ResearchResult {
  status: RunState
  run_id: string
  project: ProjectSummary
  plan: ResearchPlan
  report: StudioBrief
  research_metadata: ResearchMetadata
  report_url_json?: string | null
  report_url_md?: string | null
  message?: string | null
}

export interface RunStatus {
  run_id: string
  status: RunState
  created_at: string
  finished_at?: string | null
  error?: string | null
  error_stage?: string | null
  event_count: number
  stages: Partial<Record<Stage, EventStatus>>
  result?: ResearchResult
}

export interface IntegrationStatus {
  configured: boolean
  detail: string
  mode?: string
  model?: string
}

export interface ConfigStatus {
  parallel: IntegrationStatus
  gemini: IntegrationStatus
}
