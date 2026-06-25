import React from 'react';
import './Skeleton.css';

export function RowSkeleton() {
  return (
    <div className="skeleton-row" aria-hidden="true">
      <div className="skeleton skeleton--circle" style={{ width: 36, height: 36 }} />
      <div className="skeleton-row__body">
        <div className="skeleton skeleton--text" style={{ width: '60%' }} />
        <div className="skeleton skeleton--text" style={{ width: '40%', height: 10 }} />
      </div>
      <div className="skeleton skeleton--badge" />
    </div>
  );
}

export function CardSkeleton() {
  return (
    <div className="skeleton-card" aria-hidden="true">
      <div className="skeleton skeleton--text" style={{ width: '40%', height: 10 }} />
      <div className="skeleton skeleton--text" style={{ width: '70%', height: 28 }} />
      <div className="skeleton skeleton--text" style={{ width: '30%', height: 10 }} />
    </div>
  );
}
