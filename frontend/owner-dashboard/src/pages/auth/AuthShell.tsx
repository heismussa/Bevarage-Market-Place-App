import { Moon, Store as StoreIcon, Sun } from "lucide-react";
import type { ReactNode } from "react";

import { Card } from "@/components/ui/card";
import { useTheme } from "@/lib/theme";

export function AuthShell({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-background p-4">
      <button
        type="button"
        aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        onClick={toggleTheme}
        className="absolute top-4 right-4 rounded-xl border border-border bg-surface p-2 text-foreground hover:bg-surface-muted"
      >
        {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
      </button>
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center justify-center gap-3">
          <div className="rounded-xl bg-primary p-2.5 text-primary-foreground">
            <StoreIcon size={22} />
          </div>
          <div>
            <p className="text-lg font-bold text-foreground">BeverageMart</p>
            <p className="text-xs text-muted">Owner dashboard</p>
          </div>
        </div>
        <Card className="p-6">
          <h1 className="text-xl font-bold text-foreground">{title}</h1>
          {subtitle ? (
            <p className="mt-1 mb-5 text-sm text-muted">{subtitle}</p>
          ) : (
            <div className="mb-5" />
          )}
          {children}
        </Card>
        {footer ? <div className="mt-4 text-center text-sm text-muted">{footer}</div> : null}
      </div>
    </div>
  );
}

export function FormBanner({ message }: { message: string | null | undefined }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="mb-4 rounded-xl border border-danger/30 bg-danger-soft px-3 py-2 text-sm text-danger"
    >
      {message}
    </div>
  );
}
