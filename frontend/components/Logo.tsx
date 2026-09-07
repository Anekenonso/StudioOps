/** StudioOps wordmark. Two lines on desktop, one on mobile. */
export default function Logo({ compact = false }: { compact?: boolean }) {
  return (
    <span className="inline-flex flex-col leading-none">
      <span className="text-[1.0625rem] font-semibold tracking-[-0.025em] text-ink">
        Studio<span className="text-gold-deep">Ops</span>
      </span>
      {!compact ? (
        <span className="mt-[5px] text-[0.5625rem] font-medium uppercase tracking-[0.2em] text-muted">
          Production Intelligence
        </span>
      ) : null}
    </span>
  )
}
