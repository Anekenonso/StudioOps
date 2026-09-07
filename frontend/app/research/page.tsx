import { Suspense } from 'react'

import ResearchLive from '../../components/ResearchLive'

export const dynamic = 'force-dynamic'

export const metadata = { title: 'Researching — StudioOps' }

export default function ResearchPage() {
  return (
    <Suspense fallback={<Loading />}>
      <ResearchLive />
    </Suspense>
  )
}

function Loading() {
  return (
    <div className="shell py-14 sm:py-16">
      <div className="skeleton h-4 w-32 rounded" />
      <div className="skeleton mt-4 h-8 w-72 rounded" />
      <div className="mt-9 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((step) => (
          <div key={step} className="skeleton h-16 rounded-lg" />
        ))}
      </div>
    </div>
  )
}
