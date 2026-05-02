import { type LucideIcon } from "lucide-react";
import { Button } from "@/components/ui/button";

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
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`rounded-lg border border-dashed border-border p-8 text-center space-y-3 ${className}`}
    >
      {Icon && (
        <Icon
          className="w-10 h-10 text-muted-foreground/40 mx-auto"
          aria-hidden="true"
        />
      )}
      <p className="font-mono text-sm text-muted-foreground uppercase tracking-wider">
        {title}
      </p>
      {description && (
        <p className="font-mono text-xs text-muted-foreground/70 max-w-sm mx-auto">
          {description}
        </p>
      )}
      {(action || secondaryAction) && (
        <div className="flex items-center justify-center gap-3 flex-wrap">
          {action && (
            action.href ? (
              <a href={action.href}>
                <Button size="sm" className="font-mono gap-2" disabled={action.disabled}>
                  {action.label}
                </Button>
              </a>
            ) : (
              <Button
                size="sm"
                className="font-mono gap-2"
                onClick={action.onClick}
                disabled={action.disabled || action.loading}
              >
                {action.loading ? "Loading…" : action.label}
              </Button>
            )
          )}
          {secondaryAction && (
            secondaryAction.href ? (
              <a href={secondaryAction.href}>
                <Button size="sm" variant="outline" className="font-mono gap-2">
                  {secondaryAction.label}
                </Button>
              </a>
            ) : (
              <Button
                size="sm"
                variant="outline"
                className="font-mono gap-2"
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
