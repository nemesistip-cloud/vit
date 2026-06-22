import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  Database,
  Zap,
  ShieldCheck,
  HardDrive,
  Network,
  RefreshCw,
  Upload,
  FileText,
  Download,
  AlertCircle,
  Trash2,
  Search,
  FileImage,
  FileVideo,
  FileAudio,
  FileCode,
  FileArchive,
  FileBadge,
  CheckCircle2,
  CloudOff,
  Cloud,
  FolderOpen,
  ChevronDown,
  ArrowUpDown,
  Clock,
  Info,
  Plus,
  Link as LinkIcon,
  Activity,
  Cpu,
  Server,
} from "lucide-react";

interface TachyonStatus {
  status: string;
  active_nodes: number;
  manifest_count: number;
  total_bytes: number;
  storage_backend: string;
  storage_path: string;
  provider_breakdown: Record<string, number>;
  cloud_enabled: boolean;
  network_bandwidth: string;
}

interface ManifestRow {
  file_id: string;
  filename: string;
  size_bytes: number;
  fragment_count: number;
  created_at: string | null;
  owner_user_id: number | null;
}

interface StorageStats {
  registered_content_items: number;
  total_proofs: number;
  verified_proofs: number;
  open_challenges: number;
  total_stored_bytes: number;
  verification_rate: number;
}

type Tab = 'upload' | 'files' | 'swarm';
type SortKey = 'date' | 'name' | 'size';

interface ProviderConfig {
  gdrive: { configured: boolean; nodes: number };
  dropbox: { configured: boolean; nodes: number };
  onedrive: { configured: boolean; nodes: number };
  disk: { configured: boolean; nodes: number };
}

// ── Link Provider Dialog ──────────────────────────────────────────────────────
type CloudProvider = 'gdrive' | 'dropbox' | 'onedrive';

interface ProviderOption {
  id: CloudProvider;
  label: string;
  letter: string;
  color: string;
  fields: { key: string; label: string; placeholder: string; multiline?: boolean }[];
}

const CLOUD_PROVIDERS: ProviderOption[] = [
  {
    id: 'gdrive',
    label: 'Google Drive',
    letter: 'G',
    color: 'bg-blue-900/50 text-blue-300 border-blue-700/40',
    fields: [
      { key: 'service_account_json', label: 'Service Account JSON', placeholder: '{"type":"service_account",...}', multiline: true },
    ],
  },
  {
    id: 'dropbox',
    label: 'Dropbox',
    letter: 'Db',
    color: 'bg-sky-900/50 text-sky-300 border-sky-700/40',
    fields: [
      { key: 'access_token', label: 'Access Token', placeholder: 'sl.B...' },
      { key: 'refresh_token', label: 'Refresh Token (optional)', placeholder: '' },
      { key: 'app_key', label: 'App Key (optional)', placeholder: '' },
      { key: 'app_secret', label: 'App Secret (optional)', placeholder: '' },
    ],
  },
  {
    id: 'onedrive',
    label: 'OneDrive',
    letter: 'O',
    color: 'bg-indigo-900/50 text-indigo-300 border-indigo-700/40',
    fields: [
      { key: 'client_id', label: 'Client ID', placeholder: 'xxxxxxxx-xxxx-...' },
      { key: 'client_secret', label: 'Client Secret', placeholder: '' },
      { key: 'tenant_id', label: 'Tenant ID', placeholder: 'xxxxxxxx-xxxx-...' },
      { key: 'user_id', label: 'User ID / Email', placeholder: 'user@tenant.onmicrosoft.com' },
    ],
  },
];

