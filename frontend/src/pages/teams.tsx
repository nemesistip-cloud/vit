import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Users, Code, Cloud, Brain, Shield, Github } from "lucide-react";
import { usePublicConfig } from "@/lib/usePublicConfig";

const PROJECT_TEAMS = [
  {
    name: "Architectural Council",
    description: "Core protocol design and system orchestration.",
    members: [
      {
        name: "nemesistip-cloud",
        role: "Lead Architect",
        specialty: "Cloud Infrastructure & ML Ops",
        avatar: "https://github.com/nemesistip-cloud.png",
        github: "https://github.com/nemesistip-cloud"
      }
    ],
    icon: Shield,
    color: "text-blue-400"
  },
  {
    name: "Analytics Forge",
    description: "Maintenance of the {config?.platform?.model_count || 13}-model ensemble and signal generation.",
    members: [
      {
        name: "VIT AI Agent",
        role: "Automated Contributor",
        specialty: "Continuous Training & Evaluation",
        avatar: "",
        github: "https://github.com/nemesistip-cloud/vit"
      }
    ],
    icon: Brain,
    color: "text-purple-400"
  },
  {
    name: "Cloud Ops Team",
    description: "Google Cloud Platform management and scaling.",
    members: [
      {
        name: "GCP Automation",
        role: "Deployment Lead",
        specialty: "Cloud Run & Secret Manager",
        avatar: "",
        github: "https://github.com/nemesistip-cloud/vit"
      }
    ],
    icon: Cloud,
    color: "text-cyan-400"
  },
  {
    name: "Product & UI/UX",
    description: "Crafting the VIT Network experience.",
    members: [
      {
        name: "Jules",
        role: "Principal Engineer",
        specialty: "React & Systems Integration",
        avatar: "",
        github: "https://github.com/nemesistip-cloud/vit"
      }
    ],
    icon: Code,
    color: "text-emerald-400"
  }
];

export default function TeamsPage() {
  const { data: config } = usePublicConfig();
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-6xl mx-auto p-4 lg:p-8">
      <header className="space-y-2">
        <div className="flex items-center gap-3">
          <Users className="w-8 h-8 text-primary" />
          <h1 className="text-2xl font-bold font-mono tracking-tight text-foreground">Project Teams</h1>
        </div>
        <p className="text-sm font-mono text-muted-foreground uppercase tracking-[0.2em]">Repository Contributors & Project Profiles</p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {PROJECT_TEAMS.map((team) => (
          <Card key={team.name} className="bg-card/40 border-border/40 overflow-hidden hover:border-primary/30 transition-all">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg bg-background/60 ${team.color}`}>
                    <team.icon className="w-5 h-5" />
                  </div>
                  <div>
                    <CardTitle className="text-lg font-mono font-bold tracking-tight">{team.name}</CardTitle>
                    <CardDescription className="text-xs font-mono">{team.description}</CardDescription>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {team.members.map((member) => (
                  <div key={member.name} className="flex items-center justify-between p-3 rounded-xl bg-background/30 border border-border/10">
                    <div className="flex items-center gap-3">
                      <Avatar className="w-10 h-10 border border-border/20">
                        <AvatarImage src={member.avatar} alt={member.name} />
                        <AvatarFallback className="bg-primary/10 text-primary font-mono text-xs">
                          {member.name.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-mono font-bold text-foreground">{member.name}</span>
                          <Badge variant="secondary" className="text-[9px] font-mono py-0 h-4 bg-primary/5 text-primary border-primary/20">
                            {member.role}
                          </Badge>
                        </div>
                        <p className="text-[10px] font-mono text-muted-foreground">{member.specialty}</p>
                      </div>
                    </div>
                    <a
                      href={member.github}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-2 rounded-full hover:bg-background/80 text-muted-foreground hover:text-foreground transition-colors"
                    >
                      <Github className="w-4 h-4" />
                    </a>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <section className="p-8 rounded-3xl bg-primary/5 border border-primary/10 relative overflow-hidden">
        <div className="relative z-10 space-y-4">
          <h2 className="text-xl font-mono font-black text-foreground uppercase tracking-tight">Project Governance</h2>
          <p className="text-sm font-mono text-muted-foreground max-w-2xl leading-relaxed">
            VIT Network is a collaborative effort between human domain experts and autonomous AI agents.
            All repository contributors are mapped to project profiles that govern the protocol's
            evolution, model weights, and cross-border expansion.
          </p>
          <div className="flex gap-4">
             <Badge variant="outline" className="font-mono text-[10px]">Open Source</Badge>
             <Badge variant="outline" className="font-mono text-[10px]">GCP Native</Badge>
             <Badge variant="outline" className="font-mono text-[10px]">AI-Governed</Badge>
          </div>
        </div>
        <div className="absolute top-0 right-0 w-64 h-64 bg-primary/10 rounded-full  -mr-32 -mt-32" />
      </section>
    </div>
  );
}
