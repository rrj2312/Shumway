'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState } from 'react'
import { cn } from '@/lib/utils'
import { formatCompanyName } from '@/lib/utils'
import { api } from '@/lib/api'
import { TrendingDown, AlertCircle, Home, Search, Zap } from 'lucide-react'

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<string[]>([])
  const [showResults, setShowResults] = useState(false)

  const items = [
    {
      href: '/live',
      label: 'Live Lookup',
      icon: Zap,
      active: pathname === '/live',
    },
    {
      href: '/',
      label: 'Watchlist',
      icon: Home,
      active: pathname === '/',
    },
    {
      href: '/alerts',
      label: 'Alerts',
      icon: AlertCircle,
      active: pathname === '/alerts',
    },
  ]

  async function handleSearch(value: string) {
    setQuery(value)
    if (value.trim().length < 2) {
      setResults([])
      setShowResults(false)
      return
    }
    try {
      const matches = await api.search(value.trim())
      setResults(matches)
      setShowResults(true)
    } catch {
      setResults([])
    }
  }

  function goToCompany(companyId: string) {
    setQuery('')
    setResults([])
    setShowResults(false)
    router.push(`/company/${companyId}`)
  }

  return (
    <aside className="w-64 bg-sidebar border-r border-sidebar-border h-screen flex flex-col sticky top-0">
      {/* Logo */}
      <div className="px-6 py-8 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
            <h1 className="text-4xl font-bold text-sidebar-foreground" style={{ fontFamily: 'var(--font-gredibel)', color: '#1bd488', letterSpacing: '0.07em' }}>
              Shumway
            </h1>
          </div>
        </div>

      {/* Search */}
      <div className="px-4 py-4 border-b border-sidebar-border relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            type="text"
            value={query}
            onChange={(e) => handleSearch(e.target.value)}
            onFocus={() => results.length > 0 && setShowResults(true)}
            onBlur={() => setTimeout(() => setShowResults(false), 150)}
            placeholder="Search companies..."
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg border border-sidebar-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
          />
        </div>

        {showResults && results.length > 0 && (
          <div className="absolute left-4 right-4 mt-1 bg-card border border-border rounded-lg shadow-lg max-h-64 overflow-auto z-50">
            {results.map((id) => (
              <button
                key={id}
                onMouseDown={() => goToCompany(id)}
                className="w-full text-left px-3 py-2 text-sm text-foreground hover:bg-muted/50 transition-colors"
              >
                {formatCompanyName(id)}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-4 py-6 space-y-2">
        {items.map(item => {
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-4 py-3 rounded-lg transition-colors',
                item.active
                  ? 'bg-sidebar-primary text-sidebar-primary-foreground'
                  : 'text-sidebar-foreground hover:bg-sidebar-accent'
              )}
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-6 py-6 border-t border-sidebar-border">
        <div className="flex items-center gap-3 px-3 py-3 rounded-lg bg-sidebar-accent">
          <div className="w-10 h-10 bg-primary/10 rounded-full flex items-center justify-center">
            <span className="text-xs font-bold text-primary">SF</span>
          </div>
          <div>
            <p className="text-sm font-medium text-sidebar-foreground">Shumway</p>
            <p className="text-xs text-muted-foreground">Admin</p>
          </div>
        </div>
      </div>
    </aside>
  )
}