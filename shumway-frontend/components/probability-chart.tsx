'use client'

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { formatPercent } from '@/lib/utils'

interface Props {
  data: { year: string; probability: number }[]
}

export function ProbabilityChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
        <XAxis dataKey="year" stroke="var(--color-muted-foreground)" />
        <YAxis stroke="var(--color-muted-foreground)" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '0.75rem',
          }}
          formatter={(value: any) => [formatPercent(value), 'Forecast Probability']}
        />
        <ReferenceLine y={0.3} stroke="var(--color-warning)" strokeDasharray="5 5" label="Elevated" />
        <ReferenceLine y={0.6} stroke="var(--color-destructive)" strokeDasharray="5 5" label="High" />
        <Line
          type="monotone"
          dataKey="probability"
          stroke="var(--color-primary)"
          dot={{ fill: 'var(--color-primary)', r: 5 }}
          strokeWidth={3}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}