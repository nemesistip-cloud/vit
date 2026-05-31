import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Send, Download, CreditCard, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function RemittancePage() {
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Finance & Remittances</h1>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-widest">Seamless cross-border value transfer</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-card/50 border-border/40">
          <CardHeader>
            <CardTitle className="text-sm font-mono">Wallet Balance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="text-3xl font-bold font-mono">₦145,200.00</p>
              <p className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mt-1">≈ 12,400 VIT</p>
            </div>
            <div className="flex gap-2">
              <Button className="flex-1 font-mono text-xs gap-1.5 h-9">
                <Send className="w-3 h-3" /> Send
              </Button>
              <Button variant="outline" className="flex-1 font-mono text-xs gap-1.5 h-9">
                <Download className="w-3 h-3" /> Receive
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="md:col-span-2 bg-card/50 border-border/40">
          <CardHeader>
            <CardTitle className="text-sm font-mono">Remittance History</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-background/50 border border-border/20">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-full bg-emerald-500/10 text-emerald-400">
                      <RefreshCw className="w-3 h-3" />
                    </div>
                    <div>
                      <p className="text-xs font-mono font-bold">Transfer from London (GBP)</p>
                      <p className="text-[9px] font-mono text-muted-foreground">Oct 24, 2025 · Completed</p>
                    </div>
                  </div>
                  <p className="text-xs font-mono font-bold text-emerald-400">+₦45,000.00</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
