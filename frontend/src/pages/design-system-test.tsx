import React, { useState } from 'react';
import AppShell from '@/components/layout/AppShell';
import CategoryPills from '@/components/layout/CategoryPills';
import MetricCard from '@/components/cards/MetricCard';
import PredictionRow from '@/components/cards/PredictionRow';
import WinShareCard from '@/components/cards/WinShareCard';
import { RowSkeleton, CardSkeleton } from '@/components/skeletons/RowSkeleton';
import { Database, TrendingUp, Zap } from 'lucide-react';

export default function DesignSystemTest() {
  const [activeCategory, setActiveCategory] = useState('all');

  const categories = [
    { id: 'all', label: 'All Markets', count: 124 },
    { id: 'football', label: 'Football', count: 86 },
    { id: 'basketball', label: 'Basketball', count: 38 },
    { id: 'politics', label: 'Politics', count: 12 },
  ];

  return (
    <AppShell title="VIT DESIGN SYSTEM" showSearch={true}>
      <div className="p-4 space-y-6">
        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-vit-text-3">Category Pills</h2>
          <CategoryPills
            items={categories}
            activeId={activeCategory}
            onSelect={setActiveCategory}
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-vit-text-3">Metric Cards</h2>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="VITCoin Balance"
              value="12,450.00"
              change="12.5%"
              changePositive={true}
              icon={<Database size={16} className="text-vit-green" />}
            />
            <MetricCard
              label="Profit / Loss"
              value="+50.20"
              change="5.2%"
              changePositive={true}
              icon={<TrendingUp size={16} className="text-vit-green" />}
            />
          </div>
          <MetricCard
            variant="hero"
            label="Total Merit XP"
            value="85,240"
            subtitle="Top 2% of contributors this month"
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-vit-text-3">Prediction Rows</h2>
          <div className="bg-vit-surface rounded-lg border border-vit-border overflow-hidden">
            <PredictionRow
              homeTeam="Arsenal"
              awayTeam="Man City"
              competition="Premier League"
              kickoff="87'"
              isLive={true}
              odds="2.45"
              oddsChange={2.4}
              badgeLabel="2X BOOST"
            />
            <PredictionRow
              homeTeam="Real Madrid"
              awayTeam="Barcelona"
              competition="La Liga"
              kickoff="19:30"
              isLive={false}
              odds="1.95"
              oddsChange={-1.2}
            />
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-vit-text-3">Win Share Card</h2>
          <WinShareCard
            streakCount={5}
            titleUnlocked="Oracle of Lagos"
            predictionLabel="Arsenal vs Man City • Over 2.5 Goals"
            pnlPercent={245.5}
            referralCode="VIT_LEGEND"
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-vit-text-3">Skeletons</h2>
          <CardSkeleton />
          <div className="bg-vit-surface rounded-lg border border-vit-border overflow-hidden">
            <RowSkeleton />
            <RowSkeleton />
          </div>
        </section>
      </div>
    </AppShell>
  );
}
