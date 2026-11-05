import { formatPhoneDisplay } from "@beverage/api";
import { Ionicons } from "@expo/vector-icons";
import { useQuery } from "@tanstack/react-query";
import { useRouter } from "expo-router";
import { Pressable, Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { keys } from "@/lib/query";

export default function ProfileScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const me = useQuery({
    queryKey: keys.me,
    queryFn: async () => unwrap(await api.GET("/api/v1/auth/me/")),
    initialData: user ?? undefined,
  });
  const profile = me.data ?? user;

  return (
    <Screen title="Profile">
      <View className="mb-6 rounded-2xl border border-border bg-surface p-4">
        <Text className="text-lg font-semibold text-foreground">
          {profile?.full_name}
        </Text>
        {profile?.phone ? (
          <Text className="mt-1 text-sm text-muted">
            {formatPhoneDisplay(profile.phone)}
          </Text>
        ) : null}
        {profile?.email ? (
          <Text className="mt-0.5 text-sm text-muted">{profile.email}</Text>
        ) : null}
      </View>

      <Row
        icon="person-outline"
        label="Edit profile"
        onPress={() => router.push("/profile/edit")}
      />
      <Row
        icon="lock-closed-outline"
        label="Change password"
        onPress={() => router.push("/profile/change-password")}
      />
      <Row
        icon="location-outline"
        label="Addresses"
        onPress={() => router.push("/profile/addresses")}
      />
      <Row
        icon="receipt-outline"
        label="Orders"
        onPress={() => router.push("/orders")}
      />
      <Row
        icon="notifications-outline"
        label="Notifications"
        onPress={() => router.push("/notifications")}
      />

      <Button
        title="Log out"
        variant="danger"
        className="mt-8"
        onPress={() => void logout()}
      />
    </Screen>
  );
}

function Row({
  icon,
  label,
  onPress,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      className="mb-2 flex-row items-center gap-3 rounded-2xl border border-border bg-surface px-4 py-4"
    >
      <Ionicons name={icon} size={20} color="#C1E8FF" />
      <Text className="flex-1 text-base font-medium text-foreground">{label}</Text>
      <Ionicons name="chevron-forward" size={18} color="#7DA0CA" />
    </Pressable>
  );
}