function LinkProviderDialog({
  open,
  onClose,
  onLinked,
}: {
  open: boolean;
  onClose: () => void;
  onLinked: () => void;
}) {
  const [selectedProvider, setSelectedProvider] = useState<CloudProvider | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const providerDef = CLOUD_PROVIDERS.find(p => p.id === selectedProvider);

  const handleLink = async () => {
    if (!selectedProvider || !providerDef) return;
    setSaving(true);
    setError(null);
    try {
      const r = await fetch('/api/tachyon/providers/link', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider: selectedProvider, credentials: fields }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw new Error(d.detail || 'Failed to link provider');
      }
      setSuccess(true);
      setTimeout(() => {
        onLinked();
        onClose();
        setSuccess(false);
        setSelectedProvider(null);
        setFields({});
      }, 200);
    } catch (e: any) {
      setError(e?.message || 'Link failed');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose(); }}>
      <DialogContent className="max-w-lg bg-background border-border/60">
        <DialogHeader>
          <DialogTitle className="font-mono text-sm uppercase tracking-widest flex items-center gap-2">
            <Plus className="w-4 h-4 text-primary" /> Link Cloud Provider
          </DialogTitle>
          <DialogDescription className="font-mono text-[10px] text-muted-foreground">
            Connect a cloud storage backend for persistent swarm nodes. Changes take effect on next restart.
          </DialogDescription>
        </DialogHeader>

        {!selectedProvider ? (
          <div className="space-y-2 mt-2">
            {CLOUD_PROVIDERS.map(p => (
              <button
                key={p.id}
                onClick={() => { setSelectedProvider(p.id); setFields({}); setError(null); }}
                className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all hover:border-primary/40 hover:bg-primary/5 ${p.color}`}
              >
                <span className="w-9 h-9 rounded-md flex items-center justify-center font-mono font-bold text-sm border border-current/20 bg-current/10">
                  {p.letter}
                </span>
                <div className="text-left">
                  <div className="text-sm font-mono font-bold">{p.label}</div>
                  <div className="text-[10px] font-mono opacity-70">{p.fields.length} credential{p.fields.length !== 1 ? 's' : ''} required</div>
                </div>
                <ChevronDown className="w-3.5 h-3.5 ml-auto rotate-[-90deg]" />
              </button>
            ))}
          </div>
        ) : (
          <div className="space-y-4 mt-2">
            <button
              onClick={() => { setSelectedProvider(null); setError(null); }}
              className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground hover:text-foreground"
            >
              ← back to provider list
            </button>

            <div className="text-xs font-mono font-bold text-foreground flex items-center gap-2">
              <LinkIcon className="w-3.5 h-3.5 text-primary" /> {providerDef?.label} credentials
            </div>

            {providerDef?.fields.map(f => (
              <div key={f.key} className="space-y-1.5">
                <label className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">{f.label}</label>
                {f.multiline ? (
                  <textarea
                    rows={4}
                    value={fields[f.key] || ''}
                    onChange={e => setFields(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="w-full rounded-md border border-border/50 bg-muted/30 px-3 py-2 text-[11px] font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50 resize-none"
                  />
                ) : (
                  <input
                    type={f.key.toLowerCase().includes('secret') || f.key.toLowerCase().includes('token') ? 'password' : 'text'}
                    value={fields[f.key] || ''}
                    onChange={e => setFields(prev => ({ ...prev, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="w-full rounded-md border border-border/50 bg-muted/30 px-3 py-2 text-[11px] font-mono text-foreground placeholder:text-muted-foreground/40 focus:outline-none focus:border-primary/50"
                  />
                )}
              </div>
            ))}

            {error && (
              <div className="text-[10px] font-mono text-destructive flex items-center gap-1">
                <AlertCircle className="w-3 h-3" /> {error}
              </div>
            )}
            {success && (
              <div className="text-[10px] font-mono text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" /> Provider linked! Restart will activate new nodes.
              </div>
            )}

            <Button
              onClick={handleLink}
              disabled={saving || success}
              className="w-full font-mono text-xs h-9"
            >
              {saving ? <><RefreshCw className="w-3 h-3 mr-1.5 animate-spin" /> Saving…</> : `Link ${providerDef?.label}`}
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  const d = new Date(iso);
  const now = new Date();
  const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return d.toLocaleDateString();
}

function getFileIcon(filename: string) {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (['jpg','jpeg','png','gif','webp','svg','bmp'].includes(ext)) return FileImage;
  if (['mp4','mov','avi','mkv','webm'].includes(ext)) return FileVideo;
  if (['mp3','wav','ogg','flac','aac'].includes(ext)) return FileAudio;
  if (['js','ts','tsx','jsx','py','rs','go','java','cpp','c','html','css','json','yaml','toml'].includes(ext)) return FileCode;
  if (['zip','tar','gz','7z','rar','bz2'].includes(ext)) return FileArchive;
  if (['pdf','doc','docx','xls','xlsx','ppt','pptx'].includes(ext)) return FileBadge;
  return FileText;
}

function getFileTypeColor(filename: string): string {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  if (['jpg','jpeg','png','gif','webp','svg','bmp'].includes(ext)) return 'text-pink-400';
  if (['mp4','mov','avi','mkv','webm'].includes(ext)) return 'text-purple-400';
  if (['mp3','wav','ogg','flac','aac'].includes(ext)) return 'text-yellow-400';
  if (['js','ts','tsx','jsx','py','rs','go','java','cpp','c'].includes(ext)) return 'text-blue-400';
  if (['zip','tar','gz','7z','rar'].includes(ext)) return 'text-orange-400';
  return 'text-muted-foreground';
}

const PROVIDER_ICONS: Record<string, { label: string; color: string; letter: string }> = {
  Disk: { label: 'Local Disk', color: 'bg-slate-700 text-slate-200', letter: 'D' },
  GoogleDrive: { label: 'Google Drive', color: 'bg-blue-900 text-blue-200', letter: 'G' },
  Dropbox: { label: 'Dropbox', color: 'bg-sky-900 text-sky-200', letter: 'Db' },
  OneDrive: { label: 'OneDrive', color: 'bg-indigo-900 text-indigo-200', letter: 'O' },
};

const StoragePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('upload');
  const [status, setStatus] = useState<TachyonStatus | null>(null);
  const [stats, setStats] = useState<StorageStats | null>(null);
  const [manifests, setManifests] = useState<ManifestRow[]>([]);
  const [loadingManifests, setLoadingManifests] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<ManifestRow | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('date');
  const [linkProviderOpen, setLinkProviderOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const progressRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch('/api/tachyon/status');
      if (r.ok) setStatus(await r.json());
    } catch {}
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const r = await fetch('/api/storage/stats');
      if (r.ok) setStats(await r.json());
    } catch {}
  }, []);

  const fetchManifests = useCallback(async () => {
    setLoadingManifests(true);
    try {
      const r = await fetch('/api/tachyon/manifests?limit=200');
      if (r.ok) {
        const data = await r.json();
        setManifests(data.items || []);
      }
    } catch {} finally {
      setLoadingManifests(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    fetchStats();
    const iv = setInterval(fetchStatus, 30000);
    return () => clearInterval(iv);
  }, [fetchStatus, fetchStats]);

  useEffect(() => {
    if (activeTab === 'files') fetchManifests();
  }, [activeTab, fetchManifests]);



  const handleFileSelect = (selected: File | null) => {
    if (!selected) return;
    if (selected.size > 100 * 1024 * 1024) {
      setUploadError('File exceeds 100 MB limit.');
      return;
    }
    setUploadError(null);
    setUploadSuccess(null);
    setFile(selected);
  };

  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setUploadSuccess(null);


    const formData = new FormData();
    formData.append('file', file);

    try {
      const r = await fetch('/api/tachyon/upload', { method: 'POST', body: formData });
      if (!r.ok) throw new Error(await r.text());
      const manifest: ManifestRow = await r.json();
      if (progressRef.current) clearInterval(progressRef.current);
      setUploadProgress(100);
      setUploadSuccess(manifest);
      setFile(null);
      await fetchStatus();
      await fetchStats();
    } catch (err: any) {
      if (progressRef.current) clearInterval(progressRef.current);
      setUploadProgress(10);
      setUploadError(err?.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    setDownloading(fileId);
    try {
      const r = await fetch(`/api/tachyon/download/${fileId}`);
      if (!r.ok) throw new Error('Download failed');
      const blob = await r.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch {} finally {
      setDownloading(null);
    }
  };

  const handleDelete = async (fileId: string) => {
    setDeleting(fileId);
    try {
      const r = await fetch(`/api/tachyon/manifests/${fileId}`, { method: 'DELETE' });
      if (r.ok) {
        setManifests(prev => prev.filter(m => m.file_id !== fileId));
        await fetchStatus();
        await fetchStats();
      }
    } catch {} finally {
      setDeleting(null);
    }
  };

  const filteredManifests = manifests
    .filter(m => m.filename.toLowerCase().includes(search.toLowerCase()))
    .sort((a, b) => {
      if (sortBy === 'name') return a.filename.localeCompare(b.filename);
      if (sortBy === 'size') return b.size_bytes - a.size_bytes;
      return new Date(b.created_at || 0).getTime() - new Date(a.created_at || 0).getTime();
    });

  const backendIsCloud = status?.cloud_enabled;
  const backendLabel = status?.storage_backend || '—';
  const providerBreakdown = status?.provider_breakdown || {};

  const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'upload', label: 'Upload', icon: <Upload className="w-3 h-3" /> },
    { key: 'files', label: 'My Files', icon: <FolderOpen className="w-3 h-3" /> },
    { key: 'swarm', label: 'Swarm', icon: <Network className="w-3 h-3" /> },
  ];

  return (
    <div className="container mx-auto p-6 space-y-6 pb-24 max-w-6xl">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight font-mono uppercase flex items-center gap-3">
            <Zap className="w-7 h-7 text-primary" />
            Tachyon VESS Swarm
          </h1>
          <p className="text-muted-foreground mt-1 font-mono text-xs tracking-wide">
            Reed-Solomon erasure-coded swarm storage — fragments distributed across {status?.active_nodes ?? '…'} nodes
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-[10px] font-mono font-bold border ${
            status?.status === 'operational'
              ? 'border-green-500/30 bg-green-500/10 text-green-400'
              : 'border-yellow-500/30 bg-yellow-500/10 text-yellow-400'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${status?.status === 'operational' ? 'bg-green-400 animate-pulse' : 'bg-yellow-400'}`} />
            {status?.status?.toUpperCase() ?? 'CONNECTING'}
          </div>
          <Button variant="outline" size="sm" onClick={() => { fetchStatus(); fetchStats(); }} className="font-mono text-xs h-8">
            <RefreshCw className="w-3 h-3 mr-1.5" /> Sync
          </Button>
          <Button size="sm" onClick={() => setLinkProviderOpen(true)} className="font-mono text-xs h-8 bg-primary text-primary-foreground hover:bg-primary/90">
            <Plus className="w-3 h-3 mr-1.5" /> Link Provider
          </Button>
        </div>
      </div>

      {/* ── Stats Row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-1">
              <Database className="w-3 h-3" /> Total Files
            </div>
            <div className="text-2xl font-bold font-mono">{status?.manifest_count ?? '—'}</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
              {stats?.registered_content_items != null ? `${stats.registered_content_items} objects registered` : 'loading…'}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-1">
              <HardDrive className="w-3 h-3" /> Total Stored
            </div>
            <div className="text-2xl font-bold font-mono">
              {status?.total_bytes != null ? formatBytes(status.total_bytes) : '—'}
            </div>
            <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
              {stats?.total_stored_bytes != null ? `${formatBytes(stats.total_stored_bytes)} verified` : 'loading…'}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-1">
              <Network className="w-3 h-3" /> Nodes
            </div>
            <div className="text-2xl font-bold font-mono">{status?.active_nodes ?? '—'}</div>
            <div className="text-[10px] font-mono text-muted-foreground mt-0.5">
              {status?.network_bandwidth ?? '…'} coord capacity
            </div>
          </CardContent>
        </Card>

        <Card className={`border-border/40 ${backendIsCloud ? 'bg-primary/5 border-primary/20' : 'bg-card/50'}`}>
          <CardContent className="p-4">
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest mb-1 flex items-center gap-1">
              {backendIsCloud ? <Cloud className="w-3 h-3 text-primary" /> : <CloudOff className="w-3 h-3" />}
              Backend
            </div>
            <div className="text-sm font-bold font-mono leading-tight">
              {backendIsCloud ? 'Cloud' : 'Disk'}
            </div>
            <div className="text-[10px] font-mono text-muted-foreground mt-0.5 truncate" title={backendLabel}>
              {backendLabel}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── EEC Recovery + Swarm + Throughput ──────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {/* EEC Recovery */}
        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-primary uppercase tracking-widest font-bold">
              <Zap className="w-3 h-3" /> EEC Recovery
            </div>
            <div className="text-xl font-bold font-mono uppercase tracking-tight">Reed-Solomon</div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              Multi-Fragment Fault Tolerance Active
            </div>
            <Progress value={status?.status === 'operational' ? 100 : 40} className="h-1.5 mt-1" />
          </CardContent>
        </Card>

        {/* Managed Swarm */}
        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground uppercase tracking-widest font-bold">
              <Server className="w-3 h-3" /> Managed Swarm
            </div>
            <div className="text-xl font-bold font-mono">{status?.active_nodes ?? '…'} Providers</div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              Parallel Burst Transfer Active
            </div>
            <div className="flex gap-1.5 flex-wrap mt-1">
              {Object.entries(providerBreakdown).map(([kind, count]) => {
                const letter = kind === 'GoogleDrive' ? 'G' : kind === 'Dropbox' ? 'Db' : kind === 'OneDrive' ? 'O' : 'D';
                const color = kind === 'GoogleDrive' ? 'bg-blue-900/60 text-blue-300 border-blue-700/30' :
                  kind === 'Dropbox' ? 'bg-sky-900/60 text-sky-300 border-sky-700/30' :
                  kind === 'OneDrive' ? 'bg-indigo-900/60 text-indigo-300 border-indigo-700/30' :
                  'bg-slate-800 text-slate-300 border-slate-600/30';
                return (
                  <span key={kind} className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-bold border ${color}`}>
                    {letter}: {count}
                  </span>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Network Throughput */}
        <Card className="border-border/40 bg-card/50">
          <CardContent className="p-4 space-y-2">
            <div className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground uppercase tracking-widest font-bold">
              <Activity className="w-3 h-3" /> Network Throughput
            </div>
            <div className="text-xl font-bold font-mono">{status?.network_bandwidth ?? '—'}</div>
            <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
              Global Coordinated Capacity
            </div>
            <div className={`text-[10px] font-mono font-bold mt-1 ${status?.status === 'operational' ? 'text-green-400' : 'text-yellow-400'}`}>
              ● Coordination Plane {status?.status === 'operational' ? 'Stable' : 'Initialising'}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* ── Tab Nav ────────────────────────────────────────────────────── */}
      <div className="flex gap-1 border-b border-border/30 pb-0">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 text-xs font-mono font-bold uppercase tracking-widest border-b-2 transition-colors ${
              activeTab === t.key
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            {t.icon}
            {t.label}
            {t.key === 'files' && manifests.length > 0 && (
              <span className="ml-1 px-1.5 py-0.5 rounded-full bg-primary/15 text-primary text-[9px]">
                {manifests.length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          TAB: UPLOAD
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'upload' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            {/* Drop zone */}
            <div
              className={`relative border-2 border-dashed rounded-xl p-10 text-center transition-all cursor-pointer ${
                dragOver
                  ? 'border-primary bg-primary/10 scale-[1.01]'
                  : file
                  ? 'border-primary/50 bg-primary/5'
                  : 'border-border/40 hover:border-primary/40 hover:bg-primary/5'
              }`}
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={e => {
                e.preventDefault();
                setDragOver(false);
                handleFileSelect(e.dataTransfer.files[0] ?? null);
              }}
              onClick={() => fileInputRef.current?.click()}
            >
              <input
                ref={fileInputRef}
                type="file"
                className="hidden"
                onChange={e => handleFileSelect(e.target.files?.[0] ?? null)}
              />

              {file ? (
                <div className="space-y-2">
                  {React.createElement(getFileIcon(file.name), { className: `w-10 h-10 mx-auto ${getFileTypeColor(file.name)}` })}
                  <p className="text-sm font-mono font-bold text-foreground">{file.name}</p>
                  <p className="text-[10px] font-mono text-muted-foreground">{formatBytes(file.size)}</p>
                  <Badge variant="outline" className="text-[9px] font-mono uppercase">
                    Ready to shard
                  </Badge>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="w-14 h-14 mx-auto rounded-full bg-secondary flex items-center justify-center">
                    <Upload className="w-7 h-7 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-mono font-bold">Drop file here or click to browse</p>
                    <p className="text-[10px] font-mono text-muted-foreground mt-1 uppercase tracking-wide">
                      Max 100 MB · Any file type · End-to-end sharded
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* Upload controls */}
            {file && !uploading && !uploadSuccess && (
              <div className="flex gap-2">
                <Button
                  className="flex-1 font-mono text-xs uppercase tracking-widest"
                  onClick={handleUpload}
                >
                  <Zap className="w-3 h-3 mr-2" />
                  Start Burst Upload
                </Button>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-9 w-9"
                      onClick={() => { setFile(null); setUploadError(null); }}
                      aria-label="Clear selection"
                    >
                      <Trash2 className="w-3 h-3" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Clear selection</TooltipContent>
                </Tooltip>
              </div>
            )}

            {/* Progress */}
            {uploading && (
              <div className="space-y-2 bg-secondary/20 rounded-lg p-4 border border-border/20">
                <div className="flex justify-between text-[10px] font-mono uppercase tracking-tighter text-muted-foreground">
                  <span>
                    {uploadProgress < 30 ? 'Shredding into 4 KB fragments…'
                      : uploadProgress < 60 ? 'Distributing to swarm nodes…'
                      : uploadProgress < 90 ? 'Applying Reed-Solomon parity…'
                      : 'Persisting manifest to DB…'}
                  </span>
                  <span className="text-primary font-bold">{Math.round(uploadProgress)}%</span>
                </div>
                <Progress value={uploadProgress} className="h-2" />
              </div>
            )}

            {/* Error */}
            {uploadError && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-destructive/10 border border-destructive/20 text-xs font-mono text-destructive">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                {uploadError}
              </div>
            )}

            {/* Success */}
            {uploadSuccess && !uploading && (
              <div className="p-4 rounded-lg bg-green-500/10 border border-green-500/20 space-y-2">
                <div className="flex items-center gap-2 text-green-400 text-xs font-mono font-bold">
                  <CheckCircle2 className="w-4 h-4" />
                  Upload complete — manifest persisted
                </div>
                <div className="text-[10px] font-mono text-muted-foreground space-y-1">
                  <div>File: <span className="text-foreground">{uploadSuccess.filename}</span></div>
                  <div>Size: <span className="text-foreground">{formatBytes(uploadSuccess.size_bytes)}</span></div>
                  <div>Fragments: <span className="text-foreground">{uploadSuccess.fragment_count}</span></div>
                  <div className="font-mono text-[9px] text-muted-foreground/60 break-all">ID: {uploadSuccess.file_id}</div>
                </div>
                <Button variant="outline" size="sm" className="w-full font-mono text-xs mt-1" onClick={() => { setUploadSuccess(null); setActiveTab('files'); }}>
                  <FolderOpen className="w-3 h-3 mr-1.5" /> View in My Files
                </Button>
              </div>
            )}
          </div>

          {/* How it works panel */}
          <div className="space-y-4">
            <h2 className="text-xs font-bold font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-2">
              <Info className="w-3.5 h-3.5" /> The VESS Architecture
            </h2>

            {[
              { step: '01', title: 'Shredding', desc: 'Your file is split into 4 KB fragments. A SHA-3 hash is computed for the whole file.', icon: Zap, color: 'text-yellow-400' },
              { step: '02', title: 'Reed-Solomon Parity', desc: 'Extra parity fragments are generated so the file can be rebuilt even if some nodes fail.', icon: ShieldCheck, color: 'text-green-400' },
              { step: '03', title: 'Burst Distribution', desc: 'All fragments are uploaded in parallel to the swarm — disk nodes or cloud providers.', icon: Network, color: 'text-blue-400' },
              { step: '04', title: 'Manifest Persisted', desc: 'A manifest mapping every fragment to its node is saved to the database — survives restarts.', icon: Database, color: 'text-primary' },
            ].map(s => (
              <div key={s.step} className="flex gap-3 p-3 rounded-lg bg-secondary/20 border border-border/20">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-background border border-border/40 flex items-center justify-center">
                  <s.icon className={`w-3.5 h-3.5 ${s.color}`} />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[9px] font-mono text-muted-foreground">{s.step}</span>
                    <span className="text-xs font-mono font-bold">{s.title}</span>
                  </div>
                  <p className="text-[11px] font-mono text-muted-foreground leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          TAB: MY FILES
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'files' && (
        <div className="space-y-4">
          {/* Toolbar */}
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
              <Input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search files…"
                className="pl-8 h-8 text-xs font-mono"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono text-muted-foreground uppercase">Sort:</span>
              {(['date', 'name', 'size'] as SortKey[]).map(s => (
                <Button
                  key={s}
                  variant={sortBy === s ? 'default' : 'outline'}
                  size="sm"
                  className="h-7 px-2 text-[10px] font-mono uppercase"
                  onClick={() => setSortBy(s)}
                >
                  {s}
                </Button>
              ))}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="icon"
                    className="h-7 w-7"
                    onClick={fetchManifests}
                    aria-label="Refresh file list"
                  >
                    <RefreshCw className={`w-3 h-3 ${loadingManifests ? 'animate-spin' : ''}`} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Refresh file list</TooltipContent>
              </Tooltip>
            </div>
          </div>

          {/* File list */}
          {loadingManifests ? (
            <div className="text-center py-16 text-xs font-mono text-muted-foreground">
              <RefreshCw className="w-5 h-5 mx-auto mb-3 animate-spin" />
              Loading manifests from DB…
            </div>
          ) : filteredManifests.length === 0 ? (
            <div className="text-center py-20 rounded-xl border-2 border-dashed border-border/30 space-y-3">
              <FolderOpen className="w-10 h-10 mx-auto text-muted-foreground/30" />
              <p className="text-xs font-mono text-muted-foreground">
                {search ? `No files matching "${search}"` : 'No files uploaded yet'}
              </p>
              {!search && (
                <Button size="sm" variant="outline" className="font-mono text-xs" onClick={() => setActiveTab('upload')}>
                  <Upload className="w-3 h-3 mr-1.5" /> Upload First File
                </Button>
              )}
            </div>
          ) : (
            <div className="space-y-1.5">
              {/* Header row */}
              <div className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-3 px-4 py-1.5 text-[9px] font-mono text-muted-foreground uppercase tracking-widest">
                <span>File</span>
                <span>Size</span>
                <span>Fragments</span>
                <span className="flex items-center gap-1"><Clock className="w-2.5 h-2.5" /> Date</span>
                <span>Actions</span>
              </div>

              {filteredManifests.map(m => {
                const Icon = getFileIcon(m.filename);
                const iconColor = getFileTypeColor(m.filename);
                return (
                  <div
                    key={m.file_id}
                    className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-3 items-center px-4 py-3 rounded-lg bg-card/30 border border-border/20 hover:border-border/50 hover:bg-card/60 transition-colors group"
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 flex-shrink-0 rounded bg-background/50 flex items-center justify-center">
                        <Icon className={`w-4 h-4 ${iconColor}`} />
                      </div>
                      <div className="min-w-0">
                        <div className="text-xs font-mono font-bold truncate" title={m.filename}>{m.filename}</div>
                        <div className="text-[9px] font-mono text-muted-foreground/60 truncate">{m.file_id.slice(0, 8)}…</div>
                      </div>
                    </div>
                    <div className="text-xs font-mono text-muted-foreground">{formatBytes(m.size_bytes)}</div>
                    <div className="text-xs font-mono text-muted-foreground">{m.fragment_count} frags</div>
                    <div className="text-xs font-mono text-muted-foreground">{formatDate(m.created_at)}</div>
                    <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-foreground"
                            aria-label="Download file"
                            onClick={() => handleDownload(m.file_id, m.filename)}
                            disabled={downloading === m.file_id}
                          >
                            {downloading === m.file_id
                              ? <RefreshCw className="w-3 h-3 animate-spin" />
                              : <Download className="w-3 h-3" />}
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Download file</TooltipContent>
                      </Tooltip>

                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-destructive"
                            aria-label="Delete file"
                            onClick={() => handleDelete(m.file_id)}
                            disabled={deleting === m.file_id}
                          >
                            {deleting === m.file_id
                              ? <RefreshCw className="w-3 h-3 animate-spin" />
                              : <Trash2 className="w-3 h-3" />}
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Delete file</TooltipContent>
                      </Tooltip>
                    </div>
                  </div>
                );
              })}

              <p className="text-[10px] font-mono text-muted-foreground text-center pt-2">
                {filteredManifests.length} file{filteredManifests.length !== 1 ? 's' : ''} · {formatBytes(filteredManifests.reduce((a, m) => a + m.size_bytes, 0))} total
              </p>
            </div>
          )}
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════════
          TAB: SWARM
      ══════════════════════════════════════════════════════════════════ */}
      {activeTab === 'swarm' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-4">
            <h2 className="text-xs font-bold font-mono uppercase tracking-widest text-muted-foreground">
              Active Provider Nodes
            </h2>

            {Object.entries(providerBreakdown).length === 0 ? (
              <p className="text-xs font-mono text-muted-foreground">Loading topology…</p>
            ) : (
              Object.entries(providerBreakdown).map(([kind, count]) => {
                const meta = PROVIDER_ICONS[kind] || { label: kind, color: 'bg-secondary text-foreground', letter: kind[0] };
                const isCloud = kind !== 'Disk';
                return (
                  <Card key={kind} className={`border-border/30 ${isCloud ? 'border-primary/20 bg-primary/5' : 'bg-card/30'}`}>
                    <CardContent className="p-4 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center font-mono font-bold text-sm ${meta.color}`}>
                          {meta.letter}
                        </div>
                        <div>
                          <div className="text-sm font-mono font-bold">{meta.label}</div>
                          <div className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">
                            {count} node{count !== 1 ? 's' : ''} active
                          </div>
                        </div>
                      </div>
                      <div className="text-right space-y-1">
                        <div className={`text-[10px] font-mono font-bold ${isCloud ? 'text-primary' : 'text-green-400'}`}>
                          {isCloud ? '☁ CLOUD' : '● OPERATIONAL'}
                        </div>
                        {!isCloud && (
                          <div className="text-[9px] font-mono text-yellow-500/80 uppercase">
                            Ephemeral — resets on restart
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                );
              })
            )}

            {/* Verification stats */}
            {stats && (
              <Card className="bg-card/30 border-border/20 mt-4">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground flex items-center gap-2">
                    <ShieldCheck className="w-3 h-3" /> Proof Statistics
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-3">
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-muted-foreground">Total proofs</span>
                    <span className="font-bold">{stats.total_proofs}</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-muted-foreground">Verified proofs</span>
                    <span className="font-bold text-green-400">{stats.verified_proofs}</span>
                  </div>
                  <div className="flex justify-between text-xs font-mono">
                    <span className="text-muted-foreground">Open challenges</span>
                    <span className={`font-bold ${stats.open_challenges > 0 ? 'text-yellow-400' : 'text-muted-foreground'}`}>
                      {stats.open_challenges}
                    </span>
                  </div>
                  {stats.total_proofs > 0 && (
                    <>
                      <div className="flex justify-between text-[10px] font-mono text-muted-foreground">
                        <span>Verification rate</span>
                        <span>{stats.verification_rate.toFixed(1)}%</span>
                      </div>
                      <Progress value={stats.verification_rate} className="h-1" />
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </div>

          <div className="space-y-4">
            <h2 className="text-xs font-bold font-mono uppercase tracking-widest text-muted-foreground">
              Architecture
            </h2>

            <Card className="bg-card/30 border-border/20">
              <CardContent className="p-5 space-y-4 text-[11px] font-mono text-muted-foreground leading-relaxed">
                <p>
                  <span className="text-foreground font-bold">Verifiable Elastic Storage Swarm (VESS)</span> — Tachyon V2 implements
                  a DePIN-ready swarm. Every fragment is anchored to the VIT Blockchain for cryptographic verification.
                </p>
                <p>
                  <span className="text-foreground font-bold">Reed-Solomon EEC & Lazy Repair</span> — files are split into data
                  and parity shards. If a shard is lost, VESS automatically detects the erasure during reconstruction and
                  triggers an autonomous 'Lazy Repair' to restore swarm redundancy.
                </p>
                <p>
                  <span className="text-foreground font-bold">Burst scheduling</span> — the TachyonScheduler uploads and
                  downloads all fragments concurrently using asyncio, maximizing throughput across all provider nodes.
                </p>
                <p>
                  <span className="text-foreground font-bold">DB-persisted manifests</span> — every upload writes a manifest
                  row to Postgres mapping each fragment name → provider index. This survives restarts and redeploys.
                </p>
                <p>
                  <span className="text-foreground font-bold">Warm in-memory cache</span> — manifests are cached on first
                  access so downloads after a cold start still work without a full DB round-trip per fragment.
                </p>
              </CardContent>
            </Card>

            {/* Cloud setup prompt */}
            {!backendIsCloud && (
              <Card className="bg-yellow-500/5 border-yellow-500/20">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-[10px] font-mono uppercase tracking-widest flex items-center gap-2 text-yellow-400">
                    <AlertCircle className="w-3 h-3" /> Persistent Storage Disabled
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 text-[11px] font-mono text-muted-foreground space-y-2">
                  <p>Currently running on ephemeral disk nodes. All stored files will be lost on the next Render restart.</p>
                  <p className="text-foreground/80">To enable persistent cloud storage, add one of these secrets in the Render dashboard:</p>
                  <ul className="space-y-1 mt-2 text-[10px]">
                    <li><code className="bg-background/50 px-1 rounded">GDRIVE_SERVICE_ACCOUNT_JSON</code> → Google Drive (2 nodes)</li>
                    <li><code className="bg-background/50 px-1 rounded">DROPBOX_ACCESS_TOKEN</code> → Dropbox (2 nodes)</li>
                    <li><code className="bg-background/50 px-1 rounded">ONEDRIVE_CLIENT_ID</code> + <code className="bg-background/50 px-1 rounded">CLIENT_SECRET</code> + <code className="bg-background/50 px-1 rounded">TENANT_ID</code> → OneDrive</li>
                  </ul>
                </CardContent>
              </Card>
            )}

            {backendIsCloud && (
              <Card className="bg-green-500/5 border-green-500/20">
                <CardContent className="p-4 flex items-center gap-3 text-xs font-mono">
                  <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <div>
                    <div className="font-bold text-green-400">Persistent cloud storage active</div>
                    <div className="text-muted-foreground mt-0.5">Files survive restarts and redeploys.</div>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      )}
      <LinkProviderDialog
        open={linkProviderOpen}
        onClose={() => setLinkProviderOpen(false)}
        onLinked={() => { fetchStatus(); fetchStats(); }}
      />
    </div>
  );
};

export default StoragePage;
