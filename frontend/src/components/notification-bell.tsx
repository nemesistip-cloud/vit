import { useState, useEffect, useRef } from "react";
import { Bell, Check, CheckCheck, Settings, X, ExternalLink, Link2, Link2Off, Send, FlaskConical } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost, apiPatch } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

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
  validator_status: boolean;
  email_enabled: boolean;
  telegram_enabled: boolean;
  in_app_enabled: boolean;
  telegram_chat_id: string | null;
  telegram_linked: boolean;
}

interface TelegramLinkInfo {
  bot_username: string;
  link_url: string;
  code: string;
  expires_in: number;
  already_linked: boolean;
}

const TYPE_ICONS: Record<string, string> = {
  prediction_alert: "🎯",
  match_result: "⚽",
  wallet_activity: "💰",
  validator_reward: "🏆",
  subscription_expiry: "⚠️",
  validator_status: "🛡️",
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
  const [showTgLink, setShowTgLink] = useState(false);
  const [manualChatId, setManualChatId] = useState("");
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

  const { data: prefs, refetch: refetchPrefs } = useQuery<Preferences>({
    queryKey: ["notifications", "prefs"],
    queryFn: () => apiGet("/api/notifications/preferences"),
    enabled: showPrefs && !!user,
  });

  const { data: tgLinkInfo, refetch: fetchLinkInfo } = useQuery<TelegramLinkInfo>({
    queryKey: ["notifications", "tg-link"],
    queryFn: () => apiGet("/api/notifications/telegram/link-info"),
    enabled: false,
  });

  const markRead = useMutation({
    mutationFn: (id: number) => apiPatch(`/api/notifications/${id}/read`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const markAllRead = useMutation({
    mutationFn: () => apiPost("/api/notifications/read-all"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  });

  const updatePrefs = useMutation({
    mutationFn: (updates: Partial<Preferences>) =>
      apiPatch("/api/notifications/preferences", updates),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications", "prefs"] }),
  });

  const sendTest = useMutation({
    mutationFn: () => apiPost("/api/notifications/test"),
    onSuccess: (data: any) => {
      const r = data?.results ?? {};
      const lines = Object.entries(r)
        .map(([ch, status]) => `${ch}: ${status}`)
        .join(" · ");
      toast.success("Test sent", { description: lines });
    },
    onError: () => toast.error("Test notification failed"),
  });

  const tgUnlink = useMutation({
    mutationFn: () => apiPost("/api/notifications/telegram/unlink"),
    onSuccess: () => {
      toast.success("Telegram unlinked");
      qc.invalidateQueries({ queryKey: ["notifications", "prefs"] });
      setShowTgLink(false);
    },
    onError: () => toast.error("Unlink failed"),
  });

  const tgManualLink = useMutation({
    mutationFn: () =>
      apiPost("/api/notifications/telegram/link-manual", { chat_id: manualChatId }),
    onSuccess: () => {
      toast.success("Telegram linked! Check your Telegram for a confirmation message.");
      setManualChatId("");
      setShowTgLink(false);
      qc.invalidateQueries({ queryKey: ["notifications", "prefs"] });
    },
    onError: (err: any) =>
      toast.error(err?.message ?? "Could not link — make sure you started the bot first."),
  });

  // WebSocket for real-time push with exponential-backoff reconnect
  useEffect(() => {
    if (!user) return;
    let ws: WebSocket | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let attempt = 0;
    let destroyed = false;

    function connect() {
      if (destroyed) return;
      const proto = window.location.protocol === "https:" ? "wss" : "ws";
      const host = window.location.host;
      const jwt = localStorage.getItem("vit_token") ?? "";
      ws = new WebSocket(
        `${proto}://${host}/api/notifications/ws/${user!.id}?token=${encodeURIComponent(jwt)}`
      );
      ws.onopen = () => { attempt = 0; };
      ws.onmessage = (event) => {
        qc.invalidateQueries({ queryKey: ["notifications"] });
        try {
          const data = JSON.parse(event.data);
          if (data.type && data.title && data.type !== "unread_count") {
            const icon = TYPE_ICONS[data.type] ?? "🔔";
            toast(data.title, { description: data.body, icon, duration: 5000 });
          }
        } catch { /* non-JSON — ignore */ }
      };
      ws.onclose = () => {
        if (destroyed) return;
        const delay = Math.min(1000 * 2 ** attempt, 30000);
        attempt += 1;
        retryTimeout = setTimeout(connect, delay);
      };
    }

    connect();
    return () => {
      destroyed = true;
      if (retryTimeout) clearTimeout(retryTimeout);
      ws?.close();
    };
  }, [user, qc]);

  // Close on outside click
  useEffect(() => {
    function handler(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setOpen(false);
        setShowPrefs(false);
        setShowTgLink(false);
      }
    }
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  const unread = countData?.unread_count ?? 0;
  if (!user) return null;

  const handleGetBotLink = async () => {
    setShowTgLink(true);
    await fetchLinkInfo();
  };

  return (
    <div className="relative" ref={panelRef}>
      <Button
        variant="ghost"
        size="icon"
        className="relative"
        onClick={() => { setOpen((o) => !o); setShowPrefs(false); setShowTgLink(false); }}
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
                <span className="text-sm font-semibold text-foreground">
                  {showTgLink ? "Link Telegram" : "Notification Settings"}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7"
                  onClick={() => {
                    if (showTgLink) setShowTgLink(false);
                    else setShowPrefs(false);
                  }}
                >
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
          {showPrefs && !showTgLink && prefs && (
            <div className="p-4 space-y-4 max-h-[520px] overflow-y-auto">
              <p className="text-xs text-muted-foreground">Choose which alerts you receive.</p>

              {/* Notification types */}
              <p className="text-xs font-semibold text-foreground uppercase tracking-wide">Alert Types</p>
              {([
                ["prediction_alerts", "Prediction Alerts"],
                ["match_results", "Match Results"],
                ["wallet_activity", "Wallet Activity"],
                ["validator_rewards", "Validator Rewards"],
                ["validator_status", "Validator Status"],
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

              {/* Channels */}
              <p className="text-xs font-semibold text-foreground uppercase tracking-wide pt-2">Channels</p>

              {/* In-app */}
              <div className="flex items-center justify-between">
                <Label htmlFor="in_app_enabled" className="text-sm text-foreground">In-App</Label>
                <Switch
                  id="in_app_enabled"
                  checked={!!prefs.in_app_enabled}
                  onCheckedChange={(val) => updatePrefs.mutate({ in_app_enabled: val })}
                />
              </div>

              {/* Email */}
              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <Label htmlFor="email_enabled" className="text-sm text-foreground">Email</Label>
                  <Switch
                    id="email_enabled"
                    checked={!!prefs.email_enabled}
                    onCheckedChange={(val) => updatePrefs.mutate({ email_enabled: val })}
                  />
                </div>
                {prefs.email_enabled && (
                  <p className="text-[11px] text-muted-foreground pl-1">
                    Sent to your account email. Requires SMTP or Resend config.
                  </p>
                )}
              </div>

              {/* Telegram */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label htmlFor="telegram_enabled" className="text-sm text-foreground">Telegram</Label>
                  <Switch
                    id="telegram_enabled"
                    checked={!!prefs.telegram_enabled}
                    onCheckedChange={(val) => updatePrefs.mutate({ telegram_enabled: val })}
                  />
                </div>

                {/* Link status */}
                {prefs.telegram_linked ? (
                  <div className="flex items-center justify-between bg-emerald-950/40 border border-emerald-800/40 rounded-md px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Link2 className="w-3.5 h-3.5 text-emerald-400" />
                      <span className="text-xs text-emerald-300">Linked</span>
                      <span className="text-[10px] text-muted-foreground font-mono">
                        {prefs.telegram_chat_id}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-6 px-2 text-xs text-red-400 hover:text-red-300"
                      onClick={() => tgUnlink.mutate()}
                      disabled={tgUnlink.isPending}
                    >
                      <Link2Off className="w-3 h-3 mr-1" />
                      Unlink
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full text-xs h-7 gap-1.5"
                    onClick={handleGetBotLink}
                  >
                    <Link2 className="w-3.5 h-3.5" />
                    Link Telegram Account
                  </Button>
                )}
              </div>

              {/* Test notification button */}
              <div className="pt-2 border-t border-border">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full text-xs h-8 gap-2"
                  onClick={() => sendTest.mutate()}
                  disabled={sendTest.isPending}
                >
                  <FlaskConical className="w-3.5 h-3.5" />
                  {sendTest.isPending ? "Sending…" : "Send Test Notification"}
                </Button>
              </div>
            </div>
          )}

          {/* Telegram Linking Panel */}
          {showPrefs && showTgLink && (
            <div className="p-4 space-y-4 max-h-[520px] overflow-y-auto">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Link your Telegram account to receive VIT alerts as direct messages.
              </p>

              {/* Method 1: Bot deep-link */}
              <div className="space-y-2">
                <p className="text-xs font-semibold text-foreground uppercase tracking-wide">Option 1 — Bot Link</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Click the link below to open the VIT bot in Telegram, then tap
                  <strong className="text-foreground"> Start</strong>. Your account will be
                  linked automatically.
                </p>
                {tgLinkInfo ? (
                  <a
                    href={tgLinkInfo.link_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 w-full rounded-md border border-primary/40 bg-primary/10 px-3 py-2 text-xs text-primary hover:bg-primary/20 transition-colors"
                  >
                    <ExternalLink className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">t.me/{tgLinkInfo.bot_username}</span>
                    <span className="ml-auto text-[10px] text-muted-foreground flex-shrink-0">
                      expires {Math.round((tgLinkInfo.expires_in ?? 600) / 60)}m
                    </span>
                  </a>
                ) : (
                  <div className="text-xs text-muted-foreground italic px-1">Loading link…</div>
                )}
              </div>

              <div className="relative flex items-center gap-2">
                <div className="flex-1 h-px bg-border" />
                <span className="text-[11px] text-muted-foreground">or</span>
                <div className="flex-1 h-px bg-border" />
              </div>

              {/* Method 2: Manual chat_id */}
              <div className="space-y-2">
                <p className="text-xs font-semibold text-foreground uppercase tracking-wide">Option 2 — Enter Chat ID</p>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Message <strong className="text-foreground">@userinfobot</strong> on Telegram
                  to get your chat ID, then enter it below.
                </p>
                <div className="flex gap-2">
                  <Input
                    placeholder="e.g. 123456789"
                    value={manualChatId}
                    onChange={(e) => setManualChatId(e.target.value)}
                    className="h-8 text-xs flex-1"
                  />
                  <Button
                    size="sm"
                    className="h-8 px-3 text-xs gap-1"
                    onClick={() => tgManualLink.mutate()}
                    disabled={!manualChatId.trim() || tgManualLink.isPending}
                  >
                    <Send className="w-3 h-3" />
                    {tgManualLink.isPending ? "…" : "Link"}
                  </Button>
                </div>
                <p className="text-[11px] text-muted-foreground">
                  A test DM will be sent to confirm the ID is correct before linking.
                </p>
              </div>
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
