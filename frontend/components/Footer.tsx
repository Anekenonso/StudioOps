import Logo from './Logo'

/** Partner attribution, kept present but quiet. No account or marketing links. */
export default function Footer() {
  return (
    <footer className="mt-24 border-t border-line bg-canvas">
      <div className="shell flex flex-col gap-6 py-10 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Logo />
          <p className="mt-3 max-w-sm text-support text-muted">
            Research a film, series, or entertainment project against the live web and turn the
            findings into a decision-ready brief.
          </p>
        </div>

        <div className="flex flex-col gap-2 sm:items-end">
          <p className="text-support font-medium text-ink">Powered by Gemini + Parallel</p>
          <p className="text-support text-muted">
            Gemini plans and analyses · Parallel searches the live web
          </p>
        </div>
      </div>
    </footer>
  )
}
