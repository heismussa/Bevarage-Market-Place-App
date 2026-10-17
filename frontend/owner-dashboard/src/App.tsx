import {
  formatMoney,
  orderStatusLabel,
  paymentStatusLabel,
} from "@beverage/api";
import { colors } from "@beverage/ui-tokens";
import { LayoutDashboard, Store } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type HealthState =
  | { status: "loading" }
  | { status: "ok"; detail: string }
  | { status: "error"; detail: string };

function Shell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--color-background)] text-[var(--color-foreground)]">
      <aside className="fixed inset-y-0 left-0 hidden w-64 border-r border-[var(--color-border)] bg-[var(--color-surface)] p-5 lg:block">
        <div className="mb-8 flex items-center gap-3">
          <div
            className="rounded-xl p-2 text-white"
            style={{ background: colors.light.primary }}
          >
            <Store size={20} />
          </div>
          <div>
            <p className="font-bold">BeverageMart</p>
            <p className="text-xs text-[var(--color-muted)]">Owner dashboard</p>
          </div>
        </div>
        <nav className="space-y-1">
          <NavLink
            to="/"
            end
            className={({ isActive }) =>
              `flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium ${
                isActive
                  ? "bg-emerald-50 text-emerald-800"
                  : "text-slate-600 hover:bg-slate-50"
              }`
            }
          >
            <LayoutDashboard size={18} />
            Overview
          </NavLink>
        </nav>
      </aside>
      <main className="min-h-screen p-6 lg:pl-72">{children}</main>
    </div>
  );
}

function OverviewPage() {
  const [health, setHealth] = useState<HealthState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { data } = await api.GET("/api/v1/health/");
        if (cancelled) return;
        setHealth({
          status: "ok",
          detail: data?.status ? `API status: ${data.status}` : "API reachable",
        });
      } catch (error) {
        if (cancelled) return;
        setHealth({
          status: "error",
          detail:
            error instanceof Error
              ? error.message
              : "Could not reach the API. Is Docker running?",
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <p className="text-sm text-[var(--color-muted)]">A-01 to A-10 foundation</p>
        <h1 className="mt-1 text-3xl font-bold tracking-tight">Owner dashboard</h1>
        <p className="mt-2 text-sm text-[var(--color-muted)]">
          Shared API client, tokens, formatters and labels are ready. Auth screens
          (A-12+) come next.
        </p>
      </div>

      <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm">
        <h2 className="font-semibold">API connection</h2>
        <p className="mt-2 text-sm text-[var(--color-muted)]">
          {health.status === "loading" && "Checking…"}
          {health.status === "ok" && health.detail}
          {health.status === "error" && health.detail}
        </p>
        <div className="mt-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </section>

      <section className="rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm">
        <h2 className="font-semibold">Shared helpers smoke check</h2>
        <ul className="mt-3 space-y-1 text-sm text-[var(--color-muted)]">
          <li>Money: {formatMoney("1500.00")}</li>
          <li>Order status: {orderStatusLabel("PENDING")}</li>
          <li>
            Payment (cash): {paymentStatusLabel("PENDING", { isCash: true })}
          </li>
          <li>Payment (cancel): {paymentStatusLabel("CANCELLED")}</li>
        </ul>
      </section>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Shell>
        <Routes>
          <Route path="/" element={<OverviewPage />} />
        </Routes>
      </Shell>
    </BrowserRouter>
  );
}
