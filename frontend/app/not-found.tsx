import PrimaryButton from '../components/PrimaryButton'

export const metadata = { title: 'Not found — StudioOps' }

export default function NotFound() {
  return (
    <div className="shell py-20 sm:py-24">
      <div className="max-w-prose">
        <p className="eyebrow">404</p>
        <h1 className="mt-4 text-hero font-semibold tracking-tight text-ink">
          There is nothing here.
        </h1>
        <p className="prose-body mt-5 text-body text-muted">
          The page you asked for does not exist. Start a research run instead.
        </p>
        <div className="mt-8">
          <PrimaryButton href="/">New research</PrimaryButton>
        </div>
      </div>
    </div>
  )
}
