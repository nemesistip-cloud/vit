import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Link } from "wouter";

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
  const padY   = size === "sm" ? "py-6"  : size === "lg" ? "py-16" : "py-10";
  const iconSz = size === "sm" ? "w-8 h-8" : size === "lg" ? "w-14 h-14" : "w-10 h-10";
  const iconBg = size === "sm" ? "p-2.5" : size === "lg" ? "p-5" : "p-3.5";

  return (
    <div
      className={`rounded-xl border border-dashed border-border/50 ${padY} px-6 text-center space-y-3 bg-card/20 ${className}`}
    >
      {Icon && (
        <div className={`inline-flex ${iconBg} rounded-xl bg-muted/20 mb-1`}>
          <Icon className={`${iconSz} text-muted-foreground/30`} aria-hidden="true" />
        </div>
      )}
      <p className="font-mono text-sm font-medium text-foreground/70">
        {title}
      </p>
      {description && (
        <p className="font-mono text-xs text-muted-foreground/60 max-w-xs mx-auto leading-relaxed">
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3 flex-wrap pt-1">
          {action && (
            action.href ? (
              <Link href={action.href}>
                <Button size="sm" className="font-mono gap-2 text-xs" disabled={action.disabled}>
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
