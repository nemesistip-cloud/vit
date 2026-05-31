import { Link } from "wouter";
import { Button } from "@/components/ui/button";
import { Home, AlertTriangle } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-screen w-full flex items-center justify-center bg-background px-4">
      <div className="text-center max-w-md space-y-6">
        <div className="flex justify-center">
          <div className="rounded-full border border-destructive/30 bg-destructive/10 p-4">
            <AlertTriangle className="h-10 w-10 text-destructive" />
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Error 404</p>
          <h1 className="text-3xl font-bold font-mono tracking-tight">PAGE_NOT_FOUND</h1>
          <p className="text-sm text-muted-foreground font-mono leading-relaxed">
            The requested route does not exist in the VIT Sports Intelligence Network.
            Check the URL or navigate back to the dashboard.
          </p>
        </div>

        <Link href="/dashboard">
          <Button className="font-mono gap-2">
            <Home className="w-4 h-4" />
            Return to Dashboard
          </Button>
        </Link>
      </div>
    </div>
  );
}
