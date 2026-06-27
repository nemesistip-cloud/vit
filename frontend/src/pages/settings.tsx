import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import {
  User, Mail, Key, Shield, Bell, Moon, Sun,
  Monitor, Smartphone, Globe, ChevronRight,
  LogOut, CheckCircle, AlertCircle, Eye, EyeOff,
  QrCode, Trash2, Activity, Zap
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { useTheme } from "@/lib/theme";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function NotificationsCard() {
  return (
    <Card className="border-border/50">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-mono flex items-center gap-2">
          <Bell className="w-4 h-4 text-muted-foreground" />
          Notifications
        </CardTitle>
        <CardDescription className="font-mono text-xs">
          Manage your notification preferences.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-sm">Push Notifications</p>
            <p className="text-xs text-muted-foreground font-mono">Receive alerts about your predictions</p>
          </div>
          <Switch />
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-mono text-sm">Email Alerts</p>
            <p className="text-xs text-muted-foreground font-mono">Weekly summary and important updates</p>
          </div>
          <Switch />
        </div>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const [showSecret, setShowSecret] = useState(false);
  const [totp2faSetup, setTotp2faSetup] = useState<any>(null);

  const { data: totpStatus } = useQuery<any>({
    queryKey: ["/api/auth/totp/status"],
    queryFn: () => apiGet("/api/auth/totp/status"),
  });

  const handleSetup2FA = async () => {
    try {
      const data = await apiPost("/api/auth/totp/setup", {});
      setTotp2faSetup(data);
    } catch (err) {
      toast.error("Failed to initiate 2FA setup");
    }
  };

  const sections = [
    {
      title: "Intelligence & Terminal",
      items: [
        { icon: Monitor, label: "Advanced Analytics", desc: "Enable deep-learning signal analysis", toggle: true },
        { icon: Zap, label: "Fast Execution", desc: "Optimize for low-latency market updates", toggle: true },
      ]
    },
    {
      title: "Security & Access",
      items: [
        { icon: Shield, label: "Hardware Key", desc: "Use Yubikey or Titan for authentication" },
        { icon: Key, label: "Session Management", desc: "View and manage active terminal sessions" },
      ]
    }
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Configuration</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional Terminal Settings</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                {theme === "dark" ? <Moon className="w-4 h-4 text-blue-400" /> : <Sun className="w-4 h-4 text-yellow-400" />}
                Appearance
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-sm">Theme</p>
                  <p className="text-xs text-muted-foreground font-mono">Choose light or dark mode</p>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant={theme === "light" ? "default" : "outline"}
                    size="sm"
                    className="font-mono gap-1.5"
                    onClick={() => setTheme("light")}
                  >
                    <Sun className="w-3.5 h-3.5" /> Light
                  </Button>
                  <Button
                    variant={theme === "dark" ? "default" : "outline"}
                    size="sm"
                    className="font-mono gap-1.5"
                    onClick={() => setTheme("dark")}
                  >
                    <Moon className="w-3.5 h-3.5" /> Dark
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          <NotificationsCard />

          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Mail className="w-4 h-4 text-muted-foreground" />
                Email Verification
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-mono text-sm">{user?.email}</p>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    {user?.is_verified ? (
                      <>
                        <CheckCircle className="w-3.5 h-3.5 text-green-400" />
                        <span className="text-xs text-green-400 font-mono">Verified</span>
                      </>
                    ) : (
                      <>
                        <AlertCircle className="w-3.5 h-3.5 text-yellow-400" />
                        <span className="text-xs text-yellow-400 font-mono">Not verified</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="border-border/50">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-mono flex items-center gap-2">
                <Key className="w-4 h-4 text-muted-foreground" />
                Two-Factor Authentication
                <Badge
                  variant="outline"
                  className={`text-xs ml-auto font-mono ${totpStatus?.totp_enabled ? "text-green-400 border-green-400/30" : "text-muted-foreground"}`}
                >
                  {totpStatus?.totp_enabled ? "Enabled" : "Disabled"}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!totpStatus?.totp_enabled ? (
                <>
                  {!totp2faSetup ? (
                    <Button
                      variant="outline"
                      size="sm"
                      className="font-mono gap-1.5"
                      onClick={handleSetup2FA}
                    >
                      <QrCode className="w-3.5 h-3.5" />
                      Set up 2FA
                    </Button>
                  ) : (
                    <div className="space-y-4">
                      <div className="bg-muted/20 rounded-lg p-4 flex flex-col items-center gap-3">
                        {totp2faSetup.qr_code ? (
                          <img src={totp2faSetup.qr_code} alt="QR Code" className="w-40 h-40 rounded-md" />
                        ) : (
                          <div className="w-40 h-40 bg-muted/30 rounded-md flex items-center justify-center">
                            <QrCode className="w-8 h-8 text-muted-foreground" />
                          </div>
                        )}
                        <div className="text-center">
                          <p className="text-xs text-muted-foreground font-mono mb-1">
                            Scan with your authenticator app, or enter this secret manually:
                          </p>
                          <div className="flex items-center gap-2">
                            <code className="text-xs bg-muted/40 px-2 py-1 rounded font-mono">
                              {showSecret ? totp2faSetup.secret : "••••••••••••••••"}
                            </code>
                            <button onClick={() => setShowSecret(!showSecret)} className="text-muted-foreground hover:text-foreground">
                              {showSecret ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="text-red-400 border-red-400/30 hover:bg-red-400/10 font-mono gap-1.5"
                  onClick={() => {}}
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  Disable 2FA
                </Button>
              )}
            </CardContent>
          </Card>

          {sections.map((section, i) => (
            <div key={i} className="space-y-4">
              <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">{section.title}</h3>
              <Card className="border-white/5 bg-white/[0.01] overflow-hidden">
                <div className="divide-y divide-white/5">
                  {section.items.map((item, j) => (
                    <div key={j} className="p-5 flex items-center justify-between hover:bg-white/[0.01] transition-all">
                      <div className="flex items-center gap-4">
                        <div className="w-9 h-9 rounded border border-white/5 bg-white/5 flex items-center justify-center text-muted-foreground/60">
                          <item.icon size={16} />
                        </div>
                        <div>
                          <p className="text-sm font-bold tracking-tight">{item.label}</p>
                          <p className="text-[11px] text-muted-foreground">{item.desc}</p>
                        </div>
                      </div>
                      {item.toggle ? (
                        <Switch className="data-[state=checked]:bg-primary" />
                      ) : (
                        <Button variant="ghost" size="icon" className="w-8 h-8 opacity-20 hover:opacity-100">
                          <ChevronRight size={16} />
                        </Button>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            </div>
          ))}

          <Button
            variant="outline"
            className="w-full h-12 text-vit-negative border-vit-negative/20 hover:bg-vit-negative/5 uppercase tracking-widest text-[10px] font-bold"
            onClick={() => logout?.()}
          >
            <LogOut size={14} className="mr-2" /> De-provision Session
          </Button>
        </div>

        <div className="space-y-6">
          <Card className="bg-white/[0.02] border-white/5">
            <CardHeader>
              <CardTitle className="text-[10px] uppercase tracking-widest text-muted-foreground">Terminal Health</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              {[
                { label: "Connection", value: "Optimal", color: "text-vit-positive" },
                { label: "Latency", value: "14ms", color: "text-foreground" },
                { label: "Session", value: "Active", color: "text-foreground" },
              ].map((stat, i) => (
                <div key={i} className="flex justify-between items-center">
                  <span className="text-[11px] text-muted-foreground">{stat.label}</span>
                  <span className={cn("font-mono text-[11px] font-bold", stat.color)}>{stat.value}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
