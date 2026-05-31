import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/apiClient";
import { Link } from "wouter";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Mail, ArrowLeft, CheckCircle } from "lucide-react";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devToken, setDevToken] = useState("");

  const mutation = useMutation({
    mutationFn: (email: string) => apiPost("/auth/forgot-password", { email }),
    onSuccess: (data: any) => {
      setSent(true);
      if (data?.dev_token) {
        setDevToken(data.dev_token);
      }
    },
    onError: (err: any) => toast.error(err.message ?? "Failed to send reset email"),
  });

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm space-y-4">
        <div className="text-center space-y-1">
          <div className="w-10 h-10 bg-primary/10 border border-primary/20 rounded-xl flex items-center justify-center mx-auto mb-3">
            <Mail className="w-5 h-5 text-primary" />
          </div>
          <h1 className="text-xl font-bold font-mono">Forgot Password</h1>
          <p className="text-sm text-muted-foreground font-mono">
            Enter your email to receive a reset link
          </p>
        </div>

        {sent ? (
          <Card className="border-border/50">
            <CardContent className="pt-6 space-y-4 text-center">
              <CheckCircle className="w-10 h-10 text-green-400 mx-auto" />
              <div className="space-y-1">
                <p className="font-mono text-sm font-medium">Reset link sent!</p>
                <p className="text-xs text-muted-foreground font-mono">
                  Check your inbox (and spam folder).
                </p>
              </div>
              {devToken && (
                <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 text-left">
                  <p className="text-xs font-mono text-yellow-400 font-medium mb-1">Dev Mode — No SMTP configured</p>
                  <Link href={`/reset-password?token=${devToken}`}>
                    <span className="text-xs font-mono text-primary underline cursor-pointer">
                      Click here to reset password →
                    </span>
                  </Link>
                </div>
              )}
              <Link href="/login">
                <Button variant="outline" size="sm" className="w-full font-mono">
                  <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
                  Back to sign in
                </Button>
              </Link>
            </CardContent>
          </Card>
        ) : (
          <Card className="border-border/50">
            <CardContent className="pt-6 space-y-4">
              <div className="space-y-1.5">
                <Label className="font-mono text-xs">Email address</Label>
                <Input
                  type="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="font-mono text-sm"
                  onKeyDown={(e) => e.key === "Enter" && email && mutation.mutate(email)}
                />
              </div>
              <Button
                onClick={() => email && mutation.mutate(email)}
                disabled={!email || mutation.isPending}
                className="w-full font-mono"
              >
                {mutation.isPending ? "Sending..." : "Send Reset Link"}
              </Button>
              <Link href="/login">
                <Button variant="ghost" size="sm" className="w-full font-mono text-muted-foreground">
                  <ArrowLeft className="w-3.5 h-3.5 mr-1.5" />
                  Back to sign in
                </Button>
              </Link>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
