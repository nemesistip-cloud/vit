import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import {
  Database,
  Zap,
  ShieldCheck,
  PlusCircle,
  HardDrive,
  Network,
  ArrowUpRight,
  RefreshCw
} from "lucide-react";

const StoragePage: React.FC = () => {
  const [isLinking, setIsLinking] = useState(false);

  const speedTiers = [
    { name: "Bronze", requirement: "1 account", speed: "1 Gbps", current: true },
    { name: "Silver", requirement: "5 accounts", speed: "10 Gbps", current: false },
    { name: "Gold", requirement: "20 accounts", speed: "Uncapped", current: false },
  ];

  const accounts = [
    { provider: "Google Drive", email: "user@gmail.com", quota: "15 GB", status: "Active" },
    { provider: "OneDrive", email: "work@corp.com", quota: "1 TB", status: "Active" },
  ];

  return (
    <div className="container mx-auto p-6 space-y-8 pb-20">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-foreground">Storage System</h1>
          <p className="text-muted-foreground mt-1">Massively parallel, quantum-inspired decentralized storage.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4" /> Sync
          </Button>
          <Button className="flex items-center gap-2" onClick={() => setIsLinking(true)}>
            <PlusCircle className="w-4 h-4" /> Link Account
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2 text-primary">
              <Zap className="w-4 h-4" /> SPEED TIER
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Bronze</div>
            <p className="text-xs text-muted-foreground mt-1">Up to 1 Gbps aggregate</p>
            <Progress value={25} className="mt-4 h-2" />
            <p className="text-[10px] text-muted-foreground mt-2">Next: Silver (4 more accounts)</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Database className="w-4 h-4" /> STORAGE CREDITS
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">142.5 TSC</div>
            <p className="text-xs text-muted-foreground mt-1">1 TSC = 1 GB / Month</p>
            <div className="mt-4 flex gap-2">
              <Badge variant="secondary">Earned: 12.5 today</Badge>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <ShieldCheck className="w-4 h-4" /> NETWORK HEALTH
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3.2 Tbps</div>
            <p className="text-xs text-muted-foreground mt-1">Global aggregate bandwidth</p>
            <div className="mt-4 flex items-center gap-2 text-green-500 text-xs font-semibold">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              124,500 Nodes Active
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <HardDrive className="w-5 h-5" /> Contributed Accounts
          </h2>
          <div className="space-y-4">
            {accounts.map((acc, idx) => (
              <Card key={idx} className="overflow-hidden">
                <div className="p-4 flex justify-between items-center">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center">
                      <Network className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="font-semibold">{acc.provider}</div>
                      <div className="text-xs text-muted-foreground">{acc.email}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">{acc.quota}</div>
                    <Badge variant="outline" className="text-[10px] uppercase">{acc.status}</Badge>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Zap className="w-5 h-5" /> Speed Tiers
          </h2>
          <div className="space-y-4">
            {speedTiers.map((tier, idx) => (
              <div key={idx} className={`p-4 rounded-xl border-2 transition-all ${tier.current ? 'border-primary bg-primary/5' : 'border-border'}`}>
                <div className="flex justify-between items-center">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold">{tier.name}</span>
                      {tier.current && <Badge variant="default" className="text-[10px]">CURRENT</Badge>}
                    </div>
                    <div className="text-sm text-muted-foreground mt-1">{tier.requirement}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-primary">{tier.speed}</div>
                    <div className="text-[10px] text-muted-foreground">Transfer Limit</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <Card className="bg-gradient-to-br from-blue-600/10 to-purple-600/10 border-none">
        <CardContent className="p-8 text-center">
          <h3 className="text-2xl font-bold mb-2">Unleash the Swarm</h3>
          <p className="text-muted-foreground max-w-2xl mx-auto mb-6">
            The Tachyon Burst Transfer Protocol uses massively parallel connections to bypass single-provider throttling. Link more accounts to amplify your throughput.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-background border shadow-sm">
              <ShieldCheck className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium">Triple-Blind TEE Security</span>
            </div>
            <div className="flex items-center gap-2 px-4 py-2 rounded-full bg-background border shadow-sm">
              <Zap className="w-4 h-4 text-yellow-500" />
              <span className="text-sm font-medium">4KB Fragment Parallelism</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default StoragePage;
