import { cn } from '@/lib/utils'

interface RiskBadgeProps {
  level: 'LOW' | 'ELEVATED' | 'HIGH'
  className?: string
}

export function RiskBadge({ level, className }: RiskBadgeProps) {
  const styles = {
    LOW:      'bg-success/10 text-success border border-success/20',
    ELEVATED: 'bg-warning/10 text-warning border border-warning/20',
    HIGH:     'bg-destructive/10 text-destructive border border-destructive/20',
  }

  const labels = {
    LOW: 'Low Risk',
    ELEVATED: 'Elevated Risk',
    HIGH: 'High Risk',
  }

  return (
    <span
      className={cn(
        'inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold',
        styles[level],
        className
      )}
    >
      {labels[level]}
    </span>
  )
}