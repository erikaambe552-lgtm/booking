import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthCtx {
  user: User | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<User>;
  register: (data: Record<string, string>) => Promise<User>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    if (!getToken()) { setUser(null); return; }
    try { setUser(await api<User>("/auth/me/")); }
    catch { setToken(null); setUser(null); }
  }, []);

  useEffect(() => { refresh().finally(() => setReady(true)); }, [refresh]);

  const login = async (username: string, password: string) => {
    const r = await api<{ token: string; user: User }>("/auth/login/", { method: "POST", body: { username, password } });
    setToken(r.token); setUser(r.user); return r.user;
  };
  const register = async (data: Record<string, string>) => {
    const r = await api<{ token: string; user: User }>("/auth/register/", { method: "POST", body: data });
    setToken(r.token); setUser(r.user); return r.user;
  };
  const logout = async () => {
    try { await api("/auth/logout/", { method: "POST" }); } catch { /* token may already be invalid */ }
    setToken(null); setUser(null);
  };

  return <Ctx.Provider value={{ user, ready, login, register, logout, refresh }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth outside AuthProvider");
  return c;
}
