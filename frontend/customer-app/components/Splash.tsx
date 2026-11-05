import { ActivityIndicator, Text, View } from "react-native";

import { Button } from "./Button";

type SplashProps = {
  error?: string | null;
  onRetry?: () => void;
  onLogout?: () => void;
};

/** Full-screen overlay shown while the session is being restored. */
export function Splash({ error, onRetry, onLogout }: SplashProps) {
  return (
    <View
      className="items-center justify-center bg-background px-8"
      style={{ position: "absolute", top: 0, left: 0, right: 0, bottom: 0 }}
    >
      <Text className="text-4xl font-bold text-foreground">BeverageMart</Text>
      <Text className="mt-2 text-base text-muted">Drinks delivered, fast.</Text>
      {error ? (
        <View className="mt-8 w-full items-center">
          <Text className="mb-4 text-center text-sm text-danger">{error}</Text>
          {onRetry ? <Button title="Try again" onPress={onRetry} className="w-full" /> : null}
          {onLogout ? (
            <Button
              title="Log out"
              variant="ghost"
              onPress={onLogout}
              className="mt-2 w-full"
            />
          ) : null}
        </View>
      ) : (
        <ActivityIndicator className="mt-8" size="large" color="#C1E8FF" />
      )}
    </View>
  );
}
