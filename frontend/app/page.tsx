import ResearchWorkspace from '../components/ResearchWorkspace'
import WorkflowSteps from '../components/WorkflowSteps'

export default function Home() {
  return (
    <div className="shell py-14 sm:py-20">
      <section className="max-w-prose animate-fade-up">
        <p className="eyebrow">Film &amp; TV production intelligence</p>
        <h1 className="mt-4 text-hero font-semibold tracking-tight text-ink">
          Turn an idea into a production intelligence brief.
        </h1>
        <p className="prose-body mt-5 text-body text-muted">
          Describe your project. StudioOps plans the research, searches the live web, and returns a
          structured brief — every claim traced to a source you can open.
        </p>
      </section>

      <div className="mt-10 sm:mt-12">
        <ResearchWorkspace />
      </div>

      <div className="mt-20 sm:mt-28">
        <WorkflowSteps />
      </div>
    </div>
  )
}
