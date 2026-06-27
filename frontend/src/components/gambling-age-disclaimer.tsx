import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, ArrowRight } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export function GamblingAgeDisclaimer() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const accepted = localStorage.getItem('vit_intelligence_disclaimer_v2');
    if (!accepted) {
      setOpen(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('vit_intelligence_disclaimer_v2', 'true');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-md border-white/5 bg-background shadow-2xl p-0 overflow-hidden">
        <div className="bg-primary/5 p-8 border-b border-white/5">
          <div className="flex items-center gap-4 text-primary mb-4">
             <ShieldCheck size={32} />
             <div className="space-y-0.5">
                <p className="text-[10px] font-bold uppercase tracking-[0.2em] opacity-50">Legal Protocol</p>
                <h2 className="text-xl font-display font-bold uppercase tracking-tight">Institutional Intelligence Access</h2>
             </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            By entering the VIT Network Terminal, you acknowledge that this platform provides probabilistic intelligence, market signals, and decentralized forecasting infrastructure.
          </p>
        </div>

        <div className="p-8 space-y-6">
           <div className="space-y-4">
              <div className="flex gap-4 p-4 rounded bg-white/[0.02] border border-white/5">
                 <AlertTriangle className="text-amber-500 shrink-0" size={16} />
                 <p className="text-[11px] text-muted-foreground leading-relaxed">
                    Intelligence models are for analytical purposes. Digital asset interactions involve capital risk. Ensure you are compliant with your local jurisdiction's regulatory framework.
                 </p>
              </div>
              <div className="flex gap-4 p-4 rounded bg-white/[0.02] border border-white/5">
                 <ShieldCheck className="text-vit-positive shrink-0" size={16} />
                 <p className="text-[11px] text-muted-foreground leading-relaxed">
                    You represent that you are of legal age and possess the necessary authorization to engage with decentralized prediction markets.
                 </p>
              </div>
           </div>

           <Button onClick={handleAccept} className="w-full h-14 uppercase tracking-widest text-xs font-bold shadow-xl shadow-primary/20">
              I Understand – Enter Terminal <ArrowRight size={14} className="ml-2" />
           </Button>

           <p className="text-center text-[9px] font-mono text-muted-foreground uppercase tracking-[0.2em]">
             VIT Network v5.5.0 • Institutional Access
           </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
