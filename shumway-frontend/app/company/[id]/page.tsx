import { Sidebar } from '@/components/sidebar'
import { RiskBadge } from '@/components/risk-badge'
import { api } from '@/lib/api'
import { formatCompanyName, formatPercent } from '@/lib/utils'
import { AlertCircle } from 'lucide-react'
import { ProbabilityChart } from '@/components/probability-chart'

const STATUS_COLORS: Record<string, string> = {
  GREEN: 'border-l-success bg-success/5',
  AMBER: 'border-l-warning bg-warning/5',
  RED: 'border-l-destructive bg-destructive/5',
  UNKNOWN: 'border-l-border bg-muted/30',
}

interface Props {
  params: Promise<{ id: string }>
}

export default async function CompanyDetailPage({ params }: Props) {
  const { id: companyId } = await params

  // ... rest of the function uses `companyId` exactly as before

  const [dashboard, signalsData, historyData] = await Promise.all([
    api.dashboard(companyId).catch(() => null),
    api.signals(companyId).catch(() => ({ signals: [] })),
    api.history(companyId).catch(() => ({ history: [] })),
  ])

  if (!dashboard || !dashboard.score) {
    return (
      <div className="flex h-screen">
        <Sidebar />
        <main className="flex-1 flex items-center justify-center">
          <div className="text-center">
            <h2 className="text-2xl font-bold text-foreground">Company not found</h2>
            <p className="text-muted-foreground mt-2">No data available for "{companyId}".</p>
          </div>
        </main>
      </div>
    )
  }

  const { score, known_distress_event } = dashboard
  const riskTier = score.risk_tier as 'LOW' | 'ELEVATED' | 'HIGH'
  const signals = signalsData.signals ?? []
  const history = [...(historyData.history ?? [])].reverse().map(h => ({
    year: h.quarter,
    probability: h.hazard_probability,
  }))

  const riskBarColor = riskTier === 'HIGH' ? 'bg-destructive' : riskTier === 'ELEVATED' ? 'bg-warning' : 'bg-success'

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <div className="bg-card border-b border-border px-8 py-6 sticky top-0 z-10">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-3xl font-bold text-foreground">{formatCompanyName(companyId)}</h1>
              <p className="text-muted-foreground mt-1 font-mono text-sm">{companyId}</p>
              <p className="text-muted-foreground mt-1">
                Forecast: probability of distress in FY{Number(score.quarter) + 1}
              </p>
            </div>
            <RiskBadge level={riskTier} />
          </div>
        </div>

        <div className="px-8 py-6 space-y-6">
          {/* Documented distress event banner */}
          {known_distress_event && (
            <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 text-sm text-destructive">
              <span className="font-semibold">Documented distress event</span> — {known_distress_event.event_type}:{' '}
              {known_distress_event.source_note}
            </div>
          )}

          {/* Key Metrics */}
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-card border border-border rounded-lg p-6">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Forecast Probability</p>
              <div className="mt-4 space-y-3">
                <p className="text-4xl font-bold font-mono text-primary">{formatPercent(score.hazard_probability)}</p>
                <div className="w-full bg-muted rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full transition-all ${riskBarColor}`}
                    style={{ width: `${score.hazard_probability * 100}%` }}
                  />
                </div>
              </div>
            </div>

            <div className="bg-card border border-border rounded-lg p-6">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Red Signal Count</p>
              <p className="text-4xl font-bold text-destructive mt-4">{score.red_signal_count}</p>
              <p className="text-sm text-muted-foreground mt-2">Distress indicators detected</p>
            </div>

            <div className="bg-card border border-border rounded-lg p-6">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Score Change (YoY)</p>
              <p className="text-2xl font-bold text-foreground mt-4">
                {score.score_delta != null
                  ? `${score.score_delta > 0 ? '+' : ''}${(score.score_delta * 100).toFixed(1)}pp`
                  : '—'}
              </p>
              <p className="text-sm text-muted-foreground mt-2">FY{score.quarter}</p>
            </div>
          </div>

          {/* Historical Probability */}
          <div className="bg-card border border-border rounded-lg p-6">
            <h2 className="text-lg font-semibold text-foreground mb-4">Forecast Probability Trend</h2>
            <ProbabilityChart data={history} />
          </div>

          {/* Real signals from the API */}
          {signals.length > 0 && (
            <div className="bg-card border border-border rounded-lg p-6">
              <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                <AlertCircle className="w-5 h-5 text-destructive" />
                Signals
              </h2>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {signals.map((sig) => (
                  <div
                    key={sig.name}
                    className={`rounded-lg border border-border border-l-4 p-4 ${STATUS_COLORS[sig.status] ?? STATUS_COLORS.UNKNOWN}`}
                  >
                    <p className="text-xs text-muted-foreground font-medium leading-tight mb-2">{sig.name}</p>
                    <p className="text-xl font-mono font-semibold text-foreground">
                      {sig.value !== null ? `${sig.value.toFixed(3)}${sig.unit ? ` ${sig.unit}` : ''}` : 'N/A'}
                    </p>
                    <p className="text-xs text-muted-foreground mt-1 leading-relaxed">{sig.description}</p>
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