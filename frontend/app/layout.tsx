import type { Metadata } from 'next'

import './globals.css'

import Footer from '../components/Footer'
import Header from '../components/Header'

export const metadata: Metadata = {
  title: 'StudioOps — Production Intelligence',
  description:
    'Turn a film or TV idea into an evidenced production intelligence brief, researched from the live web.',
  applicationName: 'StudioOps',
  openGraph: {
    title: 'StudioOps — Production Intelligence',
    description:
      'Turn a film or TV idea into an evidenced production intelligence brief, researched from the live web.',
    type: 'website',
  },
  icons: { icon: '/favicon.ico' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        {/*
          Inter is loaded from a stylesheet rather than next/font so an offline
          container build cannot fail; the CSS font stack falls back to system UI.
        */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
        />
      </head>
      <body>
        <div className="flex min-h-screen flex-col">
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  )
}
