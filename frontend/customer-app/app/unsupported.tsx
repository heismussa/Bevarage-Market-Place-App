import { Text, View } from "react-native";

import { Button } from "@/components/Button";
import { Screen } from "@/components/Screen";
import { useAuth } from "@/lib/auth";

export default function UnsupportedScreen() {
  const { user, logout } = useAuth();

  return (
    <Screen scroll={false}>
      <View className="flex-1 items-center justify-center px-6">
        <Text className="text-center text-2xl font-bold text-foreground">
          This app is for customers
        </Text>
        <Text className="mt-3 text-center text-base text-muted">
          {user
            ? `You are signed in as ${user.full_name}, which is not a customer account. Store owners should use the owner dashboard.`
            : "This account type is not supported here."}
        </Text>
        <Button title="Log out" className="mt-8 w-full" onPress={() => void logout()} />
      </View>
    </Screen>
  );
}
