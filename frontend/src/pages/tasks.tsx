import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "wouter";
import { apiGet, apiPost } from "@/lib/apiClient";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { CheckCircle, Clock, Trophy, Zap, Target, Star, ArrowRight, ExternalLink } from "lucide-react";
import { toast } from "sonner";

interface TaskActionRowProps {
  task: { id: number; task_type: string; required_count: number };
  status: "not_started" | "in_progress" | "completed" | string;
  canUpdate: boolean;
  ready: boolean;
  pending: boolean;
  actionUrl: string | null;
  onUpdate: () => void;
}

function TaskActionRow({
  task,
  status,
  canUpdate,
  ready,
  pending,
  actionUrl,
  onUpdate,
}: TaskActionRowProps) {
  const isCompleted = status === "completed";
  const isExternal = actionUrl?.startsWith("http://") || actionUrl?.startsWith("https://");
  const goLabel = ready ? "Open" : isCompleted ? "Revisit" : "Go";

  return (
    <div className="flex items-center gap-2 pt-2 border-t border-border/50">
      {actionUrl ? (
        isExternal ? (
          <a
            href={actionUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-mono text-primary hover:underline"
          >
            {goLabel}
            <ExternalLink className="h-3 w-3" />
          </a>
        ) : (
          <Link href={actionUrl}>
            <span className="inline-flex items-center gap-1.5 text-xs font-mono text-primary hover:underline cursor-pointer">
              {goLabel}
              <ArrowRight className="h-3 w-3" />
            </span>
          </Link>
        )
      ) : (
        <span className="text-xs text-muted-foreground font-mono">No quick link</span>
      )}

      <div className="ml-auto">
        {isCompleted ? (
          <Badge variant="outline" className="font-mono text-[10px] border-emerald-500/40 text-emerald-400">
            Completed
          </Badge>
        ) : ready ? (
          <Button
            size="sm"
            onClick={onUpdate}
            disabled={pending}
            className="h-7 text-xs font-mono"
          >
            {pending ? "Claiming…" : "Claim Reward"}
          </Button>
        ) : canUpdate ? (
          <Button
            size="sm"
            variant="outline"
            onClick={onUpdate}
            disabled={pending}
            className="h-7 text-xs font-mono"
          >
            {pending ? "Updating…" : "Mark Progress"}
          </Button>
        ) : (
          <span className="text-[10px] text-muted-foreground font-mono uppercase tracking-wider">
            Locked
          </span>
        )}
      </div>
    </div>
  );
}

interface TaskCategory {
  id: number;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  sort_order: number;
  is_active: boolean;
  created_at: string;
}

interface Task {
  id: number;
  category_id: number;
  category: TaskCategory;
  title: string;
  description: string;
  short_description?: string;
  task_type: string;
  status: string;
  required_count: number;
  max_completions: number;
  vit_reward: number;
  xp_reward: number;
  expires_at?: string;
  icon?: string;
  color?: string;
  is_featured: boolean;
  requirements: Record<string, any>;
  action_url?: string | null;
  action_label?: string | null;
  created_at: string;
}

interface UserTaskCompletion {
  id: number;
  task_id: number;
  task: Task;
  current_progress: number;
  required_progress: number;
  is_completed: boolean;
  completed_count: number;
  last_completed_at?: string;
  next_reset_at?: string;
  total_vit_earned: number;
  total_xp_earned: number;
}

interface TaskStats {
  total_tasks_attempted: number;
  total_completions: number;
  total_vit_earned: number;
  total_xp_earned: number;
}

export default function TasksPage() {
  const [selectedCategory, setSelectedCategory] = useState<number | null>(null);
  const queryClient = useQueryClient();

  // Fetch task categories
  const { data: categories = [] } = useQuery({
    queryKey: ["task-categories"],
    queryFn: () => apiGet<TaskCategory[]>("/api/tasks/categories"),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Fetch available tasks
  const { data: tasks = [] } = useQuery({
    queryKey: ["tasks", selectedCategory],
    queryFn: () =>
      apiGet<Task[]>(`/api/tasks${selectedCategory ? `?category_id=${selectedCategory}` : ""}`),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Fetch user progress
  const { data: userProgress = [] } = useQuery({
    queryKey: ["user-task-progress"],
    queryFn: () => apiGet<UserTaskCompletion[]>("/api/tasks/user/progress"),
    staleTime: 30 * 1000, // 30 seconds
  });

  // Fetch user stats
  const { data: userStats } = useQuery({
    queryKey: ["user-task-stats"],
    queryFn: () => apiGet<TaskStats>("/api/tasks/user/stats"),
    staleTime: 60 * 1000, // 1 minute
  });

  // Update task progress mutation
  interface TaskProgressResult {
    is_completed: boolean;
    vit_earned: number;
    xp_earned: number;
    current_progress: number;
    required_progress: number;
  }
  const updateProgressMutation = useMutation({
    mutationFn: (taskId: number) => apiPost<TaskProgressResult>(`/api/tasks/${taskId}/progress`),
    onSuccess: (data, taskId) => {
      queryClient.invalidateQueries({ queryKey: ["user-task-progress"] });
      queryClient.invalidateQueries({ queryKey: ["user-task-stats"] });

      if (data.is_completed) {
        toast.success(`Task completed! Earned ${data.vit_earned} VIT and ${data.xp_earned} XP!`, {
          icon: <Trophy className="h-4 w-4" />,
        });
      } else {
        toast.success(`Progress updated! ${data.current_progress}/${data.required_progress}`);
      }
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to update task progress");
    },
  });

  // Create progress map for quick lookup
  const progressMap = new Map(userProgress.map(p => [p.task_id, p]));

  const getTaskStatus = (task: Task) => {
    const progress = progressMap.get(task.id);
    if (!progress) return "not_started";
    if (progress.is_completed) return "completed";
    return "in_progress";
  };

  const getTaskProgress = (task: Task) => {
    const progress = progressMap.get(task.id);
    return progress || { current_progress: 0, required_progress: task.required_count };
  };

  const canUpdateProgress = (task: Task) => {
    const progress = progressMap.get(task.id);
    if (!progress) return true;
    if (task.task_type === "one_time" && progress.is_completed) return false;
    if (progress.completed_count >= task.max_completions) return false;
    return true;
  };

  const handleUpdateProgress = (taskId: number) => {
    updateProgressMutation.mutate(taskId);
  };

  const getTaskTypeIcon = (taskType: string) => {
    switch (taskType) {
      case "daily": return <Clock className="h-4 w-4" />;
      case "weekly": return <Target className="h-4 w-4" />;
      case "monthly": return <Star className="h-4 w-4" />;
      case "progress": return <Zap className="h-4 w-4" />;
      default: return <CheckCircle className="h-4 w-4" />;
    }
  };

  const getTaskTypeLabel = (taskType: string) => {
    switch (taskType) {
      case "daily": return "Daily";
      case "weekly": return "Weekly";
      case "monthly": return "Monthly";
      case "progress": return "Progress";
      default: return "One-time";
    }
  };

  // Smart action-URL inference — uses the explicit task.action_url if set,
  // otherwise scans the title/description for a known section keyword and
  // returns the matching page. Returns null if nothing relevant matches.
  const inferActionUrl = (task: Task): string | null => {
    if (task.action_url) return task.action_url;
    const t = (task.title + " " + task.description + " " + (task.short_description ?? "")).toLowerCase();
    if (/(predict|tip|forecast)/.test(t)) return "/predictions";
    if (/(accumulator|acca|parlay|combo)/.test(t)) return "/accumulator";
    if (/(match|fixture|game)/.test(t)) return "/matches";
    if (/(refer|invite|friend)/.test(t)) return "/referral";
    if (/(wallet|deposit|stake|withdraw|balance)/.test(t)) return "/wallet";
    if (/(validator|validate|verify)/.test(t)) return "/validators";
    if (/(training|course|learn|tutorial|study)/.test(t)) return "/training";
    if (/(leaderboard|rank|standing)/.test(t)) return "/leaderboard";
    if (/(marketplace|listing|model.*sell|buy.*model)/.test(t)) return "/marketplace";
    if (/(profile|settings|account)/.test(t)) return "/settings";
    if (/(analytics|insight|stats|chart)/.test(t)) return "/analytics";
    if (/(odds|line|spread)/.test(t)) return "/odds";
    if (/(governance|vote|proposal)/.test(t)) return "/governance";
    if (/(subscribe|subscription|premium|pro plan)/.test(t)) return "/subscription";
    return null;
  };

  // A task is "ready to claim" when the user has met the requirement count
  // but the completion API hasn't yet been called to award the reward.
  const isReadyToClaim = (task: Task) => {
    const p = progressMap.get(task.id);
    return !!p && !p.is_completed && p.current_progress >= p.required_progress;
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Tasks</h1>
        <p className="text-muted-foreground">
          Complete tasks to earn VIT rewards and XP. Build your reputation and unlock new features.
        </p>
      </div>

      {/* KPI summary strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: "Completed",  value: userStats?.total_completions ?? 0,                       icon: CheckCircle, tint: "text-emerald-400", bg: "bg-emerald-500/10", ring: "border-emerald-500/30" },
          { label: "VIT Earned", value: (userStats?.total_vit_earned ?? 0).toFixed(2),           icon: Zap,         tint: "text-yellow-400",  bg: "bg-yellow-500/10",  ring: "border-yellow-500/30" },
          { label: "XP Earned",  value: userStats?.total_xp_earned ?? 0,                         icon: Trophy,      tint: "text-blue-400",    bg: "bg-blue-500/10",    ring: "border-blue-500/30" },
          { label: "Attempted",  value: userStats?.total_tasks_attempted ?? 0,                   icon: Target,      tint: "text-cyan-400",    bg: "bg-cyan-500/10",    ring: "border-cyan-500/30" },
        ].map((kpi) => (
          <Card key={kpi.label} className={`${kpi.ring} transition-colors`}>
            <CardContent className="p-4 flex items-center justify-between">
              <div className="min-w-0">
                <div className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono truncate">{kpi.label}</div>
                <div className={`text-3xl font-bold mt-1 ${kpi.tint} font-mono tabular-nums`}>{kpi.value}</div>
              </div>
              <div className={`p-2.5 rounded-lg ${kpi.bg}`}>
                <kpi.icon className={`w-5 h-5 ${kpi.tint}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Tabs defaultValue="all" className="space-y-6">
        <TabsList>
          <TabsTrigger value="all">All Tasks</TabsTrigger>
          <TabsTrigger value="featured">Featured</TabsTrigger>
          <TabsTrigger value="progress">My Progress</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-6">
          {/* Category Filter */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={selectedCategory === null ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All Categories
            </Button>
            {categories.map((category) => (
              <Button
                key={category.id}
                variant={selectedCategory === category.id ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(category.id)}
              >
                {category.icon && <span className="mr-2">{category.icon}</span>}
                {category.name}
              </Button>
            ))}
          </div>

          {/* Tasks Grid */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tasks.map((task) => {
              const status = getTaskStatus(task);
              const progress = getTaskProgress(task);
              const canUpdate = canUpdateProgress(task);

              return (
                <Card key={task.id} className={`relative ${task.is_featured ? 'ring-2 ring-primary' : ''}`}>
                  {task.is_featured && (
                    <div className="absolute -top-2 -right-2 bg-primary text-primary-foreground px-2 py-1 rounded-full text-xs font-medium">
                      Featured
                    </div>
                  )}

                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg">{task.title}</CardTitle>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {getTaskTypeIcon(task.task_type)}
                            <span className="ml-1">{getTaskTypeLabel(task.task_type)}</span>
                          </Badge>
                          <Badge variant="outline" className="text-xs">
                            {task.category.name}
                          </Badge>
                        </div>
                      </div>
                      {status === "completed" && (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <CardDescription className="text-sm">
                      {task.short_description || task.description}
                    </CardDescription>

                    {/* Rewards */}
                    <div className="flex items-center gap-4 text-sm">
                      {task.vit_reward > 0 && (
                        <div className="flex items-center gap-1">
                          <Zap className="h-4 w-4 text-yellow-500" />
                          <span className="font-medium">{task.vit_reward} VIT</span>
                        </div>
                      )}
                      {task.xp_reward > 0 && (
                        <div className="flex items-center gap-1">
                          <Trophy className="h-4 w-4 text-blue-500" />
                          <span className="font-medium">{task.xp_reward} XP</span>
                        </div>
                      )}
                    </div>

                    {/* Progress */}
                    {status === "in_progress" && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Progress</span>
                          <span>{progress.current_progress}/{progress.required_progress}</span>
                        </div>
                        <Progress
                          value={(progress.current_progress / progress.required_progress) * 100}
                          className="h-2"
                        />
                      </div>
                    )}

                    {/* Action Row — "Go" link + "Mark Progress" button */}
                    <TaskActionRow
                      task={task}
                      status={status}
                      canUpdate={canUpdate}
                      ready={isReadyToClaim(task)}
                      pending={updateProgressMutation.isPending}
                      actionUrl={inferActionUrl(task)}
                      onUpdate={() => handleUpdateProgress(task.id)}
                    />
                  </CardContent>
                </Card>
              );
            })}
          </div>

          {tasks.length === 0 && (
            <div className="text-center py-12">
              <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">No tasks available</h3>
              <p className="text-muted-foreground">
                Check back later for new tasks to complete.
              </p>
            </div>
          )}
        </TabsContent>

        <TabsContent value="featured" className="space-y-6">
          {/* Featured tasks - same grid but filtered */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {tasks.filter(task => task.is_featured).map((task) => {
              const status = getTaskStatus(task);
              const progress = getTaskProgress(task);
              const canUpdate = canUpdateProgress(task);

              return (
                <Card key={task.id} className="ring-2 ring-primary">
                  <div className="absolute -top-2 -right-2 bg-primary text-primary-foreground px-2 py-1 rounded-full text-xs font-medium">
                    Featured
                  </div>

                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <CardTitle className="text-lg">{task.title}</CardTitle>
                        <div className="flex items-center gap-2">
                          <Badge variant="secondary" className="text-xs">
                            {getTaskTypeIcon(task.task_type)}
                            <span className="ml-1">{getTaskTypeLabel(task.task_type)}</span>
                          </Badge>
                        </div>
                      </div>
                      {status === "completed" && (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      )}
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    <CardDescription className="text-sm">
                      {task.short_description || task.description}
                    </CardDescription>

                    <div className="flex items-center gap-4 text-sm">
                      {task.vit_reward > 0 && (
                        <div className="flex items-center gap-1">
                          <Zap className="h-4 w-4 text-yellow-500" />
                          <span className="font-medium">{task.vit_reward} VIT</span>
                        </div>
                      )}
                      {task.xp_reward > 0 && (
                        <div className="flex items-center gap-1">
                          <Trophy className="h-4 w-4 text-blue-500" />
                          <span className="font-medium">{task.xp_reward} XP</span>
                        </div>
                      )}
                    </div>

                    {status === "in_progress" && (
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span>Progress</span>
                          <span>{progress.current_progress}/{progress.required_progress}</span>
                        </div>
                        <Progress
                          value={(progress.current_progress / progress.required_progress) * 100}
                          className="h-2"
                        />
                      </div>
                    )}

                    <TaskActionRow
                      task={task}
                      status={status}
                      canUpdate={canUpdate}
                      ready={isReadyToClaim(task)}
                      pending={updateProgressMutation.isPending}
                      actionUrl={inferActionUrl(task)}
                      onUpdate={() => handleUpdateProgress(task.id)}
                    />
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="progress" className="space-y-6">
          {/* User Progress */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {userProgress.map((completion) => (
              <Card key={completion.id}>
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <CardTitle className="text-lg">{completion.task.title}</CardTitle>
                      <div className="flex items-center gap-2">
                        <Badge variant="secondary" className="text-xs">
                          {getTaskTypeIcon(completion.task.task_type)}
                          <span className="ml-1">{getTaskTypeLabel(completion.task.task_type)}</span>
                        </Badge>
                        {completion.is_completed && (
                          <Badge variant="default" className="text-xs bg-green-500">
                            <CheckCircle className="h-3 w-3 mr-1" />
                            Completed
                          </Badge>
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between text-sm">
                      <span>Progress</span>
                      <span>{completion.current_progress}/{completion.required_progress}</span>
                    </div>
                    <Progress
                      value={(completion.current_progress / completion.required_progress) * 100}
                      className="h-2"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="text-muted-foreground">Completions</div>
                      <div className="font-medium">{completion.completed_count}</div>
                    </div>
                    <div>
                      <div className="text-muted-foreground">VIT Earned</div>
                      <div className="font-medium">{completion.total_vit_earned.toFixed(2)}</div>
                    </div>
                  </div>

                  {completion.last_completed_at && (
                    <div className="text-xs text-muted-foreground">
                      Last completed: {new Date(completion.last_completed_at).toLocaleDateString()}
                    </div>
                  )}

                  {completion.next_reset_at && (
                    <div className="text-xs text-muted-foreground">
                      Resets: {new Date(completion.next_reset_at).toLocaleDateString()}
                    </div>
                  )}

                  <TaskActionRow
                    task={completion.task}
                    status={completion.is_completed ? "completed" : "in_progress"}
                    canUpdate={canUpdateProgress(completion.task)}
                    ready={!completion.is_completed && completion.current_progress >= completion.required_progress}
                    pending={updateProgressMutation.isPending}
                    actionUrl={inferActionUrl(completion.task)}
                    onUpdate={() => handleUpdateProgress(completion.task_id)}
                  />
                </CardContent>
              </Card>
            ))}
          </div>

          {userProgress.length === 0 && (
            <div className="text-center py-12">
              <Target className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium">No tasks started yet</h3>
              <p className="text-muted-foreground">
                Start completing tasks to track your progress here.
              </p>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}