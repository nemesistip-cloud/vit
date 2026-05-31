import { useState, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/apiClient";
import { useLocation, Link } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Lock, Eye, EyeOff, CheckCircle, AlertCircle } from "lucide-react";

export default function ResetPasswordPage() {
  const [location, setLocation] = useLocation();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token") ?? "";
    setToken(t);
  }, []);

  const mutation = useMutation({
    mutationFn: () => apiPost("/auth/reset-password", { token, new_password: password }),
    onSuccess: () => {
      setDone(true);
      toast.success("Password reset! You can now sign in.");
    },
    onError: (err: any) => toast.error(err.message ?? "Reset failed. Token may have expired."),
  });

  const passwordsMatch = password === confirmPassword;
  const canSubmit = token && password.length >= 8 && passwordsMatch;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center space-y-1">
          <div className="w-10 h-10 bg-primary/10 border border-primary/20 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Lock className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-xl font-bold font-mono">Reset Password</h1>
        </div>

        <Card className="border-border/50">
          <CardContent className="pt-6 space-y-4">
            {!token && (
              <div className="flex items-center gap-2 p-3 bg-yellow-500/10 border border-yellow-500/20 rounded-lg">
                <AlertCircle className="w-4 h-4 text-yellow-400 flex-shrink-0" />
                <p className="text-xs font-mono text-yellow-300">
                  No token found in URL. Please use the link from your email.
                </p>
              </div>
            )}

            {done ? (
              <div className="text-center space-y-4 py-2">
                <CheckCircle className="w-10 h-10 text-green-400 mx-auto" />
                <p className="font-mono text-sm">Password changed successfully!</p>
                <Link href="/login">
                  <Button className="w-full font-mono">Sign In</Button>
                </Link>
              </div>
            ) : (
              <>
                <div className="space-y-1.5">
                  <Label className="font-mono text-xs">New Password</Label>
                  <div className="relative">
                    <Input
                      type={showPass ? "text" : "password"}
                      placeholder="Min 8 characters"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      className="font-mono text-sm pr-10"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPass(!showPass)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                    >
                      {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="font-mono text-xs">Confirm Password</Label>
                  <Input
                    type="password"
                    placeholder="Repeat password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className={`font-mono text-sm ${confirmPassword && !passwordsMatch ? "border-red-500" : ""}`}
                  />
                  {confirmPassword && !passwordsMatch && (
                    <p className="text-xs text-red-400 font-mono">Passwords do not match</p>
                  )}
                </div>

                <Button
                  onClick={() => mutation.mutate()}
                  disabled={!canSubmit || mutation.isPending}
                  className="w-full font-mono"
                >
                  {mutation.isPending ? "Resetting..." : "Reset Password"}
                </Button>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
