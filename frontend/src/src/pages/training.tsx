import { useEffect, useRef, useState } from "react";
import { useListTrainingJobs, useGetModelPerformance, useUploadTrainingData, API } from "@/api-client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiDelete, apiFormPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Terminal, Database, Server, Cpu, Activity, Upload, FolderOpen, GitCompare, Trash2, BookOpen, ChevronDown, ChevronUp, ExternalLink, History, Rocket, Undo2, CheckCircle2 } from "lucide-react";
import { format } from "date-fns";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, CartesianGrid } from "recharts";
import { toast } from "sonner";

export default function TrainingPage() {
  const { data: jobsData, isLoading: isJobsLoading } = useListTrainingJobs();
  const { data: performance, isLoading: isPerfLoading } = useGetModelPerformance();
  const uploadTraining = useUploadTrainingData();
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    try {
      const result = await uploadTraining.mutateAsync(fd);
      const count = result?.records_uploaded ?? result?.records_in_dataset ?? 0;
      toast.success(`Dataset uploaded — ${count} record${count === 1 ? "" : "s"} added`);
    } catch (err: any) {
      toast.error(err.message || "Upload failed");
    }
    if (fileRef.current) fileRef.current.value = "";
  };

  if (isJobsLoading || isPerfLoading) {
    return <div className="h-full flex items-center justify-center font-mono text-muted-foreground">INITIALIZING_ML_PIPELINE...</div>;
  }

  const jobs = jobsData?.jobs ?? [];
  const models = performance?.models ?? [];
  const ensembleAccuracy = performance?.ensemble_accuracy ?? performance?.accuracy_rate ?? 0;
  const totalPredictions = performance?.total_predictions ?? 0;

  // Use real model performance data only — never invent placeholder rows
  // (the previous code rendered XGBoost/LightGBM/RF/NN at 0% accuracy
  //  which looked like a real dataset). When `models` is empty the chart
  //  renders an empty state below.
  const chartData = models;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-mono font-bold uppercase tracking-tight">ML Infrastructure</h1>
        <p className="text-muted-foreground font-mono text-sm">Model training status, pipeline health, and data ingestion</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-6">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-2 border-b border-border/50">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Activity className="w-4 h-4 mr-2 text-primary" />
                Ensemble Status
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="text-center">
                <div className="text-4xl font-bold font-mono text-primary">
                  {(ensembleAccuracy * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-muted-foreground font-mono uppercase mt-1">Overall Accuracy</div>
              </div>
              <div className="bg-muted/30 rounded p-3 text-xs font-mono flex justify-between border border-border">
                <span className="text-muted-foreground">Total Predictions</span>
                <span className="font-bold">{totalPredictions.toLocaleString()}</span>
              </div>
              <div className="bg-muted/30 rounded p-3 text-xs font-mono flex justify-between border border-border">
                <span className="text-muted-foreground">Training Jobs</span>
                <span className="font-bold">{jobs.length}</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-2 border-b border-border/50">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Database className="w-4 h-4 mr-2 text-primary" />
                Upload Training Data
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <p className="text-xs font-mono text-muted-foreground">
                Upload a CSV file with match data to trigger a new training pipeline run.
              </p>
              <input
                ref={fileRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleUpload}
              />
              <Button
                className="w-full font-mono"
                variant="outline"
                onClick={() => fileRef.current?.click()}
                disabled={uploadTraining.isPending}
              >
                <Upload className="w-4 h-4 mr-2" />
                {uploadTraining.isPending ? "UPLOADING..." : "SELECT_CSV_FILE"}
              </Button>
              <div className="text-xs font-mono text-muted-foreground space-y-1 pt-2 border-t border-border/50">
                <p className="font-bold uppercase">Required columns:</p>
                <p>home_team, away_team, league, kickoff_time, home_goals, away_goals</p>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2 space-y-6">
          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-4 border-b border-border/50">
              <CardTitle className="font-mono uppercase flex items-center">
                <Cpu className="w-5 h-5 mr-2 text-primary" />
                Model Performance Matrix
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6">
              <div className="h-[250px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="hsl(var(--border))" />
                    <XAxis
                      dataKey="name"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={10}
                      tickLine={false}
                      angle={-45}
                      textAnchor="end"
                    />
                    <YAxis
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={10}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(val) => `${(val * 100).toFixed(0)}%`}
                      domain={[0, 1]}
                    />
                    <RechartsTooltip
                      cursor={{ fill: "hsl(var(--muted)/0.5)" }}
                      contentStyle={{ backgroundColor: "hsl(var(--card))", borderColor: "hsl(var(--border))", fontFamily: "var(--font-mono)", fontSize: "12px" }}
                      formatter={(val: number) => [`${(val * 100).toFixed(1)}%`, "Accuracy"]}
                    />
                    <Bar dataKey="accuracy" fill="hsl(var(--primary))" radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-card/50 backdrop-blur border-border">
            <CardHeader className="pb-4 border-b border-border/50">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Server className="w-4 h-4 mr-2" />
                Pipeline Execution Queue
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-border/50">
                {jobs.map((job) => (
                  <JobRow key={job.job_id} job={job} />
                ))}
                {jobs.length === 0 && (
                  <div className="text-center py-10 text-muted-foreground font-mono text-sm">
                    NO_JOBS_IN_QUEUE
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <TrainingGuide />

      {/* Model Version History */}
      <ModelVersionHistory />

      {/* Dataset Management (from V1 DatasetPanel) */}
      <DatasetManagement />
    </div>
  );
}

type TrainingJobRow = {
  job_id: string;
  status: string;
  created_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  models_trained?: number;
  models_failed?: number;
  avg_accuracy?: number | null;
  avg_over_under_accuracy?: number | null;
  version?: string | null;
  is_production?: boolean;
};

function JobRow({ job }: { job: TrainingJobRow }) {
  const qc = useQueryClient();
  const [progress, setProgress] = useState<{ current: number; total: number; model?: string } | null>(null);

  const isRunning = job.status === "running" || job.status === "queued";

  // SSE subscription for live progress on running/queued jobs
  useEffect(() => {
    if (!isRunning) return;
    const es = new EventSource(API.training.progress(job.job_id));
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "heartbeat") {
          setProgress({ current: data.current ?? 0, total: data.total ?? 0 });
        } else if (data.type === "model_start") {
          setProgress({ current: data.index ?? 0, total: data.total ?? 0, model: data.model });
        } else if (data.type === "stream_end" || data.type === "done") {
          es.close();
          qc.invalidateQueries({ queryKey: [API.training.jobs] });
          qc.invalidateQueries({ queryKey: [API.training.modelPerformance] });
        }
      } catch {
        // ignore malformed payloads
      }
    };
    es.onerror = () => es.close();
    return () => es.close();
  }, [isRunning, job.job_id, qc]);

  const promote = useMutation({
    mutationFn: () => apiPost(API.training.promote, { job_id: job.job_id, reason: "Manual promotion from Job board" }),
    onSuccess: () => {
      toast.success(`Job ${job.job_id.slice(0, 8)} promoted to production`);
      qc.invalidateQueries({ queryKey: [API.training.jobs] });
      qc.invalidateQueries({ queryKey: [API.training.modelPerformance] });
    },
    onError: (err: any) => toast.error(err?.message || "Promotion failed"),
  });

  const rollback = useMutation({
    mutationFn: () => apiPost(API.training.rollback, { job_id: job.job_id, reason: "Manual rollback from Job board" }),
    onSuccess: () => {
      toast.success(`Rolled back to ${job.job_id.slice(0, 8)}`);
      qc.invalidateQueries({ queryKey: [API.training.jobs] });
    },
    onError: (err: any) => toast.error(err?.message || "Rollback failed"),
  });

  const pct = progress && progress.total > 0 ? Math.round((progress.current / progress.total) * 100) : 0;

  return (
    <div className="p-4 font-mono text-sm">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 min-w-0">
          <Terminal className={`w-4 h-4 flex-shrink-0 ${isRunning ? "text-primary animate-pulse" : "text-muted-foreground"}`} />
          <div className="min-w-0">
            <div className="font-bold flex items-center gap-2">
              JOB_{job.job_id?.slice(0, 8) ?? "?"}
              {job.is_production && (
                <Badge className="text-[9px] uppercase bg-green-500/15 text-green-400 border-green-500/30">
                  <CheckCircle2 className="w-3 h-3 mr-1" /> PROD
                </Badge>
              )}
            </div>
            <div className="text-xs text-muted-foreground mt-0.5">
              {job.models_trained ? `${job.models_trained} models` : isRunning ? "training..." : "pending"}
              {job.avg_accuracy != null ? ` · ${(job.avg_accuracy * 100).toFixed(1)}% acc` : ""}
              {job.avg_over_under_accuracy != null ? ` · OU ${(job.avg_over_under_accuracy * 100).toFixed(1)}%` : ""}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="text-right">
            <Badge variant="outline" className={`text-[10px] uppercase mb-1 ${
              job.status === "completed" ? "border-secondary/50 text-secondary" :
              job.status === "failed" ? "border-destructive/50 text-destructive" :
              job.status === "running" ? "border-primary/50 text-primary" :
              "border-muted-foreground/30 text-muted-foreground"
            }`}>
              {job.status}
            </Badge>
            <div className="text-xs text-muted-foreground">
              {job.created_at ? format(new Date(job.created_at), "HH:mm:ss") : "WAITING"}
            </div>
          </div>
          {job.status === "completed" && !job.is_production && (
            <Button
              size="sm"
              variant="outline"
              className="h-7 font-mono text-[10px] uppercase border-primary/40 text-primary hover:bg-primary/10"
              onClick={() => promote.mutate()}
              disabled={promote.isPending}
            >
              <Rocket className="w-3 h-3 mr-1" />
              {promote.isPending ? "..." : "Promote"}
            </Button>
          )}
          {job.status === "completed" && !job.is_production && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 font-mono text-[10px] uppercase text-muted-foreground hover:text-foreground"
              onClick={() => rollback.mutate()}
              disabled={rollback.isPending}
              title="Roll production back to this version"
            >
              <Undo2 className="w-3 h-3 mr-1" />
              Rollback
            </Button>
          )}
        </div>
      </div>
      {isRunning && progress && progress.total > 0 && (
        <div className="mt-3 pl-8 space-y-1">
          <div className="flex justify-between text-[10px] text-muted-foreground uppercase">
            <span>{progress.model ? `Training: ${progress.model}` : "Initializing..."}</span>
            <span>{progress.current} / {progress.total} ({pct}%)</span>
          </div>
          <Progress value={pct} className="h-1.5" />
        </div>
      )}
    </div>
  );
}

