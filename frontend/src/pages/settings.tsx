import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiPost } from "@/lib/apiClient";
import { useAuth } from "@/lib/auth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Shield, Mail, Lock, Key, CheckCircle, AlertCircle,
  QrCode, Eye, EyeOff, Sun, Moon, AlertTriangle,
} from "lucide-react";
import { useTheme } from "@/lib/theme";

interface TotpStatus {
  totp_enabled: boolean;
  has_pending_setup: boolean;
}

interface TotpSetup {
  secret: string;
  qr_code: string;
  provisioning_uri: string;
  instructions: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, setTheme } = useTheme();
  const qc = useQueryClient();

  const [verifyCode, setVerifyCode] = useState("");
  const [disableCode, setDisableCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");
  const [showSecret, setShowSecret] = useState(false);

  const { data: totpStatus } = useQuery<TotpStatus>({
    queryKey: ["2fa-status"],
    queryFn: () => apiGet("/auth/2fa/status"),
    staleTime: 30_000,
  });

  const setupMutation = useMutation({
    mutationFn: () => apiPost("/auth/2fa/setup", {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["2fa-setup", "2fa-status"] }),
    onError: (err: any) => toast.error(err.message ?? "Setup failed"),
  });

  const [showDisableConfirm, setShowDisableConfirm] = useState(false);

  const enableMutation = useMutation({
    mutationFn: (code: string) => apiPost("/auth/2fa/enable", { totp_code: code }),
    onSuccess: () => {
      toast.success("2FA enabled successfully!");
      setVerifyCode("");
      qc.invalidateQueries({ queryKey: ["2fa-status"] });
      (window as any).__totp_setup_data = null;
    },
    onError: (err: any) => toast.error(err.message ?? "Invalid code"),
  });

  const disableMutation = useMutation({
    mutationFn: ({ code, password }: { code: string; password: string }) =>
      apiPost("/auth/2fa/disable", { totp_code: code, password }),
    onSuccess: () => {
      toast.success("2FA disabled.");
      setDisableCode("");
      setDisablePassword("");
      qc.invalidateQueries({ queryKey: ["2fa-status"] });
    },
    onError: (err: any) => toast.error(err.message ?? "Failed to disable 2FA"),
  });

  const sendVerifyMutation = useMutation({
    mutationFn: () => apiPost("/auth/send-verification", { email: user?.email }),
    onSuccess: (data: any) => {
      toast.success("Verification email sent!");
      if (data?.dev_link) {
        toast.info(`Dev link: ${data.dev_link}`, { duration: 10000 });
      }
    },
    onError: (err: any) => toast.error(err.message ?? "Failed to send"),
  });

  const [totp2faSetup, setTotp2faSetup] = useState<TotpSetup | null>(null);

  const handleSetup2FA = async () => {
    try {
      const data = await apiPost<TotpSetup>("/auth/2fa/setup", {});
      setTotp2faSetup(data);
    } catch (err: any) {
      toast.error(err.message ?? "Setup failed");
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-primary/10 border border-primary/20 rounded-xl flex items-center justify-center">
          <Shield className="w-5 h-5 text-primary" />
        </div>
        <div>
          <h1 className="text-xl font-bold font-mono tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground font-mono">Security and account preferences</p>
        </div>
      </div>

      {/* Appearance */}
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

      {/* Email verification */}
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
            {!user?.is_verified && (
              <Button
                variant="outline"
                size="sm"
                className="font-mono text-xs"
                onClick={() => sendVerifyMutation.mutate()}
                disabled={sendVerifyMutation.isPending}
              >
                Send verification email
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 2FA */}
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
          <CardDescription className="font-mono text-xs">
            Use an authenticator app (Google Authenticator, Authy) for extra security.
          </CardDescription>
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
                  <div className="space-y-1.5">
                    <Label className="font-mono text-xs">Enter the 6-digit code from your app to confirm</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="000000"
                        value={verifyCode}
                        onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        className="font-mono text-center tracking-widest text-lg"
                        maxLength={6}
                      />
                      <Button
                        onClick={() => enableMutation.mutate(verifyCode)}
                        disabled={verifyCode.length !== 6 || enableMutation.isPending}
                        className="font-mono"
                      >
                        {enableMutation.isPending ? "Verifying..." : "Enable 2FA"}
                      </Button>
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                <p className="text-xs font-mono text-green-300">
                  2FA is active. Your account is protected with an authenticator app.
                </p>
              </div>
              <div className="space-y-2">
                {!showDisableConfirm ? (
                  <Button
                    variant="outline"
                    size="sm"
                    className="font-mono text-destructive border-destructive/30 hover:bg-destructive/10"
                    onClick={() => setShowDisableConfirm(true)}
                  >
                    <AlertTriangle className="w-3.5 h-3.5 mr-1.5" />
                    Disable 2FA
                  </Button>
                ) : (
                  <div className="space-y-3 p-3 border border-destructive/30 rounded-lg bg-destructive/5">
                    <p className="text-xs font-mono text-destructive flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      This will remove 2FA protection. Enter your code + password to confirm.
                    </p>
                    <Label className="font-mono text-xs text-muted-foreground">TOTP code + current password</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="000000"
                        value={disableCode}
                        onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                        className="font-mono w-28 tracking-widest text-center"
                        maxLength={6}
                        autoFocus
                      />
                      <Input
                        type="password"
                        placeholder="Current password"
                        value={disablePassword}
                        onChange={(e) => setDisablePassword(e.target.value)}
                        className="font-mono"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => {
                          disableMutation.mutate({ code: disableCode, password: disablePassword });
                          setShowDisableConfirm(false);
                        }}
                        disabled={disableCode.length !== 6 || !disablePassword || disableMutation.isPending}
                        className="font-mono"
                      >
                        {disableMutation.isPending ? "Disabling..." : "Confirm Disable 2FA"}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => { setShowDisableConfirm(false); setDisableCode(""); setDisablePassword(""); }}
                        className="font-mono"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Password change hint */}
      <Card className="border-border/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-mono flex items-center gap-2">
            <Lock className="w-4 h-4 text-muted-foreground" />
            Password
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground font-mono mb-3">
            To change your password, use the forgot password flow.
          </p>
          <a href="/forgot-password">
            <Button variant="outline" size="sm" className="font-mono gap-1.5">
              <Lock className="w-3.5 h-3.5" />
              Reset Password
            </Button>
          </a>
        </CardContent>
      </Card>
    </div>
  );
}
