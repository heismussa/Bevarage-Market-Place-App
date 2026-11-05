import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router";

import { AppLayout } from "@/components/AppLayout";
import { AuthProvider, useAuth } from "@/lib/auth";
import { StoreProvider, useStore } from "@/lib/store";
import { ThemeProvider } from "@/lib/theme";
import { ToastProvider } from "@/lib/toast";
import AnalyticsPage from "@/pages/AnalyticsPage";
import DashboardPage from "@/pages/DashboardPage";
import LowStockPage from "@/pages/LowStockPage";
import OrderDetailPage from "@/pages/OrderDetailPage";
import OrdersPage from "@/pages/OrdersPage";
import ProductsPage from "@/pages/ProductsPage";
import StoreProfilePage from "@/pages/StoreProfilePage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 1,
        refetchOnWindowFocus: false,
        staleTime: 15_000,
      },
    },
  });
}

function FullScreen({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background text-sm text-muted">
      {children}
    </div>
  );
}

function GuestOnly() {
  const { status } = useAuth();
  if (status === "loading") return <FullScreen>Loading…</FullScreen>;
  if (status === "authenticated") return <Navigate to="/" replace />;
  return <Outlet />;
}

function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === "loading") return <FullScreen>Loading…</FullScreen>;
  if (status !== "authenticated") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <Outlet />;
}

function StoreShell() {
  const { stores, isLoading } = useStore();
  const location = useLocation();
  if (isLoading) return <FullScreen>Loading stores…</FullScreen>;
  const onStoreForm = location.pathname.startsWith("/store");
  if (stores.length === 0 && !onStoreForm) {
    return <Navigate to="/store/new" replace />;
  }
  return <AppLayout />;
}

export default function App() {
  const [queryClient] = useState(createQueryClient);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                <Route element={<GuestOnly />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                </Route>
                <Route element={<RequireAuth />}>
                  <Route
                    element={
                      <StoreProvider>
                        <Outlet />
                      </StoreProvider>
                    }
                  >
                    <Route element={<StoreShell />}>
                      <Route path="/" element={<DashboardPage />} />
                      <Route path="/orders" element={<OrdersPage />} />
                      <Route path="/orders/:id" element={<OrderDetailPage />} />
                      <Route path="/products" element={<ProductsPage />} />
                      <Route path="/low-stock" element={<LowStockPage />} />
                      <Route path="/analytics" element={<AnalyticsPage />} />
                      <Route path="/store" element={<StoreProfilePage />} />
                      <Route path="/store/new" element={<StoreProfilePage create />} />
                    </Route>
                  </Route>
                </Route>
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
