import { formatPhoneDisplay } from "@beverage/api";
import {
  BarChart3,
  ChevronDown,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Menu,
  Moon,
  Package,
  PackageOpen,
  Plus,
  ShoppingBag,
  Store as StoreIcon,
  Sun,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router";

import { ChangePasswordDialog } from "@/components/ChangePasswordDialog";
import { NotificationsMenu } from "@/components/NotificationsMenu";
import { Badge } from "@/components/ui/badge";
import { Popover } from "@/components/ui/popover";
import { useAuth } from "@/lib/auth";
import { useDashboard } from "@/lib/queries";
import { useStore } from "@/lib/store";
import { useTheme } from "@/lib/theme";
import { useToast } from "@/lib/toast";
import { cn } from "@/lib/utils";

type NavItem = {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
  end?: boolean;
  badge?: number;
  badgeVariant?: "warning" | "danger";
};

function Sidebar({ items, onNavigate }: { items: NavItem[]; onNavigate?: () => void }) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="rounded-xl bg-primary p-2 text-primary-foreground">
          <StoreIcon size={20} />
        </div>
        <div>
          <p className="font-bold">BeverageMart</p>
          <p className="text-xs text-muted">Owner dashboard</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary-soft font-semibold text-foreground"
                  : "text-muted hover:bg-surface-muted hover:text-foreground",
              )
            }
          >
            <item.icon size={18} />
            <span className="flex-1">{item.label}</span>
            {item.badge ? (
              <Badge variant={item.badgeVariant ?? "warning"}>{item.badge}</Badge>
            ) : null}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function StoreSwitcher() {
  const { stores, store, selectStore } = useStore();
  const navigate = useNavigate();

  if (!store) return null;

  return (
    <Popover
      align="left"
      panelClassName="w-64"
      trigger={({ toggle }) => (
        <button
          type="button"
          onClick={toggle}
          className="flex max-w-56 items-center gap-2 rounded-xl border border-border bg-surface px-3 py-2 text-sm font-medium hover:bg-surface-muted"
        >
          <StoreIcon size={16} className="shrink-0 text-primary" />
          <span className="truncate">{store.store_name}</span>
          <ChevronDown size={14} className="shrink-0 text-muted" />
        </button>
      )}
    >
      {({ close }) => (
        <div className="p-1">
          <p className="px-3 py-2 text-xs font-semibold tracking-wide text-muted uppercase">
            Your stores
          </p>
          {stores.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                selectStore(item.id);
                close();
              }}
              className={cn(
                "flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm hover:bg-surface-muted",
                item.id === store.id && "font-semibold text-primary",
              )}
            >
              <span className="truncate">{item.store_name}</span>
              <Badge variant={item.status === "OPEN" ? "success" : "default"}>
                {item.status === "OPEN" ? "Open" : "Closed"}
              </Badge>
            </button>
          ))}
          <button
            type="button"
            onClick={() => {
              close();
              navigate("/store/new");
            }}
            className="mt-1 flex w-full items-center gap-2 rounded-lg border-t border-border px-3 py-2 text-sm text-primary hover:bg-surface-muted"
          >
            <Plus size={14} /> Add another store
          </button>
        </div>
      )}
    </Popover>
  );
}

function ProfileMenu({ onChangePassword }: { onChangePassword: () => void }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const initials = (user?.full_name ?? "?")
    .split(/\s+/)
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <Popover
      panelClassName="w-64"
      trigger={({ toggle }) => (
        <button
          type="button"
          onClick={toggle}
          aria-label="Profile menu"
          className="flex items-center gap-2 rounded-xl p-1.5 hover:bg-surface-muted"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-bold text-primary-foreground">
            {initials}
          </span>
          <ChevronDown size={14} className="hidden text-muted sm:block" />
        </button>
      )}
    >
      {({ close }) => (
        <div>
          <div className="border-b border-border px-4 py-3">
            <p className="truncate font-semibold">{user?.full_name}</p>
            <p className="text-xs text-muted">
              {user?.phone ? formatPhoneDisplay(user.phone) : ""}
            </p>
          </div>
          <div className="p-1">
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-surface-muted"
              onClick={() => {
                close();
                navigate("/store");
              }}
            >
              <StoreIcon size={16} /> Store profile
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm hover:bg-surface-muted"
              onClick={() => {
                close();
                onChangePassword();
              }}
            >
              <KeyRound size={16} /> Change password
            </button>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-danger hover:bg-danger-soft"
              onClick={() => {
                close();
                void logout();
              }}
            >
              <LogOut size={16} /> Log out
            </button>
          </div>
        </div>
      )}
    </Popover>
  );
}

