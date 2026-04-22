import { useEffect, useState } from "react";
import { useLocation, useSearch } from "wouter";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { apiPost } from "@/lib/apiClient";
import { useQueryClient } from "@tanstack/react-query";

export default function PaymentCallbackPage() {
  const [, setLocation] = useLocation();
  const search = useSearch();
  const queryClient = useQueryClient();

  const params = new URLSearchParams(search);
  const status = params.get("deposit") || params.get("status") || "unknown";
  const reference = params.get("reference") || params.get("ref") || params.get("trxref") || "";
  const [verifying, setVerifying] = useState(false);
  const [verified, setVerified] = useState<"success" | "failed" | null>(null);
  const [verifyResult, setVerifyResult] = useState<any>(null);

  useEffect(() => {
    if (reference && (status === "success" || status !== "cancelled")) {
      verifyPayment();
    }
  }, [reference]);

  const verifyPayment = async () => {
    if (!reference) return;
    setVerifying(true);
    try {
      const result = await apiPost<any>("/api/wallet/deposit/verify", {
        reference,
        currency: "NGN",
      });
      setVerifyResult(result);
      if (result.status === "confirmed") {
        setVerified("success");
        toast.success(`Deposit of ${result.amount?.toLocaleString()} ${result.currency} confirmed!`);
        queryClient.invalidateQueries({ queryKey: ["/api/wallet/me"] });
        queryClient.invalidateQueries({ queryKey: ["/api/wallet/transactions"] });
      } else {
        setVerified("failed");
        toast.error("Payment could not be confirmed. Contact support with your reference.");
      }
    } catch (e: any) {
      setVerified("failed");
      toast.error(e.message || "Verification failed");
    } finally {
      setVerifying(false);
    }
  };

  const isCancelled = status === "cancelled" || status === "cancel";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4">
      <Card className="w-full max-w-md bg-card border-border">
        <CardContent className="p-8 text-center space-y-6">
          {isCancelled ? (
            <>
              <XCircle className="w-16 h-16 text-destructive mx-auto" />
              <div>
                <h2 className="text-xl font-mono font-bold uppercase tracking-tight mb-2">Payment Cancelled</h2>
                <p className="text-muted-foreground font-mono text-sm">
                  Your payment was cancelled. No funds have been charged.
                </p>
              </div>
            </>
          ) : verifying ? (
            <>
              <Loader2 className="w-16 h-16 text-primary mx-auto animate-spin" />
              <div>
                <h2 className="text-xl font-mono font-bold uppercase tracking-tight mb-2">Verifying Payment</h2>
                <p className="text-muted-foreground font-mono text-sm">
                  Confirming your transaction with the payment gateway...
                </p>
              </div>
            </>
          ) : verified === "success" ? (
            <>
              <CheckCircle2 className="w-16 h-16 text-primary mx-auto" />
              <div>
                <h2 className="text-xl font-mono font-bold uppercase tracking-tight mb-2">Payment Confirmed</h2>
                <p className="text-muted-foreground font-mono text-sm">
                  {verifyResult?.amount?.toLocaleString()} {verifyResult?.currency} has been added to your wallet.
                </p>
                {reference && (
                  <p className="text-xs text-muted-foreground mt-2 font-mono">Ref: {reference}</p>
                )}
              </div>
            </>
          ) : verified === "failed" ? (
            <>
              <XCircle className="w-16 h-16 text-destructive mx-auto" />
              <div>
                <h2 className="text-xl font-mono font-bold uppercase tracking-tight mb-2">Verification Failed</h2>
                <p className="text-muted-foreground font-mono text-sm">
                  We couldn't verify your payment. If funds were deducted, contact support with reference: {reference}
                </p>
              </div>
            </>
          ) : (
            <>
              <div className="text-4xl">💳</div>
              <div>
                <h2 className="text-xl font-mono font-bold uppercase tracking-tight mb-2">Payment Status</h2>
                <p className="text-muted-foreground font-mono text-sm capitalize">{status}</p>
              </div>
            </>
          )}

          <div className="flex flex-col gap-2">
            <Button
              className="w-full font-mono uppercase tracking-widest text-sm"
              onClick={() => setLocation("/wallet")}
            >
              Return to Treasury
            </Button>
            {verified === "failed" && (
              <Button
                variant="outline"
                className="w-full font-mono uppercase tracking-widest text-sm"
                onClick={verifyPayment}
                disabled={verifying}
              >
                {verifying ? "Retrying..." : "Retry Verification"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
