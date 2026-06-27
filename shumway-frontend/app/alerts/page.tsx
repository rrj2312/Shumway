import { Sidebar } from '@/components/sidebar'
import { RiskBadge } from '@/components/risk-badge'
import { api } from '@/lib/api'
import { formatCompanyName } from '@/lib/utils'
import { AlertCircle, Zap, TrendingDown } from 'lucide-react'

const severityColors: Record<string, string> = {
  warning: 'text-warning',
  critical: 'text-destructive',
}

const severityToRiskBadge: Record<string, 'LOW' | 'ELEVATED' | 'HIGH'> = {
  warning: 'ELEVATED',
  critical: 'HIGH',
}

export default async function AlertsPage() {
  const alerts = await api.alerts(100).catch(() => [])

  const criticalAlerts = alerts.filter(a => a.severity === 'critical').length
  const warningAlerts = alerts.filter(a => a.severity === 'warning').length

  const sorted = [...alerts].sort((a, b) => {
    const severityOrder: Record<string, number> = { critical: 0, warning: 1 }
    if (severityOrder[a.severity] !== severityOrder[b.severity]) {
      return severityOrder[a.severity] - severityOrder[b.severity]
    }
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="bg-card border-b border-border px-8 py-6 sticky top-0 z-10">
          <h1 className="text-3xl font-bold text-foreground">Alerts</h1>
          <p className="text-muted-foreground mt-1">Threshold crossings from the latest scoring run</p>
        </div>

        <div className="px-8 py-6 grid grid-cols-3 gap-4">
          <div className="bg-card border border-border rounded-lg p-6">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Total Alerts</p>
            <p className="text-3xl font-bold text-foreground mt-3">{alerts.length}</p>
            <p className="text-xs text-muted-foreground mt-2">Most recent scan</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-6">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Critical Severity</p>
            <p className="text-3xl font-bold text-destructive mt-3">{criticalAlerts}</p>
            <p className="text-xs text-muted-foreground mt-2">Require attention</p>
          </div>
          <div className="bg-card border border-border rounded-lg p-6">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Warning Severity</p>
            <p className="text-3xl font-bold text-warning mt-3">{warningAlerts}</p>
            <p className="text-xs text-muted-foreground mt-2">Being monitored</p>
          </div>
        </div>

        <div className="px-8 py-6">
          <div className="mb-4">
            <h2 className="text-xl font-semibold text-foreground">Recent Alerts</h2>
            <p className="text-sm text-muted-foreground">Sorted by severity and recency</p>
          </div>

          <div className="space-y-3">
            {sorted.map((alert, idx) => (
              <div
                key={`${alert.company_id}-${alert.signal}-${idx}`}
                className="bg-card border border-border rounded-lg p-4 hover:border-primary/30 transition-colors"
              >
                <div className="flex items-start gap-4">
                  <div className={`mt-1 p-2 rounded-lg ${alert.severity === 'critical' ? 'bg-destructive/10' : 'bg-warning/10'}`}>
                    <AlertCircle className={`w-5 h-5 ${severityColors[alert.severity]}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="font-semibold text-foreground">{alert.signal.replace(/_/g, ' ')}</p>
                        <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
                        <p className="text-xs text-muted-foreground mt-2">
                          {formatCompanyName(alert.company_id)} •{' '}
                          {new Date(alert.created_at).toLocaleString('en-IN')}
                        </p>
                      </div>
                      <RiskBadge level={severityToRiskBadge[alert.severity]} className="flex-shrink-0" />
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  )
}