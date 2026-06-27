'use client'

import Link from 'next/link'
import { useState } from 'react'
import { WatchlistEntry } from '@/lib/api'
import { formatCompanyName, formatPercent } from '@/lib/utils'

interface WatchlistTableProps {
  companies: WatchlistEntry[]
}

type SortField = 'company_id' | 'hazard_probability' | 'red_signal_count'
type SortOrder = 'asc' | 'desc'

const RISK_DOTS: Record<string, string> = {
  LOW: '#1BD488',
  ELEVATED: '#F9CA24',
  HIGH: '#BF0404',
}

export function WatchlistTable({ companies: initialCompanies }: WatchlistTableProps) {
  const [sortField, setSortField] = useState<SortField>('hazard_probability')
  const [sortOrder, setSortOrder] = useState<SortOrder>('desc')

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortOrder('desc')
    }
  }

  const sorted = [...initialCompanies].sort((a, b) => {
    let aValue: any = a[sortField]
    let bValue: any = b[sortField]
    if (sortField === 'company_id') {
      aValue = a.company_id.toLowerCase()
      bValue = b.company_id.toLowerCase()
    }
    if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1
    if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1
    return 0
  })

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return <span className="opacity-0">↑</span>
    return <span>{sortOrder === 'asc' ? '↑' : '↓'}</span>
  }

  return (
    <div className="rounded-lg border-2 border-border bg-card overflow-hidden shadow-md">
      <div className="px-6 py-4 bg-success border-b-2 border-border">
        <h3 className="font-semibold text-foreground flex items-center gap-2">
          <span className="inline-block w-3 h-3 bg-foreground rounded-full"></span>
          Watchlist
        </h3>
      </div>
      <table className="w-full">
        <thead>
          <tr className="border-b border-border bg-muted">
            <th className="px-6 py-3 text-left text-xs font-semibold text-foreground">
              <button onClick={() => handleSort('company_id')} className="hover:text-secondary transition-colors">
                Company <SortIcon field="company_id" />
              </button>
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-foreground font-mono">
              Basis Year
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-foreground font-mono">
              <button onClick={() => handleSort('hazard_probability')} className="hover:text-secondary transition-colors">
                Forecast Probability <SortIcon field="hazard_probability" />
              </button>
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-foreground">
              Risk Tier
            </th>
            <th className="px-6 py-3 text-left text-xs font-semibold text-foreground font-mono">
              <button onClick={() => handleSort('red_signal_count')} className="hover:text-secondary transition-colors">
                Red Signal Count <SortIcon field="red_signal_count" />
              </button>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(company => (
            <tr key={company.company_id} className="border-b border-border hover:bg-success/5 transition-colors">
              <td className="px-6 py-4 text-sm font-medium text-foreground">
                <Link href={`/company/${company.company_id}`} className="hover:text-primary transition-colors">
                  {formatCompanyName(company.company_id)}
                </Link>
              </td>
              <td className="px-6 py-4 text-sm font-mono text-foreground">
                FY{company.quarter}
              </td>
              <td className="px-6 py-4">
                <span className="font-mono text-sm font-semibold text-foreground">
                  {formatPercent(company.hazard_probability)}
                </span>
              </td>
              <td className="px-6 py-4">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: RISK_DOTS[company.risk_tier] }} />
                  <span className="text-xs font-semibold text-foreground">{company.risk_tier}</span>
                </div>
              </td>
              <td className="px-6 py-4 text-sm font-mono text-foreground">
                {company.red_signal_count}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}