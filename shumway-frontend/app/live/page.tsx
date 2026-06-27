'use client'

import { Sidebar } from '@/components/sidebar'
import { api, LiveScoreResult } from '@/lib/api'
import { formatPercent } from '@/lib/utils'
import { useState } from 'react'
import { Search, Loader2 } from 'lucide-react'

function riskTierFromProbability(p: number): 'LOW' | 'ELEVATED' | 'HIGH' {
  if (p >= 0.6) return 'HIGH'
  if (p >= 0.3) return 'ELEVATED'
  return 'LOW'
}

const RISK_DOT: Record<string, string> = {
  LOW: '#1BD488',
  ELEVATED: '#F9CA24',
  HIGH: '#BF0404',
}

const FEATURE_LABELS: Record<string, string> = {
  profitability: 'Profitability',
  leverage: 'Leverage',
  interest_coverage: 'Interest Coverage Ratio',
  cf_divergence: 'CF Divergence',
  roe: 'Return on Equity',
}

export default function LiveLookupPage() {
  const [ticker, setTicker] = useState('')
  const [result, setResult] = useState<LiveScoreResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (!ticker.trim()) return

    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const data = await api.liveScore(ticker.trim().toUpperCase())
      setResult(data)
    } catch (err) {
      setError(`Could not fetch live data for "${ticker}". Try a format like TCS.NS or YESBANK.NS.`)
    } finally {
      setLoading(false)
    }
  }

  const riskTier = result ? riskTierFromProbability(result.hazard_probability) : null

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="bg-card border-b border-border px-8 py-6 sticky top-0 z-10">
          <h1 className="text-3xl font-bold text-foreground">Live Lookup</h1>
          <p className="text-muted-foreground mt-1">
            Real-time forecast for any currently-listed NSE/BSE company, using the most recent quarterly filing
          </p>
        </div>

        <div className="px-8 py-6 max-w-2xl">
          <form onSubmit={handleSearch} className="flex gap-2 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="text"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                placeholder="e.g. TCS.NS, YESBANK.NS, VEDL.NS"
                className="w-full pl-9 pr-3 py-3 text-sm rounded-lg border border-border bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-3 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Search'}
            </button>
          </form>

          {error && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 text-sm text-destructive mb-6">
              {error}
            </div>
          )}

          {result && riskTier && (
            <div className="space-y-6">
              <div className="bg-card border border-border rounded-lg p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h2 className="text-xl font-bold text-foreground">{result.ticker}</h2>
                    <p className="text-xs text-muted-foreground font-mono mt-1">
                      As of {result.as_of_quarter} · {result.features_available}/5 features available
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: RISK_DOT[riskTier] }} />
                    <span className="text-sm font-semibold text-foreground">{riskTier}</span>
                  </div>
                </div>

                <p className="text-4xl font-bold font-mono text-primary">
                  {formatPercent(result.hazard_probability)}
                </p>
                <p className="text-xs text-muted-foreground mt-2">Forecast hazard probability</p>

                <p className="text-xs text-muted-foreground mt-4 leading-relaxed border-t border-border pt-4">
                  {result.note}
                </p>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {Object.entries(result.features).map(([key, value]) => (
                  <div key={key} className="rounded-lg border border-border p-4 bg-card">
                    <p className="text-xs text-muted-foreground font-medium mb-2">{FEATURE_LABELS[key] ?? key}</p>
                    <p className="text-lg font-mono font-semibold text-foreground">
                      {value !== null ? value.toFixed(3) : 'N/A'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  )
}