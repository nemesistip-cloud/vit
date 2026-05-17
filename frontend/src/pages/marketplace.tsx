import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFormPost, apiGet, apiPost, apiPatch, apiDelete } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle,
} from "@/components/ui/card";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  BookOpen, FileCode2, ShoppingBag, Plus, Star, Zap, TrendingUp,
  BarChart2, DollarSign, Search, Coins, AlertTriangle, Lock,
  Unlock, ShieldCheck, TrendingDown, Trophy, Target, Activity,
  ChevronUp, Flame,
} from "lucide-react";
import { EmptyState } from "@/components/empty-state";
import { toast } from "sonner";
import { usePublicConfig } from "@/lib/usePublicConfig";

// ── Types ──────────────────────────────────────────────────────────────

interface Listing {
  id: number;
  creator_id: number;
  name: string;
  slug: string;
  description: string | null;
  category: string;
  tags: string | null;
  price_per_call: string;
  model_key: string | null;
  usage_count: number;
  avg_rating: number;
  rating_count: number;
  total_revenue: string;
  creator_revenue: string;
  total_staked: string;
  staker_count: number;
  is_active: boolean;
  is_verified: boolean;
  accuracy_rate: number;
  roi: number;
  clv_correlation: number;
  created_at: string;
}

interface BrowseResponse {
  items: Listing[];
  total: number;
  page: number;
  pages: number;
}

interface Stats {
  total_listings: number;
  active_listings: number;
  total_calls: number;
  total_volume_vitcoin: number;
  protocol_revenue_vitcoin: number;
  top_models: { id: number; name: string; usage_count: number; avg_rating: number }[];
}

interface StakeInfo {
  id: number;
  listing_id: number;
  amount: string;
  current_amount: string;
  slashed_amount: string;
  earnings_accumulated: string;
  lock_period_days: number;
  staked_at: string;
  unlock_at: string | null;
  is_unlocked: boolean;
  status: string;
}

interface ListingStakes {
  listing_id: number;
  staker_count: number;
  total_staked: string;
  stakes: StakeInfo[];
}

interface MyStakes {
  count: number;
  stakes: StakeInfo[];
}

interface LeaderboardItem {
  id: number;
  creator_id: number;
  name: string;
  slug: string;
  description: string | null;
  category: string;
  tags: string | null;
  model_key: string | null;
  price_per_call: string;
  usage_count: number;
  avg_rating: number;
  rating_count: number;
  total_staked: string;
  staker_count: number;
  total_revenue: string;
  is_active: boolean;
  is_verified: boolean;
  win_rate: number;
  roi: number;
  accuracy_rate: number;
  clv_correlation: number;
  total_predictions: number;
  est_apy: number;
}

interface LeaderboardResponse {
  items: LeaderboardItem[];
  total: number;
  sort_by: string;
}

// ── Helpers ────────────────────────────────────────────────────────────

function StarRating({ value, count }: { value: number; count: number }) {
  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      <Star className={`w-3 h-3 ${value >= 1 ? "text-yellow-400 fill-yellow-400" : ""}`} />
      <span className="font-medium text-foreground">{value.toFixed(1)}</span>
      <span>({count})</span>
    </span>
  );
}

