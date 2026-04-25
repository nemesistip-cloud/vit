import { Redirect } from "wouter";
import { useAuth } from "@/lib/auth";
import { AISourcesTab } from "@/pages/admin";
import { Brain } from "lucide-react";

export default function AISourcesPage() {
  const { user, hasTier, isAdmin } = useAuth();

  if (!user) return <Redirect to="/login" />;

  // Allow admins OR analyst+ tier
  if (!isAdmin && !hasTier("analyst")) {
    return <Redirect to="/subscription" />;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white p-4 md:p-6">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6 flex items-center gap-3">
          <Brain className="w-7 h-7 text-cyan-400" />
          <div>
            <h1 className="text-2xl font-bold">AI Sources</h1>
            <p className="text-sm text-gray-400">
              Upload raw Claude / Grok / ChatGPT analysis match-by-match to
              feed the prediction ensemble.
            </p>
          </div>
        </div>
        <AISourcesTab />
      </div>
    </div>
  );
}
