import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Smartphone, Download, CheckCircle } from "lucide-react";

export default function PWAInstallPage() {
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [isInstalled, setIsCompleted] = useState(false);

  useEffect(() => {
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      setDeferredPrompt(e);
    });

    window.addEventListener('appinstalled', () => {
      setIsCompleted(true);
      setDeferredPrompt(null);
    });
  }, []);

  const handleInstall = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') {
      setDeferredPrompt(null);
    }
  };

  return (
    <div className="max-w-md mx-auto px-4 py-12">
      <Card className="bg-card border-border/50 shadow-2xl">
        <CardHeader className="text-center pb-2">
          <div className="w-16 h-16 bg-cyan-500/10 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Smartphone className="w-8 h-8 text-cyan-400" />
          </div>
          <CardTitle className="text-2xl font-bold">Install VIT Sports</CardTitle>
          <CardDescription>Get the best experience on your mobile device</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6 pt-4 text-center">
          <ul className="text-sm text-zinc-400 space-y-3 text-left">
            <li className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>Offline access to live scores and predictions</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>Push notifications for high-edge bets</span>
            </li>
            <li className="flex items-start gap-3">
              <CheckCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
              <span>Faster loading with reduced data usage</span>
            </li>
          </ul>

          {isInstalled ? (
            <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl">
              <p className="text-emerald-400 font-medium">App Installed Successfully!</p>
            </div>
          ) : deferredPrompt ? (
            <Button
              className="w-full h-12 bg-cyan-600 hover:bg-cyan-500 text-lg font-bold"
              onClick={handleInstall}
            >
              <Download className="w-5 h-5 mr-2" />
              Install Now
            </Button>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-zinc-500">
                To install, tap your browser's menu and select <strong>"Add to Home Screen"</strong> or <strong>"Install App"</strong>.
              </p>
              <div className="text-xs p-3 bg-muted/30 rounded-lg text-zinc-400 italic">
                PWA support detected. If the button didn't appear, you may already have the app or your browser requires manual install.
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
