import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { toast } from "sonner";
import {
  Card, CardContent, CardHeader, CardTitle, CardDescription,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import { Brain, Upload, CheckCircle2, XCircle, Loader2, RefreshCw, BarChart3 } from "lucide-react";

type UploadEntry = {
  id: number;
  match_id: number;
  match: string;
  source: string;
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  confidence: number;
  created_at: string | null;
};

type SourcesData = { sources: string[]; count: number };
type UploadsData = { count: number; uploads: UploadEntry[] };

function ProbBar({ label, value, color }: { label: string; value: number; color: string }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-10 text-muted-foreground font-mono">{label}</span>
      <div className="flex-1 bg-muted/30 rounded h-2 overflow-hidden">
        <div className={`h-full rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right font-mono text-foreground">{pct}%</span>
    </div>
  );
}

export default function AIUploadPage() {
  const qc = useQueryClient();

  const [matchId, setMatchId]     = useState("");
  const [source, setSource]       = useState("");
  const [homeProb, setHomeProb]   = useState("");
  const [drawProb, setDrawProb]   = useState("");
  const [awayProb, setAwayProb]   = useState("");
  const [confidence, setConf]     = useState("0.70");
  const [reason, setReason]       = useState("");
  const [raw, setRaw]             = useState("");

  const { data: sourcesData } = useQuery<SourcesData>({
    queryKey: ["ai-upload-sources"],
    queryFn:  () => apiGet("/api/ai-upload/sources"),
  });

  const { data: uploadsData, isLoading: uploadsLoading } = useQuery<UploadsData>({
    queryKey: ["ai-upload-list"],
    queryFn:  () => apiGet("/api/ai-upload/list?limit=50"),
    refetchInterval: 30_000,
  });

  const submitMut = useMutation({
    mutationFn: (body: object) => apiPost("/api/ai-upload/submit", body),
    onSuccess: () => {
      toast.success("AI prediction submitted successfully");
      qc.invalidateQueries({ queryKey: ["ai-upload-list"] });
      setMatchId(""); setHomeProb(""); setDrawProb(""); setAwayProb("");
      setReason(""); setRaw(""); setConf("0.70");
    },
    onError: (e: any) => toast.error(e.message ?? "Submission failed"),
  });

  const handleSubmit = () => {
    const mid = parseInt(matchId);
    const hp  = parseFloat(homeProb);
    const dp  = parseFloat(drawProb);
    const ap  = parseFloat(awayProb);
    const cf  = parseFloat(confidence);

    if (!mid || mid <= 0)          return toast.error("Enter a valid match ID");
    if (!source)                   return toast.error("Select an AI source");
    if (isNaN(hp) || hp < 0 || hp > 1) return toast.error("Home prob must be 0–1");
    if (isNaN(dp) || dp < 0 || dp > 1) return toast.error("Draw prob must be 0–1");
    if (isNaN(ap) || ap < 0 || ap > 1) return toast.error("Away prob must be 0–1");

    submitMut.mutate({
      match_id:    mid,
      source,
      home_prob:   hp,
      draw_prob:   dp,
      away_prob:   ap,
      confidence:  isNaN(cf) ? 0.7 : cf,
      reason:      reason || undefined,
      raw_content: raw || undefined,
    });
  };

  const sources = sourcesData?.sources ?? [];
  const uploads = uploadsData?.uploads ?? [];

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
          <Brain className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold font-mono">AI Upload</h1>
          <p className="text-sm text-muted-foreground">Submit external AI model probability estimates for match analytics</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Submit Form */}
        <Card className="lg:col-span-2 border-border/50 bg-card/50">
          <CardHeader className="pb-4">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Upload className="w-4 h-4 text-primary" />
              Submit AI Prediction
            </CardTitle>
            <CardDescription className="text-xs">
              Enter probability estimates from any AI source (Native Ensemble)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Match ID */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">Match ID</Label>
              <Input
                type="number"
                placeholder="e.g. 42"
                value={matchId}
                onChange={e => setMatchId(e.target.value)}
                className="font-mono text-sm h-9"
              />
            </div>

            {/* Source */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">AI Source</Label>
              <Select value={source} onValueChange={setSource}>
                <SelectTrigger className="h-9 text-sm font-mono">
                  <SelectValue placeholder="Select AI source…" />
                </SelectTrigger>
                <SelectContent>
                  {sources.map(s => (
                    <SelectItem key={s} value={s} className="font-mono text-sm capitalize">
                      {s}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Probabilities */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">Probabilities (0–1)</Label>
              <div className="grid grid-cols-3 gap-2">
                <div>
                  <span className="text-[10px] text-muted-foreground font-mono">Home</span>
                  <Input
                    type="number" step="0.01" min="0" max="1"
                    placeholder="0.45"
                    value={homeProb}
                    onChange={e => setHomeProb(e.target.value)}
                    className="font-mono text-sm h-8 mt-1"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-muted-foreground font-mono">Draw</span>
                  <Input
                    type="number" step="0.01" min="0" max="1"
                    placeholder="0.27"
                    value={drawProb}
                    onChange={e => setDrawProb(e.target.value)}
                    className="font-mono text-sm h-8 mt-1"
                  />
                </div>
                <div>
                  <span className="text-[10px] text-muted-foreground font-mono">Away</span>
                  <Input
                    type="number" step="0.01" min="0" max="1"
                    placeholder="0.28"
                    value={awayProb}
                    onChange={e => setAwayProb(e.target.value)}
                    className="font-mono text-sm h-8 mt-1"
                  />
                </div>
              </div>
              {homeProb && drawProb && awayProb && (
                <div className="mt-2 space-y-1.5">
                  <ProbBar label="Home" value={parseFloat(homeProb) || 0} color="bg-primary" />
                  <ProbBar label="Draw" value={parseFloat(drawProb) || 0} color="bg-yellow-500" />
                  <ProbBar label="Away" value={parseFloat(awayProb) || 0} color="bg-blue-500" />
                </div>
              )}
            </div>

            {/* Confidence */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">Confidence (0–1)</Label>
              <Input
                type="number" step="0.01" min="0" max="1"
                placeholder="0.70"
                value={confidence}
                onChange={e => setConf(e.target.value)}
                className="font-mono text-sm h-9"
              />
            </div>

            {/* Reason */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">Reasoning (optional)</Label>
              <Textarea
                placeholder="Brief summary of the AI's reasoning…"
                value={reason}
                onChange={e => setReason(e.target.value)}
                rows={2}
                className="font-mono text-xs resize-none"
              />
            </div>

            {/* Raw content */}
            <div className="space-y-1.5">
              <Label className="text-xs font-mono text-muted-foreground">Raw AI Response (optional)</Label>
              <Textarea
                placeholder="Paste the full AI analytics here…"
                value={raw}
                onChange={e => setRaw(e.target.value)}
                rows={3}
                className="font-mono text-xs resize-none"
              />
            </div>

            <Button
              onClick={handleSubmit}
              disabled={submitMut.isPending}
              className="w-full h-9 text-sm font-mono"
            >
              {submitMut.isPending ? (
                <><Loader2 className="w-4 h-4 mr-2 animate-spin" /> Submitting…</>
              ) : (
                <><Upload className="w-4 h-4 mr-2" /> Submit Prediction</>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Recent Uploads */}
        <Card className="lg:col-span-3 border-border/50 bg-card/50">
          <CardHeader className="pb-4 flex flex-row items-center justify-between">
            <div>
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-primary" />
                Recent Uploads
              </CardTitle>
              <CardDescription className="text-xs mt-1">
                {uploadsData?.count ?? 0} total submissions
              </CardDescription>
            </div>
            <Button
              variant="ghost" size="sm"
              onClick={() => qc.invalidateQueries({ queryKey: ["ai-upload-list"] })}
              className="h-7 px-2"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </Button>
          </CardHeader>
          <CardContent>
            {uploadsLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : uploads.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground text-sm font-mono">
                No uploads yet. Submit your first AI prediction.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow className="border-border/50">
                      <TableHead className="text-xs font-mono text-muted-foreground">Match</TableHead>
                      <TableHead className="text-xs font-mono text-muted-foreground">Source</TableHead>
                      <TableHead className="text-xs font-mono text-muted-foreground text-right">H</TableHead>
                      <TableHead className="text-xs font-mono text-muted-foreground text-right">D</TableHead>
                      <TableHead className="text-xs font-mono text-muted-foreground text-right">A</TableHead>
                      <TableHead className="text-xs font-mono text-muted-foreground text-right">Conf</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {uploads.map(u => (
                      <TableRow key={u.id} className="border-border/30 hover:bg-muted/20">
                        <TableCell className="text-xs font-mono py-2 max-w-[160px] truncate">
                          {u.match}
                        </TableCell>
                        <TableCell className="py-2">
                          <Badge variant="outline" className="text-[10px] font-mono px-1.5 py-0 capitalize">
                            {u.source}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-xs font-mono text-right text-primary py-2">
                          {Math.round(u.home_prob * 100)}%
                        </TableCell>
                        <TableCell className="text-xs font-mono text-right text-yellow-500 py-2">
                          {Math.round(u.draw_prob * 100)}%
                        </TableCell>
                        <TableCell className="text-xs font-mono text-right text-blue-400 py-2">
                          {Math.round(u.away_prob * 100)}%
                        </TableCell>
                        <TableCell className="text-xs font-mono text-right text-muted-foreground py-2">
                          {Math.round(u.confidence * 100)}%
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Available Sources */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono">Accepted AI Sources</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2">
            {sources.map(s => (
              <Badge key={s} variant="secondary" className="font-mono text-xs capitalize">
                {s}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
