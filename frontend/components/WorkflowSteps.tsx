const STEPS = [
  {
    number: '01',
    title: 'Understand the Brief',
    body: 'Gemini understands your project, goals, audience, and research requirements.',
  },
  {
    number: '02',
    title: 'Research the Web',
    body: 'Parallel searches the live web for relevant entertainment intelligence.',
  },
  {
    number: '03',
    title: 'Analyze & Synthesize',
    body: 'StudioOps identifies signals, patterns, opportunities, and risks.',
  },
  {
    number: '04',
    title: 'Generate Studio Brief',
    body: 'Receive a structured, actionable brief with supporting sources.',
  },
]

/** The four-step product explanation shown below the research workspace. */
export default function WorkflowSteps() {
  return (
    <section id="how-it-works" className="scroll-mt-24">
      <div className="max-w-prose">
        <p className="eyebrow">How StudioOps works</p>
        <h2 className="mt-3 text-section font-semibold text-ink">
          Four steps from an idea to an evidenced brief.
        </h2>
      </div>

      <ol className="mt-10 grid gap-px overflow-hidden rounded-xl border border-line bg-line sm:grid-cols-2 lg:grid-cols-4">
        {STEPS.map((step) => (
          <li key={step.number} className="group bg-card p-6 transition-colors duration-200 hover:bg-canvas lg:p-7">
            <div className="flex items-center gap-3">
              <span className="text-support font-medium tabular-nums text-gold-deep">
                {step.number}
              </span>
              <span className="h-px flex-1 bg-line transition-colors duration-200 group-hover:bg-gold/50" />
            </div>
            <h3 className="mt-5 text-cardtitle font-semibold text-ink">{step.title}</h3>
            <p className="mt-2.5 text-support text-muted">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
