import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Store, UserPlus, Briefcase, ChevronRight } from "lucide-react";

export function AgentPortal() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="bg-primary/5 border-primary/20">
          <CardHeader>
            <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center mb-2">
              <Store className="w-5 h-5 text-primary" />
            </div>
            <CardTitle className="text-lg font-mono">Betting Shop Agent</CardTitle>
            <CardDescription className="text-xs font-mono">Run a VIT Terminal in your existing shop. Earn 5-10% commissions.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full font-mono text-xs gap-2">
              Apply Now <ChevronRight className="w-3 h-3" />
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
          <CardContent>
            <Button variant="secondary" className="w-full font-mono text-xs gap-2 bg-purple-500/10 hover:bg-purple-500/20 text-purple-400">
              Join Network <ChevronRight className="w-3 h-3" />
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
