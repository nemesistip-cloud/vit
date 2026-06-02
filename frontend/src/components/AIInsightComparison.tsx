import React from 'react';
import { Sparkles, BrainCircuit, Zap, CheckCircle2 } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Progress } from './ui/progress';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/apiClient';

interface Insight {
  summary: string;
  key_factors: string[];
  recommendation: string;
  confidence: number;
}

interface InsightsMap {
  native?: Insight;
}

interface AIInsightComparisonProps {
  matchId: string;
}

export const AIInsightComparison: React.FC<AIInsightComparisonProps> = ({ matchId }) => {
  const { data, isLoading } = useQuery<any>({
    queryKey: ["ai-insights", matchId],
    queryFn: () => apiGet(\`/api/predict/\${matchId}/insights\`),
    enabled: !!matchId,
  });

  if (isLoading) return <div className="p-8 text-center">Analyzing match via native ensemble...</div>;

  const native = data?.native;

  return (
    <div className="grid grid-cols-1 gap-6">
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="flex flex-row items-center space-x-3">
          <Sparkles className="h-6 w-6 text-primary" />
          <div>
            <CardTitle className="text-xl">Native Ensemble Analytics</CardTitle>
            <p className="text-sm text-muted-foreground">Blockchain-verified internal model consensus</p>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {native ? (
            <>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Ensemble Confidence</span>
                  <span>{(native.confidence * 100).toFixed(1)}%</span>
                </div>
                <Progress value={native.confidence * 100} className="h-2" />
              </div>
              <p className="text-sm leading-relaxed">{native.summary}</p>
              <div className="space-y-1">
                {native.key_factors && native.key_factors.map((f: string, i: number) => (
                  <div key={i} className="flex items-start space-x-2 text-xs text-muted-foreground">
                    <CheckCircle2 className="h-3 w-3 mt-0.5 text-primary" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 p-3 rounded-lg bg-primary/10 border border-primary/20">
                <p className="text-xs font-semibold text-primary uppercase tracking-wider mb-1">Recommendation</p>
                <p className="text-sm font-medium">{native.recommendation}</p>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground italic">No native analytics available for this match yet.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
