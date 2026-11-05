import { ApiError, getTokenStore } from "@beverage/api";
import { useQueryClient } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { http } from "@/lib/api";
import type { Me, TokenPair } from "@/lib/types";

type AuthStatus = "loading" | "authenticated" | "anonymous";

export type RegisterInput = {
  full_name: string;
  phone: string;
  password: string;
  email?: string | null;
};

type AuthContextValue = {
  status: AuthStatus;
  user: Me | null;
  /** Set when a signed-in account was rejected (e.g. wrong role). */
  notice: string | null;
  login: (phone: string, password: string) => Promise<Me>;
  register: (input: RegisterInput) => Promise<Me>;
  logout: () => Promise<void>;
  changePassword: (current: string, next: string) => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

const NOT_OWNER_MESSAGE =
  "This dashboard is for store owners only. Use the BeverageMart customer app instead.";

async function rejectNonOwner(): Promise<never> {
  await getTokenStore().clear();
  throw new ApiError("PERMISSION_DENIED", NOT_OWNER_MESSAGE, 403);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUser] = useState<Me | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // Session restore: GET /auth/me/ when tokens exist.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const access = await getTokenStore().getAccess();
      const refresh = await getTokenStore().getRefresh();
      if (!access && !refresh) {
        if (!cancelled) setStatus("anonymous");
        return;
      }
      try {
        const me = await http.get<Me>("/api/v1/auth/me/");
        if (cancelled) return;
        if (me.role !== "STORE_OWNER") {
          await getTokenStore().clear();
          setNotice(NOT_OWNER_MESSAGE);
          setStatus("anonymous");
          return;
        }
        setUser(me);
        setStatus("authenticated");
      } catch {
        if (cancelled) return;
        await getTokenStore().clear();
        setStatus("anonymous");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // The shared client emits this when a refresh fails.
  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      setStatus("anonymous");
      setNotice("Your session expired. Please log in again.");
      queryClient.clear();
    };
    window.addEventListener("beverage:session-expired", onExpired);
    return () => window.removeEventListener("beverage:session-expired", onExpired);
  }, [queryClient]);

  const login = useCallback(
    async (phone: string, password: string) => {
      const tokens = await http.post<TokenPair>("/api/v1/auth/login/", {
        body: { phone, password },
      });
      await getTokenStore().setTokens({
        access: tokens.access,
        refresh: tokens.refresh,
      });
      const me = await http.get<Me>("/api/v1/auth/me/");
      if (me.role !== "STORE_OWNER") return rejectNonOwner();
      queryClient.clear();
      setUser(me);
      setNotice(null);
      setStatus("authenticated");
      return me;
    },
    [queryClient],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      await http.post("/api/v1/auth/register/", {
        body: {
          full_name: input.full_name,
          phone: input.phone,
          password: input.password,
          email: input.email ? input.email : null,
          role: "STORE_OWNER",
        },
      });
      return login(input.phone, input.password);
    },
    [login],
  );

  const logout = useCallback(async () => {
    await getTokenStore().clear();
    queryClient.clear();
    setUser(null);
    setNotice(null);
    setStatus("anonymous");
  }, [queryClient]);

  const changePassword = useCallback(async (current: string, next: string) => {
    const tokens = await http.post<TokenPair>("/api/v1/auth/password/change/", {
      body: { current_password: current, new_password: next },
    });
    // Other devices are logged out; keep this one signed in with the fresh tokens.
    await getTokenStore().setTokens({
      access: tokens.access,
      refresh: tokens.refresh,
    });
  }, []);

  const refreshUser = useCallback(async () => {
    const me = await http.get<Me>("/api/v1/auth/me/");
    setUser(me);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      notice,
      login,
      register,
      logout,
      changePassword,
      refreshUser,
    }),
    [status, user, notice, login, register, logout, changePassword, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
