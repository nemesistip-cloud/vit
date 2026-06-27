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
    <AppShell>
      <div className="p-4 space-y-6">
        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/40 font-display">Category Pills</h2>
          <CategoryPills
            items={categories}
            activeId={activeCategory}
            onSelect={setActiveCategory}
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/40 font-display">Metric Cards</h2>
          <div className="grid grid-cols-2 gap-4">
            <MetricCard
              label="Treasury Balance"
              value="12,450.00"
              change="12.5%"
              changePositive={true}
              icon={<Database size={16} />}
            />
            <MetricCard
              label="Alpha Yield"
              value="+50.20"
              change="5.2%"
              changePositive={true}
              icon={<TrendingUp size={16} />}
            />
          </div>
          <MetricCard
            variant="hero"
            label="Aggregate XP"
            value="85,240"
            subtitle="Tier: Oracle of Node 14"
          />
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/40 font-display">Signal Rows</h2>
          <div className="bg-card rounded-lg border border-white/5 overflow-hidden">
            <PredictionRow
              homeTeam="Arsenal"
              awayTeam="Man City"
              competition="Premier League"
              kickoff="87'"
              odds="2.45"
            />
            <PredictionRow
              homeTeam="Real Madrid"
              awayTeam="Barcelona"
              competition="La Liga"
              kickoff="19:30"
              odds="1.95"
            />
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-bold uppercase tracking-widest text-muted-foreground/40 font-display">Skeletons</h2>
          <CardSkeleton />
          <div className="bg-card rounded-lg border border-white/5 overflow-hidden">
            <RowSkeleton />
            <RowSkeleton />
          </div>
        </section>
      </div>
    </AppShell>
  );
}
