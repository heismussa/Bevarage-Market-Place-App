import "../global.css";

import { QueryClientProvider } from "@tanstack/react-query";
import { Stack, useRootNavigationState, useRouter, useSegments } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import { useEffect } from "react";
import { View } from "react-native";

import { Splash } from "@/components/Splash";
import { AuthProvider, useAuth } from "@/lib/auth";
import { queryClient } from "@/lib/query";
import { ToastProvider } from "@/lib/toast";

void SplashScreen.preventAutoHideAsync();

function RootNavigator() {
  const { status, user, error, retry, logout } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const navigationState = useRootNavigationState();

  useEffect(() => {
    // Our own <Splash/> overlay (same background) takes over from the native one.
    void SplashScreen.hideAsync();
  }, []);

  useEffect(() => {
    if (!navigationState?.key) return;
    if (status === "loading" || status === "error") return;

    const group = segments[0] as string | undefined;
    const inAuth = group === "(auth)";
    const inUnsupported = group === "unsupported";

    if (status === "unauthenticated") {
      if (!inAuth) router.replace("/login");
      return;
    }

    // Authenticated: only CUSTOMER accounts are supported in this app.
    if (user?.role !== "CUSTOMER") {
      if (!inUnsupported) router.replace("/unsupported");
      return;
    }
    if (inAuth || inUnsupported) router.replace("/");
  }, [navigationState?.key, status, user?.role, segments, router]);

  return (
    <View className="flex-1 bg-background">
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: "#021024" },
        }}
      >
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(app)" />
        <Stack.Screen name="unsupported" />
      </Stack>
      {status === "loading" || status === "error" ? (
        <Splash
          error={status === "error" ? error : null}
          onRetry={() => void retry()}
          onLogout={() => void logout()}
        />
      ) : null}
    </View>
  );
}

export default function RootLayout() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <StatusBar style="light" />
          <RootNavigator />
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