function ModelVersionHistory() {
  const [expanded, setExpanded] = useState(false);
  const { data, isLoading, refetch, isFetching } = useQuery<{
    history: {
      model: string; version: number; accuracy: number | null; log_loss: number | null;
      calibration_error: number | null; total_predictions: number; evaluated_at: string | null; is_active: boolean;
    }[];
    count: number;
  }>({
    queryKey: ["model-version-history"],
    queryFn: () => apiGet("/admin/models/version-history?limit=50"),
    enabled: expanded,
    staleTime: 60 * 1000,
  });

  const history = data?.history ?? [];

  return (
    <Card className="bg-card/50 backdrop-blur border-border/50">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono uppercase flex items-center gap-2 text-sm">
            <History className="w-4 h-4 text-primary" />
            Model Version History
          </CardTitle>
          <div className="flex items-center gap-2">
            {expanded && (
              <Button variant="ghost" size="sm" className="font-mono text-xs h-7" onClick={() => refetch()} disabled={isFetching}>
                {isFetching ? "⟳" : "↺"} Refresh
              </Button>
            )}
            <Button variant="ghost" size="sm" className="font-mono text-xs" onClick={() => setExpanded(!expanded)}>
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
              {expanded ? "Collapse" : "Expand"}
            </Button>
          </div>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-4">
          {isLoading ? (
            <p className="font-mono text-xs text-muted-foreground text-center py-6">Loading version history...</p>
          ) : history.length === 0 ? (
            <p className="font-mono text-xs text-muted-foreground text-center py-6">
              No historical model snapshots found. Performance records are created after each training run.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs font-mono">
                <thead>
                  <tr className="border-b border-border/50">
                    {["Model", "Ver", "Accuracy", "LogLoss", "CalErr", "Predictions", "Evaluated", "Status"].map((h) => (
                      <th key={h} className="text-left text-muted-foreground uppercase py-2 pr-4">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {history.map((row, i) => (
                    <tr key={i} className="border-b border-border/20 hover:bg-muted/10 transition-colors">
                      <td className="py-2 pr-4 font-medium truncate max-w-[120px]">{row.model}</td>
                      <td className="py-2 pr-4 text-muted-foreground">v{row.version}</td>
                      <td className={`py-2 pr-4 font-bold ${row.accuracy && row.accuracy >= 0.65 ? "text-green-400" : row.accuracy ? "text-yellow-400" : "text-muted-foreground"}`}>
                        {row.accuracy != null ? `${(row.accuracy * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 pr-4 text-secondary">
                        {row.log_loss != null ? row.log_loss.toFixed(4) : "—"}
                      </td>
                      <td className="py-2 pr-4 text-yellow-400">
                        {row.calibration_error != null ? row.calibration_error.toFixed(4) : "—"}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {row.total_predictions > 0 ? row.total_predictions.toLocaleString() : "—"}
                      </td>
                      <td className="py-2 pr-4 text-muted-foreground">
                        {row.evaluated_at ? format(new Date(row.evaluated_at), "MMM dd HH:mm") : "—"}
                      </td>
                      <td className="py-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] ${row.is_active ? "text-green-400 border-green-400/30" : "text-muted-foreground"}`}
                        >
                          {row.is_active ? "ACTIVE" : "ARCHIVED"}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

function TrainingGuide() {
  const [expanded, setExpanded] = useState(false);

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-3 border-b border-border/50">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono uppercase flex items-center gap-2 text-sm">
            <BookOpen className="w-4 h-4 text-primary" />
            Training Guide — How to Train on Historical Match Data
          </CardTitle>
          <Button variant="ghost" size="sm" className="font-mono text-xs" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            {expanded ? "Hide" : "Show"}
          </Button>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-5 space-y-6 text-sm font-mono">

          {/* Overview */}
          <div className="p-4 bg-primary/5 border border-primary/20 rounded-lg space-y-2">
            <p className="font-bold text-primary uppercase text-xs">What training does</p>
            <p className="text-muted-foreground leading-relaxed text-xs">
              The ML ensemble trains 3–5 models (Logistic Regression, Random Forest, Gradient Boosting, XGBoost, LightGBM)
              on your historical match data. Each model learns to predict Home / Draw / Away probabilities from match odds
              and Poisson-derived features. The ensemble averages their predictions for higher accuracy and stability.
            </p>
          </div>

          {/* Step by step */}
          <div className="space-y-3">
            <p className="font-bold uppercase text-xs text-foreground">Step-by-Step</p>
            {[
              {
                step: "1",
                title: "Get historical match data",
                desc: "Download match result CSVs from a free source. Football-Data.co.uk provides season-by-season files for EPL, La Liga, Serie A, Bundesliga, Ligue 1, and more — all free.",
                link: "https://football-data.co.uk/data.php",
                linkLabel: "football-data.co.uk →",
              },
              {
                step: "2",
                title: "Prepare the CSV format",
                desc: "The system auto-detects column names. Minimum required: home_team, away_team, plus either home_goals+away_goals OR actual_outcome (H/D/A). Adding odds columns (B365H, B365D, B365A) improves accuracy significantly.",
              },
              {
                step: "3",
                title: "Upload the CSV",
                desc: 'Use the Dataset Management panel below → "Upload Data" tab. Select your CSV file, choose Merge mode to add to existing data, then click Upload & Normalize. Accepted formats: .csv, .json.',
              },
              {
                step: "4",
                title: "Verify the dataset",
                desc: 'Switch to the "Dataset Browser" tab to confirm your data was imported correctly. Check the record count, inspect row samples, and filter by league.',
              },
              {
                step: "5",
                title: "Run the training script",
                desc: "From the project shell, run: python scripts/train_models.py — this reads the database, extracts features, trains all models with 5-fold cross-validation, and saves .pkl files to the /models/ directory.",
              },
              {
                step: "6",
                title: "Enable real ML models",
                desc: "Set the environment variable USE_REAL_ML_MODELS=true and restart the server. The orchestrator will now load your trained .pkl files for all prediction requests.",
              },
              {
                step: "7",
                title: "Monitor accuracy",
                desc: 'View the Model Performance Matrix chart and "Model Comparison" tab for live accuracy, log-loss, and calibration error metrics per model.',
              },
            ].map(({ step, title, desc, link, linkLabel }) => (
              <div key={step} className="flex gap-4 p-3 border border-border rounded-lg bg-background/30">
                <div className="flex-shrink-0 w-7 h-7 rounded-full bg-primary/20 border border-primary/40 flex items-center justify-center text-primary font-bold text-xs">
                  {step}
                </div>
                <div className="space-y-1 min-w-0">
                  <p className="font-bold text-xs uppercase text-foreground">{title}</p>
                  <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
                  {link && (
                    <a href={link} target="_blank" rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-primary hover:underline mt-1">
                      <ExternalLink className="w-3 h-3" /> {linkLabel}
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* CSV column reference */}
          <div className="space-y-2">
            <p className="font-bold uppercase text-xs">CSV Column Reference</p>
            <div className="overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border">
                    {["Column", "Aliases", "Required?", "Notes"].map(h => (
                      <th key={h} className="text-left p-2 text-muted-foreground uppercase font-medium">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/40">
                  {[
                    ["home_team", "HomeTeam", "Yes", "Full team name"],
                    ["away_team", "AwayTeam", "Yes", "Full team name"],
                    ["home_goals", "FTHG, HG", "Recommended", "Full-time goals scored by home side"],
                    ["away_goals", "FTAG, AG", "Recommended", "Full-time goals scored by away side"],
                    ["actual_outcome", "FTR, result", "Alternative to goals", "H = home win, D = draw, A = away win"],
                    ["home_odds", "B365H, PSH, WHH", "Optional", "Decimal odds for home win — improves accuracy"],
                    ["draw_odds", "B365D, PSD, WHD", "Optional", "Decimal odds for draw"],
                    ["away_odds", "B365A, PSA, WHA", "Optional", "Decimal odds for away win"],
                    ["league", "competition", "Optional", "League name or code"],
                    ["date", "Date, kickoff", "Optional", "Match date (any format)"],
                    ["season", "Season", "Optional", "e.g. 2023/24"],
                  ].map(([col, aliases, required, notes]) => (
                    <tr key={col} className="hover:bg-muted/10">
                      <td className="p-2 font-bold text-primary">{col}</td>
                      <td className="p-2 text-muted-foreground">{aliases}</td>
                      <td className="p-2">
                        <Badge variant={required === "Yes" ? "default" : required === "Recommended" ? "secondary" : "outline"}
                          className="text-[9px] uppercase">
                          {required}
                        </Badge>
                      </td>
                      <td className="p-2 text-muted-foreground">{notes}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Training script reference */}
          <div className="space-y-2">
            <p className="font-bold uppercase text-xs">Training Script Reference</p>
            <div className="bg-background border border-border rounded-lg p-4 space-y-2 text-xs">
              <p className="text-muted-foreground">Run from the project root shell:</p>
              <pre className="text-primary font-mono">{"# Train on database records (default)\npython scripts/train_models.py\n\n# Train on an external CSV file\npython scripts/train_models.py --source csv --csv path/to/matches.csv\n\n# Combine database + CSV\npython scripts/train_models.py --source both --csv path/to/matches.csv"}</pre>
              <p className="text-muted-foreground pt-2">Required: at least 50 settled matches. The more data (2,000+ rows), the better the predictions.</p>
            </div>
          </div>

          {/* Free data sources */}
          <div className="space-y-2">
            <p className="font-bold uppercase text-xs">Free Historical Data Sources</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {[
                { name: "Football-Data.co.uk", desc: "Season CSV files for 30+ leagues. Has B365 odds columns.", url: "https://football-data.co.uk/data.php" },
                { name: "football-data.org API", desc: "REST API with 15+ competitions on free tier (no historical odds).", url: "https://football-data.org" },
                { name: "OpenFootball (GitHub)", desc: "Open-source historical match data in JSON/CSV format.", url: "https://github.com/openfootball" },
                { name: "Kaggle Datasets", desc: 'Search "football match results" for community-contributed historical datasets.', url: "https://kaggle.com/datasets" },
              ].map(({ name, desc, url }) => (
                <a key={name} href={url} target="_blank" rel="noopener noreferrer"
                  className="flex flex-col p-3 border border-border rounded-lg bg-background/30 hover:border-primary/40 transition-colors group">
                  <span className="font-bold text-xs text-primary group-hover:underline flex items-center gap-1">
                    <ExternalLink className="w-3 h-3" /> {name}
                  </span>
                  <span className="text-xs text-muted-foreground mt-1">{desc}</span>
                </a>
              ))}
            </div>
          </div>

        </CardContent>
      )}
    </Card>
  );
}

type DatasetTab = "upload" | "browser" | "models";

function DatasetManagement() {
  const [activeTab, setActiveTab] = useState<DatasetTab>("upload");
  const [file, setFile] = useState<File | null>(null);
  const [merge, setMerge] = useState(false);
  const [browserPage, setBrowserPage] = useState(1);
  const [browserLeague, setBrowserLeague] = useState("");
  const [browserSearch, setBrowserSearch] = useState("");
  const [clearConfirm, setClearConfirm] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const qc = useQueryClient();

  const { data: stats, refetch: refetchStats } = useQuery<any>({
    queryKey: ["dataset-stats"],
    queryFn: () => apiGet<any>("/training/dataset/stats"),
  });

  const { data: browser, isLoading: browserLoading, refetch: refetchBrowser } = useQuery<any>({
    queryKey: ["dataset-browser", browserPage, browserLeague, browserSearch],
    queryFn: () => {
      const params = new URLSearchParams({ page: String(browserPage) });
      if (browserLeague) params.set("league", browserLeague);
      if (browserSearch) params.set("search", browserSearch);
      return apiGet<any>(`/training/dataset/browser?${params.toString()}`);
    },
    enabled: activeTab === "browser",
  });

  const { data: models, isLoading: modelsLoading, refetch: refetchModels } = useQuery<any>({
    queryKey: ["model-comparison"],
    queryFn: () => apiGet<any>("/training/models/compare"),
    enabled: activeTab === "models",
  });

  const uploadMutation = useMutation({
    mutationFn: async (f: File) => {
      const fd = new FormData();
      fd.append("file", f);
      fd.append("merge", String(merge));
      return apiFormPost<any>("/training/dataset/upload", fd);
    },
    onSuccess: (data) => {
      toast.success(`Uploaded ${data.records_uploaded?.toLocaleString()} records`);
      setFile(null);
      refetchStats();
    },
    onError: (e: any) => toast.error(e.message || "Upload failed"),
  });

  const clearMutation = useMutation({
    mutationFn: () => apiDelete<any>("/training/dataset/clear"),
    onSuccess: () => {
      toast.success("Dataset cleared");
      setClearConfirm(false);
      refetchStats();
      qc.invalidateQueries({ queryKey: ["dataset-browser"] });
    },
    onError: (e: any) => toast.error(e.message),
  });

  const TABS: { id: DatasetTab; label: string; icon: React.ElementType }[] = [
    { id: "upload",  label: "Upload Data",        icon: Upload },
    { id: "browser", label: "Dataset Browser",    icon: FolderOpen },
    { id: "models",  label: "Model Comparison",   icon: GitCompare },
  ];

  return (
    <Card className="bg-card/50 backdrop-blur border-border">
      <CardHeader className="border-b border-border/50 pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="font-mono uppercase flex items-center gap-2">
            <Database className="w-5 h-5 text-primary" /> Dataset Management
          </CardTitle>
          {/* Stats row */}
          {stats && (
            <div className="flex gap-4 font-mono text-xs text-muted-foreground">
              <span>Historical: <strong className="text-foreground">{stats.historical?.count?.toLocaleString() ?? 0}</strong></span>
              <span>Simulated: <strong className="text-foreground">{stats.simulated?.count?.toLocaleString() ?? 0}</strong></span>
              <span>Total: <strong className="text-primary">{stats.total?.toLocaleString() ?? 0}</strong></span>
            </div>
          )}
        </div>
        <div className="flex gap-2 mt-3">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded font-mono text-xs font-medium transition-colors ${
                  activeTab === tab.id
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/30 text-muted-foreground hover:bg-muted/50"
                }`}
              >
                <Icon className="w-3 h-3" />
                {tab.label}
              </button>
            );
          })}
        </div>
      </CardHeader>
      <CardContent className="pt-5">
        {activeTab === "upload" && (
          <div className="space-y-4 max-w-lg">
            <p className="text-xs font-mono text-muted-foreground leading-relaxed">
              Upload a <strong>.csv</strong> or <strong>.json</strong> file of historical match results.
              <br />
              <strong>Required columns:</strong> home_team, away_team, home_goals, away_goals
              <br />
              <strong>Optional:</strong> league, date, season, actual_outcome
            </p>

            <div className="space-y-2">
              <input
                ref={fileRef}
                type="file"
                accept=".csv,.json"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              <Button variant="outline" className="font-mono text-xs uppercase" onClick={() => fileRef.current?.click()}>
                <Upload className="w-3 h-3 mr-1.5" />
                {file ? file.name : "SELECT FILE (.csv / .json)"}
              </Button>
              {file && (
                <p className="text-xs font-mono text-muted-foreground">
                  {(file.size / 1024).toFixed(1)} KB
                </p>
              )}
            </div>

            <label className="flex items-center gap-2 text-xs font-mono cursor-pointer">
              <input type="checkbox" checked={merge} onChange={(e) => setMerge(e.target.checked)} />
              Merge with existing dataset (instead of replacing)
            </label>

            <Button
              className="font-mono uppercase text-xs"
              disabled={!file || uploadMutation.isPending}
              onClick={() => file && uploadMutation.mutate(file)}
            >
              {uploadMutation.isPending ? "UPLOADING..." : "UPLOAD & NORMALIZE"}
            </Button>

            {(stats?.historical?.count ?? 0) > 0 && (
              <div className="pt-4 border-t border-border/50">
                <Button
                  variant={clearConfirm ? "destructive" : "outline"}
                  size="sm"
                  className="font-mono text-xs uppercase"
                  onClick={() => clearConfirm ? clearMutation.mutate() : setClearConfirm(true)}
                  disabled={clearMutation.isPending}
                >
                  <Trash2 className="w-3 h-3 mr-1.5" />
                  {clearMutation.isPending ? "CLEARING..." : clearConfirm ? "CONFIRM CLEAR" : "CLEAR DATASET"}
                </Button>
                {clearConfirm && (
                  <Button variant="ghost" size="sm" className="ml-2 font-mono text-xs" onClick={() => setClearConfirm(false)}>
                    Cancel
                  </Button>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === "browser" && (
          <div className="space-y-4">
            <div className="flex flex-wrap gap-3">
              <Input
                placeholder="Search team name..."
                value={browserSearch}
                onChange={(e) => { setBrowserSearch(e.target.value); setBrowserPage(1); }}
                className="font-mono text-sm bg-background/50 max-w-xs"
              />
              <Select value={browserLeague || "all"} onValueChange={(v) => { setBrowserLeague(v === "all" ? "" : v); setBrowserPage(1); }}>
                <SelectTrigger className="w-48 font-mono bg-background/50 text-sm">
                  <SelectValue placeholder="All Leagues" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Leagues</SelectItem>
                  {(browser?.leagues ?? []).map((l: string) => (
                    <SelectItem key={l} value={l}>{l.replace(/_/g, " ")}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button variant="outline" size="sm" className="font-mono text-xs" onClick={() => refetchBrowser()}>
                ↺ Refresh
              </Button>
            </div>

            {browserLoading ? (
              <p className="font-mono text-muted-foreground text-sm text-center py-6">Loading...</p>
            ) : !browser || browser.total === 0 ? (
              <p className="font-mono text-muted-foreground text-sm text-center py-6">
                No records. Upload data first.
              </p>
            ) : (
              <>
                <p className="font-mono text-xs text-muted-foreground">
                  {browser.total.toLocaleString()} records · Page {browser.page} of {browser.pages}
                </p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs font-mono">
                    <thead>
                      <tr className="border-b border-border">
                        {["Home", "Away", "Score", "League", "Date", "Result"].map((h) => (
                          <th key={h} className="text-left p-2 text-muted-foreground uppercase">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(browser.records ?? []).map((r: any, i: number) => (
                        <tr key={i} className="border-b border-border/30 hover:bg-muted/10">
                          <td className="p-2 font-bold">{r.home_team}</td>
                          <td className="p-2 font-bold">{r.away_team}</td>
                          <td className="p-2 font-bold">
                            {r.home_goals != null && r.away_goals != null ? `${r.home_goals}–${r.away_goals}` : "—"}
                          </td>
                          <td className="p-2 text-muted-foreground">{(r.league || "").replace(/_/g, " ")}</td>
                          <td className="p-2 text-muted-foreground">{r.date || "—"}</td>
                          <td className="p-2">
                            {r.actual_outcome ? (
                              <Badge variant={r.actual_outcome === "home" ? "default" : r.actual_outcome === "away" ? "destructive" : "outline"}
                                className="text-[9px] uppercase">
                                {r.actual_outcome}
                              </Badge>
                            ) : "—"}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                {browser.pages > 1 && (
                  <div className="flex items-center gap-3 font-mono text-xs">
                    <Button variant="outline" size="sm" disabled={browser.page <= 1} onClick={() => setBrowserPage((p) => p - 1)}>← Prev</Button>
                    <span className="text-muted-foreground">Page {browser.page} of {browser.pages}</span>
                    <Button variant="outline" size="sm" disabled={browser.page >= browser.pages} onClick={() => setBrowserPage((p) => p + 1)}>Next →</Button>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {activeTab === "models" && (
          <div className="space-y-3">
            <Button variant="outline" size="sm" className="font-mono text-xs uppercase" onClick={() => refetchModels()} disabled={modelsLoading}>
              {modelsLoading ? "⟳" : "↺"} Refresh
            </Button>
            {modelsLoading ? (
              <p className="font-mono text-muted-foreground text-sm text-center py-6">Loading...</p>
            ) : (models?.models ?? []).length === 0 ? (
              <p className="font-mono text-muted-foreground text-sm text-center py-6">
                No model metrics available. Run a training job first.
              </p>
            ) : (
              (models?.models ?? []).map((m: any, i: number) => {
                const rank = i + 1;
                const rankColor = rank === 1 ? "text-yellow-400" : rank === 2 ? "text-muted-foreground" : rank === 3 ? "text-orange-500" : "text-muted-foreground/50";
                return (
                  <div key={m.model} className={`flex items-center gap-4 p-3 rounded-lg border ${i === 0 ? "border-yellow-400/30 bg-yellow-400/5" : "border-border bg-card/30"}`}>
                    <span className={`font-mono font-bold text-lg w-6 ${rankColor}`}>{rank}</span>
                    <div className="flex-1 min-w-0">
                      <p className="font-bold text-sm font-mono truncate">{m.model}</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        {m.training_samples ? `${m.training_samples.toLocaleString()} samples` : ""}
                        {m.last_trained ? ` · ${new Date(m.last_trained).toLocaleDateString()}` : ""}
                      </p>
                    </div>
                    <div className="flex gap-4 text-xs font-mono">
                      <div className="text-center">
                        <div className="font-bold text-primary">{m.accuracy != null ? `${(m.accuracy * 100).toFixed(1)}%` : "—"}</div>
                        <div className="text-muted-foreground uppercase">Acc</div>
                      </div>
                      <div className="text-center">
                        <div className="font-bold text-secondary">{m.log_loss != null ? m.log_loss.toFixed(4) : "—"}</div>
                        <div className="text-muted-foreground uppercase">LogLoss</div>
                      </div>
                      <div className="text-center">
                        <div className="font-bold text-yellow-400">{m.calibration_error != null ? m.calibration_error.toFixed(4) : "—"}</div>
                        <div className="text-muted-foreground uppercase">CalErr</div>
                      </div>
                      <div className="text-center">
                        <div className="font-bold text-muted-foreground">v{m.version || 1}</div>
                        <div className="text-muted-foreground uppercase">Ver</div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
