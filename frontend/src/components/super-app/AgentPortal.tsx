import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Store, UserPlus, Briefcase, ChevronRight, CheckCircle } from "lucide-react";
import { apiPost } from "@/lib/apiClient";
import { useToast } from "@/hooks/use-toast";

export function AgentPortal() {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [formData, setFormData] = useState({ business_name: "", location: "" });
  const { toast } = useToast();

  const handleApply = async (type: string) => {
    if (!formData.location) {
      toast({ title: "Error", description: "Please provide a location", variant: "destructive" });
      return;
    }

    setIsSubmitting(true);
    try {
      await apiPost("/api/blockchain/agents/apply", {
        agent_type: type,
        ...formData
      });
      setIsSuccess(true);
      toast({ title: "Success", description: "Application submitted successfully" });
    } catch (err: any) {
      toast({ title: "Error", description: err.message || "Failed to submit application", variant: "destructive" });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSuccess) {
    return (
      <Card className="bg-emerald-500/5 border-emerald-500/20 text-center py-10">
        <CardContent className="space-y-4">
          <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto" />
          <h3 className="text-lg font-mono font-bold text-emerald-400">Application Received</h3>
          <p className="text-xs font-mono text-muted-foreground">Our regional manager will review your application within 24 hours.</p>
          <Button variant="outline" onClick={() => setIsSuccess(false)} className="font-mono text-xs">Back</Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader>
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center mb-2">
              <Store className="w-5 h-5 text-primary" />
            </div>
            <CardTitle className="text-lg font-mono">Market Liquidity Agent</CardTitle>
            <CardDescription className="text-xs font-mono">Run a VIT Terminal in your existing shop. Earn 5-10% commissions.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <Input
              placeholder="Business Name"
              className="font-mono text-xs"
              value={formData.business_name}
              onChange={e => setFormData({...formData, business_name: e.target.value})}
            />
            <Input
              placeholder="Location (City, State)"
              className="font-mono text-xs"
              value={formData.location}
              onChange={e => setFormData({...formData, location: e.target.value})}
            />
            <Button
              className="w-full font-mono text-xs gap-2"
              disabled={isSubmitting}
              onClick={() => handleApply("shop")}
            >
              {isSubmitting ? "Submitting..." : "Apply as Shop Agent"} <ChevronRight className="w-3 h-3" />
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-purple-500/5 border-purple-500/20">
          <CardHeader>
            <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center mb-2">
              <UserPlus className="w-5 h-5 text-purple-400" />
            </div>
            <CardTitle className="text-lg font-mono">Community Agent</CardTitle>
            <CardDescription className="text-xs font-mono">Build your network, help others save/remit, and earn $VIT rewards.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 pt-10">
             <Input
              placeholder="Primary Location"
              className="font-mono text-xs"
              value={formData.location}
              onChange={e => setFormData({...formData, location: e.target.value})}
            />
            <Button
              variant="secondary"
              className="w-full font-mono text-xs gap-2 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400"
              disabled={isSubmitting}
              onClick={() => handleApply("community")}
            >
              {isSubmitting ? "Joining..." : "Join Community Network"} <ChevronRight className="w-3 h-3" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
