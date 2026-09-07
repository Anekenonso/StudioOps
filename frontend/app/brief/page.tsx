import { Suspense } from 'react'

import BriefView from '../../components/BriefView'

export const dynamic = 'force-dynamic'

export const metadata = { title: 'Studio Brief — StudioOps' }

export default function BriefPage() {
  return (
    <Suspense fallback={<Loading />}>
      <BriefView />
    </Suspense>
  )
}

function Loading() {
  return (
    <div className="shell py-16" aria-busy>
      <div className="skeleton h-4 w-28 rounded" />
      <div className="skeleton mt-4 h-10 w-80 rounded" />
      <div className="skeleton mt-8 h-40 rounded-xl" />
    </div>
  )
}
