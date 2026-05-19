import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { apiPost } from "@/lib/apiClient";
import { Link } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle, XCircle, Loader2, Mail } from "lucide-react";

export default function VerifyEmailPage() {
  const [token, setToken] = useState("");
  const [autoTriggered, setAutoTriggered] = useState(false);

  const mutation = useMutation({
    mutationFn: (t: string) => apiPost("/auth/verify-email", { token: t }),
  });

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const t = params.get("token") ?? "";
    setToken(t);
    if (t && !autoTriggered) {
      setAutoTriggered(true);
      mutation.mutate(t);
    }
  }, []);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        <Card className="border-border/50">
          <CardContent className="pt-8 pb-6 text-center space-y-4">
            {mutation.isPending && (
              <>
                <Loader2 className="w-10 h-10 text-primary mx-auto animate-spin" />
                <p className="font-mono text-sm">Verifying your email...</p>
              </>
            )}
            {mutation.isSuccess && (
              <>
                <CheckCircle className="w-10 h-10 text-green-400 mx-auto" />
                <div className="space-y-1">
                  <p className="font-mono text-sm font-medium text-green-400">Email verified!</p>
                  <p className="text-xs text-muted-foreground font-mono">
                    Your account is now fully verified.
                  </p>
                </div>
                <Link href="/dashboard">
                  <Button className="w-full font-mono">Go to Dashboard</Button>
                </Link>
              </>
            )}
            {mutation.isError && (
              <>
                <XCircle className="w-10 h-10 text-red-400 mx-auto" />
                <div className="space-y-1">
                  <p className="font-mono text-sm font-medium text-red-400">Verification failed</p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {(mutation.error as any)?.message ?? "Token is invalid or expired."}
                  </p>
                </div>
                <Link href="/dashboard">
                  <Button variant="outline" className="w-full font-mono">
                    <Mail className="w-4 h-4 mr-1.5" />
                    Resend from settings
                  </Button>
                </Link>
              </>
            )}
            {!mutation.isPending && !mutation.isSuccess && !mutation.isError && !token && (
              <>
                <Mail className="w-10 h-10 text-muted-foreground mx-auto" />
                <p className="font-mono text-sm text-muted-foreground">
                  No verification token found in URL.
                </p>
                <Link href="/dashboard">
                  <Button variant="outline" className="w-full font-mono">Back to app</Button>
                </Link>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
