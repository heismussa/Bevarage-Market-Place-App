import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps, ReactNode } from "react";
import { ActivityIndicator, Text, View } from "react-native";

import { errorMessage } from "@/lib/errors";

import { Button } from "./Button";

export function LoadingView({ label }: { label?: string }) {
  return (
    <View className="flex-1 items-center justify-center py-16">
      <ActivityIndicator size="large" color="#C1E8FF" />
      {label ? <Text className="mt-3 text-sm text-muted">{label}</Text> : null}
    </View>
  );
}

export function ErrorView({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  return (
    <View className="flex-1 items-center justify-center px-6 py-16">
      <Ionicons name="cloud-offline-outline" size={44} color="#F87171" />
      <Text className="mt-3 text-center text-base text-foreground">
        {errorMessage(error)}
      </Text>
      {onRetry ? (
        <Button title="Try again" variant="secondary" small className="mt-4" onPress={onRetry} />
      ) : null}
    </View>
  );
}

export function EmptyState({
  icon = "file-tray-outline",
  title,
  message,
  action,
}: {
  icon?: ComponentProps<typeof Ionicons>["name"];
  title: string;
  message?: string;
  action?: ReactNode;
}) {
  return (
    <View className="items-center justify-center px-6 py-16">
      <Ionicons name={icon} size={48} color="#7DA0CA" />
      <Text className="mt-3 text-center text-lg font-semibold text-foreground">
        {title}
      </Text>
      {message ? (
        <Text className="mt-1 text-center text-sm text-muted">{message}</Text>
      ) : null}
      {action ? <View className="mt-4">{action}</View> : null}
    </View>
  );
}

export function Banner({
  message,
  tone = "error",
}: {
  message: string;
  tone?: "error" | "warning" | "info";
}) {
  const styles =
    tone === "error"
      ? "border-danger bg-danger/10"
      : tone === "warning"
        ? "border-warning bg-warning/10"
        : "border-border bg-surface";
  const text =
    tone === "error"
      ? "text-danger"
      : tone === "warning"
        ? "text-warning"
        : "text-foreground";
  return (
    <View className={`mb-4 rounded-xl border px-4 py-3 ${styles}`}>
      <Text className={`text-sm ${text}`}>{message}</Text>
    </View>
  );
}
