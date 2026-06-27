import { Sidebar } from '@/components/sidebar'
import { WatchlistTable } from '@/components/watchlist-table'
import { api } from '@/lib/api'

export default async function WatchlistPage() {
  const [watchlist, stats] = await Promise.all([
    api.watchlist(169).catch(() => []),
    api.stats().catch(() => null),
  ])

  const companyCount = stats?.total_companies ?? watchlist.length
  const companyYears = stats?.total_company_years ?? 0
  const distressEvents = stats?.documented_distress_events ?? 0
  const yearRange = stats ? `${stats.year_range.min}–${stats.year_range.max}` : '—'
  const disclaimer = stats?.note ??
    'Documented distress events are intentionally few — well-verified public corporate failures are rare. Reported metrics should be read directionally, not as production-grade estimates.'

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="px-8 py-8 space-y-6">
          {/* Hero Stats Grid */}
          <div className="grid grid-cols-4 gap-4">
            <div className="rounded-xl shadow-lg p-7 border-0 relative overflow-hidden" style={{ backgroundColor: '#1BD488' }}>
              <p className="text-xs font-bold uppercase tracking-wider mb-3 relative" style={{ color: '#111827' }}>Companies Tracked</p>
              <p className="text-5xl font-mono font-bold relative" style={{ color: '#111827' }}>{companyCount}</p>
              <p className="text-xs mt-4 relative font-semibold" style={{ color: '#111827' }}>Active monitoring</p>
            </div>

            <div className="bg-primary rounded-xl shadow-lg p-7 text-white relative overflow-hidden">
              <p className="text-xs font-bold text-white/90 uppercase tracking-wider mb-3">Company-Years</p>
              <p className="text-5xl font-mono font-bold">{companyYears.toLocaleString()}</p>
              <p className="text-xs text-white/80 mt-4 font-semibold">Historical data</p>
            </div>

            <div className="bg-secondary rounded-xl shadow-lg p-7 text-white relative overflow-hidden">
              <p className="text-xs font-bold text-white/90 uppercase tracking-wider mb-3">Distress Events</p>
              <p className="text-5xl font-mono font-bold">{distressEvents}</p>
              <p className="text-xs text-white/80 mt-4 font-semibold">Documented cases</p>
            </div>

            <div className="bg-white rounded-xl shadow-lg p-7 relative" style={{ borderLeft: '6px solid #1BD488' }}>
              <p className="text-xs font-bold text-foreground uppercase tracking-wider mb-3">Data Range</p>
              <p className="text-5xl font-mono font-bold text-foreground">{yearRange}</p>
              <p className="text-xs text-foreground/70 mt-4 font-semibold">Coverage period</p>
            </div>
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-muted-foreground leading-relaxed max-w-4xl px-2">
            {disclaimer}
          </p>
          <p className="text-xs text-muted-foreground leading-relaxed max-w-4xl px-2">
            "Basis Year" is the fiscal year whose financial ratios were used as model inputs. "Forecast Probability" is the predicted probability of distress in the following fiscal year.
          </p>

          {/* Table */}
          <WatchlistTable companies={watchlist} />
        </div>
      </main>
    </div>
  )
}