export function AppLayout() {
  const { store } = useStore();
  const { theme, toggleTheme } = useTheme();
  const toast = useToast();
  const location = useLocation();
  const dashboard = useDashboard(store?.id);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [passwordOpen, setPasswordOpen] = useState(false);

  const pending = dashboard.data?.pending_orders ?? 0;
  const lowStock = dashboard.data?.low_stock_count ?? 0;

  // Announce newly arrived PENDING orders found by polling.
  const lastPending = useRef<number | null>(null);
  const lastStoreId = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (!dashboard.data) return;
    if (lastStoreId.current !== store?.id) {
      lastStoreId.current = store?.id;
      lastPending.current = dashboard.data.pending_orders;
      return;
    }
    const previous = lastPending.current;
    if (previous !== null && dashboard.data.pending_orders > previous) {
      toast.info("New order waiting for your response.");
    }
    lastPending.current = dashboard.data.pending_orders;
  }, [dashboard.data, store?.id, toast]);

  // Close the mobile drawer on navigation.
  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const items: NavItem[] = [
    { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
    {
      to: "/orders",
      label: "Orders",
      icon: ShoppingBag,
      badge: pending,
      badgeVariant: "warning",
    },
    { to: "/products", label: "Products", icon: Package },
    {
      to: "/low-stock",
      label: "Low stock",
      icon: PackageOpen,
      badge: lowStock,
      badgeVariant: "danger",
    },
    { to: "/analytics", label: "Sales Analytics", icon: BarChart3 },
    { to: "/store", label: "Store Profile", icon: StoreIcon },
  ];

  return (
    <div className="min-h-screen bg-background text-foreground">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-border bg-sidebar lg:block">
        <Sidebar items={items} />
      </aside>

      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div
            className="absolute inset-0 bg-[var(--color-overlay)]"
            aria-hidden
            onClick={() => setMobileOpen(false)}
          />
          <aside className="relative h-full w-64 border-r border-border bg-sidebar">
            <button
              type="button"
              aria-label="Close menu"
              className="absolute top-4 right-3 rounded-lg p-1 text-muted hover:bg-surface-muted"
              onClick={() => setMobileOpen(false)}
            >
              <X size={18} />
            </button>
            <Sidebar items={items} onNavigate={() => setMobileOpen(false)} />
          </aside>
        </div>
      ) : null}

      <div className="lg:pl-64">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-border bg-sidebar/90 px-4 backdrop-blur sm:px-6">
          <button
            type="button"
            aria-label="Open menu"
            className="rounded-xl p-2 text-foreground hover:bg-surface-muted lg:hidden"
            onClick={() => setMobileOpen(true)}
          >
            <Menu size={20} />
          </button>
          <StoreSwitcher />
          <div className="flex-1" />
          <button
            type="button"
            aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
            onClick={toggleTheme}
            className="rounded-xl p-2 text-foreground hover:bg-surface-muted"
          >
            {theme === "dark" ? <Sun size={20} /> : <Moon size={20} />}
          </button>
          <NotificationsMenu />
          <ProfileMenu onChangePassword={() => setPasswordOpen(true)} />
        </header>
        <main className="mx-auto max-w-7xl p-4 sm:p-6">
          <Outlet />
        </main>
      </div>

      <ChangePasswordDialog open={passwordOpen} onClose={() => setPasswordOpen(false)} />
    </div>
  );
}
