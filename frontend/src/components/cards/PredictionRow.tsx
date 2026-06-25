import React from 'react';
import './PredictionRow.css';

interface PredictionRowProps {
  homeTeam: string;
  awayTeam: string;
  competition: string;
  kickoff: string;      // "87'" for live, "19:30" for upcoming
  isLive?: boolean;
  odds: string | number;
  oddsChange?: number;   // positive/negative/null
  onTap?: () => void;
  badgeLabel?: string;   // "0 Fees" | "2X Boost" etc
}

export default function PredictionRow({
  homeTeam,
  awayTeam,
  competition,
  kickoff,
  isLive,
  odds,
  oddsChange,
  onTap,
  badgeLabel,
}: PredictionRowProps) {
  const oddsUp = oddsChange && oddsChange > 0;
  const oddsDown = oddsChange && oddsChange < 0;

  return (
    <button className="prediction-row" onClick={onTap} aria-label={`${homeTeam} vs ${awayTeam}, open prediction`}>
      <div className="prediction-row__teams">
        <span className="prediction-row__match">
          {homeTeam} <span className="prediction-row__vs">vs</span> {awayTeam}
        </span>
        <span className="prediction-row__meta">
          {competition}
          {badgeLabel && (
            <span className="prediction-row__badge">{badgeLabel}</span>
          )}
        </span>
      </div>

      <div className="prediction-row__right">
        <span className="prediction-row__time" aria-label={isLive ? `${kickoff} minutes` : kickoff}>
          {isLive && <span className="prediction-row__live-dot" aria-hidden="true" />}
          {kickoff}
        </span>
        <span
          className={`prediction-row__odds ${oddsUp ? 'prediction-row__odds--up' : ''} ${oddsDown ? 'prediction-row__odds--down' : ''}`}
          aria-label={`Odds ${odds}${oddsChange ? `, changed ${oddsChange > 0 ? 'up' : 'down'} ${Math.abs(oddsChange)}%` : ''}`}
        >
          {oddsChange && (
            <span className="prediction-row__odds-change" aria-hidden="true">
              {oddsUp ? '+' : ''}{oddsChange}%
            </span>
          )}
          {odds}
        </span>
      </div>
    </button>
  );
}
