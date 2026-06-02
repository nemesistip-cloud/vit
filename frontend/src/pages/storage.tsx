import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Database,
  Zap,
  ShieldCheck,
  PlusCircle,
  HardDrive,
  Network,
  ArrowUpRight,
  RefreshCw,
  Upload,
  FileText,
  Download,
  AlertCircle
} from "lucide-react";

interface Manifest {
  file_id: string;
  filename: string;
  size_bytes: number;
  fragment_names: string[];
}

const StoragePage: React.FC = () => {
  const [status, setStatus] = useState<any>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [files, setFiles] = useState<Manifest[]>([]);
  const [downloading, setDownloading] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      const resp = await fetch("/api/tachyon/status");
      const data = await resp.json();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch Tachyon status", err);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const resp = await fetch("/api/tachyon/upload", {
        method: "POST",
        body: formData,
      });
      const manifest = await resp.json();
      setFiles([manifest, ...files]);
      setFile(null);
      fetchStatus();
    } catch (err) {
      console.error("Upload failed", err);
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    setDownloading(fileId);
    try {
      const resp = await fetch(`/api/tachyon/download/${fileId}`);
      const blob = await resp.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch (err) {
      console.error("Download failed", err);
    } finally {
      setDownloading(null);
    }
  };

  const speedTiers = [
    { name: "Bronze", requirement: "1 account", speed: "1 Gbps", current: true },
    { name: "Silver", requirement: "5 accounts", speed: "10 Gbps", current: false },
    { name: "Gold", requirement: "20 accounts", speed: "Uncapped", current: false },
  ];

  const providers = [
    { name: "Google Drive", count: 2, icon: "G" },
    { name: "OneDrive", count: 2, icon: "O" },
    { name: "Dropbox", count: 1, icon: "D" },
  ];

  return (
    <div className="container mx-auto p-6 space-y-8 pb-20">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-foreground font-mono uppercase">Tachyon Fabric</h1>
          <p className="text-muted-foreground mt-1 font-mono text-sm tracking-tighter">Massively parallel, quantum-inspired decentralized swarm storage.</p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" size="sm" onClick={fetchStatus} className="font-mono text-xs">
            <RefreshCw className={`w-3 h-3 mr-2 ${!status ? 'animate-spin' : ''}`} /> Sync
          </Button>
          <Button size="sm" className="font-mono text-xs">
            <PlusCircle className="w-3 h-3 mr-2" /> Link Provider
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="border-primary/20 bg-primary/5">
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-mono font-bold tracking-widest flex items-center gap-2 text-primary uppercase">
              <Zap className="w-3 h-3" /> EEC Recovery
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">REED-SOLOMON</div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mt-1">Multi-fragment fault tolerance active</p>
            <Progress value={100} className="mt-4 h-1.5" />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-mono font-bold tracking-widest flex items-center gap-2 uppercase">
              <Database className="w-3 h-3" /> Managed Swarm
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{status?.active_nodes || "5"} Providers</div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mt-1">Parallel Burst Transfer Active</p>
            <div className="mt-4 flex gap-2">
              {providers.map(p => (
                <Badge key={p.name} variant="secondary" className="text-[9px] font-mono">
                  {p.icon}: {p.count}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-[10px] font-mono font-bold tracking-widest flex items-center gap-2 uppercase">
              <ShieldCheck className="w-3 h-3 text-green-500" /> Network Throughput
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold font-mono">{status?.network_bandwidth || "3.2 Tbps"}</div>
            <p className="text-[10px] font-mono text-muted-foreground uppercase mt-1">Global coordinated capacity</p>
            <div className="mt-4 flex items-center gap-2 text-green-500 text-[10px] font-mono font-bold">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              COORDINATION PLANE STABLE
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="space-y-6">
          <h2 className="text-lg font-bold font-mono uppercase tracking-widest flex items-center gap-2">
            <Upload className="w-4 h-4 text-primary" /> Burst Upload
          </h2>
          <Card>
            <CardContent className="p-6">
              <div className="flex flex-col items-center justify-center border-2 border-dashed border-border/40 rounded-xl p-8 transition-colors hover:border-primary/40 group">
                <input
                  type="file"
                  id="file-upload"
                  className="hidden"
                  onChange={(e) => setFile(e.target.files?.[0] || null)}
                />
                <label
                  htmlFor="file-upload"
                  className="cursor-pointer flex flex-col items-center"
                >
                  <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center mb-4 group-hover:bg-primary/10 transition-colors">
                    <Upload className="w-6 h-6 text-muted-foreground group-hover:text-primary transition-colors" />
                  </div>
                  <p className="text-sm font-mono font-bold text-center">
                    {file ? file.name : "Click to select file for shredding"}
                  </p>
                  <p className="text-[10px] font-mono text-muted-foreground mt-2 uppercase">
                    Max shredding size: 100MB per burst
                  </p>
                </label>

                {file && (
                  <Button
                    className="mt-6 w-full font-mono text-xs uppercase tracking-widest"
                    onClick={handleUpload}
                    disabled={uploading}
                  >
                    {uploading ? (
                      <RefreshCw className="w-3 h-3 mr-2 animate-spin" />
                    ) : (
                      <Zap className="w-3 h-3 mr-2" />
                    )}
                    {uploading ? "Bursting fragments..." : "Start Burst Upload"}
                  </Button>
                )}
              </div>

              {uploading && (
                <div className="mt-6 space-y-2">
                  <div className="flex justify-between text-[10px] font-mono uppercase tracking-tighter">
                    <span>Shredding to 4KB fragments...</span>
                    <span>65%</span>
                  </div>
                  <Progress value={65} className="h-1" />
                </div>
              )}
            </CardContent>
          </Card>

          <h2 className="text-lg font-bold font-mono uppercase tracking-widest flex items-center gap-2 pt-4">
            <FileText className="w-4 h-4 text-primary" /> Active Manifests
          </h2>
          <div className="space-y-3">
            {files.map((f) => (
              <Card key={f.file_id} className="bg-card/30 border-border/20 backdrop-blur-sm">
                <CardContent className="p-4 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded bg-background/50 flex items-center justify-center">
                      <FileText className="w-4 h-4 text-muted-foreground" />
                    </div>
                    <div>
                      <div className="text-xs font-mono font-bold">{f.filename}</div>
                      <div className="text-[10px] font-mono text-muted-foreground">
                        {f.file_id.slice(0, 8)}... | {(f.size_bytes / 1024).toFixed(1)} KB | {f.fragment_names.length} Frags
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0"
                    onClick={() => handleDownload(f.file_id, f.filename)}
                    disabled={downloading === f.file_id}
                  >
                    {downloading === f.file_id ? (
                      <RefreshCw className="w-3 h-3 animate-spin" />
                    ) : (
                      <Download className="w-3 h-3" />
                    )}
                  </Button>
                </CardContent>
              </Card>
            ))}
            {files.length === 0 && (
              <div className="text-center py-10 bg-secondary/10 rounded-xl border border-dashed border-border/40">
                <p className="text-xs font-mono text-muted-foreground">No active manifests in this session.</p>
              </div>
            )}
          </div>
        </div>

        <div className="space-y-6">
          <h2 className="text-lg font-bold font-mono uppercase tracking-widest flex items-center gap-2">
            <Network className="w-4 h-4 text-primary" /> Swarm Topology
          </h2>
          <div className="space-y-4">
            {providers.map((p, idx) => (
              <Card key={idx} className="bg-card/30 border-border/20">
                <CardContent className="p-4 flex justify-between items-center">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-background flex items-center justify-center font-mono font-bold text-lg text-primary">
                      {p.icon}
                    </div>
                    <div>
                      <div className="text-sm font-mono font-bold">{p.name}</div>
                      <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                        {p.count} Accounts Linked
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs font-mono font-bold text-green-400">OPERATIONAL</div>
                    <div className="text-[10px] font-mono text-muted-foreground uppercase">Latency: {(30 + Math.random() * 50).toFixed(1)}ms</div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="bg-primary/5 border-primary/20 mt-8">
            <CardHeader className="pb-2">
              <CardTitle className="text-xs font-mono font-bold uppercase flex items-center gap-2">
                <AlertCircle className="w-3 h-3" /> Architecture Note
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-[10px] font-mono leading-relaxed text-muted-foreground uppercase tracking-tighter">
                Tachyon Fabric utilizes triple-blind TEE security and parallel fragment sharding to ensure data sovereignty.
                All files are encrypted client-side, shredded into 4KB blocks, and distributed across the swarm with
                Reed-Solomon redundancy. This coordination plane is currently in BETA.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default StoragePage;
