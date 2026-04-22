import { useAuth } from "@/lib/auth";

interface PermissionGateProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  permission?: string;
  adminRole?: string | string[];
  minTier?: string;
  requireAdmin?: boolean;
  requireSuperAdmin?: boolean;
}

export function PermissionGate({
  children,
  fallback = null,
  permission,
  adminRole,
  minTier,
  requireAdmin,
  requireSuperAdmin,
}: PermissionGateProps) {
  const { user, hasPermission, hasAdminRole, hasTier, isAdmin, isSuperAdmin } = useAuth();

  if (!user) return <>{fallback}</>;
  if (requireSuperAdmin && !isSuperAdmin) return <>{fallback}</>;
  if (requireAdmin && !isAdmin) return <>{fallback}</>;
  if (adminRole && !hasAdminRole(adminRole)) return <>{fallback}</>;
  if (permission && !hasPermission(permission)) return <>{fallback}</>;
  if (minTier && !hasTier(minTier)) return <>{fallback}</>;

  return <>{children}</>;
}

export function TierGate({
  minTier,
  children,
  fallback,
}: {
  minTier: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}) {
  return (
    <PermissionGate minTier={minTier} fallback={fallback}>
      {children}
    </PermissionGate>
  );
}
