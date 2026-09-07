import Link from 'next/link'
import type { ReactNode } from 'react'

import { classNames } from '../lib/format'

type Variant = 'primary' | 'secondary' | 'ghost'
type Size = 'md' | 'lg'

interface BaseProps {
  children: ReactNode
  variant?: Variant
  size?: Size
  fullWidth?: boolean
  className?: string
}

interface ButtonProps extends BaseProps {
  href?: undefined
  onClick?: () => void
  type?: 'button' | 'submit'
  disabled?: boolean
  loading?: boolean
}

interface LinkProps extends BaseProps {
  href: string
  external?: boolean
  download?: boolean
}

const BASE =
  'group relative inline-flex items-center justify-center gap-2 rounded-lg font-medium ' +
  'transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-out ' +
  'disabled:cursor-not-allowed disabled:opacity-55'

const VARIANTS: Record<Variant, string> = {
  primary:
    'bg-gold text-navy shadow-[0_1px_2px_rgba(23,23,23,0.08)] hover:bg-gold-deep hover:text-white ' +
    'active:translate-y-[1px]',
  secondary:
    'border border-line bg-card text-ink hover:border-ink/25 hover:bg-canvas active:translate-y-[1px]',
  ghost: 'text-muted hover:text-ink',
}

const SIZES: Record<Size, string> = {
  md: 'h-10 px-4 text-[0.9375rem]',
  lg: 'h-[3.25rem] px-7 text-base',
}

function styles(props: BaseProps): string {
  return classNames(
    BASE,
    VARIANTS[props.variant ?? 'primary'],
    SIZES[props.size ?? 'md'],
    props.fullWidth && 'w-full',
    props.className,
  )
}

/** The single call-to-action primitive: gold for the main action, quieter otherwise. */
export default function PrimaryButton(props: ButtonProps | LinkProps) {
  if ('href' in props && props.href !== undefined) {
    const { href, external, download, children } = props
    if (external || download) {
      return (
        <a
          href={href}
          className={styles(props)}
          download={download}
          {...(external ? { target: '_blank', rel: 'noreferrer noopener' } : {})}
        >
          {children}
        </a>
      )
    }
    return (
      <Link href={href} className={styles(props)}>
        {children}
      </Link>
    )
  }

  const { onClick, type = 'button', disabled, loading, children } = props
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={styles(props)}
    >
      {loading ? (
        <span
          aria-hidden
          className="h-3.5 w-3.5 animate-spin rounded-full border-[1.5px] border-current border-t-transparent"
        />
      ) : null}
      {children}
    </button>
  )
}
