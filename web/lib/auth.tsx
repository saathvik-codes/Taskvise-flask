"use client";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, type User } from "./api";

type AuthState = { user: User | null; loading: boolean; login: (username: string, password: string) => Promise<User>; logout: () => Promise<void>; refresh: () => Promise<void> };
const Ctx = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try { setUser((await api<{ user: User }>("/api/auth/me")).user); } catch { setUser(null); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);

  const value = useMemo<AuthState>(() => ({
    user, loading, refresh,
    login: async (username, password) => { const r = await api<{ user: User }>("/api/auth/login", { body: { username, password } }); setUser(r.user); return r.user; },
    logout: async () => { await api("/api/auth/logout", { method: "POST", body: {} }).catch(() => {}); setUser(null); },
  }), [user, loading, refresh]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
export const useAuth = () => { const v = useContext(Ctx); if (!v) throw new Error("AuthProvider missing"); return v; };
