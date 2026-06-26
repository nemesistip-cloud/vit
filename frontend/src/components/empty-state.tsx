import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
    disabled?: boolean;
    loading?: boolean;
  };
  secondaryAction?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  className?: string;
  size?: "sm" | "md" | "lg";
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className = "",
  size = "md",
}: EmptyStateProps) {
  const padY   = size === "sm" ? "py-8"  : size === "lg" ? "py-16" : "py-12";
  const iconSz = size === "sm" ? "w-8 h-8" : size === "lg" ? "w-14 h-14" : "w-10 h-10";
  const iconPad = size === "sm" ? "p-2.5" : size === "lg" ? "p-4" : "p-3";

  return (
    <div
      className={cn(
        "rounded-xl border border-dashed border-border/60",
        "bg-card/30 text-center space-y-3 px-6",
        padY,
        className
      )}
    >
      {Icon && (
        <div className={cn("inline-flex rounded-xl bg-muted/30 mb-1", iconPad)}>
          <Icon className={cn(iconSz, "text-muted-foreground/50")} aria-hidden="true" />
        </div>
      )}

      <p className="font-mono text-sm font-semibold text-foreground/80">
        {title}
      </p>

      {description && (
        <p className="font-mono text-xs text-muted-foreground/70 max-w-xs mx-auto leading-relaxed">
          {description}
        </p>
      )}

      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3 flex-wrap pt-2">
          {action && (
            action.href ? (
              <Link href={action.href}>
                <Button
                  size="sm"
                  className="font-mono gap-2 text-xs"
                  disabled={action.disabled}
                >
                  {action.label}
                </Button>
              </Link>
            ) : (
              <Button
                size="sm"
                className="font-mono gap-2 text-xs"
                onClick={action.onClick}
                disabled={action.disabled || action.loading}
              >
                {action.loading && (
                  <span className="w-3 h-3 rounded-full border-2 border-current border-t-transparent animate-spin" />
                )}
                {action.loading ? "Loading…" : action.label}
              </Button>
            )
          )}

          {secondaryAction && (
            secondaryAction.href ? (
              <Link href={secondaryAction.href}>
                <Button size="sm" variant="outline" className="font-mono gap-2 text-xs">
                  {secondaryAction.label}
                </Button>
              </Link>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="font-mono gap-2 text-xs"
                onClick={secondaryAction.onClick}
              >
                {secondaryAction.label}
              </Button>
            )
          )}
        </div>
      )}
    </div>
  );
}
