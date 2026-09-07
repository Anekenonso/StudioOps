'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

import { classNames } from '../lib/format'
import Logo from './Logo'

const NAV = [
  { label: 'New Research', href: '/' },
  { label: 'About', href: '/#how-it-works' },
]

/**
 * Desktop: wordmark left, two links right. Mobile: hamburger + wordmark only.
 * No account icon anywhere — V1 has no accounts.
 */
export default function Header() {
  const pathname = usePathname()
  const [open, setOpen] = useState(false)

  // Close the sheet on navigation so it never lingers over a new screen.
  useEffect(() => setOpen(false), [pathname])

  return (
    <header className="sticky top-0 z-40 border-b border-line bg-canvas/85 backdrop-blur-md">
      <div className="shell flex h-16 items-center justify-between gap-4 sm:h-[4.5rem]">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
            aria-controls="mobile-nav"
            aria-label={open ? 'Close menu' : 'Open menu'}
            className="-ml-1 flex h-9 w-9 items-center justify-center rounded-md text-ink transition-colors hover:bg-line/60 md:hidden"
          >
            <svg width="18" height="14" viewBox="0 0 18 14" aria-hidden fill="none">
              {open ? (
                <>
                  <path d="M2 2l14 10" stroke="currentColor" strokeWidth="1.6" />
                  <path d="M16 2L2 12" stroke="currentColor" strokeWidth="1.6" />
                </>
              ) : (
                <>
                  <path d="M0 1.5h18" stroke="currentColor" strokeWidth="1.6" />
                  <path d="M0 7h18" stroke="currentColor" strokeWidth="1.6" />
                  <path d="M0 12.5h18" stroke="currentColor" strokeWidth="1.6" />
                </>
              )}
            </svg>
          </button>

          <Link href="/" className="rounded-sm" aria-label="StudioOps home">
            <span className="hidden md:block">
              <Logo />
            </span>
            <span className="block md:hidden">
              <Logo compact />
            </span>
          </Link>
        </div>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className={classNames(
                'rounded-md px-3 py-2 text-support text-muted transition-colors duration-200 hover:bg-line/50 hover:text-ink',
                item.href === '/' && pathname === '/' && 'text-ink',
              )}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>

      {/* Mobile sheet */}
      <div
        id="mobile-nav"
        hidden={!open}
        className="animate-fade-in border-t border-line bg-card md:hidden"
      >
        <nav className="shell flex flex-col py-2">
          {NAV.map((item) => (
            <Link
              key={item.label}
              href={item.href}
              className="border-b border-line/70 py-3 text-body text-ink last:border-0"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
