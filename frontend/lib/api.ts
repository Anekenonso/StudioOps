export type ResearchBrief = {
  title: string
  description: string
  format?: string
  genre?: string
  target_audience?: string
  geography?: string
  research_questions?: string[]
}

export async function submitResearch(brief: ResearchBrief) {
  const res = await fetch('/api/v1/research', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(brief),
  })
  return res.json()
}