function CategoryBadge({ cat }: { cat: string }) {
  const colors: Record<string, string> = {
    prediction: "bg-blue-500/10 text-blue-400",
    analytics:  "bg-purple-500/10 text-purple-400",
    strategy:   "bg-green-500/10 text-green-400",
    data:       "bg-orange-500/10 text-orange-400",
  };
  return (
    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${colors[cat] ?? "bg-muted text-muted-foreground"}`}>
      {cat}
    </span>
  );
}

// ── Stake Modal ─────────────────────────────────────────────────────────

function StakeModal({ listing }: { listing: Listing }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [amount, setAmount] = useState("50");
  const { data: pubCfg } = usePublicConfig();
  const stakerPct = pubCfg?.platform.staker_revenue_pct ?? 5;
  const [lockDays, setLockDays] = useState(7);

  const { data: stakesData } = useQuery<ListingStakes>({
    queryKey: ["marketplace", "stakes", listing.id],
    queryFn: () => apiGet(`/api/marketplace/models/${listing.id}/stakes`),
    enabled: open,
  });

  const stake = useMutation({
    mutationFn: () =>
      apiPost(`/api/marketplace/models/${listing.id}/stake`, {
        amount: parseFloat(amount),
        lock_days: lockDays,
      }),
    onSuccess: () => {
      toast.success(`Staked ${amount} VIT on ${listing.name}`);
      qc.invalidateQueries({ queryKey: ["marketplace"] });
      qc.invalidateQueries({ queryKey: ["marketplace", "my-stakes"] });
      setOpen(false);
    },
    onError: (e: any) => toast.error(e?.message ?? "Staking failed"),
  });

  const unstake = useMutation({
    mutationFn: () => apiDelete(`/api/marketplace/models/${listing.id}/stake`),
    onSuccess: (data: any) => {
      toast.success(`Unstaked — received ${data.payout} VIT`);
      qc.invalidateQueries({ queryKey: ["marketplace"] });
      qc.invalidateQueries({ queryKey: ["marketplace", "my-stakes"] });
      setOpen(false);
    },
    onError: (e: any) => toast.error(e?.message ?? "Unstake failed"),
  });

  const totalStaked = parseFloat(listing.total_staked ?? "0");

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-1.5 border-amber-500/40 text-amber-400 hover:bg-amber-500/10">
          <Coins className="w-3 h-3" />
          Stake {totalStaked > 0 ? `· ${totalStaked.toFixed(0)} VIT` : ""}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Coins className="w-4 h-4 text-amber-400" /> Stake VIT on {listing.name}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-5">
          {/* Current pool info */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Pool", value: `${parseFloat(listing.total_staked ?? "0").toFixed(1)} VIT` },
              { label: "Stakers", value: listing.staker_count?.toString() ?? "0" },
              { label: "Your Share", value: `${stakerPct}% of calls` },
            ].map(({ label, value }) => (
              <div key={label} className="bg-muted/50 rounded-lg p-2 text-center">
                <p className="text-[10px] text-muted-foreground">{label}</p>
                <p className="text-sm font-semibold text-foreground">{value}</p>
              </div>
            ))}
          </div>

          {/* Earnings info */}
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200 space-y-1">
            <p className="font-medium flex items-center gap-1">
              <TrendingUp className="w-3 h-3" /> Staker Revenue Sharing
            </p>
            <p className="text-muted-foreground">
              {stakerPct}% of every call fee is distributed to stakers proportionally to stake size.
              Slashing risk applies — poor model performance may trigger a partial slash.
            </p>
          </div>

          {/* Stake input */}
          <div className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">Amount (VIT, min 10)</Label>
              <Input
                type="number"
                min="10"
                step="10"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="50"
              />
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Lock period</Label>
              <Select value={String(lockDays)} onValueChange={(v) => setLockDays(parseInt(v))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {[
                    [7, "7 days"],
                    [14, "14 days"],
                    [30, "30 days"],
                    [90, "90 days"],
                  ].map(([days, label]) => (
                    <SelectItem key={days} value={String(days)}>{label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button
            className="w-full gap-2"
            onClick={() => stake.mutate()}
            disabled={stake.isPending || parseFloat(amount) < 10}
          >
            <Lock className="w-4 h-4" />
            {stake.isPending ? "Staking..." : `Stake ${amount} VIT for ${lockDays} days`}
          </Button>

          {/* Current stakes table */}
          {stakesData?.stakes && stakesData.stakes.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground">Current stakers</p>
              {stakesData.stakes.slice(0, 5).map((s) => (
                <div key={s.id} className="flex items-center justify-between text-xs bg-muted/30 rounded px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    {s.is_unlocked
                      ? <Unlock className="w-3 h-3 text-green-400" />
                      : <Lock className="w-3 h-3 text-amber-400" />}
                    <span>{parseFloat(s.current_amount).toFixed(1)} VIT</span>
                  </div>
                  <div className="text-right text-muted-foreground">
                    <span>+{parseFloat(s.earnings_accumulated).toFixed(2)} earned</span>
                    {parseFloat(s.slashed_amount) > 0 && (
                      <span className="text-red-400 ml-2">−{parseFloat(s.slashed_amount).toFixed(2)} slashed</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Unstake button */}
          <Button
            variant="outline"
            size="sm"
            className="w-full gap-2 border-muted text-muted-foreground"
            onClick={() => unstake.mutate()}
            disabled={unstake.isPending}
          >
            <Unlock className="w-3 h-3" />
            {unstake.isPending ? "Withdrawing..." : "Withdraw my stake"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Call Modal ─────────────────────────────────────────────────────────

function CallModal({ listing }: { listing: Listing }) {
  const qc = useQueryClient();
  const [input, setInput] = useState("");
  const [result, setResult] = useState<any>(null);
  const [open, setOpen] = useState(false);

  const call = useMutation({
    mutationFn: () =>
      apiPost(`/api/marketplace/models/${listing.id}/call`, { input_summary: input || null }),
    onSuccess: (data: any) => {
      setResult(data);
      qc.invalidateQueries({ queryKey: ["marketplace"] });
    },
  });

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) { setResult(null); setInput(""); } }}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-2">
          <Zap className="w-3 h-3" /> Call · {listing.price_per_call} VIT
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" /> {listing.name}
          </DialogTitle>
        </DialogHeader>

        {result ? (
          <div className="space-y-3">
            <p className="text-sm font-medium text-green-400">Call successful — {listing.price_per_call} VITCoin charged</p>
            <div className="bg-muted rounded-lg p-3 text-xs font-mono whitespace-pre-wrap max-h-60 overflow-y-auto">
              {JSON.stringify(result.prediction, null, 2)}
            </div>
            <Button variant="outline" size="sm" className="w-full" onClick={() => { setResult(null); setInput(""); }}>
              Make another call
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">{listing.description ?? "No description provided."}</p>
            <div>
              <Label className="text-xs text-muted-foreground mb-1 block">Context / Input (optional)</Label>
              <Textarea
                placeholder="e.g. match_id: 12345, home_team: Arsenal"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                className="text-xs"
                rows={3}
              />
            </div>
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Cost</span>
              <span className="font-semibold text-primary">{listing.price_per_call} VITCoin</span>
            </div>
            <Button
              className="w-full gap-2"
              onClick={() => call.mutate()}
              disabled={call.isPending}
            >
              <Zap className="w-4 h-4" />
              {call.isPending ? "Calling..." : `Call Model`}
            </Button>
            {call.isError && (
              <p className="text-xs text-destructive text-center">
                {(call.error as Error)?.message ?? "Call failed"}
              </p>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Rate Modal ─────────────────────────────────────────────────────────

function RateModal({ listing }: { listing: Listing }) {
  const qc = useQueryClient();
  const [stars, setStars] = useState(5);
  const [review, setReview] = useState("");
  const [open, setOpen] = useState(false);

  const rate = useMutation({
    mutationFn: () =>
      apiPost(`/api/marketplace/models/${listing.id}/rate`, { stars, review: review || null }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["marketplace"] });
      setOpen(false);
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline" className="gap-1">
          <Star className="w-3 h-3" /> Rate
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Rate {listing.name}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div>
            <Label className="text-xs text-muted-foreground mb-2 block">Stars</Label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((s) => (
                <button key={s} onClick={() => setStars(s)}>
                  <Star className={`w-6 h-6 transition-colors ${s <= stars ? "text-yellow-400 fill-yellow-400" : "text-muted"}`} />
                </button>
              ))}
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground mb-1 block">Review (optional)</Label>
            <Textarea
              placeholder="Share your experience..."
              value={review}
              onChange={(e) => setReview(e.target.value)}
              rows={3}
            />
          </div>
          <Button className="w-full" onClick={() => rate.mutate()} disabled={rate.isPending}>
            {rate.isPending ? "Submitting..." : "Submit Rating"}
          </Button>
          {rate.isError && (
            <p className="text-xs text-destructive text-center">
              {(rate.error as Error)?.message ?? "Rating failed — have you called this model?"}
            </p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── List Model Modal ────────────────────────────────────────────────────

function ListModelModal() {
  const qc = useQueryClient();
  const { user, hasTier, isAdmin } = useAuth();
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [form, setForm] = useState({
    name: "", description: "", category: "prediction",
    tags: "", price_per_call: "1.0", model_key: "xgboost_v1",
    webhook_url: "", primary_file: "",
  });
  const canCreate = isAdmin || user?.role === "validator" || user?.role === "developer" || hasTier("analyst");

  const { data: modelKeysData } = useQuery<{ keys: string[] }>({
    queryKey: ["marketplace-model-keys"],
    queryFn: () => apiGet<{ keys: string[] }>("/api/marketplace/model-keys"),
    enabled: open,
    staleTime: 60_000,
  });
  const modelKeys = modelKeysData?.keys ?? [];

  const create = useMutation({
    mutationFn: () => {
      const data = new FormData();
      data.append("name", form.name);
      data.append("description", form.description);
      data.append("category", form.category);
      data.append("tags", form.tags);
      data.append("price_per_call", String(parseFloat(form.price_per_call) || 1));
      data.append("model_key", form.model_key || "xgboost_v1");
      if (form.webhook_url) data.append("webhook_url", form.webhook_url);
      if (form.primary_file) data.append("primary_file", form.primary_file);
      files.forEach((file) => data.append("model_files", file, file.webkitRelativePath || file.name));
      return apiFormPost("/api/marketplace/models/upload", data);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["marketplace"] });
      qc.invalidateQueries({ queryKey: ["marketplace", "my-listings"] });
      setOpen(false);
      setFiles([]);
      setForm({ name: "", description: "", category: "prediction", tags: "", price_per_call: "1.0", model_key: "xgboost_v1", webhook_url: "", primary_file: "" });
      toast.success("Model package submitted for admin review.");
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-2"><Plus className="w-4 h-4" /> Create Model Listing</Button>
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Upload a VIT Model Package</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          {!canCreate && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
              Model creation is for developers and analyst-tier accounts. Upgrade to Analyst or request developer access to publish models.
            </div>
          )}
          <div>
            <Label className="text-xs text-muted-foreground">Name *</Label>
            <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Prediction Model" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Description</Label>
            <Textarea value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} rows={2} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs text-muted-foreground">Category</Label>
              <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {["prediction", "analytics", "strategy", "data"].map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">Price (VITCoin/call)</Label>
              <Input
                type="number" min="0" step="0.1"
                value={form.price_per_call}
                onChange={(e) => setForm({ ...form, price_per_call: e.target.value })}
              />
            </div>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Tags (comma-separated)</Label>
            <Input value={form.tags} onChange={(e) => setForm({ ...form, tags: e.target.value })} placeholder="football, xgboost, poisson" />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">System Model Slot *</Label>
            {modelKeys.length > 0 ? (
              <Select value={form.model_key} onValueChange={(v) => setForm({ ...form, model_key: v })}>
                <SelectTrigger><SelectValue placeholder="Select one of the 13 system models" /></SelectTrigger>
                <SelectContent>
                  {modelKeys.map((k) => <SelectItem key={k} value={k}>{k}</SelectItem>)}
                </SelectContent>
              </Select>
            ) : (
              <Input value={form.model_key} onChange={(e) => setForm({ ...form, model_key: e.target.value })} placeholder="xgboost_v1" />
            )}
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Model files *</Label>
            <Input
              type="file"
              multiple
              accept=".pkl,.joblib,.py,.json,.yaml,.yml,.txt,.md,.csv,.npz,.npy,.onnx,.pt,.pth,.h5,.bin,.pyd"
              onChange={(e) => {
                const selected = Array.from(e.target.files ?? []);
                setFiles(selected);
                setForm((prev) => ({ ...prev, primary_file: selected[0]?.name ?? "" }));
              }}
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Supported: .py, .pkl, .joblib, JSON/YAML configs, numpy, ONNX, PyTorch, H5, docs, and data artifacts. Max package size: 100MB.
            </p>
            {files.length > 0 && (
              <div className="mt-2 max-h-24 overflow-y-auto rounded-md bg-muted/50 p-2 text-[11px] text-muted-foreground">
                {files.map((file) => (
                  <div key={`${file.name}-${file.size}`} className="flex justify-between gap-3">
                    <span className="truncate">{file.name}</span>
                    <span>{(file.size / 1024).toFixed(1)} KB</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Primary file</Label>
            <Select value={form.primary_file} onValueChange={(v) => setForm({ ...form, primary_file: v })} disabled={files.length === 0}>
              <SelectTrigger><SelectValue placeholder="Select primary runtime or source file" /></SelectTrigger>
              <SelectContent>
                {files.map((file) => <SelectItem key={file.name} value={file.name}>{file.name}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Webhook URL (optional)</Label>
            <Input value={form.webhook_url} onChange={(e) => setForm({ ...form, webhook_url: e.target.value })} placeholder="https://api.example.com/vit/predict" />
          </div>
          <Button className="w-full" onClick={() => create.mutate()} disabled={create.isPending || !form.name || files.length === 0 || !canCreate}>
            {create.isPending ? "Submitting..." : "Submit Package for Review"}
          </Button>
          {create.isError && (
            <p className="text-xs text-destructive text-center">{(create.error as Error)?.message}</p>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── Model Card ─────────────────────────────────────────────────────────

function ModelCard({ listing }: { listing: Listing }) {
  const { user } = useAuth();
  const isOwner = user?.id === listing.creator_id;
  const totalStaked = parseFloat(listing.total_staked ?? "0");

  return (
    <Card className="flex flex-col hover:border-primary/40 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <CategoryBadge cat={listing.category} />
              {listing.is_verified && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-green-500/10 text-green-400">
                  ✓ Verified
                </span>
              )}
              {listing.accuracy_rate > 0 && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400">
                  {Math.round(listing.accuracy_rate * 100)}% Acc
                </span>
              )}
              {listing.roi !== 0 && (
                <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${listing.roi > 0 ? "bg-green-500/10 text-green-400" : "bg-red-500/10 text-red-400"}`}>
                  {listing.roi > 0 ? "+" : ""}{listing.roi}% ROI
                </span>
              )}
              {isOwner && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                  Your model
                </span>
              )}
              {totalStaked > 0 && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 flex items-center gap-0.5">
                  <Coins className="w-2.5 h-2.5" /> {totalStaked.toFixed(0)} staked
                </span>
              )}
            </div>
            <CardTitle className="text-sm truncate">{listing.name}</CardTitle>
          </div>
          <span className="text-sm font-bold text-primary flex-shrink-0">{listing.price_per_call} VIT</span>
        </div>
        {listing.description && (
          <CardDescription className="text-xs line-clamp-2">{listing.description}</CardDescription>
        )}
      </CardHeader>

      <CardContent className="pb-3 flex-1">
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          <span className="flex items-center gap-1">
            <Zap className="w-3 h-3" /> {listing.usage_count.toLocaleString()} calls
          </span>
        <StarRating value={listing.avg_rating || 0} count={listing.rating_count || 0} />
        </div>
        {listing.tags && (
          <div className="flex flex-wrap gap-1 mt-2">
            {listing.tags.split(",").slice(0, 4).map((t) => (
              <span key={t} className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
              {t?.trim()}
              </span>
            ))}
          </div>
        )}
      </CardContent>

      <CardFooter className="pt-0 gap-2 flex-wrap">
        {!isOwner && <CallModal listing={listing} />}
        {!isOwner && <RateModal listing={listing} />}
        {!isOwner && <StakeModal listing={listing} />}
        {isOwner && (
          <span className="text-xs text-muted-foreground">
            Revenue: {parseFloat(listing.creator_revenue).toFixed(2)} VIT
          </span>
        )}
      </CardFooter>
    </Card>
  );
}

