import React from 'react';
import './MetricCard.css';

interface MetricCardProps {
  label: string;
  value: string | number;
  change?: string | number;
  changePositive?: boolean;
  subtitle?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'hero' | 'compact';
}

export default function MetricCard({
  label,
  value,
  change,
  changePositive,
  subtitle,
  icon,
  variant = 'default',
}: MetricCardProps) {
  return (
    <div className={`metric-card metric-card--${variant}`} role="region" aria-label={label}>
      {icon && <span className="metric-card__icon" aria-hidden="true">{icon}</span>}
      <div className="metric-card__body">
        <span className="metric-card__label">{label}</span>
        <span className="metric-card__value data">{value}</span>
        {change && (
          <span
            className={`metric-card__change ${changePositive ? 'metric-card__change--pos' : 'metric-card__change--neg'}`}
            aria-label={`${changePositive ? 'up' : 'down'} ${change}`}
          >
            {changePositive ? '▲' : '▼'} {change}
          </span>
        )}
        {subtitle && <span className="metric-card__subtitle">{subtitle}</span>}
      </div>
    </div>
  );
}
