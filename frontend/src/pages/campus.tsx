import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { EmptyState } from "@/components/empty-state";
import { toast } from "sonner";
import {
  Users, Briefcase, BookOpen, Trophy, Plus, ThumbsUp,
  Clock, CheckCircle2, ChevronRight, Coins, Building2,
  MessageSquare, LayoutGrid,
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────

interface Circle {
  id: number; name: string; description: string | null;
  circle_type: string; university: string;
  faculty: string | null; department: string | null;
  member_count: number; created_at: string;
}

interface Gig {
  id: number; title: string; description: string;
  gig_type: string; budget_vit: number; budget_ngn: number;
  university: string; status: string; posted_by: number;
  assigned_to: number | null; deadline: string | null;
  created_at: string; completed_at: string | null;
}

interface Overview {
  university: string | null;
  stats: { total_courses: number; total_resources: number; total_circles: number; open_gigs: number };
  top_circles: { id: number; name: string; member_count: number; circle_type: string }[];
  recent_gigs: { id: number; title: string; gig_type: string; budget_vit: number; university: string }[];
}

// ─── Overview tab ────────────────────────────────────────────────────────────

function OverviewTab() {
  const { data, isLoading } = useQuery<Overview>({
    queryKey: ["campus-overview"],
    queryFn: () => apiGet("/api/campus/overview"),
  });

  if (isLoading) return <LoadingState />;
  if (!data) return null;

  const stats = [
    { label: "Courses", value: data.stats.total_courses, icon: BookOpen, color: "text-blue-400" },
    { label: "Resources", value: data.stats.total_resources, icon: LayoutGrid, color: "text-purple-400" },
    { label: "Circles", value: data.stats.total_circles, icon: Users, color: "text-emerald-400" },
    { label: "Open Gigs", value: data.stats.open_gigs, icon: Briefcase, color: "text-amber-400" },
  ];

  return (
    <div className="space-y-6">
      {data.university && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground font-mono">
          <Building2 className="w-4 h-4" />
          {data.university}
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((s) => (
          <Card key={s.label} className="bg-card/50 border-border/40">
            <CardContent className="p-4 flex flex-col gap-1">
              <s.icon className={`w-5 h-5 ${s.color}`} />
              <div className="text-2xl font-bold font-mono">{s.value.toLocaleString()}</div>
              <div className="text-xs text-muted-foreground font-mono uppercase tracking-widest">{s.label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Users className="w-4 h-4 text-primary" /> Top Circles
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.top_circles.length === 0 ? (
              <p className="text-xs text-muted-foreground font-mono">No circles yet.</p>
            ) : data.top_circles.map((c) => (
              <div key={c.id} className="flex items-center justify-between p-2 rounded-lg bg-background/40 border border-border/20">
                <div>
                  <div className="text-xs font-medium">{c.name}</div>
                  <div className="text-[10px] text-muted-foreground font-mono">{c.circle_type}</div>
                </div>
                <Badge variant="outline" className="font-mono text-[10px]">{c.member_count} members</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="bg-card/50 border-border/40">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-mono flex items-center gap-2">
              <Briefcase className="w-4 h-4 text-amber-400" /> Recent Open Gigs
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.recent_gigs.length === 0 ? (
              <p className="text-xs text-muted-foreground font-mono">No open gigs.</p>
            ) : data.recent_gigs.map((g) => (
              <div key={g.id} className="flex items-center justify-between p-2 rounded-lg bg-background/40 border border-border/20">
                <div>
                  <div className="text-xs font-medium">{g.title}</div>
                  <div className="text-[10px] text-muted-foreground font-mono">{g.gig_type} · {g.university}</div>
                </div>
                {g.budget_vit > 0 && (
                  <Badge className="font-mono text-[10px] bg-amber-500/20 text-amber-400 border-amber-500/30">
                    <Coins className="w-2.5 h-2.5 mr-1" />{g.budget_vit} VIT
                  </Badge>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ─── Circles tab ─────────────────────────────────────────────────────────────

function CirclesTab() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", description: "", university: "", circle_type: "general" });
  const [activeCircle, setActiveCircle] = useState<Circle | null>(null);
  const [postContent, setPostContent] = useState("");

  const { data: circles = [], isLoading } = useQuery<Circle[]>({
    queryKey: ["campus-circles"],
    queryFn: () => apiGet("/api/campus/circles"),
  });

  const { data: posts = [] } = useQuery({
    queryKey: ["campus-posts", activeCircle?.id],
    queryFn: () => apiGet(`/api/campus/circles/${activeCircle!.id}/posts`),
    enabled: !!activeCircle,
  });

  const createCircle = useMutation({
    mutationFn: (d: typeof form) => apiPost("/api/campus/circles", d),
    onSuccess: () => { toast.success("Circle created!"); qc.invalidateQueries({ queryKey: ["campus-circles"] }); setCreating(false); },
    onError: (e: any) => toast.error(e?.message || "Failed to create circle"),
  });

  const createPost = useMutation({
    mutationFn: ({ id, content }: { id: number; content: string }) =>
      apiPost(`/api/campus/circles/${id}/posts`, { content }),
    onSuccess: () => { toast.success("Post added!"); qc.invalidateQueries({ queryKey: ["campus-posts", activeCircle?.id] }); setPostContent(""); },
    onError: (e: any) => toast.error(e?.message || "Failed to post"),
  });

  const upvote = useMutation({
    mutationFn: ({ circleId, postId }: { circleId: number; postId: number }) =>
      apiPost(`/api/campus/circles/${circleId}/posts/${postId}/upvote`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["campus-posts", activeCircle?.id] }),
  });

  if (isLoading) return <LoadingState />;

  if (activeCircle) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setActiveCircle(null)} className="font-mono text-xs gap-1">
            ← Back
          </Button>
          <h2 className="font-bold">{activeCircle.name}</h2>
          <Badge variant="outline" className="font-mono text-[10px]">{activeCircle.member_count} members</Badge>
        </div>

        <div className="flex gap-2">
          <Textarea
            placeholder="Share something with the circle..."
            className="text-sm resize-none h-20"
            value={postContent}
            onChange={(e) => setPostContent(e.target.value)}
          />
          <Button
            size="sm"
            onClick={() => createPost.mutate({ id: activeCircle.id, content: postContent })}
            disabled={!postContent.trim() || createPost.isPending}
            className="self-end"
          >Post</Button>
        </div>

        <div className="space-y-3">
          {(posts as any[]).length === 0 ? (
            <EmptyState title="No posts yet" description="Be the first to post in this circle." />
          ) : (posts as any[]).map((p) => (
            <Card key={p.id} className="bg-card/50 border-border/40">
              <CardContent className="p-4 space-y-2">
                <p className="text-sm">{p.content}</p>
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground font-mono">{p.created_at?.slice(0, 16)}</span>
                  <Button
                    variant="ghost" size="sm"
                    className="h-7 gap-1 text-[10px] font-mono"
                    onClick={() => upvote.mutate({ circleId: activeCircle.id, postId: p.id })}
                  >
                    <ThumbsUp className="w-3 h-3" /> {p.upvotes}
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-mono">{circles.length} circle{circles.length !== 1 ? "s" : ""}</span>
        <Button size="sm" onClick={() => setCreating(!creating)} className="gap-1 font-mono text-xs">
          <Plus className="w-3.5 h-3.5" /> New Circle
        </Button>
      </div>

      {creating && (
        <Card className="bg-card/50 border-primary/30">
          <CardContent className="p-4 space-y-3">
            <Input placeholder="Circle name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            <Input placeholder="University" value={form.university} onChange={(e) => setForm({ ...form, university: e.target.value })} />
            <Textarea placeholder="Description (optional)" className="resize-none h-16" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => createCircle.mutate(form)} disabled={!form.name || !form.university || createCircle.isPending}>
                Create
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setCreating(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {circles.length === 0 ? (
        <EmptyState title="No circles yet" description="Create the first circle for your university." />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {circles.map((c) => (
            <Card
              key={c.id}
              className="bg-card/50 border-border/40 hover:border-primary/50 transition-colors cursor-pointer"
              onClick={() => setActiveCircle(c)}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <div className="font-medium text-sm">{c.name}</div>
                    <div className="text-[10px] text-muted-foreground font-mono">{c.university}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>
                {c.description && <p className="text-xs text-muted-foreground mb-2 line-clamp-2">{c.description}</p>}
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-[10px]">{c.circle_type}</Badge>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    <Users className="w-2.5 h-2.5 mr-1" />{c.member_count}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Gigs tab ─────────────────────────────────────────────────────────────────

function GigsTab() {
  const qc = useQueryClient();
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: "", description: "", gig_type: "general", budget_vit: 0, budget_ngn: 0, university: "" });

  const { data: gigs = [], isLoading } = useQuery<Gig[]>({
    queryKey: ["campus-gigs"],
    queryFn: () => apiGet("/api/campus/gigs"),
  });

  const createGig = useMutation({
    mutationFn: (d: typeof form) => apiPost("/api/campus/gigs", d),
    onSuccess: () => { toast.success("Gig posted!"); qc.invalidateQueries({ queryKey: ["campus-gigs"] }); setCreating(false); },
    onError: (e: any) => toast.error(e?.message || "Failed to post gig"),
  });

  const applyGig = useMutation({
    mutationFn: (id: number) => apiPost(`/api/campus/gigs/${id}/apply`, {}),
    onSuccess: () => { toast.success("Applied! You're now assigned."); qc.invalidateQueries({ queryKey: ["campus-gigs"] }); },
    onError: (e: any) => toast.error(e?.message || "Failed to apply"),
  });

  if (isLoading) return <LoadingState />;

  const statusColor: Record<string, string> = {
    open: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    assigned: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    completed: "bg-muted text-muted-foreground",
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground font-mono">{gigs.filter((g) => g.status === "open").length} open gig{gigs.length !== 1 ? "s" : ""}</span>
        <Button size="sm" onClick={() => setCreating(!creating)} className="gap-1 font-mono text-xs">
          <Plus className="w-3.5 h-3.5" /> Post Gig
        </Button>
      </div>

      {creating && (
        <Card className="bg-card/50 border-primary/30">
          <CardContent className="p-4 space-y-3">
            <Input placeholder="Gig title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Input placeholder="University" value={form.university} onChange={(e) => setForm({ ...form, university: e.target.value })} />
            <Textarea placeholder="Describe the gig..." className="resize-none h-20" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input placeholder="VITCoin reward" type="number" min={0} value={form.budget_vit || ""} onChange={(e) => setForm({ ...form, budget_vit: parseFloat(e.target.value) || 0 })} />
              <Input placeholder="NGN reward" type="number" min={0} value={form.budget_ngn || ""} onChange={(e) => setForm({ ...form, budget_ngn: parseFloat(e.target.value) || 0 })} />
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={() => createGig.mutate(form)} disabled={!form.title || !form.university || createGig.isPending}>Post</Button>
              <Button size="sm" variant="ghost" onClick={() => setCreating(false)}>Cancel</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {gigs.length === 0 ? (
        <EmptyState title="No gigs yet" description="Post the first micro-task for your campus." />
      ) : (
        <div className="space-y-3">
          {gigs.map((g) => (
            <Card key={g.id} className="bg-card/50 border-border/40">
              <CardContent className="p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-medium text-sm">{g.title}</span>
                      <Badge className={`font-mono text-[10px] ${statusColor[g.status] ?? ""}`}>
                        {g.status === "open" ? <><CheckCircle2 className="w-2.5 h-2.5 mr-1" />Open</> :
                         g.status === "assigned" ? <><Clock className="w-2.5 h-2.5 mr-1" />Assigned</> :
                         "Completed"}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 mb-2">{g.description}</p>
                    <div className="flex flex-wrap gap-1.5">
                      <Badge variant="outline" className="font-mono text-[10px]">{g.gig_type}</Badge>
                      <Badge variant="outline" className="font-mono text-[10px]">{g.university}</Badge>
                      {g.budget_vit > 0 && (
                        <Badge className="font-mono text-[10px] bg-amber-500/20 text-amber-400 border-amber-500/30">
                          <Coins className="w-2.5 h-2.5 mr-1" />{g.budget_vit} VIT
                        </Badge>
                      )}
                      {g.budget_ngn > 0 && (
                        <Badge className="font-mono text-[10px] bg-green-500/20 text-green-400 border-green-500/30">
                          ₦{g.budget_ngn.toLocaleString()}
                        </Badge>
                      )}
                    </div>
                  </div>
                  {g.status === "open" && (
                    <Button size="sm" variant="outline" className="font-mono text-xs shrink-0"
                      onClick={() => applyGig.mutate(g.id)} disabled={applyGig.isPending}>
                      Apply
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Shared helpers ───────────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="h-48 flex items-center justify-center font-mono text-muted-foreground text-xs">
      LOADING...
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function CampusPage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold font-mono tracking-tight">Campus Hub</h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">
          Circles · Gigs · Resources · Leaderboard
        </p>
      </header>

      <Tabs defaultValue="overview">
        <TabsList className="font-mono text-xs">
          <TabsTrigger value="overview" className="gap-1.5">
            <LayoutGrid className="w-3.5 h-3.5" /> Overview
          </TabsTrigger>
          <TabsTrigger value="circles" className="gap-1.5">
            <Users className="w-3.5 h-3.5" /> Circles
          </TabsTrigger>
          <TabsTrigger value="gigs" className="gap-1.5">
            <Briefcase className="w-3.5 h-3.5" /> Gigs
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-4"><OverviewTab /></TabsContent>
        <TabsContent value="circles" className="mt-4"><CirclesTab /></TabsContent>
        <TabsContent value="gigs" className="mt-4"><GigsTab /></TabsContent>
      </Tabs>
    </div>
  );
}
