import { useState, useEffect, useRef, useCallback } from "react";
import { Bell, Check, CheckCheck, Settings, X } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";

interface Notification {
  id: number;
  type: string;
  title: string;
  body: string;
  is_read: boolean;
  channel: string;
  created_at: string;
}

interface Preferences {
  prediction_alerts: boolean;
  match_results: boolean;
  wallet_activity: boolean;
  validator_rewards: boolean;
  subscription_expiry: boolean;
  email_enabled: boolean;
  telegram_enabled: boolean;
  in_app_enabled: boolean;
}

const TYPE_ICONS: Record<string, string> = {
  prediction_alert: "🎯",
  match_result: "⚽",
  wallet_activity: "💰",
  validator_reward: "🏆",
  subscription_expiry: "⚠️",
  system: "🔔",
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

export function NotificationBell() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const { data: countData } = useQuery<{ unread_count: number }>({
    queryKey: ["notifications", "count"],
    queryFn: () => apiGet("/api/notifications/unread-count"),
    refetchInterval: 30000,
    enabled: !!user,
  });

  const { data: notifications = [] } = useQuery<Notification[]>({
    queryKey: ["notifications", "list"],
    queryFn: () => apiGet("/api/notifications?limit=20"),
    enabled: open && !!user,
  });

  const { data: prefs } = useQuery<Preferences>({
    queryKey: ["notifications", "prefs"],
    queryFn: () => apiGet("/api/notifications/preferences"),
    enabled: showPrefs && !!user,
  });

  const markRead = useMutation({
    mutationFn: (id: number) => apiPatch(`/api/notifications/${id}/read`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const markAllRead = useMutation({
    mutationFn: () => apiPost("/api/notifications/read-all"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  const updatePrefs = useMutation({
    mutationFn: (updates: Partial<Preferences>) =>
      apiPatch("/api/notifications/preferences", updates),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["notifications", "prefs"] });
    },
  });

  // WebSocket for real-time push
  useEffect(() => {
    if (!user) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    const ws = new WebSocket(`${proto}://${host}/api/notifications/ws/${user.id}`);
    ws.onmessage = () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
    };
    return () => ws.close();
  }, [user, qc]);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowPrefs(false);
      }
    }
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const unread = countData?.unread_count ?? 0;

  if (!user) return null;

  return (
    <div className="relative" ref={panelRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => { setOpen((o) => !o); setShowPrefs(false); }}
        aria-label="Notifications"
      >
        <Bell className="w-5 h-5 text-muted-foreground" />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 bg-primary text-primary-foreground text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </Button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 bg-background border border-border rounded-lg shadow-xl overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-border">
            {showPrefs ? (
              <>
                <span className="text-sm font-semibold text-foreground">Notification Settings</span>
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setShowPrefs(false)}>
                  <X className="w-4 h-4" />
                </Button>
              </>
            ) : (
              <>
                <span className="text-sm font-semibold text-foreground">Notifications</span>
                <div className="flex gap-1">
                  {unread > 0 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      title="Mark all as read"
                      onClick={() => markAllRead.mutate()}
                    >
                      <CheckCheck className="w-4 h-4 text-muted-foreground" />
                    </Button>
                  )}
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7"
                    title="Preferences"
                    onClick={() => setShowPrefs(true)}
                  >
                    <Settings className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </div>
              </>
            )}
          </div>

          {/* Preferences Panel */}
          {showPrefs && prefs && (
            <div className="p-4 space-y-4 max-h-96 overflow-y-auto">
              <p className="text-xs text-muted-foreground mb-2">Choose what alerts you receive.</p>

              <p className="text-xs font-semibold text-foreground uppercase tracking-wide">Notification Types</p>
              {([
                ["prediction_alerts", "Prediction Alerts"],
                ["match_results", "Match Results"],
                ["wallet_activity", "Wallet Activity"],
                ["validator_rewards", "Validator Rewards"],
                ["subscription_expiry", "Subscription Expiry"],
              ] as [keyof Preferences, string][]).map(([key, label]) => (
                <div key={key} className="flex items-center justify-between">
                  <Label htmlFor={key} className="text-sm text-foreground">{label}</Label>
                  <Switch
                    id={key}
                    checked={!!prefs[key]}
                    onCheckedChange={(val) => updatePrefs.mutate({ [key]: val })}
                  />
                </div>
              ))}

              <p className="text-xs font-semibold text-foreground uppercase tracking-wide pt-2">Channels</p>
              {([
                ["in_app_enabled", "In-App"],
                ["email_enabled", "Email"],
                ["telegram_enabled", "Telegram"],
              ] as [keyof Preferences, string][]).map(([key, label]) => (
                <div key={key} className="flex items-center justify-between">
                  <Label htmlFor={key} className="text-sm text-foreground">{label}</Label>
                  <Switch
                    id={key}
                    checked={!!prefs[key]}
                    onCheckedChange={(val) => updatePrefs.mutate({ [key]: val })}
                  />
                </div>
              ))}
            </div>
          )}

          {/* Notification List */}
          {!showPrefs && (
            <div className="max-h-96 overflow-y-auto divide-y divide-border">
              {notifications.length === 0 ? (
                <div className="py-10 text-center text-sm text-muted-foreground">
                  No notifications yet
                </div>
              ) : (
                notifications.map((n) => (
                  <div
                    key={n.id}
                    className={`flex gap-3 px-4 py-3 hover:bg-muted/40 transition-colors cursor-pointer ${
                      !n.is_read ? "bg-primary/5" : ""
                    }`}
                    onClick={() => !n.is_read && markRead.mutate(n.id)}
                  >
                    <span className="text-xl leading-none mt-0.5">
                      {TYPE_ICONS[n.type] ?? "🔔"}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm truncate ${!n.is_read ? "font-semibold text-foreground" : "text-foreground"}`}>
                          {n.title}
                        </p>
                        {!n.is_read && (
                          <span className="mt-1 w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-2 mt-0.5">{n.body}</p>
                      <p className="text-[10px] text-muted-foreground/60 mt-1">{timeAgo(n.created_at)}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
