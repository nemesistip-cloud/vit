import { usePublicConfig } from "@/lib/usePublicConfig";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/apiClient";
import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Vote, TrendingUp, Users, ShieldCheck, RefreshCw, AlertCircle, Globe } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Link } from "wouter";
import { Skeleton } from "@/components/ui/skeleton";

interface ElectionEvent {
  id: number;
  title: string;
  country: string;
  date: string;
  status: string;
  candidates: Record<string, any>;
  sentiment_data: any;
}

export default function ElectionsPage() {
  const { data: config } = usePublicConfig();
  const [events, setEvents] = useState<ElectionEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState<number | null>(null);

  const { data: systemStats } = useQuery<any>({
    queryKey: ["system-analytics"],
    queryFn: () => apiGet("/api/analytics/system"),
  });

  const fetchEvents = async () => {
    try {
      const resp = await fetch("/api/elections/events");
      const data = await resp.json();
      setEvents(data);
    } catch (err) {
      console.error("Failed to fetch elections", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvents();
  }, []);

  const runAnalysis = async (id: number) => {
    setAnalyzing(id);
    try {
      await fetch(`/api/elections/events/${id}/analyze`, { method: "POST" });
      await fetchEvents();
    } catch (err) {
      console.error("Analysis failed", err);
    } finally {
      setAnalyzing(null);
    }
  };

  const stats = [
    { label: "Active Events", value: events.length.toString(), icon: Vote, color: "text-blue-400" },
    { label: "Intelligence Engine", value: `${config?.platform?.model_count || systemStats?.models?.active_count || 22} Models`, icon: ShieldCheck, color: "text-emerald-400" },
    { label: "AI Consensus", value: systemStats?.predictions?.avg_confidence ? `${(systemStats.predictions.avg_confidence * 100).toFixed(1)}%` : "Active", icon: TrendingUp, color: "text-purple-400" },
    { label: "Data Integrity", value: "Verified", icon: ShieldCheck, color: "text-yellow-400" },
  ];

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="flex justify-between items-start">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground uppercase">Elections & Governance</h1>
          <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Verifiable Polling & Forecast Intelligence</p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchEvents} disabled={loading} className="font-mono text-xs uppercase tracking-wider">
          <RefreshCw className={`w-3 h-3 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </Button>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <Card key={stat.label} className="bg-card/50 border-border/40 ">
            <CardContent className="p-4 flex items-center gap-4">
              <div className={`p-2 rounded-lg bg-background/50 ${stat.color}`}>
                <stat.icon className="w-5 h-5" />
              </div>
              <div>
                <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-wider">{stat.label}</p>
                <p className="text-lg font-bold font-mono">{stat.value}</p>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-6">
        {loading ? (
          <div className="space-y-6">
            {[1, 2].map(i => <Skeleton key={i} className="h-64 w-full rounded-xl" />)}
          </div>
        ) : events.map((event) => (
          <Card key={event.id} className="bg-card/50 border-border/40  overflow-hidden border-l-4 border-l-secondary hover:border-l-primary transition-all">
            <div className="p-6 border-b border-border/20 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-bold font-mono uppercase tracking-tight">{event.title}</h3>
                  <Badge variant="outline" className="font-mono text-[10px] uppercase tracking-wider">{event.country}</Badge>
                  <Badge variant="secondary" className="font-mono text-[10px] uppercase tracking-widest">{event.status}</Badge>
                </div>
                <p className="text-xs font-mono text-muted-foreground mt-1 uppercase tracking-wider">
                  Election Date: {new Date(event.date).toLocaleDateString()}
                </p>
              </div>
              <Button
                size="sm"
                className="font-mono text-xs uppercase tracking-widest"
                onClick={() => runAnalysis(event.id)}
                disabled={analyzing === event.id}
              >
                <TrendingUp className={`w-3 h-3 mr-2 ${analyzing === event.id ? 'animate-pulse' : ''}`} />
                {analyzing === event.id ? "Analyzing..." : "Refresh AI Sentiment"}
              </Button>
            </div>

            <CardContent className="p-6 grid grid-cols-1 lg:grid-cols-3 gap-6">
              <div className="lg:col-span-2 space-y-6">
                {event.sentiment_data ? (
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <h4 className="text-xs font-mono font-bold uppercase tracking-widest flex items-center gap-2">
                        <TrendingUp className="w-3 h-3 text-primary" />
                        AI Sentiment Analysis
                      </h4>
                      <span className="text-[10px] font-mono text-muted-foreground uppercase">
                        Last Updated: {new Date(event.sentiment_data.last_updated).toLocaleString()}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.entries(event.sentiment_data.scores || {}).map(([candidate, score]: [string, any]) => (
                        <div key={candidate} className="bg-background/40 p-4 rounded-lg border border-border/20">
                          <div className="flex justify-between items-end mb-2">
                            <span className="text-xs font-mono font-bold uppercase tracking-tight">{candidate}</span>
                            <span className="text-lg font-bold font-mono text-primary">{(score * 100).toFixed(1)}%</span>
                          </div>
                          <div className="w-full h-1.5 bg-background rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary transition-all duration-1000"
                              style={{ width: `${score * 100}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>

                    <div className="bg-primary/5 p-4 rounded-lg border border-primary/20">
                      <h5 className="text-[10px] font-mono font-bold uppercase text-primary mb-2 flex items-center gap-2 tracking-widest">
                        <AlertCircle className="w-3 h-3" /> AI Rationale
                      </h5>
                      <p className="text-xs font-mono leading-relaxed italic opacity-80">
                        "{event.sentiment_data.rationale}"
                      </p>
                      <div className="mt-2 text-[10px] font-mono text-muted-foreground uppercase tracking-wider">
                        Data Points Analyzed: {event.sentiment_data.data_points_analyzed}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-48 flex flex-col items-center justify-center border-2 border-dashed border-border/40 rounded-xl bg-muted/10">
                    <p className="text-xs font-mono text-muted-foreground mb-4 uppercase tracking-widest">No sentiment data available</p>
                    <Button variant="outline" size="sm" onClick={() => runAnalysis(event.id)} className="font-mono text-[10px] uppercase">
                      Run Initial Analysis
                    </Button>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <h4 className="text-xs font-mono font-bold uppercase tracking-widest">Candidates</h4>
                <div className="space-y-2">
                  {Object.keys(event.candidates).map((name) => (
                    <div key={name} className="flex items-center gap-3 p-2 bg-background/30 rounded border border-border/10">
                      <div className="w-8 h-8 rounded bg-primary/10 flex items-center justify-center text-[10px] font-bold font-mono">
                        {name.split(' ').map(n => n[0]).join('')}
                      </div>
                      <span className="text-xs font-mono uppercase tracking-tight">{name}</span>
                    </div>
                  ))}
                </div>
                <div className="pt-4 mt-4 border-t border-border/20">
                  <Link href={`/predictions?market_id=${event.id}`}>
                    <Button className="w-full font-mono text-[10px] uppercase gap-2 bg-secondary text-secondary-foreground hover:bg-secondary/90 tracking-widest">
                      Predict Outcome <TrendingUp className="w-3 h-3" />
                    </Button>
                  </Link>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {!loading && events.length === 0 && (
          <div className="text-center py-24 bg-card/20 rounded-3xl border border-dashed border-border/40">
            <Vote className="w-12 h-12 text-muted-foreground/20 mx-auto mb-4" />
            <h3 className="text-lg font-mono font-bold uppercase tracking-tight">No Election Events</h3>
            <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Seed events via admin panel</p>
          </div>
        )}
      </div>
    </div>
  );
}
