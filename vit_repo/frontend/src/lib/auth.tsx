import { createContext, useContext, useEffect, useState } from "react";
import { useLocation } from "wouter";
import { useGetMe } from "@/api-client";
import type { User } from "@/api-client/schemas";

const TIER_ORDER: Record<string, number> = {
  viewer: 0, analyst: 1, pro: 2, elite: 3,
};

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  login: (token: string, refreshToken?: string) => void;
  logout: () => void;
  hasPermission: (permission: string) => boolean;
  hasAdminRole: (roles: string | string[]) => boolean;
  hasTier: (minTier: string) => boolean;
  isAdmin: boolean;
  isSuperAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window !== "undefined") {
      return localStorage.getItem("vit_token");
    }
    return null;
  });
  const [, setLocation] = useLocation();

  const { data: user, isLoading, isError } = useGetMe({
    query: {
      enabled: !!token,
      retry: false,
    },
  });

  useEffect(() => {
    if (isError) {
      localStorage.removeItem("vit_token");
      localStorage.removeItem("vit_refresh_token");
      setToken(null);
      setLocation("/login");
    }
  }, [isError, setLocation]);

  useEffect(() => {
    const handle = () => {
      setToken(null);
      setLocation("/login");
    };
    window.addEventListener("vit:logout", handle);
    return () => window.removeEventListener("vit:logout", handle);
  }, [setLocation]);

  const login = (newToken: string, refreshToken?: string) => {
    localStorage.setItem("vit_token", newToken);
    if (refreshToken) localStorage.setItem("vit_refresh_token", refreshToken);
    setToken(newToken);
    setLocation("/dashboard");
  };

  const logout = () => {
    localStorage.removeItem("vit_token");
    localStorage.removeItem("vit_refresh_token");
    setToken(null);
    setLocation("/login");
  };

  const hasPermission = (permission: string): boolean => {
    if (!user) return false;
    const perms = user.permissions ?? [];
    return perms.includes(permission);
  };

  const hasAdminRole = (roles: string | string[]): boolean => {
    if (!user || !user.admin_role) return false;
    const allowed = Array.isArray(roles) ? roles : [roles];
    return allowed.includes(user.admin_role);
  };

  const hasTier = (minTier: string): boolean => {
    if (!user) return false;
    if (user.role === "admin") return true;
    const userLevel = TIER_ORDER[user.subscription_tier ?? "viewer"] ?? 0;
    const requiredLevel = TIER_ORDER[minTier] ?? 0;
    return userLevel >= requiredLevel;
  };

  const isAdmin = !!user && user.role === "admin";
  const isSuperAdmin = !!user && user.admin_role === "super_admin";

  return (
    <AuthContext.Provider
      value={{
        user: user ?? null,
        isLoading: isLoading && !!token,
        login,
        logout,
        hasPermission,
        hasAdminRole,
        hasTier,
        isAdmin,
        isSuperAdmin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
