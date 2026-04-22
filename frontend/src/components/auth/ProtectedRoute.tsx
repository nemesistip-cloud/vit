import { Redirect } from "wouter";
import { useAuth } from "@/lib/auth";

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAdmin?: boolean;
  requireSuperAdmin?: boolean;
  requiredPermission?: string;
  requiredAdminRole?: string | string[];
  requiredTier?: string;
}

export function ProtectedRoute({
  children,
  requireAdmin,
  requireSuperAdmin,
  requiredPermission,
  requiredAdminRole,
  requiredTier,
}: ProtectedRouteProps) {
  const { user, isLoading, isAdmin, isSuperAdmin, hasPermission, hasAdminRole, hasTier } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="w-8 h-8 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) return <Redirect to="/login" />;

  if (requireSuperAdmin && !isSuperAdmin) return <Redirect to="/dashboard" />;
  if (requireAdmin && !isAdmin) return <Redirect to="/dashboard" />;
  if (requiredAdminRole && !hasAdminRole(requiredAdminRole)) return <Redirect to="/dashboard" />;
  if (requiredPermission && !hasPermission(requiredPermission)) return <Redirect to="/dashboard" />;
  if (requiredTier && !hasTier(requiredTier)) return <Redirect to="/dashboard" />;

  return <>{children}</>;
}