// ── Leaderboard Tab ────────────────────────────────────────────────────

const RANK_COLORS = [
  "text-yellow-400",
  "text-foreground/80",
  "text-amber-600",
];

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  prediction: <Target className="w-3 h-3" />,
  analytics:  <Activity className="w-3 h-3" />,
  strategy:   <Flame className="w-3 h-3" />,
};

function RoiBadge({ roi }: { roi: number }) {
  const positive = roi >= 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-xs font-semibold px-1.5 py-0.5 rounded ${
      positive ? "bg-green-500/15 text-green-400" : "bg-red-500/15 text-red-400"
    }`}>
      {positive && <ChevronUp className="w-3 h-3" />}
      {roi.toFixed(1)}%
    </span>
  );
}

function LeaderboardTab() {
  const { user } = useAuth();
  const [sortBy, setSortBy] = useState<string>("roi");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const { data: pubCfg } = usePublicConfig();
  const stakerPct = pubCfg?.platform.staker_revenue_pct ?? 5;

  const { data, isLoading } = useQuery<LeaderboardResponse>({
    queryKey: ["marketplace", "leaderboard", sortBy],
    queryFn: () => apiGet(`/api/marketplace/leaderboard?sort_by=${sortBy}`),
  });

  const items = data?.items ?? [];

  const summaryStats = {
    totalPooled:   items.reduce((s, m) => s + parseFloat(m.total_staked), 0),
    totalStakers:  items.reduce((s, m) => s + m.staker_count, 0),
    avgRoi:        items.length ? items.reduce((s, m) => s + m.roi, 0) / items.length : 0,
    topApy:        items.length ? Math.max(...items.map((m) => m.est_apy)) : 0,
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-16 rounded-xl bg-muted animate-pulse" />
        ))}
      </div>
    );
  }

  if (!items.length) {
    return (
      <EmptyState
        icon={Trophy}
        title="Leaderboard is loading"
        description="System models are being initialised. Refresh in a moment."
      />
    );
  }

  return (
    <div className="space-y-5">
      {/* Summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Total Staking Pool", value: `${summaryStats.totalPooled.toFixed(0)} VIT`, icon: Coins, color: "text-amber-400" },
          { label: "Total Stakers",      value: summaryStats.totalStakers.toString(),          icon: BarChart2, color: "text-blue-400" },
          { label: "Avg Model ROI",      value: `${summaryStats.avgRoi.toFixed(1)}%`,          icon: TrendingUp, color: "text-green-400" },
          { label: "Best Est. APY",      value: summaryStats.topApy > 0 ? `${summaryStats.topApy.toFixed(1)}%` : "—", icon: Zap, color: "text-primary" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="p-3">
            <div className={`flex items-center gap-1 text-xs mb-1 ${color}`}>
              <Icon className="w-3 h-3" /> {label}
            </div>
            <p className="text-base font-bold text-foreground">{value}</p>
          </Card>
        ))}
      </div>

      {/* Sort controls */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
          <Trophy className="w-4 h-4 text-yellow-400" /> Model Rankings
          <span className="text-muted-foreground font-normal">({items.length} models)</span>
        </h2>
        <Select value={sortBy} onValueChange={(v) => setSortBy(v)}>
          <SelectTrigger className="w-40 h-8 text-xs">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="roi">ROI %</SelectItem>
            <SelectItem value="win_rate">Win Rate %</SelectItem>
            <SelectItem value="total_staked">Most Staked</SelectItem>
            <SelectItem value="usage_count">Most Used</SelectItem>
            <SelectItem value="est_apy">Est. APY</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Column headers */}
      <div className="hidden md:grid grid-cols-[2rem_1fr_5rem_5rem_6rem_6rem_5rem_7rem] gap-3 px-4 text-[10px] text-muted-foreground uppercase tracking-wider">
        <span>#</span>
        <span>Model</span>
        <span className="text-right">Win Rate</span>
        <span className="text-right">ROI</span>
        <span className="text-right">Staked</span>
        <span className="text-right">Est. APY</span>
        <span className="text-right">Calls</span>
        <span className="text-right">Action</span>
      </div>

      {/* Rows */}
      <div className="space-y-2">
        {items.map((model, idx) => {
          const rank = idx + 1;
          const staked = parseFloat(model.total_staked);
          const isExpanded = expandedId === model.id;

          const fakeListingForStake: Listing = {
            id: model.id,
            creator_id: model.creator_id,
            name: model.name,
            slug: model.slug,
            description: model.description,
            category: model.category,
            tags: model.tags,
            price_per_call: model.price_per_call,
            model_key: model.model_key,
            usage_count: model.usage_count,
            avg_rating: model.avg_rating,
            rating_count: model.rating_count,
            total_revenue: model.total_revenue,
            creator_revenue: "0",
            total_staked: model.total_staked,
            staker_count: model.staker_count,
            is_active: model.is_active,
            is_verified: model.is_verified,
            accuracy_rate: model.accuracy_rate ?? 0,
            roi: model.roi ?? 0,
            clv_correlation: model.clv_correlation ?? 0,
            created_at: "",
          };

          return (
            <Card
              key={model.id}
              className={`transition-all cursor-pointer hover:border-primary/40 ${isExpanded ? "border-primary/60 bg-primary/5" : ""}`}
              onClick={() => setExpandedId(isExpanded ? null : model.id)}
            >
              <div className="p-3 md:p-4">
                {/* Desktop layout */}
                <div className="hidden md:grid grid-cols-[2rem_1fr_5rem_5rem_6rem_6rem_5rem_7rem] gap-3 items-center">
                  {/* Rank */}
                  <span className={`text-lg font-bold ${RANK_COLORS[idx] ?? "text-muted-foreground"}`}>
                    {rank <= 3 ? ["🥇","🥈","🥉"][idx] : `#${rank}`}
                  </span>

                  {/* Name + badges */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-sm font-semibold text-foreground truncate">{model.name}</span>
                      {model.is_verified && (
                        <ShieldCheck className="w-3.5 h-3.5 text-blue-400 shrink-0" aria-label="Verified" />
                      )}
                      <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full flex items-center gap-0.5 ${
                        model.category === "prediction" ? "bg-blue-500/10 text-blue-400" :
                        model.category === "analytics"  ? "bg-purple-500/10 text-purple-400" :
                        "bg-green-500/10 text-green-400"
                      }`}>
                        {CATEGORY_ICONS[model.category]} {model.category}
                      </span>
                    </div>
                    {model.model_key && (
                      <span className="text-[10px] text-muted-foreground font-mono">{model.model_key}</span>
                    )}
                  </div>

                  {/* Win Rate */}
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">{model.win_rate.toFixed(1)}%</p>
                    <p className="text-[10px] text-muted-foreground">win rate</p>
                  </div>

                  {/* ROI */}
                  <div className="text-right">
                    <RoiBadge roi={model.roi} />
                    <p className="text-[10px] text-muted-foreground mt-0.5">ROI</p>
                  </div>

                  {/* Staking pool */}
                  <div className="text-right">
                    <p className="text-sm font-semibold text-amber-400">{staked.toFixed(0)} VIT</p>
                    <p className="text-[10px] text-muted-foreground">{model.staker_count} stakers</p>
                  </div>

                  {/* Est APY */}
                  <div className="text-right">
                    <p className={`text-sm font-semibold ${model.est_apy > 0 ? "text-green-400" : "text-muted-foreground"}`}>
                      {model.est_apy > 0 ? `${model.est_apy.toFixed(1)}%` : "—"}
                    </p>
                    <p className="text-[10px] text-muted-foreground">est APY</p>
                  </div>

                  {/* Usage */}
                  <div className="text-right">
                    <p className="text-sm font-semibold text-foreground">{model.usage_count.toLocaleString()}</p>
                    <p className="text-[10px] text-muted-foreground">calls</p>
                  </div>

                  {/* Action — stop propagation so card click doesn't fire */}
                  <div className="flex justify-end" onClick={(e) => e.stopPropagation()}>
                    {user?.id !== model.creator_id && (
                      <StakeModal listing={fakeListingForStake} />
                    )}
                  </div>
                </div>

                {/* Mobile layout */}
                <div className="md:hidden flex items-start gap-3">
                  <span className={`text-lg font-bold shrink-0 w-8 ${RANK_COLORS[idx] ?? "text-muted-foreground"}`}>
                    {rank <= 3 ? ["🥇","🥈","🥉"][idx] : `#${rank}`}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-sm font-semibold text-foreground">{model.name}</span>
                      {model.is_verified && <ShieldCheck className="w-3 h-3 text-blue-400" />}
                    </div>
                    <div className="flex gap-3 mt-1 text-xs text-muted-foreground flex-wrap">
                      <span className="text-foreground font-medium">{model.win_rate.toFixed(1)}% win</span>
                      <RoiBadge roi={model.roi} />
                      <span className="text-amber-400">{staked.toFixed(0)} VIT staked</span>
                      {model.est_apy > 0 && <span className="text-green-400">{model.est_apy.toFixed(1)}% APY</span>}
                    </div>
                  </div>
                  <div onClick={(e) => e.stopPropagation()}>
                    {user?.id !== model.creator_id && (
                      <StakeModal listing={fakeListingForStake} />
                    )}
                  </div>
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-border space-y-3" onClick={(e) => e.stopPropagation()}>
                    {model.description && (
                      <p className="text-sm text-muted-foreground">{model.description}</p>
                    )}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                      {[
                        { label: "Total Predictions", value: model.total_predictions.toLocaleString() },
                        { label: "Price per Call",    value: `${model.price_per_call} VIT` },
                        { label: "Avg Rating",        value: `${model.avg_rating.toFixed(1)} ★` },
                        { label: "Revenue Generated", value: `${parseFloat(model.total_revenue).toFixed(2)} VIT` },
                      ].map(({ label, value }) => (
                        <div key={label} className="bg-muted/50 rounded-lg p-2">
                          <p className="text-[10px] text-muted-foreground">{label}</p>
                          <p className="font-semibold text-foreground">{value}</p>
                        </div>
                      ))}
                    </div>
                    {model.tags && (
                      <div className="flex flex-wrap gap-1">
                        {model.tags.split(",").map((t) => (
                          <span key={t} className="text-[10px] bg-muted px-1.5 py-0.5 rounded text-muted-foreground">
                            {t?.trim()}
                          </span>
                        ))}
                      </div>
                    )}
                    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-200">
                      <p className="font-medium flex items-center gap-1 mb-1">
                        <Coins className="w-3 h-3" /> Staking Opportunity
                      </p>
                      <p className="text-muted-foreground">
                        Pool: <strong className="text-amber-400">{staked.toFixed(2)} VIT</strong> across {model.staker_count} stakers.
                        {model.est_apy > 0
                          ? ` Estimated APY ${model.est_apy.toFixed(1)}% based on recent call volume.`
                          : ` Be the first staker and earn ${stakerPct}% of all call fees.`}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <p className="text-xs text-muted-foreground text-center pb-2">
        Win rate and ROI figures are based on historical back-tested model performance.
        Estimated APY = annualised staker share ÷ pool size, using last-week call volume.
      </p>
    </div>
  );
}


