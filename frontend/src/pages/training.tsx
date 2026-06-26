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
import { Terminal, Database, Server, Cpu, Activity, Upload, FolderOpen, GitCompare, Trash2, BookOpen, ChevronDown, ChevronUp, ExternalLink, History, Rocket, Undo2, CheckCircle2, Clock, Globe } from "lucide-react";
import { format } from "date-fns";
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip as RechartsTooltip, CartesianGrid } from "recharts";
import { toast } from "sonner";

export default function TrainingPage() {
  const { data: jobsData, isLoading: isJobsLoading } = useListTrainingJobs();
  const { data: performance, isLoading: isPerfLoading } = useQuery<any>({
    queryKey: ["/api/analytics/summary"],
    queryFn: () => apiGet("/api/analytics/summary"),
  });

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
    return <div className="h-full flex items-center justify-center font-mono text-muted-foreground animate-pulse">INITIALIZING_ML_PIPELINE...</div>;
  }

  const jobs = jobsData?.jobs ?? [];
  const ensembleAccuracy = performance?.avg_clv ? (performance.avg_clv * 100 + 50).toFixed(1) : "—";
  const totalPredictions = performance?.total_predictions ?? 0;

  return (
    <div className="space-y-6 pb-20">
      <div className="flex flex-col gap-2">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Intelligence Engine Infrastructure</h1>
        <p className="text-muted-foreground font-mono text-sm">Model training status, pipeline health, and data ingestion</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="space-y-6">
          <Card className="bg-card/50  border-border">
            <CardHeader className="pb-2 border-b border-border/50">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Activity className="w-4 h-4 mr-2 text-primary" />
                Ensemble Status
              </CardTitle>
            </CardHeader>
            <CardContent className="pt-6 space-y-4">
              <div className="text-center">
                <div className="text-4xl font-bold font-mono text-primary">
                  {ensembleAccuracy === "—" ? "—" : `${ensembleAccuracy}%`}
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

          <Card className="bg-card/50  border-border">
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
                variant="outline"
                className="w-full font-mono text-xs"
                onClick={() => fileRef.current?.click()}
                disabled={uploadTraining.isPending}
              >
                <Upload className="w-3 h-3 mr-2" />
                {uploadTraining.isPending ? "UPLOADING..." : "SELECT DATASET (.CSV)"}
              </Button>
            </CardContent>
          </Card>
        </div>

        <div className="md:col-span-2 space-y-6">
          <Card className="bg-card/50 border-border h-full flex flex-col min-h-[400px]">
            <CardHeader className="pb-2 border-b border-border/50 flex flex-row items-center justify-between">
              <CardTitle className="font-mono uppercase text-sm flex items-center">
                <Terminal className="w-4 h-4 mr-2 text-primary" />
                Job Monitor
              </CardTitle>
              <Badge variant="outline" className="text-[10px] font-mono border-emerald-500/30 text-emerald-400 bg-emerald-500/10">
                PIPELINE_ACTIVE
              </Badge>
            </CardHeader>
            <CardContent className="flex-1 p-0 overflow-hidden">
              <div className="divide-y divide-border/50">
                {jobs.length === 0 ? (
                  <div className="p-12 text-center text-muted-foreground font-mono text-xs italic">
                    No active or historical jobs found in registry.
                  </div>
                ) : (
                  jobs.map((job: any) => (
                    <div key={job.id} className="p-4 flex items-center justify-between hover:bg-muted/10 transition-colors">
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded border flex items-center justify-center ${
                          job.status === 'completed' ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400' :
                          job.status === 'failed' ? 'border-rose-500/30 bg-rose-500/10 text-rose-400' :
                          'border-blue-500/30 bg-blue-500/10 text-blue-400 animate-pulse'
                        }`}>
                          {job.status === 'completed' ? <CheckCircle2 size={14} /> :
                           job.status === 'failed' ? <History size={14} /> : <Rocket size={14} />}
                        </div>
                        <div>
                          <p className="text-xs font-mono font-bold">JOB_{job.id.slice(0, 8)}</p>
                          <div className="flex items-center gap-2 mt-0.5">
                            <span className="text-[10px] text-muted-foreground font-mono uppercase">{job.status}</span>
                            <span className="text-gray-600 text-[10px]">•</span>
                            <span className="text-[10px] text-muted-foreground font-mono">{job.model_key || 'ENSEMBLE_REWEIGHT'}</span>
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                         <p className="text-[10px] font-mono text-muted-foreground">
                           {job.started_at ? format(new Date(job.started_at), 'MMM dd, HH:mm') : '--'}
                         </p>
                         <p className="text-[10px] font-mono text-primary mt-0.5">
                           {job.duration_seconds ? `${job.duration_seconds}s` : 'Processing...'}
                         </p>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
