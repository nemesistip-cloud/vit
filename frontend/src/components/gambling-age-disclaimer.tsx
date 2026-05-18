import { AlertCircle, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { useEffect, useState } from "react";
import { usePublicConfig } from "@/lib/usePublicConfig";

interface GamblingAgeDisclaimerProps {
  isOpen?: boolean;
  onClose?: () => void;
  showOnce?: boolean;
}

/**
 * GamblingAgeDisclaimer Component
 * 
 * Displays a responsible gambling disclaimer and age verification warning.
 * Shows once per session or can be dismissed by the user.
 * 
 * Gap M1: Regulatory compliance for gambling platforms
 */
export function GamblingAgeDisclaimer({
  isOpen = true,
  onClose,
  showOnce = true,
}: GamblingAgeDisclaimerProps) {
  const [open, setOpen] = useState(isOpen);
  const [dismissed, setDismissed] = useState(false);
  const { data: config } = usePublicConfig();

  // Check localStorage to prevent showing multiple times
  useEffect(() => {
    if (showOnce) {
      const lastShown = localStorage.getItem("gambling_disclaimer_shown");
      const today = new Date().toDateString();
      
      if (lastShown === today) {
        setDismissed(true);
        setOpen(false);
      } else {
        localStorage.setItem("gambling_disclaimer_shown", today);
      }
    }
  }, [showOnce]);

  const handleDismiss = () => {
    setOpen(false);
    setDismissed(true);
    onClose?.();
  };

  return (
    <Dialog open={open && !dismissed} onOpenChange={handleDismiss}>
      <DialogContent className="max-w-lg border-amber-500/30 bg-gradient-to-b from-amber-950/40 to-amber-900/20">
        <DialogTitle className="flex items-center gap-2 text-amber-300 text-lg font-bold">
          <AlertCircle className="w-6 h-6 text-amber-400" />
          Responsible Gambling Notice
        </DialogTitle>

        <div className="space-y-4 py-4 text-sm">
          {/* Age Warning */}
          <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4">
            <p className="font-semibold text-amber-300 mb-2">⚠️ Age Restriction</p>
            <p className="text-amber-100">
              You must be at least 18 years old (or the legal gambling age in your jurisdiction) to use prediction markets and make wagers. By continuing, you confirm that you meet this requirement.
            </p>
          </div>

          {/* Risk Warning */}
          <div className="space-y-3">
            <p className="font-semibold text-foreground">Key Points:</p>
            <ul className="space-y-2 text-muted-foreground">
              <li className="flex gap-2">
                <span className="text-amber-400">•</span>
                <span>Sports predictions involve risk of financial loss</span>
              </li>
              <li className="flex gap-2">
                <span className="text-amber-400">•</span>
                <span>Only wager money you can afford to lose</span>
              </li>
              <li className="flex gap-2">
                <span className="text-amber-400">•</span>
                <span>Set personal betting limits and stick to them</span>
              </li>
              <li className="flex gap-2">
                <span className="text-amber-400">•</span>
                <span>Never chase losses or gamble under the influence</span>
              </li>
              <li className="flex gap-2">
                <span className="text-amber-400">•</span>
                <span>Model predictions are not guarantees of outcomes</span>
              </li>
            </ul>
          </div>

          {/* Help Resources */}
          <div className="rounded-lg border border-green-500/30 bg-green-500/10 p-4">
            <p className="font-semibold text-green-300 mb-2">Need Help?</p>
            <p className="text-green-100 text-xs">
              If you or someone you know is struggling with gambling, organizations like{" "}
              <a href="https://www.ncpg.org" target="_blank" rel="noopener noreferrer" className="underline hover:text-green-200">
                NCPG
              </a>
              {" "}and{" "}
              <a href="https://www.gamcare.org.uk" target="_blank" rel="noopener noreferrer" className="underline hover:text-green-200">
                GamCare
              </a>
              {" "}provide free, confidential support.
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            onClick={handleDismiss}
            className="flex-1 bg-amber-600/80 hover:bg-amber-600 text-white"
          >
            I Understand & Accept
          </Button>
          <Button
            onClick={handleDismiss}
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>

        {/* Footer disclaimer */}
        <p className="text-xs text-muted-foreground text-center">
          By using our platform, you agree to our{" "}
          <a href="/terms" className="text-amber-300 hover:underline">
            Terms of Service
          </a>
          {" "}and{" "}
          <a href="/privacy" className="text-amber-300 hover:underline">
            Privacy Policy
          </a>
        </p>
      </DialogContent>
    </Dialog>
  );
}

export default GamblingAgeDisclaimer;