// ── My Stakes Tab ─────────────────────────────────────────────────────

function MyStakesTab() {
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<MyStakes>({
    queryKey: ["marketplace", "my-stakes"],
    queryFn: () => apiGet("/api/marketplace/my-stakes"),
  });

  const unstake = useMutation({
    mutationFn: (listing_id: number) =>
      apiDelete(`/api/marketplace/models/${listing_id}/stake`),
    onSuccess: (res: any) => {
      toast.success(`Received ${res.payout} VIT`);
      qc.invalidateQueries({ queryKey: ["marketplace", "my-stakes"] });
    },
    onError: (e: any) => toast.error(e?.message ?? "Unstake failed"),
  });

  if (isLoading) return <div className="h-32 rounded-xl bg-muted animate-pulse" />;

  if (!data || data.count === 0) {
    return (
      <EmptyState
        icon={Coins}
        title="No active stakes"
        description="Stake VITCoin on marketplace models to earn a share of their call revenue."
      />
    );
  }

  const stakes = data.stakes ?? [];
  const totalValue = stakes.reduce(
    (sum, s) => sum + parseFloat(s.current_amount) + parseFloat(s.earnings_accumulated), 0
  );
  const totalEarnings = stakes.reduce(
    (sum, s) => sum + parseFloat(s.earnings_accumulated), 0
  );
  const totalSlashed = stakes.reduce(
    (sum, s) => sum + parseFloat(s.slashed_amount), 0
  );

  return (
    <div className="space-y-4">
      {/* Summary strip */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Total Staked Value", value: `${totalValue.toFixed(2)} VIT`, icon: Coins, color: "text-amber-400" },
          { label: "Earnings Accumulated", value: `${totalEarnings.toFixed(4)} VIT`, icon: TrendingUp, color: "text-green-400" },
          { label: "Total Slashed", value: `${totalSlashed.toFixed(4)} VIT`, icon: TrendingDown, color: "text-red-400" },
        ].map(({ label, value, icon: Icon, color }) => (
          <Card key={label} className="p-3">
            <div className={`flex items-center gap-1 text-xs mb-1 ${color}`}>
              <Icon className="w-3 h-3" /> {label}
            </div>
            <p className="text-base font-bold text-foreground">{value}</p>
          </Card>
        ))}
      </div>

      {/* Stakes list */}
      <div className="space-y-3">
        {stakes.map((s) => (
          <Card key={s.id} className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="space-y-1 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-foreground">
                    Model #{s.listing_id}
                  </span>
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-medium ${
                    s.status === "active"
                      ? "bg-green-500/10 text-green-400"
                      : "bg-muted text-muted-foreground"
                  }`}>
                    {s.status}
                  </span>
                  {s.is_unlocked
                    ? <Unlock className="w-3 h-3 text-green-400" aria-label="Unlocked — can withdraw" />
                    : <Lock className="w-3 h-3 text-amber-400" aria-label="Still locked" />}
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs text-muted-foreground">
                  <div>
                    <span className="block text-[10px]">Staked</span>
                    <span className="text-foreground font-medium">{parseFloat(s.amount).toFixed(2)} VIT</span>
                  </div>
                  <div>
                    <span className="block text-[10px]">Current</span>
                    <span className="text-foreground font-medium">{parseFloat(s.current_amount).toFixed(2)} VIT</span>
                  </div>
                  <div>
                    <span className="block text-[10px]">Earnings</span>
                    <span className="text-green-400 font-medium">+{parseFloat(s.earnings_accumulated).toFixed(4)} VIT</span>
                  </div>
                  {parseFloat(s.slashed_amount) > 0 && (
                    <div>
                      <span className="block text-[10px]">Slashed</span>
                      <span className="text-red-400 font-medium">−{parseFloat(s.slashed_amount).toFixed(4)} VIT</span>
                    </div>
                  )}
                </div>

                {s.unlock_at && (
                  <p className="text-[10px] text-muted-foreground">
                    {s.is_unlocked
                      ? "Unlocked — ready to withdraw"
                      : `Unlocks ${new Date(s.unlock_at).toLocaleDateString()}`}
                  </p>
                )}
              </div>

              {s.is_unlocked && (
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1 shrink-0"
                  onClick={() => unstake.mutate(s.listing_id)}
                  disabled={unstake.isPending}
                >
                  <Unlock className="w-3 h-3" /> Withdraw
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────

export default function MarketplacePage() {
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [sortBy, setSortBy] = useState("usage_count");
  const [page, setPage] = useState(1);
  const [tab, setTab] = useState("leaderboard");

  const { data: statsData } = useQuery<Stats>({
    queryKey: ["marketplace", "stats"],
    queryFn: () => apiGet("/api/marketplace/stats"),
  });

  const { data: browseData, isLoading } = useQuery<BrowseResponse>({
    queryKey: ["marketplace", "browse", search, category, sortBy, page],
    queryFn: () =>
      apiGet(
        `/api/marketplace/models?page=${page}&sort_by=${sortBy}` +
        (search ? `&search=${encodeURIComponent(search)}` : "") +
        (category !== "all" ? `&category=${category}` : "")
      ),
    placeholderData: (prev) => prev,
  });

  const { data: myListings } = useQuery<Listing[]>({
    queryKey: ["marketplace", "my-listings"],
    queryFn: () => apiGet("/api/marketplace/my-listings"),
    enabled: tab === "my-models",
  });

  const { data: myUsage } = useQuery<any[]>({
    queryKey: ["marketplace", "my-usage"],
    queryFn: () => apiGet("/api/marketplace/my-usage?limit=30"),
    enabled: tab === "my-usage",
  });

  const stats    = statsData;
  const listings = browseData?.items ?? [];
  const totalPages = browseData?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Header banner */}
      <div className="relative rounded-2xl overflow-hidden border border-primary/20 bg-gradient-to-br from-primary/10 via-background to-amber-500/5 p-6">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,_var(--tw-gradient-stops))] from-primary/5 via-transparent to-transparent pointer-events-none" />
        <div className="relative flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
              <ShoppingBag className="w-6 h-6 text-primary" /> AI Model Marketplace
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Buy, sell, and stake on AI prediction models using VITCoin
            </p>
          </div>
          <ListModelModal />
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { label: "Active Models",    value: stats ? String(stats.active_listings) : "—",                          icon: ShoppingBag, tint: "text-primary",    bg: "bg-primary/10"    },
          { label: "Total Calls",      value: stats ? stats.total_calls.toLocaleString() : "—",                     icon: Zap,         tint: "text-yellow-400", bg: "bg-yellow-500/10" },
          { label: "Volume (VIT)",     value: stats ? stats.total_volume_vitcoin.toFixed(2) : "—",                   icon: TrendingUp,  tint: "text-green-400",  bg: "bg-green-500/10"  },
          { label: "Protocol Revenue", value: stats ? stats.protocol_revenue_vitcoin.toFixed(2) : "—",               icon: DollarSign,  tint: "text-amber-400",  bg: "bg-amber-500/10"  },
        ].map(({ label, value, icon: Icon, tint, bg }) => (
          <Card key={label} className="p-4 border-border/60 hover:border-primary/30 transition-colors">
            <div className="flex items-center justify-between mb-3">
              <p className="text-[11px] uppercase tracking-wider text-muted-foreground font-mono">{label}</p>
              <div className={`p-1.5 rounded-lg ${bg}`}>
                <Icon className={`w-3.5 h-3.5 ${tint}`} />
              </div>
            </div>
            <p className={`text-xl font-bold ${tint}`}>{value}</p>
          </Card>
        ))}
      </div>

      {/* Tabs */}
      <Tabs value={tab} onValueChange={setTab}>
        <TabsList className="flex-wrap h-auto gap-1 p-1">
          <TabsTrigger value="leaderboard" className="gap-1.5">
            <Trophy className="w-3 h-3" /> Leaderboard
          </TabsTrigger>
          <TabsTrigger value="browse">Browse</TabsTrigger>
          <TabsTrigger value="my-models">My Models</TabsTrigger>
          <TabsTrigger value="my-usage">My Usage</TabsTrigger>
          <TabsTrigger value="my-stakes" className="gap-1.5">
            <Coins className="w-3 h-3" /> My Stakes
          </TabsTrigger>
          <TabsTrigger value="docs">Build & Train Guide</TabsTrigger>
          {(stats?.top_models?.length ?? 0) > 0 && <TabsTrigger value="top">Top Models</TabsTrigger>}
        </TabsList>

        {/* Leaderboard Tab */}
        <TabsContent value="leaderboard" className="space-y-4">
          <LeaderboardTab />
        </TabsContent>

        {/* Browse Tab */}
        <TabsContent value="browse" className="space-y-4">
          {/* Filters */}
          <div className="flex flex-wrap gap-3">
            <div className="relative flex-1 min-w-48">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search models..."
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
              />
            </div>
            <Select value={category} onValueChange={(v) => { setCategory(v); setPage(1); }}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Category" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {["prediction", "analytics", "strategy", "data"].map((c) => (
                  <SelectItem key={c} value={c}>{c}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={(v) => { setSortBy(v); setPage(1); }}>
              <SelectTrigger className="w-36"><SelectValue placeholder="Sort by" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="usage_count">Most Used</SelectItem>
                <SelectItem value="rating">Highest Rated</SelectItem>
                <SelectItem value="accuracy_rate">Highest Accuracy</SelectItem>
                <SelectItem value="roi">Highest ROI</SelectItem>
                <SelectItem value="price">Lowest Price</SelectItem>
                <SelectItem value="revenue">Top Revenue</SelectItem>
                <SelectItem value="created_at">Newest</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-48 rounded-xl bg-muted animate-pulse" />
              ))}
            </div>
          ) : listings.length === 0 ? (
            <EmptyState
              icon={ShoppingBag}
              title="No models found."
              description="Be the first to list one!"
            />
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {listings.map((l) => <ModelCard key={l.id} listing={l} />)}
              </div>
              {totalPages > 1 && (
                <div className="flex justify-center gap-2">
                  <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
                  <span className="text-sm text-muted-foreground self-center">Page {page} / {totalPages}</span>
                  <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</Button>
                </div>
              )}
            </>
          )}
        </TabsContent>

        {/* My Models Tab */}
        <TabsContent value="my-models" className="space-y-4">
          {!myListings || myListings.length === 0 ? (
            <div className="text-center py-16 text-muted-foreground">
              <BarChart2 className="w-10 h-10 mx-auto mb-3 opacity-30" />
              <p>You haven't listed any models yet.</p>
              <div className="mt-4"><ListModelModal /></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {myListings.map((l) => <ModelCard key={l.id} listing={l} />)}
            </div>
          )}
        </TabsContent>

        {/* My Usage Tab */}
        <TabsContent value="my-usage">
          {!myUsage || myUsage.length === 0 ? (
            <EmptyState
              icon={Zap}
              title="No model calls yet."
              description="Start by calling a model from the marketplace."
            />
          ) : (
            <div className="space-y-2">
              {myUsage.map((log) => (
                <div key={log.id} className="flex items-center justify-between p-3 bg-muted/40 rounded-lg text-sm">
                  <div>
                    <p className="font-medium text-foreground">Model #{log.listing_id}</p>
                    {log.input_summary && <p className="text-xs text-muted-foreground truncate max-w-xs">{log.input_summary}</p>}
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-primary">{log.vitcoin_charged} VIT</p>
                    <p className="text-xs text-muted-foreground">{new Date(log.called_at).toLocaleDateString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </TabsContent>

        {/* My Stakes Tab */}
        <TabsContent value="my-stakes">
          <MyStakesTab />
        </TabsContent>

        {/* Docs Tab */}
        <TabsContent value="docs" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle className="flex items-center gap-2"><BookOpen className="w-5 h-5 text-primary" /> Model creation guide</CardTitle>
                <CardDescription>Use this checklist before submitting a package to the marketplace.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {[
                  ["1", "Pick a system slot", "Choose one of the 13 VIT model families, such as xgboost_v1, lgbm_v1, neural_net_v1, poisson_goals_v1, market_odds_v1, or btts_totals_v1."],
                  ["2", "Package your files", "Upload the model runtime (.pkl/.joblib) or Python source (.py), plus configs, encoders, features, docs, and small data artifacts needed for review."],
                  ["3", "Expose a training/prediction interface", "Python submissions should include def predict, def train, class Model, or class VITModel. Binary models should load with joblib and expose predict or train."],
                  ["4", "Set pricing", "Set the VITCoin cost per call. After approval, calls earn creator revenue while analysts can train eligible models from the training area."],
                  ["5", "Wait for review", "Admins review source and artifacts before activation. Loadable binaries can be registered automatically; Python source remains review-gated for safety."],
                  ["6", "Attract stakers", "Once live, users can stake VITCoin on your model. You earn more signals and stakers earn a share of your call revenue — proportional to their stake."],
                ].map(([step, title, text]) => (
                  <div key={step} className="flex gap-3">
                    <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">{step}</span>
                    <div>
                      <p className="font-medium text-foreground">{title}</p>
                      <p className="text-xs text-muted-foreground">{text}</p>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2"><FileCode2 className="w-5 h-5 text-primary" /> Supported model types</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs text-muted-foreground">
                  <div>
                    <p className="font-medium text-foreground">Loadable binaries</p>
                    <p>.pkl, .joblib with predict or train methods.</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Python source</p>
                    <p>.py modules with predict/train functions or Model/VITModel classes.</p>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">Model artifacts</p>
                    <p>ONNX, PyTorch, H5, numpy arrays, JSON/YAML configs, CSV feature maps, and Markdown/TXT docs.</p>
                  </div>
                </CardContent>
              </Card>
              <Card className="border-amber-500/30 bg-amber-500/5">
                <CardHeader className="pb-2">
                  <CardTitle className="flex items-center gap-2 text-amber-400">
                    <AlertTriangle className="w-4 h-4" /> Slashing Risk
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-xs text-muted-foreground space-y-1">
                  <p>Models with sustained low accuracy, misconduct, or inactivity may be slashed by admins.</p>
                  <p>A slash reduces all stakers' balances by the slash percentage (default 10%).</p>
                  <p>Slashed funds are burned, not redistributed.</p>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        {/* Top Models Tab */}
        <TabsContent value="top">
          <div className="space-y-3">
            {stats?.top_models?.map((m, i) => (
              <div key={m.id} className="flex items-center gap-4 p-4 bg-muted/40 rounded-lg">
                <span className="text-2xl font-bold text-muted-foreground w-8">#{i + 1}</span>
                <div className="flex-1">
                  <p className="font-medium text-foreground">{m.name}</p>
                  <StarRating value={m.avg_rating} count={0} />
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-foreground">{m.usage_count.toLocaleString()} calls</p>
                </div>
              </div>
            ))}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
