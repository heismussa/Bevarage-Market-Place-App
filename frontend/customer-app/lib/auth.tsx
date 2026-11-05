import { ApiError, normalizePhone } from "@beverage/api";
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

import {
  api,
  clearTokens,
  hasStoredTokens,
  onSessionExpired,
  saveTokens,
  unwrap,
} from "./api";
import { errorMessage } from "./errors";
import type { Me } from "./types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated" | "error";

export type RegisterInput = {
  full_name: string;
  phone: string;
  password: string;
  email?: string | null;
};

type AuthContextValue = {
  status: AuthStatus;
  user: Me | null;
  /** Set when status === "error" (e.g. server unreachable on startup). */
  error: string | null;
  login: (phone: string, password: string) => Promise<Me>;
  /** Registers a CUSTOMER and logs in. `loggedIn:false` means the account exists but login failed. */
  register: (input: RegisterInput) => Promise<{ loggedIn: boolean }>;
  logout: () => Promise<void>;
  /** Retry the startup session check. */
  retry: () => Promise<void>;
  setUser: (user: Me) => void;
  /** Store a fresh token pair, e.g. after password change. */
  replaceTokens: (tokens: { access: string; refresh: string }) => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

function requirePhone(raw: string): string {
  const phone = normalizePhone(raw);
  if (!phone) {
    throw new ApiError("VALIDATION_ERROR", "Enter a valid phone number.", 400, {
      phone: ["Enter a valid phone number."],
    });
  }
  return phone;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthStatus>("loading");
  const [user, setUserState] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  const retry = useCallback(async () => {
    setStatus("loading");
    setError(null);
    try {
      if (!(await hasStoredTokens())) {
        setStatus("unauthenticated");
        return;
      }
      const me = unwrap(await api.GET("/api/v1/auth/me/"));
      setUserState(me);
      setStatus("authenticated");
    } catch (e) {
      if (e instanceof ApiError && (e.status === 401 || e.status === 403)) {
        await clearTokens();
        setUserState(null);
        setStatus("unauthenticated");
        return;
      }
      setError(errorMessage(e));
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    void retry();
  }, [retry]);

  useEffect(
    () =>
      onSessionExpired(() => {
        queryClient.clear();
        setUserState(null);
        setStatus("unauthenticated");
      }),
    [queryClient],
  );

  const login = useCallback(
    async (phone: string, password: string) => {
      const tokens = unwrap(
        await api.POST("/api/v1/auth/login/", {
          body: { phone: requirePhone(phone), password },
        }),
      );
      await saveTokens({ access: tokens.access, refresh: tokens.refresh });
      try {
        const me = unwrap(await api.GET("/api/v1/auth/me/"));
        queryClient.clear();
        setUserState(me);
        setStatus("authenticated");
        return me;
      } catch (e) {
        await clearTokens();
        throw e;
      }
    },
    [queryClient],
  );

  const register = useCallback(
    async (input: RegisterInput) => {
      const phone = requirePhone(input.phone);
      const email = input.email?.trim();
      unwrap(
        await api.POST("/api/v1/auth/register/", {
          body: {
            full_name: input.full_name.trim(),
            phone,
            password: input.password,
            email: email ? email : null,
            role: "CUSTOMER",
          },
        }),
      );
      try {
        await login(phone, input.password);
        return { loggedIn: true };
      } catch {
        return { loggedIn: false };
      }
    },
    [login],
  );

  const logout = useCallback(async () => {
    await clearTokens();
    queryClient.clear();
    setUserState(null);
    setStatus("unauthenticated");
  }, [queryClient]);

  const replaceTokens = useCallback(
    async (tokens: { access: string; refresh: string }) => {
      await saveTokens(tokens);
    },
    [],
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      error,
      login,
      register,
      logout,
      retry,
      setUser: setUserState,
      replaceTokens,
    }),
    [status, user, error, login, register, logout, retry, replaceTokens],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
