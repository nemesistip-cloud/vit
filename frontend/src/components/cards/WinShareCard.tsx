import React from 'react';
import './WinShareCard.css';

interface WinShareCardProps {
  streakCount: number;
  titleUnlocked?: string;
  predictionLabel: string;
  pnlPercent: string | number;
  pnlPositive?: boolean;
  referralCode?: string;
  onShare?: () => void;
}

export default function WinShareCard({
  streakCount,
  titleUnlocked,
  predictionLabel,
  pnlPercent,
  pnlPositive = true,
  referralCode,
  onShare,
}: WinShareCardProps) {
  return (
    <article className="win-share-card" aria-label={`${streakCount}-win streak share card`}>
      <div className="win-share-card__header">
        <span className="win-share-card__logo" aria-hidden="true">◆ VIT NETWORK</span>
        <time className="win-share-card__date" dateTime={new Date().toISOString()}>
          {new Date().toLocaleDateString('en-NG', { year: 'numeric', month: '2-digit', day: '2-digit' })}
        </time>
      </div>

      <div className="win-share-card__hero">
        <div className="win-share-card__streak">
          <span className="win-share-card__streak-number" aria-label={`${streakCount}-win streak`}>
            {streakCount}-Win
          </span>
          <span className="win-share-card__streak-label">Streak</span>
        </div>
        <div className="win-share-card__character" aria-hidden="true">
          {/* Prophecy Chain character art — inject from Merit tier */}
        </div>
      </div>

      {titleUnlocked && (
        <div className="win-share-card__title">
          <span className="win-share-card__title-label">Title Unlocked</span>
          <span className="win-share-card__title-name">{titleUnlocked}</span>
        </div>
      )}

      <div className="win-share-card__pnl">
        <span className="win-share-card__pnl-label">Closed Prediction</span>
        <span className="win-share-card__pnl-match">{predictionLabel}</span>
        <span
          className={`win-share-card__pnl-value ${pnlPositive ? 'win-share-card__pnl-value--pos' : 'win-share-card__pnl-value--neg'}`}
          aria-label={`${pnlPositive ? 'profit' : 'loss'} ${pnlPercent}`}
        >
          {pnlPositive ? '+' : ''}{pnlPercent}%
        </span>
      </div>

      {referralCode && (
        <div className="win-share-card__referral">
          <div>
            <strong>Referral Code {referralCode}</strong>
            <p>Sign up for 500 VIT + zero-fee predictions</p>
          </div>
        </div>
      )}

      <button className="win-share-card__share-btn" onClick={onShare} aria-label="Share win card">
        Share Win
      </button>
    </article>
  );
}
