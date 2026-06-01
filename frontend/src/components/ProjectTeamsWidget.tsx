import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "./ui/button";
import { Users, Shield, Github, ChevronRight } from "lucide-react";
import { Link } from "wouter";

export function ProjectTeamsWidget() {
  return (
    <Card className="bg-card/50 border-border/40">
      <CardHeader>
        <CardTitle className="text-sm font-mono flex items-center gap-2">
          <Shield className="w-4 h-4 text-primary" /> Project Teams
        </CardTitle>
        <CardDescription className="text-[10px] font-mono uppercase">Repository Contributors & Governance</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between p-3 rounded-xl bg-background/40 border border-border/20">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-400 border border-blue-500/20">
              <Shield className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono font-bold">Architectural Council</div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase">Core Protocol Governance</div>
            </div>
          </div>
          <Badge variant="outline" className="text-[8px] font-mono border-primary/20 text-primary">1 ACTIVE</Badge>
        </div>

        <div className="flex items-center justify-between p-3 rounded-xl bg-background/40 border border-border/20">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-400 border border-purple-500/20">
              <Users className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[11px] font-mono font-bold">Analytics Forge</div>
              <div className="text-[9px] font-mono text-muted-foreground uppercase">Model Weight Optimization</div>
            </div>
          </div>
          <Badge variant="outline" className="text-[8px] font-mono border-border text-muted-foreground">AI AGENT</Badge>
        </div>

        <Link href="/community">
          <Button variant="ghost" className="w-full h-8 font-mono text-[10px] uppercase gap-2 hover:bg-primary/5">
            View All Project Teams <ChevronRight className="w-3 h-3" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}
