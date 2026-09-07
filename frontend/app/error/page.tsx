import { Suspense } from 'react'

import ErrorView from '../../components/ErrorView'

export const dynamic = 'force-dynamic'

export const metadata = { title: 'Research stopped — StudioOps' }

export default function ErrorPage() {
  return (
    <Suspense fallback={<div className="shell py-20" />}>
      <ErrorView />
    </Suspense>
  )
}
