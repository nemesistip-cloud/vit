import { useState } from "react";
import { Shield, CheckCircle2, AlertCircle, Camera, FileText, ChevronRight, Clock, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export default function KYCPage() {
  const [step, setStep] = useState(0);

  const statusItems = [
    { label: "Identity Proof", icon: User, color: "text-primary", bg: "bg-primary/5", border: "border-primary/20" },
    { label: "Liveness Check", icon: Camera, color: "text-muted-foreground", bg: "bg-white/5", border: "border-white/5" },
    { label: "Address Verification", icon: FileText, color: "text-muted-foreground", bg: "bg-white/5", border: "border-white/5" },
  ];

  return (
    <div className="space-y-8 pb-20 animate-in fade-in duration-500 px-1">
      {/* ── Header ── */}
      <div className="space-y-1">
         <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-foreground">Identity Protocol</h1>
         <p className="font-mono text-[9px] text-muted-foreground uppercase tracking-[0.2em]">Institutional KYC/AML Verification</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
           <Card className="border-primary/20 bg-primary/[0.02]">
              <CardHeader className="flex flex-row items-center justify-between">
                 <CardTitle className="text-sm uppercase tracking-widest font-display">Provision Verification</CardTitle>
                 <Badge variant="outline" className="bg-primary/5 text-primary border-primary/20">LEVEL 1</Badge>
              </CardHeader>
              <CardContent className="space-y-6">
                 <p className="text-xs text-muted-foreground leading-relaxed">
                    Institutional access requires a verified identity to comply with multi-jurisdictional regulations.
                    Your data is encrypted and stored in the VESS swarm.
                 </p>
                 <Button className="w-full h-12 uppercase tracking-widest text-[10px] font-bold shadow-lg shadow-primary/20">
                    Initialize Secure Upload
                 </Button>
              </CardContent>
           </Card>

           <div className="space-y-4">
              <h3 className="font-display text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground pl-1">Compliance Status</h3>
              <div className="grid grid-cols-1 gap-3">
                 {[
                    { label: "Personal Information", status: "Verified", icon: <CheckCircle2 size={14} />, color: "text-vit-positive" },
                    { label: "Government ID", status: "Pending Analysis", icon: <Clock size={14} />, color: "text-vit-warning" },
                    { label: "Biometric Liveness", status: "Awaiting Action", icon: <Shield size={14} />, color: "text-muted-foreground" },
                 ].map((item, i) => (
                    <Card key={i} className="border-white/5 bg-white/[0.01] hover:bg-white/[0.02] transition-all">
                       <div className="p-5 flex items-center justify-between">
                          <div className="flex items-center gap-4">
                             <div className={cn("w-9 h-9 rounded border border-white/5 bg-white/5 flex items-center justify-center", item.color)}>
                                {item.icon}
                             </div>
                             <p className="text-sm font-bold tracking-tight">{item.label}</p>
                          </div>
                          <Badge variant="outline" className={cn("text-[8px] font-bold uppercase border-none px-2", item.color + " bg-white/5")}>
                             {item.status}
                          </Badge>
                       </div>
                    </Card>
                 ))}
              </div>
           </div>
        </div>

        <div className="space-y-6">
           <div className="bg-white/[0.02] border border-white/5 rounded-lg p-6">
              <div className="flex items-center gap-2 mb-4 text-primary">
                 <Shield size={16} />
                 <h4 className="font-display text-[10px] font-bold uppercase tracking-[0.2em]">Privacy Shield</h4>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                 VIT Network utilizes Zero-Knowledge Proofs for identity verification where possible, ensuring your raw data is never exposed to third parties.
              </p>
           </div>
        </div>
      </div>
    </div>
  );
}
import { User } from "lucide-react";
