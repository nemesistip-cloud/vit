import { useState } from "react";
import { Brain, Coins, Target, X, ChevronRight, Check, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

/* ============================================================
   ON1: Welcome Modal (shown after registration)
   ON2: Interactive Tour (3 steps)
   ============================================================ */

interface WelcomeModalProps {
  username: string;
  onClose: () => void;
  onStartTour: () => void;
}

export function WelcomeModal({ username, onClose, onStartTour }: WelcomeModalProps) {
  const [celebrating, setCelebrating] = useState(false);

  const handleStart = () => {
    setCelebrating(true);
    setTimeout(() => {
      onStartTour();
    }, 600);
  };

  return (
    <div className="fixed inset-0 z-[400] flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" onClick={onClose} />
      <div className={`relative bg-card border border-border rounded-2xl max-w-md w-full p-8 shadow-2xl vit-animate-scale-in ${celebrating ? "vit-animate-celebrate" : ""}`}>
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-muted-foreground hover:text-foreground transition-colors"
        >
          <X className="w-4 h-4" />
        </button>

        {/* Celebration particles */}
        {celebrating && (
          <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-2xl">
            {Array.from({ length: 12 }).map((_, i) => (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full"
                style={{
                  background: i % 3 === 0 ? "#00f5ff" : i % 3 === 1 ? "#ffd700" : "#a855f7",
                  left: `${Math.random() * 100}%`,
                  top: `${Math.random() * 100}%`,
                  animation: `vit-float ${1 + Math.random()}s ease-in-out infinite`,
                  animationDelay: `${Math.random() * 0.5}s`,
                }}
              />
            ))}
          </div>
        )}

        <div className="text-center">
          {/* Icon */}
          <div className="relative inline-flex mb-6">
            <div className="w-20 h-20 bg-primary/10 border-2 border-primary/30 rounded-2xl flex items-center justify-center vit-glow-cyan">
              <Sparkles className="w-10 h-10 text-primary" />
            </div>
            <span className="absolute -top-2 -right-2 text-2xl">🎉</span>
          </div>

          <h2 className="text-2xl font-bold font-mono mb-2">
            Welcome, <span className="text-primary">{username}</span>!
          </h2>
          <p className="text-muted-foreground text-sm mb-4 leading-relaxed">
            Your account is active and your wallet has been funded with a{" "}
            <span className="text-secondary font-bold">100 VIT welcome bonus</span>.
          </p>

          <div className="grid grid-cols-3 gap-3 mb-6">
            {[
              { icon: Brain,  label: "12 AI Models", color: "text-primary"  },
              { icon: Coins,  label: "100 VIT Bonus", color: "text-secondary" },
              { icon: Target, label: "First Prediction", color: "text-purple-400" },
            ].map(({ icon: Icon, label, color }) => (
              <div key={label} className="bg-background/50 rounded-lg p-3 border border-border/50">
                <Icon className={`w-5 h-5 ${color} mx-auto mb-1`} />
                <div className="text-[10px] font-mono text-muted-foreground text-center leading-tight">{label}</div>
              </div>
            ))}
          </div>

          <div className="flex flex-col gap-2">
            <Button onClick={handleStart} className="w-full font-mono gap-2 h-11">
              Take the 3-Step Tour
              <ChevronRight className="w-4 h-4" />
            </Button>
            <Button variant="ghost" onClick={onClose} className="w-full font-mono text-xs text-muted-foreground">
              Skip, go to dashboard
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── ON2: Interactive Tour ────────────────────────────── */

interface TourStep {
  step: number;
  icon: React.ElementType;
  title: string;
  description: string;
  action: string;
  color: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    step: 1,
    icon: Target,
    title: "Make Your First Prediction",
    description: "Browse live matches, tap a match card, and place your first AI-assisted prediction. Our ensemble of 12 models will show you their confidence before you commit.",
    action: "Go to Matches",
    color: "text-primary",
  },
  {
    step: 2,
    icon: Brain,
    title: "View AI Ensemble Breakdown",
    description: "After selecting a match, expand the 'AI Transparency' panel to see how each of the 12 models voted, their individual confidence, and historical accuracy.",
    action: "View AI Details",
    color: "text-purple-400",
  },
  {
    step: 3,
    icon: Coins,
    title: "Check Your Wallet & Rewards",
    description: "Your 100 VIT welcome bonus is ready. Track your balance, view transaction history, and stake VIT on predictions to earn rewards.",
    action: "Open Wallet",
    color: "text-secondary",
  },
];

interface TourProps {
  onComplete: () => void;
  onSkip: () => void;
  onNavigate: (path: string) => void;
}

export function OnboardingTour({ onComplete, onSkip, onNavigate }: TourProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const step = TOUR_STEPS[currentStep];
  const isLast = currentStep === TOUR_STEPS.length - 1;

  const PATHS = ["/matches", "/matches", "/wallet"];

  const handleAction = () => {
    onNavigate(PATHS[currentStep]);
    if (isLast) {
      onComplete();
    } else {
      setCurrentStep((s) => s + 1);
    }
  };

  return (
    <div className="fixed inset-0 z-[400] flex items-end sm:items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onSkip} />
      <div className="relative bg-card border border-border rounded-2xl max-w-sm w-full p-6 shadow-2xl vit-animate-slide-up">

        {/* Progress */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex gap-1.5">
            {TOUR_STEPS.map((_, i) => (
              <div
                key={i}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  i === currentStep ? "w-8 bg-primary" : i < currentStep ? "w-4 bg-primary/40" : "w-4 bg-muted"
                }`}
              />
            ))}
          </div>
          <button onClick={onSkip} className="text-muted-foreground hover:text-foreground transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Step indicator */}
        <Badge className="mb-4 font-mono text-xs border-border/50 bg-muted/50 text-muted-foreground">
          Step {step.step} of {TOUR_STEPS.length}
        </Badge>

        {/* Icon */}
        <div className={`w-12 h-12 rounded-xl bg-background border border-border flex items-center justify-center mb-4`}>
          <step.icon className={`w-6 h-6 ${step.color}`} />
        </div>

        <h3 className="text-lg font-bold font-mono mb-2">{step.title}</h3>
        <p className="text-sm text-muted-foreground mb-6 leading-relaxed">{step.description}</p>

        <div className="flex flex-col gap-2">
          <Button onClick={handleAction} className="w-full font-mono gap-2">
            {isLast ? (
              <>
                <Check className="w-4 h-4" />
                Complete Tour
              </>
            ) : (
              <>
                {step.action}
                <ChevronRight className="w-4 h-4" />
              </>
            )}
          </Button>
          {!isLast && (
            <Button
              variant="ghost"
              onClick={() => setCurrentStep((s) => s + 1)}
              className="w-full font-mono text-xs text-muted-foreground"
            >
              Skip this step
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── ON3: First Prediction Quick Flow ─────────────────── */

const PRESET_STAKES = [5, 10, 25, 50];

interface FirstPredictionFlowProps {
  match: { home: string; away: string; homeConf: number; awayConf: number; drawConf: number };
  onConfirm: (side: string, stake: number) => void;
  onClose: () => void;
}

export function FirstPredictionFlow({ match, onConfirm, onClose }: FirstPredictionFlowProps) {
  const [selected, setSelected] = useState<string | null>(null);
  const [stake, setStake] = useState(10);
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = () => {
    if (!selected) return;
    setConfirmed(true);
    setTimeout(() => {
      onConfirm(selected, stake);
    }, 1500);
  };

  if (confirmed) {
    return (
      <div className="fixed inset-0 z-[400] flex items-center justify-center p-4">
        <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />
        <div className="relative bg-card border border-primary/40 rounded-2xl max-w-sm w-full p-8 text-center shadow-2xl vit-glow-cyan vit-animate-scale-in">
          <div className="text-5xl mb-4">🎯</div>
          <h3 className="text-xl font-bold font-mono text-primary mb-2">Prediction Placed!</h3>
          <p className="text-sm text-muted-foreground">
            <span className="text-foreground font-medium">{stake} VIT</span> staked on{" "}
            <span className="text-primary font-medium">{selected}</span>
          </p>
          <p className="text-xs text-muted-foreground mt-2 font-mono">Settling after match...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-[400] flex items-end sm:items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-card border border-border rounded-2xl max-w-sm w-full shadow-2xl vit-animate-slide-up overflow-hidden">
        <div className="p-6 border-b border-border">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-mono text-muted-foreground uppercase">Your First Prediction</span>
            <button onClick={onClose}><X className="w-4 h-4 text-muted-foreground" /></button>
          </div>
          <h3 className="font-bold font-mono text-foreground">{match.home} vs {match.away}</h3>
        </div>

        <div className="p-6 space-y-5">
          {/* Outcome selection */}
          <div>
            <div className="text-xs font-mono text-muted-foreground uppercase mb-3">Select Outcome</div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { side: match.home, conf: match.homeConf, label: "Home" },
                { side: "Draw",     conf: match.drawConf, label: "Draw" },
                { side: match.away, conf: match.awayConf, label: "Away" },
              ].map(({ side, conf, label }) => (
                <button
                  key={side}
                  onClick={() => setSelected(side)}
                  className={`rounded-lg border p-3 text-center transition-all duration-200 ${
                    selected === side
                      ? "border-primary/60 bg-primary/10 shadow-sm vit-glow-cyan"
                      : "border-border bg-background/50 hover:border-border"
                  }`}
                >
                  <div className="text-[10px] font-mono text-muted-foreground uppercase">{label}</div>
                  <div className="text-sm font-bold font-mono truncate">{side}</div>
                  <div className={`text-xs font-mono mt-1 ${conf >= 70 ? "text-primary" : "text-muted-foreground"}`}>
                    {conf}% AI
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* Stake slider */}
          <div>
            <div className="flex items-center justify-between mb-3">
              <div className="text-xs font-mono text-muted-foreground uppercase">Stake (VIT)</div>
              <div className="text-sm font-bold font-mono text-secondary">{stake} VIT</div>
            </div>
            <input
              type="range"
              min={1}
              max={100}
              value={stake}
              onChange={(e) => setStake(Number(e.target.value))}
              className="w-full accent-primary h-1.5 rounded-full"
            />
            <div className="flex gap-2 mt-3">
              {PRESET_STAKES.map((p) => (
                <button
                  key={p}
                  onClick={() => setStake(p)}
                  className={`flex-1 text-xs font-mono rounded py-1 border transition-all ${
                    stake === p ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:border-border/80"
                  }`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>

          {/* Confirm */}
          <Button
            className="w-full font-mono h-11"
            disabled={!selected}
            onClick={handleConfirm}
          >
            {selected
              ? `Confirm: ${stake} VIT on ${selected}`
              : "Select an outcome"}
          </Button>
        </div>
      </div>
    </div>
  );
}
